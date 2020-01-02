import logging
from typing import Collection, List

from sts_inquiry.consts import INSTANCES
from sts_inquiry.pipeline.a_fetch.landscape_fetcher import EdgePrototype, StwPrototype
from sts_inquiry.pipeline.a_fetch.player_fetcher import PlayerPrototype
from sts_inquiry.structs import World, Edge, Region, Stw, Neighbor, Player

log = logging.getLogger("sts-inquiry")


def link_landscape(regions: List[Region], edge_protos: Collection[EdgePrototype],
                   stw_protos: Collection[StwPrototype]) -> World:
    log.info(" * Linking %d regions, %d stws, %d edges...", len(regions), len(stw_protos), len(edge_protos))

    # Convert stws, ignoring neighbors for now.
    # Players are also ignored since that information will be linked into the world later on.
    rids_to_regions = {reg.rid: reg for reg in regions}
    stws = {stw_p.aid: Stw(aid=stw_p.aid,
                           region=rids_to_regions[stw_p.rid],
                           occupants=[],
                           neighbors=[],
                           name=stw_p.name,
                           description=stw_p.description,
                           latitude=stw_p.latitude,
                           longitude=stw_p.longitude,
                           difficulty=stw_p.difficulty,
                           entertainment=stw_p.entertainment,
                           comments=stw_p.comments)
            for stw_p in stw_protos}

    # Tell each region its stws.
    for stw in stws.values():
        stw.region.stws.append(stw)

    # Convert edges; use set to remove duplicates.
    edges = [Edge(stws=frozenset({stws[edg_p.aid_1], stws[edg_p.aid_2]}),
                  handover=edg_p.handover)
             for edg_p in edge_protos]

    # Tell each stw its neighbors.
    for edge in edges:
        stw_1, stw_2 = edge.stws
        stw_1.neighbors.append(Neighbor(stw=stw_2, handover=edge.handover))
        stw_2.neighbors.append(Neighbor(stw=stw_1, handover=edge.handover))

    log.info(" * Finished linking landscape.")

    # Create the world.
    return World(regions=regions,
                 stws=list(stws.values()),
                 edges=edges)


def link_players(world: World, player_items: List[PlayerPrototype]):
    player_lookup = {(pl_i.aid, pl_i.instance): Player(name=pl_i.name,
                                                       stitz=pl_i.stitz,
                                                       start_time=pl_i.start_time)
                     for pl_i in player_items}

    for stw in world.stws:
        stw.occupants = [player_lookup.get((stw.aid, inst)) for inst in INSTANCES]
