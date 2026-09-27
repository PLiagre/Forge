#!/usr/bin/env bash
# Un tour d'un rôle : un verrou, la base à jour, Python, puis on sort.
#
# Rôles : pilote (un tour de la chaîne), journal, boussole, veille. Un tour
# qui tourne encore fait passer le suivant : le verrou est par rôle. Le
# pilote tourne depuis la copie principale, restée sur la base ; les lots
# travaillent dans leurs worktrees (.atelier/chantiers/), et ne touchent
# jamais atelier/ : le code qui pilote ne change que par le mode direct.
set -euo pipefail

_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"
atelier_defauts
atelier_pythonpath

role="${1:-}"
case "$role" in
  pilote|journal|boussole|veille) : ;;
  *) dire "usage : tour.sh <pilote|journal|boussole|veille>"; exit 2 ;;
esac

mkdir -p "$ATELIER_VERROUS"
exec 9>"$ATELIER_VERROUS/atelier-$role.lock"
if ! flock -n 9; then
  dire "tour $role : un tour tourne encore — celui-ci passe"
  exit 0
fi

# Le pilote tourne depuis la copie principale, et elle reste sur la base. Une
# main qui l'a mise sur une autre branche (mode direct) suspend la chaîne au
# lieu de la faire tourner sur du code qui n'est pas celui de master.
courante="$(git -C "$ATELIER_PROJET" branch --show-current 2>/dev/null || true)"
if [[ "$courante" != "${ATELIER_BASE:-master}" ]]; then
  dire "tour $role : la copie principale est sur « ${courante:-HEAD détaché} », pas sur ${ATELIER_BASE:-master} — tour suspendu"
  exit 0
fi

# La base d'abord : le pilote décide sur ce qui a été fusionné.
if [[ "${ATELIER_SANS_PULL:-0}" != "1" ]]; then
  git -C "$ATELIER_PROJET" pull --quiet --ff-only >&2 || dire "tour $role : base non rafraîchie — on continue"
fi

# Un tour ne dure jamais plus de trois heures : un agent a son propre délai,
# ceci garde le tour lui-même d'un réseau qui ne répond plus.
code=0
case "$role" in
  pilote)   sans_cles timeout -k 30 10800 python3 -m atelier --projet "$ATELIER_PROJET" tour || code=$? ;;
  journal)  sans_cles timeout -k 30 1800 python3 -m atelier --projet "$ATELIER_PROJET" journal || code=$? ;;
  boussole) sans_cles timeout -k 30 1800 python3 -m atelier --projet "$ATELIER_PROJET" boussole || code=$? ;;
  veille)   sans_cles timeout -k 30 600 python3 -m atelier --projet "$ATELIER_PROJET" veille \
              | tee "${ATELIER_VEILLE:-$HOME/.atelier/veille.txt}" || code=$? ;;
esac
exit "$code"
