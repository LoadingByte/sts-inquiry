import os
import sys
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler
from zipfile import ZipFile, ZIP_LZMA


def setup_logging(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(name)-11s %(levelname)-8s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": sys.stderr
            },
            "file": {
                "level": "INFO",
                "formatter": "default",
                "()": _rotating_file_handler,
                "filename": os.path.join(log_dir, "sts-inquiry.log"),
                "maxBytes": 512 * 1024,
                "backupCount": 5,
            }
        },
        "loggers": {
            "": {  # root
                "handlers": ["console", "file"],
                "level": "NOTSET"
            },
            "sts-inquiry": {
                "level": "INFO"
            }
        }
    })


def _rotating_file_handler(filename, maxBytes, backupCount):
    handler = RotatingFileHandler(filename, maxBytes=maxBytes, backupCount=backupCount)
    handler.namer = _logrot_namer
    handler.rotator = _logrot_rotator
    return handler


def _logrot_namer(name):
    return name + ".zip"


def _logrot_rotator(source, dest):
    with ZipFile(dest, "w", ZIP_LZMA) as df:
        df.write(source, os.path.basename(source))
    os.remove(source)
