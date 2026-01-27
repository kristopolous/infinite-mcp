#!/bin/bash
[[ -d servers ]] || git clone https://github.com/modelcontextprotocol/servers
grep -Po 'https://github.com/[^?#"\s)]*' servers/README.md | grep -E 'https://github[^)]*/[^)]*/[^)]*' | cut -c 20- | cut -d '/' -f 1,2 | sort | uniq | while read i; do
    echo -e "\n\n$i"
    if [[ ! -e "$i" ]]; then
        base="$(dirname $i)";
        [[ -d "$base" ]] || mkdir "$base"
        timeout 10s git clone --depth 1 "https://github.com/$i" "$i"
    else
        (
            cd "$i"
            what=$(git rev-parse --abbrev-ref HEAD)
            timeout 5s git fetch origin $what
            git reset --hard origin/$what
        )
    fi
done
