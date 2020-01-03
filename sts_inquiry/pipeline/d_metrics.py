import logging
from statistics import mean, mode, StatisticsError
from typing import Iterable, Iterator, Collection, List, Set, FrozenSet

import pandas as pd

from sts_inquiry.consts import INSTANCES, PLAYING_TIME_ORDER_ASC
from sts_inquiry.structs import Edge, Stw

log = logging.getLogger("sts-inquiry")


def _statistic(stat: callable, vals: Iterable):
    try:
        return stat(val for val in vals if val is not None)
    except (ValueError, TypeError, StatisticsError):
        return None


def landscape_metrics(all_clusters: Iterable[Set[FrozenSet[Stw]]]) -> Iterator[pd.DataFrame]:
    log.info(" * Computing landscape metrics for all clusters...")

    for clusters in all_clusters:
        col_neighbors = [{nghbr.stw
                          for stw in cluster for nghbr in stw.neighbors
                          if nghbr.stw not in cluster}
                         for cluster in clusters]
        col_intra_edges = [_intra_or_nghbr_edges("intra", cluster) for cluster in clusters]
        col_nghbr_edges = [_intra_or_nghbr_edges("nghbr", cluster) for cluster in clusters]
        col_regions = [{stw.region for stw in cluster} for cluster in clusters]

        col_difficulty = [_statistic(mean, (stw.difficulty for stw in cluster)) for cluster in clusters]
        col_entertainment = [_statistic(mean, (stw.entertainment for stw in cluster)) for cluster in clusters]
        col_mode_playing_time = [_statistic(mode, (cmt.playing_time for stw in cluster for cmt in stw.comments))
                                 for cluster in clusters]

        cols = {
            "cid": range(len(clusters)),
            "cluster": list(clusters),
            "neighbors": col_neighbors,
            "intra_edges": col_intra_edges,
            "regions": col_regions,

            # Metrics
            "intra_handovers": [sum(edge.handover for edge in edges) for edges in col_intra_edges],
            "nghbr_handovers": [sum(edge.handover for edge in edges) for edges in col_nghbr_edges],
            "n_neighbors": [len(nghbrs) for nghbrs in col_neighbors],
            "difficulty": col_difficulty,
            "entertainment": col_entertainment,
            "difent": [_statistic(mean, [dif, ent]) for dif, ent in zip(col_difficulty, col_entertainment)],
            "mode_playing_time": col_mode_playing_time,

            # Used for sorting and filtering
            "mode_playing_time_ordinal": [(PLAYING_TIME_ORDER_ASC.index(mpt) if mpt else None)
                                          for mpt in col_mode_playing_time],
            "concat_names": ["+++".join(stw.name for stw in cluster) for cluster in clusters],
            "rids": [{region.rid for region in regions} for regions in col_regions]
        }

        df = pd.DataFrame(cols)

        # Necessary for player metrics
        df = pd.concat((df.assign(instance=inst) for inst in INSTANCES), ignore_index=True)

        yield df

    log.info(" * Finished computing landscape metrics.")


def _intra_or_nghbr_edges(intra_or_nghbr: str, cluster: FrozenSet[Stw]) -> Set[Edge]:
    intra_or_nghbr = intra_or_nghbr == "intra"
    return {Edge(frozenset({stw, nghbr.stw}), nghbr.handover)
            for stw in cluster for nghbr in stw.neighbors
            if (nghbr.stw in cluster) == intra_or_nghbr}


def player_metrics(dfs: List[pd.DataFrame]):
    for idx in range(len(dfs)):
        df = dfs[idx]

        cols = {
            "free": [_n_occupied(cluster, inst) == 0 for inst, cluster in zip(df["instance"], df["cluster"])],
            "nghbr_occupants": [_n_occupied(nghbrs, inst) for inst, nghbrs in zip(df["instance"], df["neighbors"])],
            "region_occupants": [
                _statistic(max, (
                    _n_occupied(region.stws, inst) for region in regions
                )) for inst, cluster, regions in zip(df["instance"], df["cluster"], df["regions"])]
        }

        dfs[idx] = df.assign(**cols)


def _n_occupied(stws: Collection[Stw], inst: int) -> int:
    return sum(stw.occupants_at(inst) is not None for stw in stws)
