#!/usr/bin/env bash
# Poser l'état « relecture » sur la révision courante d'une PR.
#
# Ce script est un fichier, pas un bloc de YAML, pour une raison mesurée :
# GitHub joue les blocs `run:` avec `bash -e`, et un `set` qui n'éteint pas
# `errexit` laisse la première commande en échec tuer l'étape. C'est arrivé
# le 4 septembre 2026 sur la PR 225 — le verdict était « pas encore relue »,
# code 1, l'étape est morte là, et l'état n'a jamais été posé. Le contrôle
# ne rougissait pas : il n'existait pas. Un fichier se joue sur un banc
# (`outils/tests/test_scripts.py`), un bloc de YAML ne se joue nulle part.
#
# Il rend compte de lui-même, pas du verdict : le verdict est l'état qu'il
# pose. Il ne sort donc en erreur que s'il n'a pas pu le poser.
#
#   DEPOT      proprietaire/nom
#   PR         le numéro de la PR
#   REVISION   la révision jugée ; demandée à GitHub si elle est vide
set -uo pipefail

: "${DEPOT:?DEPOT manquant}"
: "${PR:?PR manquant}"
REVISION="${REVISION:-}"

if [ -z "$REVISION" ]; then
  # Sur appel, l'événement ne porte pas de révision : on la demande,
  # plutôt que de juger une PR sans savoir laquelle.
  REVISION=$(gh pr view "$PR" --json headRefOid -q .headRefOid) || REVISION=""
fi
if [ -z "$REVISION" ]; then
  echo "révision de la PR $PR introuvable : rien à juger, rien à poser" >&2
  exit 1
fi

# `|| code=$?` est la seule forme qui survive à `errexit` : un `$?` lu à la
# ligne suivante ne sera jamais atteint si la commande a échoué.
code=0
verdict=$(python -m outils relecture --depot "$DEPOT" --pr "$PR" --revision "$REVISION" 2>&1) || code=$?
echo "$verdict"

# Un outil muet n'est pas un outil qui approuve. Poser « success » sans
# savoir pourquoi serait le pire des états : une porte verte que personne
# n'a ouverte.
if [ -z "$verdict" ]; then
  echo "verdict vide (code $code) : rien à poser, on refuse plutôt que d'approuver" >&2
  exit 1
fi
if [ "$code" -eq 0 ]; then etat=success; else etat=failure; fi

# La ligne est déjà bornée par `outils` (github.borner) : rien à couper ici.
args=(-f state="$etat" -f context=relecture -f description="${verdict%%$'\n'*}")
# Un `target_url` vide se refuse plutôt que de s'écrire : GitHub garderait
# un lien mort sur le contrôle.
if [ -n "${LIEN:-}" ]; then args+=(-f target_url="$LIEN"); fi

gh api "repos/$DEPOT/statuses/$REVISION" "${args[@]}" > /dev/null || {
  echo "état « relecture » non posé sur $REVISION : GitHub a refusé" >&2
  exit 1
}
echo "état « relecture » posé sur $REVISION : $etat"
