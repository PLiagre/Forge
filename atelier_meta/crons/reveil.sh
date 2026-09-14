#!/usr/bin/env bash
# Un réveil : `reveil.sh HH:MM <rôle>`. Il ne fait rien d'autre que
# vérifier l'heure, lancer le tour, et journaliser ce qu'il a coûté.
#
# Pourquoi une heure en argument alors que le cron en porte déjà une :
# les heures du registre sont celles de Paris, et les champs du crontab
# sont lus en UTC. Une ligne est donc armée aux *deux* heures UTC
# possibles, et c'est cette garde qui tranche — une fois, et une seule,
# été comme hiver. Sans elle, la moitié de l'année tombe à côté.
set -euo pipefail

_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"
atelier_defauts

heure="${1:-}"
role="${2:-}"
if [[ -z "$heure" || -z "$role" ]]; then
  dire "usage : reveil.sh HH:MM <rôle>"
  exit 2
fi

# Hors horaire, on se tait complètement : pas un mot, pas un journal.
# Un cron qui écrit à chaque minute est un cron qu'on finit par éteindre.
[[ "$(date +%H:%M)" == "$heure" ]] || exit 0

mkdir -p "$ATELIER_LOGS"
journal="$ATELIER_LOGS/$role.log"

{
  echo "=== $(date) — réveil $heure : $role"
} >> "$journal"

code=0
bash "$ATELIER_ROOT/crons/tour.sh" "$role" >> "$journal" 2>&1 || code=$?

echo "=== $role : code $code" >> "$journal"
exit "$code"
