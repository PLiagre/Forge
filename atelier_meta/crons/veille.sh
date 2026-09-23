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

# Le rapport s'écrit toujours au même endroit, et pas seulement quand
# l'installateur l'y redirige : c'est lui que `atelier-boucle etat` lit
# pour dire, en une ligne, ce que la veille de ce matin a vu. Un
# constat qui ne survit pas à son tour ne se lit jamais.
# Les deux flux restent deux flux — un refus de branchement part sur
# l'erreur standard, et c'est là qu'un appelant le cherche. Le rapport
# les reçoit tous les deux, parce que le lecteur d'après veut la page
# entière.
rapport="${ATELIER_VEILLE:-$HOME/.atelier/veille.txt}"
mkdir -p "$(dirname "$rapport")"
: > "$rapport"
exec > >(tee -a "$rapport") 2> >(tee -a "$rapport" >&2)

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
# Lire un état local n'est pas invoquer un agent — ça ne coûte rien et
# n'appelle personne. Mais une console peut porter une règle absolue
# « je ne lance pas le binaire d'un autre », et cette règle vaut mieux
# que ce contrôle : on la respecte, et on dit ce qu'on n'a pas regardé.
if [[ "${ATELIER_SANS_CLAUDE:-0}" == "1" ]]; then
  printf '?     claude — non regardé (ATELIER_SANS_CLAUDE=1)\n'
elif command -v claude >/dev/null 2>&1; then
  # Deux pannes distinctes, et les confondre coûte une soirée. Le
  # 14 septembre 2026, le binaire du PATH était un talon qui refusait
  # de démarrer — « native binary not installed » — et le poste de
  # relecture serait tombé à chaque réveil sans que rien ne rougisse.
  # Un binaire qui ne rend pas sa version n'est pas un binaire absent.
  if ! claude --version >/dev/null 2>&1; then
    printf 'FAIL  claude — présent mais il ne démarre pas : %s\n' \
      "$(claude --version 2>&1 | head -1)"
    printf '      node %s/install.cjs, ou réinstalle sans --omit=optional\n' \
      "$(dirname "$(dirname "$(readlink -f "$(command -v claude)")")")"
  elif etat_claude="$(claude auth status --text 2>&1)"; then
    printf 'PASS  claude — %s\n' "$(printf '%s' "$etat_claude" | head -1)"
  else
    printf 'FAIL  claude — pas connecté. Lance : claude setup-token\n'
  fi
else
  printf '?     claude — absent du PATH\n'
fi
for binaire in agent hermes; do
  if ! command -v "$binaire" >/dev/null 2>&1; then
    printf '?     %s — absent du PATH\n' "$binaire"
  elif "$binaire" --version >/dev/null 2>&1; then
    printf 'PASS  %s — %s\n' "$binaire" "$(command -v "$binaire")"
  else
    printf 'FAIL  %s — présent mais il ne démarre pas : %s\n' \
      "$binaire" "$("$binaire" --version 2>&1 | head -1)"
  fi
done

# Les deux `tee` écrivent dans un processus à part : sans cette attente,
# le script rendrait la main avant que le rapport soit complet, et son
# lecteur verrait une page tronquée sans savoir qu'elle l'est.
exec 1>&- 2>&-
wait
exit "$code"
