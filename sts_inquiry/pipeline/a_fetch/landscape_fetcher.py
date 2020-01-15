from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Iterator, Tuple, List, Set
from urllib.parse import urljoin

import requests
from lxml import html
from markupsafe import Markup

from sts_inquiry import app
from sts_inquiry.consts import PLAYING_DURATION_CONVERSION
from sts_inquiry.structs import Comment

_STS_URL = app.config["STS_URL"]
_USER_AGENT = app.config["FETCH_USER_AGENT"]

log = logging.getLogger("sts-inquiry")


def fetch_landscape() -> Tuple[List[SuperRegionPrototype], List[RegionPrototype],
                               Set[EdgePrototype], List[StwPrototype]]:
    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT

    log.info(" * Fetching super regions and region rids...")
    superregion_protos, region_protos = _fetch_rids(session)
    if len(region_protos) == 0:
        raise ValueError("No regions found.")

    log.info(" * Fetching region maps for %d regions...", len(region_protos))
    aids = set()
    edge_protos = set()
    for region_proto in region_protos:
        r_aids, r_edge_protos = _fetch_region_map(session, region_proto.rid)
        aids.update(r_aids)
        edge_protos.update(r_edge_protos)

    log.info(" * Fetching %d stws...", len(aids))
    stw_protos = []
    for ctr, aid in enumerate(aids):
        stw_protos.append(_fetch_stw(session, aid))
        if (ctr + 1) % 50 == 0:
            log.info(" *  * Fetched %d of %d stws.", ctr + 1, len(aids))

    log.info(" * Finished fetching raw landscape information.")

    # Return the crawled objects.
    return superregion_protos, region_protos, edge_protos, stw_protos


# ========== MAIN PAGE ==========

def _fetch_rids(session: requests.Session) -> Tuple[List[SuperRegionPrototype], List[RegionPrototype]]:
    resp = session.get(urljoin(_STS_URL, "anlagen.php"))
    page = html.fromstring(resp.content)

    superregion_protos = []
    for superregion_node in page.xpath("//td[@class='border1']/a"):
        # Extract from JavaScript function call.
        urid = int(re.findall(r"\d+", superregion_node.attrib["href"])[0])
        if urid != 0:
            superregion_protos.append(SuperRegionPrototype(urid=urid, name=superregion_node.text.strip()))

    region_protos = []
    for region_node in page.xpath("//tr[@class='regionname']")[17:18]:
        region_protos.append(RegionPrototype(
            rid=int(region_node.attrib["rid"]),
            urid=int(region_node.attrib["urid"]),
            name=region_node.xpath("td[@class='regionname']/text()")[0].strip()
        ))

    return superregion_protos, region_protos


# ========== REGION MAP JSON ==========

def _fetch_region_map(session: requests.Session, rid: int) -> Tuple[List[int], List[EdgePrototype]]:
    resp = session.get(urljoin(_STS_URL, f"landschaft-data.php?rid={rid}"))
    data = json.loads(resp.text)

    kids_to_aids = {}
    for node in data["knoten"]:
        # These types of nodes are irrelevant to us:
        # - Nodes without aid: Links to other regions.
        # - Nodes with style "0": Stws that haven't been published yet.
        if "aid" in node and node["style"] != "0":
            kids_to_aids[node["kid"]] = int(node["aid"])

    edge_protos = []
    for edge in data["edges"]:
        try:
            aid_1 = kids_to_aids[edge["kid1"]]
            aid_2 = kids_to_aids[edge["kid2"]]
            edge_protos.append(EdgePrototype(aid_1=aid_1, aid_2=aid_2, handover=edge["uep"]))
        except KeyError:
            # This happens when one of the kids references a node which we have ignored above.
            pass

    return list(kids_to_aids.values()), edge_protos


# ========== SINGLE STW ==========

def _fetch_stw(session: requests.Session, aid: int) -> StwPrototype:
    resp = session.get(urljoin(_STS_URL, f"anlagen.php?subdata=ajax&m=anlage&aid={aid}"))
    data = _stw_parse_custom_format(resp.text)

    assert aid == int(data["A"]), f"Stw aid in url {aid} doesn't match returned aid {data['A']}."

    rid = int(data["R"])
    name = data["N"]

    latitude, longitude = None, None
    if "C" in data:
        str_lat, str_lon = data["C"].split(":")
        latitude, longitude = float(str_lat), float(str_lon)

    desc, difficulty, entertainment, forum_id = _stw_parse_desc(data["B"])

    comments = []
    if forum_id:
        # Reverse the comments so that the newest ones are right at the top.
        comments = list(reversed(list(_fetch_comments(session, forum_id))))

    return StwPrototype(aid=aid, rid=rid,
                        name=name, description=desc, latitude=latitude, longitude=longitude,
                        difficulty=difficulty, entertainment=entertainment, comments=comments)


def _stw_parse_custom_format(text: str) -> dict:
    dct = {}

    key = None
    for line in text.splitlines():
        if len(line) >= 2 and line[0].isupper() and line[1] == ":":
            key = line[0]
            dct[key] = line[2:]
        else:
            dct[key] += line

    return dct


def _stw_parse_desc(desc: str):
    desc = html.fromstring(desc)

    clean_desc = Markup("\n".join(html.tostring(p, encoding="utf-8").decode("utf-8")
                                  for p in desc.xpath("*[not(self::div)]")))

    dif_and_ent = desc.xpath("div[last()]//b/text()")
    difficulty, entertainment = None, None
    if len(dif_and_ent) == 3:
        difficulty, entertainment = float(dif_and_ent[1]), float(dif_and_ent[2])

    # Extract the forum id from the JavaScript function call in the href of the only link in the score box.
    forum_id = None
    forum_href = desc.xpath("div[last()]//a/@href")
    if len(forum_href) == 1:
        forum_id = re.findall(r"\d+", forum_href[0])[0]

    return clean_desc, difficulty, entertainment, forum_id


# ========== COMMENT FORUM FOR SINGLE STW ==========


def _fetch_comments(session: requests.Session, forum_id: str) -> Iterator[Comment]:
    resp = session.get(urljoin(_STS_URL, f"forum/viewtopic.php?t={forum_id}"))
    page = html.fromstring(resp.content)

    # Note: We skip the first comment since it's just saying that this thread is a shoutbox.
    posts = [(post.xpath("text()"),
              post.xpath("ancestor::table//b[text()='Verfasst:']/parent::div/text()")[0])
             for post in page.xpath("//div[@class='postbody']")[1:]]

    for content, time in posts:
        playing_duration = None
        if content[-1].startswith("Spieldauer:"):
            playing_duration = PLAYING_DURATION_CONVERSION[content[-1].strip()]
            content = content[:-1]
        year = int(re.findall(r"\d{4}", time)[0])
        yield Comment(text=" ".join(content), playing_duration=playing_duration, year=year)


@dataclass(frozen=True)
class SuperRegionPrototype:
    urid: int
    name: str


@dataclass(frozen=True)
class RegionPrototype:
    rid: int
    urid: int
    name: str


@dataclass(frozen=True)
class EdgePrototype:
    aid_1: int
    aid_2: int
    handover: bool


@dataclass(frozen=True)
class StwPrototype:
    aid: int
    rid: int

    name: str
    description: Markup
    latitude: float
    longitude: float

    difficulty: float
    entertainment: float
    comments: List[Comment]
