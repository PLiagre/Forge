#!/usr/bin/env bash
# Le tour du pilote : la feuille de route décide, Hermes rend compte.
#
# La décision n'est pas prise ici, et elle n'est pas prise par Hermes :
# elle est calculée par `atelier piloter`, en Python, contre le registre
# des lots. Hermes reçoit ce qui a été fait ; il n'invente ni numéro de
# lot, ni statut, ni chemin. C'est ce qui fait qu'une console bavarde ne
# peut pas déposer une carte que la feuille ne commande pas.
set -euo pipefail

_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"
atelier_defauts
atelier_pythonpath

if [[ -z "${ATELIER_PROJET:-}" ]]; then
  dire "pilote : ATELIER_PROJET n'est pas posé — l'atelier ne devine pas le dépôt produit"
  exit 2
fi
projet="$ATELIER_PROJET"

# La feuille de route vient de la base : décider sur une copie périmée,
# c'est redéposer un lot déjà livré.
if [[ "${ATELIER_SANS_PULL:-0}" != "1" ]]; then
  git -C "$projet" pull --ff-only >&2 2>&1 || dire "pilote : base non rafraîchie — on continue"
fi

arme=0
[[ "${ATELIER_INVOQUER:-0}" == "1" ]] && arme=1

# La décision, et ce qu'elle a coûté. On garde les deux flux : un FAIL
# part sur stderr, et c'est précisément ce qu'Hermes doit lire.
run=()
(( arme )) && run=(--run)
code=0
decision="$(atelier piloter --projet "$projet" "${run[@]+"${run[@]}"}" 2>&1)" || code=$?
printf '%s\n' "$decision"

if (( ! arme )); then
  # À sec, on montre aussi la commande qu'on aurait lancée : c'est la
  # seule façon de vérifier un prompt sans payer pour le lire.
  atelier invocation --role pilote --projet "$projet" --decision "$decision" || true
  echo "à sec : aucune carte déposée, aucun quota dépensé"
  exit 0
fi

# Rien à dire n'est pas une raison de réveiller quelqu'un. Un tour à vide
# est juste : il coûte zéro.
if [[ "$(printf '%s' "$decision" | tr -d '[:space:]')" == "RIEN" ]]; then
  exit 0
fi

# La console rend compte ; elle ne décide rien, et la décision est déjà
# dans le journal. Sur le VPS, du 3 au 12 septembre 2026, elle a rendu
# cinq réponses vides sur cinq invocations, sur un quota payant. Elle ne
# s'appelle donc que si on le demande : ATELIER_CONSOLE=1 dans le profil.
if [[ "${ATELIER_CONSOLE:-0}" != "1" ]]; then
  exit "$code"
fi

argv=()
mapfile -t -d '' argv < <(atelier invocation --role pilote --projet "$projet" --decision "$decision" --nul)
if (( ! ${#argv[@]} )); then
  dire "pilote : l'atelier n'a rendu aucune commande"
  exit 1
fi

delai="${ATELIER_TIMEOUT:-900}"
hermes=0
( cd "$projet" && sans_cles timeout -k 10 "$delai" "${argv[@]}" ) || hermes=$?
(( hermes == 0 )) || dire "pilote : la console a rendu le code $hermes"

# Le code de sortie est celui de la décision, pas celui de la console :
# une feuille incohérente reste un échec même si Hermes a bien parlé.
exit "$code"
