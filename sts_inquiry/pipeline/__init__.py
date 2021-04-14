from threading import Lock
from typing import Optional, List, Tuple

import pandas as pd

from sts_inquiry.structs import World
from .a_fetch import fetch_landscape, fetch_players
from .b_link import link_landscape, link_players
from .c_cluster import cluster_landscape
from .d_metrics import landscape_metrics, player_metrics


def run_landscape_pipeline() -> Tuple[World, List[pd.DataFrame]]:
    world = link_landscape(*fetch_landscape())
    return world, list(landscape_metrics(cluster_landscape(world)))


def run_player_pipeline(world: World, dfs: List[pd.DataFrame], lock: Optional[Lock]):
    def process_fetched_players(players):
        if lock is not None:
            with lock:
                link_players(world, players)
                player_metrics(dfs)
        else:
            link_players(world, players)
            player_metrics(dfs)

    try:
        fetched_players = fetch_players()
    except Exception:
        # When the player list cannot be fetched, remove all previous player information
        # so that we do not display stale data.
        process_fetched_players([])
        raise

    process_fetched_players(fetched_players)
