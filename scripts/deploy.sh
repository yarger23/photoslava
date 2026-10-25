#!/usr/bin/env bash
set -euo pipefail
photoslava_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$photoslava_source"
for photoslava_tool in git python3 nginx systemctl; do
  command -v "$photoslava_tool" >/dev/null || { echo "Required program missing: $photoslava_tool" >&2; exit 1; }
done
if [[ "$(id -u)" != 0 ]]; then echo 'Run this script as root (or with sudo).' >&2; exit 1; fi
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo 'Local tracked files have changes. Commit or review them before updating.' >&2; exit 1
fi
if [[ "$(git branch --show-current)" != main ]]; then echo 'Switch to branch main first.' >&2; exit 1; fi
photoslava_remote="$(git remote get-url origin)"
case "$photoslava_remote" in
  git@github.com:yarger23/photoslava.git|https://github.com/yarger23/photoslava.git) ;;
  *) echo 'Unexpected Git remote; refusing deployment.' >&2; exit 1 ;;
esac
git pull --ff-only origin main
python3 scripts/publish.py
