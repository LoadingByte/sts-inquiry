from typing import List, Tuple

import pandas as pd

from sts_inquiry.structs import World
from .a_fetch import fetch_landscape, fetch_players
from .b_link import link_landscape, link_players
from .c_cluster import cluster_landscape
from .d_metrics import landscape_metrics, player_metrics


def run_landscape_pipeline() -> Tuple[World, List[pd.DataFrame]]:
    world = link_landscape(*fetch_landscape())
    return world, list(landscape_metrics(cluster_landscape(world)))


def run_player_pipeline(world: World, dfs: List[pd.DataFrame]):
    link_players(world, list(fetch_players()))
    player_metrics(dfs)
