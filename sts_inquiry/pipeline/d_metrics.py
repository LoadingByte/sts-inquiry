import logging
from statistics import mean, mode, StatisticsError
from typing import Iterable, Iterator, Collection, List, Set, FrozenSet

import pandas as pd

from sts_inquiry.pipeline.consts import PLAYING_TIME_ORDER_ASC
from sts_inquiry.structs import Edge, Stw


def landscape_metrics(all_clusters: Iterable[Set[FrozenSet[Stw]]]) -> Iterator[pd.DataFrame]:
    logging.info(" * Computing landscape metrics for all clusters...")

    for clusters in all_clusters:
        neighbors = [{nghb.stw
                      for stw in cluster for nghb in stw.neighbors
                      if nghb.stw not in cluster}
                     for cluster in clusters]
        intra_edges = [_intra_or_nghbr_edges("intra", cluster) for cluster in clusters]
        nghbr_edges = [_intra_or_nghbr_edges("nghbr", cluster) for cluster in clusters]
        mode_playing_time = [_statistic(mode, (cmt.playing_time for stw in cluster for cmt in stw.comments))
                             for cluster in clusters]
        difficulty = [_statistic(mean, (stw.difficulty for stw in cluster)) for cluster in clusters]
        entertainment = [_statistic(mean, (stw.entertainment for stw in cluster)) for cluster in clusters]

        cols = {
            "cluster": list(clusters),
            "neighbors": neighbors,
            "intra_edges": intra_edges,
            "regions": [{stw.region for stw in cluster} for cluster in clusters],

            # Metrics
            "intra_handovers": [sum(edge.handover for edge in edges) for edges in intra_edges],
            "nghbr_handovers": [sum(edge.handover for edge in edges) for edges in nghbr_edges],
            "n_neighbors": [len(nghbs) for nghbs in neighbors],
            "difficulty": difficulty,
            "entertainment": entertainment,
            "difent": [_statistic(mean, [dif, ent]) for dif, ent in zip(difficulty, entertainment)],
            "mode_playing_time": mode_playing_time,

            # Used for sorting and filtering
            "mode_playing_time_ordinal": [(PLAYING_TIME_ORDER_ASC.index(mpt) if mpt else None)
                                          for mpt in mode_playing_time],
            "concat_names": ["+++".join(stw.name for stw in cluster) for cluster in clusters]
        }

        yield pd.DataFrame(cols)

    logging.info(" * Finished computing landscape metrics.")


def _intra_or_nghbr_edges(intra_or_nghbr: str, cluster: FrozenSet[Stw]) -> Set[Edge]:
    intra_or_nghbr = intra_or_nghbr == "intra"
    return {Edge(frozenset({stw, nghb.stw}), nghb.handover)
            for stw in cluster for nghb in stw.neighbors
            if (nghb.stw in cluster) == intra_or_nghbr}


def _statistic(stat: callable, vals: Iterable):
    try:
        return stat(val for val in vals if val is not None)
    except StatisticsError:
        return None


def player_metrics(dfs: List[pd.DataFrame]):
    for idx in range(len(dfs)):
        df = dfs[idx]
        clusters = df["cluster"]

        cols = {
            "intra_occupied": [_n_occupied(cluster, min) for cluster in clusters],
            "nghbr_occupied": [_n_occupied(nghbs, max) for nghbs in df["neighbors"]],
            "region_occupied": [max(_n_occupied(set(region.stws).difference(cluster), max) for region in regions)
                                for cluster, regions in zip(clusters, df["regions"])]
        }

        dfs[idx] = df.assign(**cols)


def _n_occupied(stws: Collection[Stw], minmax: callable) -> int:
    return minmax(sum(stw.occupants[0] is not None for stw in stws),
                  sum(stw.occupants[1] is not None for stw in stws))
