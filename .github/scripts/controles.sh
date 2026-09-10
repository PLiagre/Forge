#!/usr/bin/env bash
# Redemander les contrôles d'une proposition dont ils manquent.
#
# Le cas ordinaire : une proposition ouverte par le jeton d'Actions —
# celle d'un palier, celle d'une demande de lot — ne déclenche aucun
# travail, parce que GitHub refuse la récursion sur ce qu'un jeton
# d'Actions a produit. Elle reste alors sans contrôle, donc bloquée, et
# muette sur la raison.
#
# Ce script ne décide rien : `outils controles` a lu la proposition et
# rendu une ligne. En particulier c'est lui qui dit « déjà fait » quand
# les contrôles requis sont là — un geste déclenché deux fois ne se fait
# pas deux fois.
#
#   DEPOT   proprietaire/nom
#   PR      le numéro de la proposition
#   BASE    la branche d'arrivée (master)
set -uo pipefail

: "${DEPOT:?DEPOT manquant}"
: "${PR:?PR manquant}"
BASE="${BASE:-master}"

# `|| code=$?` est la seule forme qui survive à `errexit` : la ligne
# d'après ne serait jamais atteinte si la commande échouait (règle 13).
code=0
ligne=$(python3 -m outils controles --depot "$DEPOT" --projet . --pr "$PR" 2> raison.log) || code=$?
cat raison.log >&2
if [ "$code" != 0 ]; then
  echo "la décision n'a pas pu être prise pour la proposition $PR : rien n'est redemandé" >&2
  exit 1
fi

if [ "$ligne" = RIEN ]; then
  echo "rien à redemander sur la proposition $PR"
  exit 0
fi

read -r action numero branche revision <<< "$ligne"
if [ "$action" != redemander ]; then
  echo "décision illisible : « $ligne »" >&2
  exit 1
fi

# Les trois travaux, nommément. `relecture` se joue depuis la base : il
# ne doit pas tourner sur le code de la proposition qu'il juge.
gh workflow run tests.yml --ref "$branche" -f base="$BASE" -f branche="$branche" -f pr="$numero"
gh workflow run security.yml --ref "$branche"
gh workflow run relecture.yml --ref "$BASE" -f pr="$numero"
echo "contrôles redemandés sur $branche ($revision) pour la proposition $numero"
