#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker-compose build frontend
docker-compose rm -sf frontend
docker-compose up -d frontend
