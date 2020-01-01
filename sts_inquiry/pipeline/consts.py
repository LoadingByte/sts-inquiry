BASE_URL = "https://www.stellwerksim.de"
USER_AGENT = "Mozilla/5.0 Firefox"  # This UA activates the beta version of the Sts website.

PLAYING_TIME_CONVERSION = {
    "Spieldauer: unter 15 Minuten": "<15 min",
    "Spieldauer: unter 30 Minuten": "<30 min",
    "Spieldauer: zwischen 30 und 90 Minuten": "30-90 min",
    "Spieldauer: über 90 Minuten": ">90 min"
}

PLAYING_TIME_ORDER_ASC = ["<15 min", "<30 min", "30-90 min", ">90 min"]
