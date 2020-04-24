from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Iterator
from urllib.parse import urljoin

import requests
from lxml import html

from sts_inquiry import app

_STS_URL = app.config["STS_URL"]
_USER_AGENT = app.config["FETCH_USER_AGENT"]
_USERNAME = app.config["FETCH_USERNAME"]
_PASSWORD = app.config["FETCH_PASSWORD"]

log = logging.getLogger("sts-inquiry")

session_cookie_key: Optional[str] = None
session_id = ""


def fetch_players() -> List[PlayerPrototype]:
    global session_id

    if not _USERNAME or not _PASSWORD:
        raise RuntimeError("Retrieving the current player list requires to be logged in. "
                           "However, the account credentials specified in the settings file are empty. "
                           "Please fill in valid account credentials.")

    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT
    if session_cookie_key is not None:
        session.cookies[session_cookie_key] = session_id

    players = list(_try_fetch_players(session))

    if players:
        return players

    # If the player list is empty, the reason for that might be that our session id has expired.
    # Verify whether that is the case by checking whether the main page shows that we are logged in.
    # If we are logged in, the empty player list answer by the server is actually truthful and we can return it.
    if _check_logged_in(session):
        return players

    # Login with the user-specified account and capture the now logged in session id.
    log.info("The session id is not present or has expired. Logging in to acquire a valid one...")
    session_id = _login(session)

    # If we are still not logged in even though it seemed like the login was successful, fail.
    if not _check_logged_in(session):
        raise RuntimeError("Tried to log in, but the session id supplied by the server still seems to not be "
                           "logged in. "
                           "Make sure that the account credentials specified in the settings file is valid.")

    # Now, if we reach this piece of code, we are definitely logged in.
    # We can faithfully return the player list returned by the server.
    return list(_try_fetch_players(session))


def _try_fetch_players(session: requests.Session) -> Iterator[PlayerPrototype]:
    resp = session.get(urljoin(_STS_URL, "anlagen.php?subdata=ajax&m=players"))

    for line in resp.text.splitlines():
        line = line.strip()
        if line != "":
            name, _, str_aid, str_inst, _, str_stitz, str_start = line.split(":")
            aid, instance = int(str_aid), int(str_inst)
            stitz = bool(int(str_stitz))
            start_time = datetime.fromtimestamp(int(str_start))
            yield PlayerPrototype(name=name, stitz=stitz, start_time=start_time, aid=aid, instance=instance)


def _check_logged_in(session: requests.Session) -> bool:
    return "angemeldet als" in session.get(_STS_URL).text


def _login(session: requests.Session) -> str:
    global session_cookie_key

    # Remove the session information from the previous request because requests sometimes duplicates cookie keys.
    session.cookies.clear()

    login_url = urljoin(_STS_URL, "forum/ucp.php?mode=login")

    # Request the login form once to get three tokens.
    resp = session.get(login_url)
    page = html.fromstring(resp.content)
    creation_time = page.xpath("//input[@name='creation_time']/@value")[0]
    form_token = page.xpath("//input[@name='form_token']/@value")[0]
    sid = page.xpath("//input[@name='sid']/@value")[0]

    # The login doesn't work if the first and second request happen in rapid succession,
    # so we wait for two seconds.
    time.sleep(2)

    # Then, we accurately mimic what a browser would send to the login page.
    session.post(login_url, data={
        "username": _USERNAME,
        "password": _PASSWORD,
        "redirect": ["./ucp.php?mode=login", "index.php"],
        "creation_time": creation_time,
        "form_token": form_token,
        "sid": sid,
        "login": "Anmelden"
    })

    if session_cookie_key is None:
        session_cookie_key = next((k for k in session.cookies.keys() if k.endswith("_sid")), None)

    if session_cookie_key not in session.cookies:
        raise RuntimeError("Tried to log in, but the server didn't answer with a session id. "
                           "Make sure that the account credentials specified in the settings file are valid.")
    else:
        return session.cookies[session_cookie_key]


@dataclass(frozen=True)
class PlayerPrototype:
    name: str
    stitz: bool
    start_time: datetime

    aid: int
    instance: int
