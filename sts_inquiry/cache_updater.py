import logging
from threading import Thread, Timer

from sts_inquiry import app, cache
from sts_inquiry.pipeline import run_landscape_pipeline, run_player_pipeline

log = logging.getLogger("sts-inquiry")

_fi_landscape = app.config["FETCH_INTERVAL_LANDSCAPE"]
_fi_players = app.config["FETCH_INTERVAL_PLAYERS"]
assert _fi_landscape % _fi_players == 0, "FETCH_INTERVAL_LANDSCAPE must be a multiple of FETCH_INTERVAL_PLAYERS"

_player_updates_per_landscape_update = _fi_landscape // _fi_players
_remaining_player_updates_till_landscape_update = 0


def _periodic():
    global _remaining_player_updates_till_landscape_update

    if _remaining_player_updates_till_landscape_update == 0:
        _remaining_player_updates_till_landscape_update = _player_updates_per_landscape_update
        _fetch_and_handle_errors("world", _update_landscape)
    _remaining_player_updates_till_landscape_update -= 1

    _fetch_and_handle_errors("player list", _update_players)

    # Schedule the next iteration.
    # We do this AFTER the update(s) so that they have enough time to complete before the next update starts.
    t = Timer(_fi_players, _periodic)
    t.daemon = True
    t.start()


def _fetch_and_handle_errors(label, update_fn):
    log.info("A %s cache update is due. Will now start fetching the current %s...", label, label)
    try:
        update_fn()
        log.info("Successfully finished updating the %s cache.", label)
    except Exception as e:
        log.error("The following exception occurred while updating the %s cache. "
                  "Will retry when the next cache update is due.", label)
        log.error(" * %s: %s", e.__class__.__name__, e)
        if e.__cause__:
            log.error(" * Caused by %s: %s", e.__cause__.__class__.__name__, e.__cause__)


def _update_landscape():
    world, dfs = run_landscape_pipeline()

    with cache.LOCK:
        cache.update(world, dfs)


def _update_players():
    run_player_pipeline(cache.world, cache.dfs, cache.LOCK)


Thread(target=_periodic, daemon=True).start()
