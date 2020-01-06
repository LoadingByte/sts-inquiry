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
from sts_inquiry.structs import Region, Comment

_STS_URL = app.config["STS_URL"]
_USER_AGENT = app.config["FETCH_USER_AGENT"]

log = logging.getLogger("sts-inquiry")


def fetch_landscape() -> Tuple[List[Region], Set[EdgePrototype], List[StwPrototype]]:
    session = requests.Session()
    session.headers.update({"User-Agent": _USER_AGENT})

    log.info(" * Fetching region rids...")
    rids = set(_fetch_rids(session))
    if len(rids) == 0:
        raise ValueError("No regions found.")

    log.info(" * Fetching region maps for %d regions...", len(rids))
    regions = []
    aids = set()
    edge_protos = set()
    for rid in rids:
        region, r_aids, r_edges = _fetch_region_map(session, rid)
        regions.append(region)
        aids.update(r_aids)
        edge_protos.update(r_edges)

    log.info(" * Fetching %d stws...", len(aids))
    stw_protos = []
    for ctr, aid in enumerate(aids):
        stw_protos.append(_fetch_stw(session, aid))
        if (ctr + 1) % 50 == 0:
            log.info(" *  * Fetched %d of %d stws.", ctr + 1, len(aids))

    log.info(" * Finished fetching raw landscape information.")

    # Return the crawled objects.
    return regions, edge_protos, stw_protos


# ========== MAIN PAGE ==========

def _fetch_rids(session: requests.Session) -> Iterator[int]:
    resp = session.get(urljoin(_STS_URL, "anlagen.php"))
    page = html.fromstring(resp.content)

    for rid in page.xpath("//tr[@class='regionname']/@rid"):
        yield int(rid)


# ========== REGION MAP JSON ==========

def _fetch_region_map(session: requests.Session, rid: int) -> Tuple[Region, List[int], List[EdgePrototype]]:
    resp = session.get(urljoin(_STS_URL, f"landschaft-data.php?rid={rid}"))
    data = json.loads(resp.text)

    region = Region(rid=rid, name=data["region"], stws=[])

    kids_to_aids = {}
    for node in data["knoten"]:
        # These types of nodes are irrelevant to us:
        # - Nodes without aid: Links to other regions.
        # - Nodes with style "0": Stws that haven't been published yet.
        if "aid" in node and node["style"] != "0":
            aid = node["aid"]
            kids_to_aids[node["kid"]] = int(aid)

    edges = []
    for edge in data["edges"]:
        try:
            aid_1 = kids_to_aids[edge["kid1"]]
            aid_2 = kids_to_aids[edge["kid2"]]
            edges.append(EdgePrototype(aid_1=aid_1, aid_2=aid_2, handover=edge["uep"]))
        except KeyError:
            # This happens when one of the kids references a node which we have ignored above.
            pass

    return region, list(kids_to_aids.values()), edges


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
            playing_duration = PLAYING_DURATION_CONVERSION[content[-1]]
            content = content[:-1]
        year = int(re.findall(r"\d{4}", time)[0])
        yield Comment(text=" ".join(content), playing_duration=playing_duration, year=year)


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
