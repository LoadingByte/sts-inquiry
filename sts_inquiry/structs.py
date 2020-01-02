from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, FrozenSet

from markupsafe import Markup


@dataclass(frozen=True)
class World:
    regions: List[Region]
    stws: List[Stw]
    edges: List[Edge]


@dataclass(frozen=True)
class Edge:
    stws: FrozenSet[Stw]
    handover: bool

    def fst(self):
        stw, _ = self.stws
        return stw

    def snd(self):
        _, stw = self.stws
        return stw

    def __str__(self):
        stw_1, stw_2 = self.stws
        return f"{stw_1} {'<>' if self.handover else '..'} {stw_2}"

    def __repr__(self):
        return f"Edge {self}"


@dataclass(eq=False)
class Region:
    rid: int
    name: str
    stws: List[Stw]

    def __eq__(self, other):
        return isinstance(other, Region) and self.rid == other.rid

    def __hash__(self):
        return hash((self.rid,))


@dataclass(eq=False)
class Stw:
    aid: int
    region: Region
    occupants: List[Player]

    neighbors: List[Neighbor]

    name: str
    description: Markup
    latitude: Optional[float]
    longitude: Optional[float]

    difficulty: Optional[float]  # 1 through 4
    entertainment: Optional[float]  # 1 through 4
    comments: List[Comment]

    def occupants_at(self, instance: int):
        return self.occupants[instance - 1]

    def __eq__(self, other):
        return isinstance(other, Stw) and self.aid == other.aid

    def __hash__(self):
        return hash((self.aid,))

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Stw {self.name}"


@dataclass(frozen=True)
class Neighbor:
    stw: Stw
    handover: bool


@dataclass(frozen=True)
class Player:
    name: str
    stitz: bool
    start_time: datetime


@dataclass(frozen=True)
class Comment:
    text: str
    playing_time: Optional[str]
