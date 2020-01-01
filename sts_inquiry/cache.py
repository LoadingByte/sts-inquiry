from typing import List

import pandas as pd

from sts_inquiry.structs import World

ready: bool = False
world: World
dfs: List[pd.DataFrame]


def update(new_world: World, new_dfs: List[pd.DataFrame]):
    global ready, world, dfs

    world = new_world
    dfs = new_dfs
    ready = True
