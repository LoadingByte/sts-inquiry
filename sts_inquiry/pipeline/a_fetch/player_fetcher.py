from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator
from urllib.parse import urljoin

import requests

from sts_inquiry import app

_STS_URL = app.config["STS_URL"]
_USER_AGENT = app.config["FETCH_USER_AGENT"]


def fetch_players() -> Iterator[PlayerPrototype]:
    # Any IOError here will be forwarded to the calling function, which is the desired behavior.
    resp = requests.get(urljoin(_STS_URL, "anlagen.php?subdata=ajax&m=players"),
                        headers={"User-Agent": _USER_AGENT})

    for line in resp.text.splitlines():
        line = line.strip()
        if line != "":
            name, _, str_aid, str_inst, _, str_stitz, str_start = line.split(":")
            aid, instance = int(str_aid), int(str_inst)
            stitz = bool(int(str_stitz))
            start_time = datetime.fromtimestamp(int(str_start))
            yield PlayerPrototype(name=name, stitz=stitz, start_time=start_time, aid=aid, instance=instance)


@dataclass(frozen=True)
class PlayerPrototype:
    name: str
    stitz: bool
    start_time: datetime

    aid: int
    instance: int
