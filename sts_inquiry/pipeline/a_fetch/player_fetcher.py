from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

import requests

from sts_inquiry.pipeline.consts import BASE_URL, USER_AGENT


def fetch_players() -> Iterator[PlayerPrototype]:
    # Any IOError here will be forwarded to the calling function, which is the desired behavior.
    resp = requests.get(f"{BASE_URL}/anlagen.php?subdata=ajax&m=players",
                        headers={"User-Agent": USER_AGENT})

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
