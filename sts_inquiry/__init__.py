import logging
import sys
from urllib.parse import urljoin

import numpy as np
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware


def app_root_404(env, resp):
    resp("404", [("Content-Type", "text/plain")])
    return [b"404 The application root has been reconfigured."]


# Create the app.
app = Flask(__name__)
app.config["WTF_CSRF_ENABLED"] = False

# Load config from disk.
app.config.from_pyfile("settings.cfg", silent=True)
app.config.from_envvar("STS_INQUIRY_SETTINGS", silent=True)

# Setup logging.
log_handlers = [logging.StreamHandler(sys.stderr), logging.FileHandler(app.config["LOGFILE"])]
for handler in log_handlers:
    handler.setLevel(logging.INFO)
logging.basicConfig(handlers=log_handlers, level=logging.NOTSET,
                    format="%(asctime)s %(name)-8s %(levelname)-8s %(message)s")

# Change the application root if configured.
app_root = app.config.get("APPLICATION_ROOT", "/")
if app_root != "/":
    app.config["APPLICATION_ROOT"] = app_root
    app.wsgi_app = DispatcherMiddleware(app_root_404, {app_root: app.wsgi_app})

# Configure the template engine.
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.jinja_env.globals.update(zip=zip, isnan=np.isnan, urljoin=urljoin, sts_url=app.config["STS_URL"])

# Initialize routes.
from . import views

# Start the cache scheduler.
from . import cache_updater
