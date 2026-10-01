#!/bin/sh
# Run from your machine: pull main on the VPS, rebuild, restart, smoke-test.
set -eu
ssh instanta 'cd /opt/podcast/repo && git pull --ff-only && docker compose -f deploy/docker-compose.yml up -d --build'
sleep 5
curl -fsS https://api.podcast.scuda.es/health && echo " deployed"
