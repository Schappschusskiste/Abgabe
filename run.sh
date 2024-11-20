#!/bin/sh
. .venv/bin/activate
LIBCAMERA_LOG_LEVELS=ERROR exec python app.py
