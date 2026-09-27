#!/usr/bin/env bash
# La veille : ce qui manque pour tourner, dit à la main. Le cron la joue par
# `tour.sh veille` à 06:45 ; ce script existe pour la taper sans rien savoir.
set -euo pipefail
_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"
atelier_defauts
atelier_pythonpath
exec python3 -m atelier --projet "$ATELIER_PROJET" veille
