#!/bin/sh
set -eu

install -o app -g app -m 0400 /data/options.json /run/sungrow-options.json
exec su-exec app:app env OPTIONS_PATH=/run/sungrow-options.json python /app/main.py
