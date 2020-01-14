import os
from urllib.parse import urljoin, urlencode

import numpy as np
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from sts_inquiry.log import setup_logging


def app_root_404(env, resp):
    resp("404", [("Content-Type", "text/plain")])
    return [b"404 The application root has been reconfigured."]


# Create the app.
app = Flask(__name__)
app.config["WTF_CSRF_ENABLED"] = False

# Load config from disk.
app.config.from_pyfile("settings.cfg")
if "STS_INQUIRY_SETTINGS" in os.environ:
    app.config.from_envvar("STS_INQUIRY_SETTINGS")

# Setup logging.
app.logger.handlers.clear()
setup_logging(app.config["LOG_DIR"])

# Change the application root if configured.
app_root = app.config.get("APPLICATION_ROOT", "/")
if app_root != "/":
    app.config["APPLICATION_ROOT"] = app_root
    app.wsgi_app = DispatcherMiddleware(app_root_404, {app_root: app.wsgi_app})

# Configure the template engine.
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.jinja_env.globals.update(zip=zip, isnan=np.isnan,
                             urljoin=urljoin, urlencode=urlencode, sts_url=app.config["STS_URL"])

# Initialize routes.
from . import views

# Start the cache scheduler.
from . import cache_updater
