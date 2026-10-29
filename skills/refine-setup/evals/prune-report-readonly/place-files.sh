#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
touch -t 202601010000 skills/used-skill/SKILL.md skills/old-unused/SKILL.md skills/another-old-unused/SKILL.md
