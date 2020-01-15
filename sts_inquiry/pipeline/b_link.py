import logging
from typing import Collection, List

from sts_inquiry.consts import INSTANCES
from sts_inquiry.pipeline.a_fetch.landscape_fetcher import SuperRegionPrototype, RegionPrototype, EdgePrototype, \
    StwPrototype
from sts_inquiry.pipeline.a_fetch.player_fetcher import PlayerPrototype
from sts_inquiry.structs import World, Edge, SuperRegion, Region, Stw, Neighbor, Player

log = logging.getLogger("sts-inquiry")


def link_landscape(superregion_protos: Collection[SuperRegionPrototype], region_protos: Collection[RegionPrototype],
                   edge_protos: Collection[EdgePrototype], stw_protos: Collection[StwPrototype]) -> World:
    log.info(" * Linking %d superregions, %d regions, %d stws, %d edges...",
             len(superregion_protos), len(region_protos), len(stw_protos), len(edge_protos))

    # Convert superregions.
    superregions = {proto.urid: SuperRegion(urid=proto.urid,
                                            name=proto.name,
                                            regions=[])
                    for proto in superregion_protos}

    # Convert regions.
    regions = {proto.rid: Region(rid=proto.rid,
                                 name=proto.name,
                                 superregion=superregions[proto.urid],
                                 stws=[])
               for proto in region_protos}
    # Backref: Tell each superregion its regions.
    for region in regions.values():
        region.superregion.regions.append(region)

    # Convert stws, ignoring neighbors for now.
    # Players are also ignored since that information will be linked into the world later on.
    stws = {proto.aid: Stw(aid=proto.aid,
                           region=regions[proto.rid],
                           occupants=[],
                           neighbors=[],
                           name=proto.name,
                           description=proto.description,
                           latitude=proto.latitude,
                           longitude=proto.longitude,
                           difficulty=proto.difficulty,
                           entertainment=proto.entertainment,
                           comments=proto.comments)
            for proto in stw_protos}
    # Backref: Tell each region its stws.
    for stw in stws.values():
        stw.region.stws.append(stw)

    # Convert edges; use a set to remove duplicates.
    edges = [Edge(stws=frozenset({stws[proto.aid_1], stws[proto.aid_2]}),
                  handover=proto.handover)
             for proto in edge_protos]
    # Tell each stw its neighbors.
    for edge in edges:
        stw_1, stw_2 = edge.stws
        stw_1.neighbors.append(Neighbor(stw=stw_2, handover=edge.handover))
        stw_2.neighbors.append(Neighbor(stw=stw_1, handover=edge.handover))

    log.info(" * Finished linking landscape.")

    # Create the world.
    return World(superregions=list(superregions.values()),
                 regions=list(regions.values()),
                 stws=list(stws.values()),
                 edges=edges)


def link_players(world: World, player_items: List[PlayerPrototype]):
    player_lookup = {(pl_i.aid, pl_i.instance): Player(name=pl_i.name,
                                                       stitz=pl_i.stitz,
                                                       start_time=pl_i.start_time)
                     for pl_i in player_items}

    for stw in world.stws:
        stw.occupants = [player_lookup.get((stw.aid, inst)) for inst in INSTANCES]
