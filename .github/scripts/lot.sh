#!/usr/bin/env bash
# Une demande de lot devient une fiche au registre, en proposition.
#
# `outils saisie --ecrire` a déjà lu le formulaire et posé la fiche. Ici on
# l'emballe : une branche, un commit, une proposition, et un mot sur la
# demande pour dire où elle est partie.
#
#   DEPOT    proprietaire/nom
#   LIGNE    « lot NNN <souche> »
#   BASE     la branche d'arrivée (master)
#   ISSUE    le numéro de la demande, pour lui répondre
set -euo pipefail

: "${DEPOT:?DEPOT manquant}"
BASE="${BASE:-master}"
ISSUE="${ISSUE:-}"
reservee=false
reponse=false
numero_pr=0

if [ -n "${EVENEMENT_LOT:-}" ]; then
  plan=$(python3 -m outils demande --projet . --depot "$DEPOT" --evenement "$EVENEMENT_LOT")
  if [ "$plan" = RIEN ]; then
    echo "demande ignorée ou déjà traitée ; aucune écriture"
    exit 0
  fi
  read -r action numero branche ISSUE numero_pr reservee reponse <<< "$plan"
  [ "$action" = deposer ] || { echo "plan de demande illisible" >&2; exit 1; }
else
  # Appel local explicite, sans événement GitHub. Le workflow passe toujours
  # par la garde ci-dessus, même lors d'un rejeu manuel dans Actions.
  : "${LIGNE:?LIGNE manquante}"
  numero=$(echo "$LIGNE" | cut -d' ' -f2)
  souche=$(echo "$LIGNE" | cut -d' ' -f3)
  branche="feuille/$souche"
fi

if [ "$reservee" != true ] && git ls-remote --exit-code --heads origin "$branche" > /dev/null 2>&1; then
  echo "$branche existe déjà : la demande a déjà été traitée" >&2
  exit 1
fi

{
  printf "Le lot %s entre au registre, état « a-briefer ».\n\n" "$numero"
  printf "Il vient de la demande #%s. Le bon de travail reste à écrire : le\n" "${ISSUE:-?}"
  printf "poste d'écriture le fera, et sa proposition passera la fiche à « pret ».\n"
} > corps.txt
{ printf "Le lot %s entre au registre.\n\n" "$numero"; cat corps.txt; } > message.txt

# La même connexion que pour un palier : GitHub doit pouvoir relier ce
# commit à quelqu'un, sinon la relecture refuse avant de regarder quoi que
# ce soit (AGENTS.md, règle de rôle).
if [ "$reservee" != true ]; then
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git checkout -b "$branche"
  git add ROADMAP.md
  git commit --file message.txt
  # Sans force : une réservation concurrente fait échouer la poussée.
  git push -u origin "$branche"
fi

if [ "$numero_pr" = 0 ]; then
  lien=$(gh pr create --repo "$DEPOT" --base "$BASE" --head "$branche" \
    --title "Lot $numero entre au registre" --body-file corps.txt)
  numero_pr=${lien##*/}
else
  lien="https://github.com/$DEPOT/pull/$numero_pr"
fi

# Une proposition ouverte par le jeton d'Actions ne déclenche aucun
# contrôle : GitHub refuse la récursion. On les demande donc nommément.
if [ "$reponse" != true ]; then
gh workflow run tests.yml --ref "$branche" -f base="$BASE" -f branche="$branche"
gh workflow run security.yml --ref "$branche"
gh workflow run relecture.yml --ref "$BASE" -f pr="$numero_pr"
fi

if [ -n "$ISSUE" ]; then
  if [ "$reponse" != true ]; then
    gh issue comment "$ISSUE" --repo "$DEPOT" --body "Le lot $numero entre au registre : $lien
<!-- demande-lot:$ISSUE:succes -->"
  fi
  gh issue close "$ISSUE" --repo "$DEPOT" --reason completed
fi
echo "lot $numero déposé par la proposition $numero_pr"
