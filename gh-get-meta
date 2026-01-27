#!/bin/bash
find gh -mindepth 2 -maxdepth 2 -type d |while read i; do
  [[ -s $i/_meta-info.json ]] && continue
  repo=$(echo $i | cut -d '/' -f 2-3)
  echo -n "."
  gh repo view --json archivedAt,forkCount,stargazerCount,pushedAt,watchers $repo > $i/_meta-info.json
  sleep 0.5
done
