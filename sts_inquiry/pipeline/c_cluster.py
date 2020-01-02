import logging
from typing import List, Set, FrozenSet

from sts_inquiry import app
from sts_inquiry.structs import World, Stw

_MAX_CLUSTER_SIZE = app.config["MAX_CLUSTER_SIZE"]


def cluster_landscape(world: World) -> List[Set[FrozenSet[Stw]]]:
    logging.info(" * Computing stw clusters up to size %d...", _MAX_CLUSTER_SIZE)

    # We get these first two clusters for free.
    one_clusters = {frozenset({stw}) for stw in world.stws}
    two_clusters = {frozenset(edge.stws) for edge in world.edges}

    all_clusters = [one_clusters, two_clusters]

    for _ in range(_MAX_CLUSTER_SIZE - 2):
        prev_clusters = all_clusters[-1]

        cur_clusters = set()
        all_clusters.append(cur_clusters)

        for cluster in prev_clusters:
            nghb_stws = {nghb.stw
                         for stw in cluster for nghb in stw.neighbors
                         if nghb.stw not in cluster}
            for nghb_stw in nghb_stws:
                cur_clusters.add(cluster.union({nghb_stw}))

    logging.info(" * Finished computing a total of %d stw clusters.", sum(len(clusters) for clusters in all_clusters))

    return all_clusters
