#!/usr/bin/env bash
# Sortir une proposition du brouillon, et lui redonner ses contrôles.
#
# Un brouillon n'est pas regardé par la chaîne : `integration.examiner`
# le dit et s'arrête là. Les propositions de couverture de tests arrivent
# en brouillon, et elles y restent tant que personne ne les en sort.
#
# GitHub ne déclenche `pull_request` que sur `opened`, `synchronize` et
# `reopened` : sortir du brouillon ne relance aucun travail. Les
# contrôles se redemandent donc dans le même geste, sinon la proposition
# passerait de « brouillon » à « contrôle absent » sans rien y gagner.
#
#   DEPOT   proprietaire/nom
#   PR      le numéro de la proposition
#   BASE    la branche d'arrivée (master)
set -uo pipefail

: "${DEPOT:?DEPOT manquant}"
: "${PR:?PR manquant}"
BASE="${BASE:-master}"

code=0
ligne=$(python3 -m outils brouillon --depot "$DEPOT" --pr "$PR" 2> raison.log) || code=$?
cat raison.log >&2
if [ "$code" != 0 ]; then
  echo "la décision n'a pas pu être prise pour la proposition $PR : rien n'est touché" >&2
  exit 1
fi

if [ "$ligne" = RIEN ]; then
  echo "la proposition $PR n'est pas un brouillon à sortir"
  exit 0
fi

read -r action numero branche <<< "$ligne"
if [ "$action" != sortir ]; then
  echo "décision illisible : « $ligne »" >&2
  exit 1
fi

gh pr ready "$numero" --repo "$DEPOT"
gh workflow run tests.yml --ref "$branche" -f base="$BASE" -f branche="$branche" -f pr="$numero"
gh workflow run security.yml --ref "$branche"
gh workflow run relecture.yml --ref "$BASE" -f pr="$numero"
echo "proposition $numero sortie du brouillon ; ses contrôles repartent"
