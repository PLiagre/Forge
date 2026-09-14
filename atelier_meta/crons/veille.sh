#!/usr/bin/env bash
# Ce qu'on regarde avant d'armer, et chaque matin avant le premier tour.
#
# Regarder n'est pas dépenser : aucun agent n'est lancé ici. La veille ne
# connaît pas le produit qu'elle garde — elle lit son branchement, pas
# son code. Un atelier qui saurait ce qu'est une cellule ou un quartier
# serait un atelier de plus à réécrire au produit suivant.
#
# Deux niveaux, et la distinction porte :
#   - le branchement est illisible → on refuse, code non nul ;
#   - un binaire manque, un quota est inconnu → on le dit, et on rend 0.
#     Un poste absent n'empêche pas les autres de tourner, et un inconnu
#     ne se compte pas pour un échec.
set -euo pipefail

_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"
atelier_defauts
atelier_pythonpath

if [[ -z "${ATELIER_PROJET:-}" ]]; then
  dire "veille : ATELIER_PROJET n'est pas posé — aucun branchement à lire"
  exit 2
fi

# Le branchement, et lui seul, décide du code de sortie.
code=0
atelier doctor --projet "$ATELIER_PROJET" || code=$?

# Le reste est un rapport. `pret` dit ce qui manquerait pour armer ; son
# code de retour ne gouverne pas celui de la veille, parce qu'une machine
# où le relecteur n'est pas installé fait quand même tourner le coder.
echo "---"
atelier pret --projet "$ATELIER_PROJET" || true

# Un binaire présent n'est pas un binaire connecté. C'est la panne qui
# ressemble le plus à une file vide : le réveil part, l'agent refuse, le
# tour rend zéro, et rien ne dit pourquoi. On regarde, on ne connecte pas.
echo "---"
if command -v claude >/dev/null 2>&1; then
  if etat_claude="$(claude auth status --text 2>&1)"; then
    printf 'PASS  claude — %s\n' "$(printf '%s' "$etat_claude" | head -1)"
  else
    printf 'FAIL  claude — pas connecté. Lance : claude setup-token\n'
  fi
else
  printf '?     claude — absent du PATH\n'
fi
for binaire in agent hermes; do
  if command -v "$binaire" >/dev/null 2>&1; then
    printf 'PASS  %s — %s\n' "$binaire" "$(command -v "$binaire")"
  else
    printf '?     %s — absent du PATH\n' "$binaire"
  fi
done

exit "$code"
