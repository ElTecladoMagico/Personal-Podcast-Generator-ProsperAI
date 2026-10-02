#!/bin/sh
# Run from your machine: pull main on the VPS, rebuild, restart, then wait until it is healthy.
set -eu
ssh instanta 'cd /opt/podcast/repo && git pull --ff-only && docker compose -f deploy/docker-compose.yml up -d --build'
for _ in $(seq 1 30); do  # migrations and imports take ~10-20 s after a rebuild
  if curl -fsS https://api.podcast.scuda.es/health 2>/dev/null; then echo " deployed"; exit 0; fi
  sleep 2
done
echo "API not healthy after 60 s: ssh instanta 'docker logs --tail 50 podcast-api'" >&2
exit 1
