from threading import Lock
from typing import List

import pandas as pd

from sts_inquiry.structs import World

# Because we cannot assume that operations on Pandas objects are thread-safe, we better make sure that
# only one user request at the time can do stuff with the dfs.
LOCK = Lock()

ready: bool = False
world: World
dfs: List[pd.DataFrame]


def update(new_world: World, new_dfs: List[pd.DataFrame]):
    global ready, world, dfs

    # Try to free memory.
    try:
        del world
        for df in dfs[:]:
            del df
    except NameError:
        # This happens on the first update when there's no old stuff to free.
        pass

    world = new_world
    dfs = new_dfs
    ready = True
