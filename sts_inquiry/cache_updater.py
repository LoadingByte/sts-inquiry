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
        _fetch_and_handle_errors("world", _update_landscape_and_players)
    else:
        # Only try to fetch players if the landscape has successfully been fetched.
        if hasattr(cache, "world"):
            _fetch_and_handle_errors("player list", _update_players)

    _remaining_player_updates_till_landscape_update -= 1

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
        log.exception(" * %s: %s", e.__class__.__name__, e)
        if e.__cause__:
            log.exception(" * Caused by %s: %s", e.__cause__.__class__.__name__, e.__cause__)
        log.error("Failed to update the %s cache because of the preceding exception. "
                  "Will retry when the next cache update is due.", label)


def _update_landscape_and_players():
    world, dfs = run_landscape_pipeline()

    def update_cache():
        with cache.LOCK:
            cache.update(world, dfs)

    try:
        run_player_pipeline(world, dfs, None)
        update_cache()
    except Exception:
        update_cache()
        raise


def _update_players():
    run_player_pipeline(cache.world, cache.dfs, cache.LOCK)


Thread(target=_periodic, daemon=True).start()
