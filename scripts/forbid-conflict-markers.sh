#!/usr/bin/env bash
set -euo pipefail
if git grep -nE '^(<<<<<<< |>>>>>>> |=======$)' HEAD -- '*.md' '*.lean' '*.py' '*.json' '*.toml'; then
  echo 'REFUSING PUBLISH: unresolved conflict markers found' >&2
  exit 1
fi
