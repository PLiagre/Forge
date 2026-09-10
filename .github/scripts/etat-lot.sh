#!/usr/bin/env bash
# Changer l'état d'un lot — par une proposition, jamais par une écriture directe.
#
# L'état d'un lot ne s'écrit qu'à un endroit : sa fiche au registre. Et
# rien n'entre dans la base sans passer par une proposition relue : c'est
# vrai d'un lot, c'est vrai d'un palier, c'est vrai ici. Ce travail écrit
# donc la fiche sur une branche, ouvre la proposition, et s'arrête là.
#
# La transition n'est pas jugée ici : `outils etat` la confie au même
# code que `atelier feuille valider`. Une transition interdite fait
# rougir ce travail, avec le message qui la nomme.
#
#   DEPOT   proprietaire/nom
#   LOT     le numéro du lot, 049
#   ETAT    l'état visé : abandonne, idee
#   BASE    la branche d'arrivée (master)
set -uo pipefail

: "${DEPOT:?DEPOT manquant}"
: "${LOT:?LOT manquant}"
: "${ETAT:?ETAT manquant}"
BASE="${BASE:-master}"

# Un premier passage sans `--ecrire` : il valide la transition et donne la
# souche de la branche. Rien n'est touché tant qu'on ne sait pas si le
# geste a déjà été fait.
code=0
ligne=$(python3 -m outils etat --projet . --lot "$LOT" --etat "$ETAT" 2> raison.log) || code=$?
cat raison.log >&2
if [ "$code" != 0 ]; then
  echo "le lot $LOT ne passe pas à « $ETAT » : rien n'est écrit" >&2
  exit 1
fi

if [ "$ligne" = RIEN ]; then
  echo "le lot $LOT est déjà dans l'état demandé"
  exit 0
fi

read -r action numero etat souche <<< "$ligne"
if [ "$action" != etat ]; then
  echo "décision illisible : « $ligne »" >&2
  exit 1
fi
branche="feuille/$souche"

# La garde d'idempotence porte sur une proposition OUVERTE de cette
# branche : tant qu'elle n'est pas fusionnée, la fiche n'a pas bougé dans
# la base, et chaque réveil la reproposerait.
ouverte=$(gh pr list --state open --base "$BASE" --json number,headRefName \
  --jq ".[] | select(.headRefName == \"$branche\") | .number" | head -1)
if [ -n "$ouverte" ]; then
  echo "la proposition $ouverte porte déjà ce changement d'état : rien à faire"
  exit 0
fi

# Une branche restée d'une proposition fermée porte une fiche qui n'a
# jamais atterri. Elle ne vaut plus rien, et elle empêcherait la poussée.
if git ls-remote --exit-code --heads origin "$branche" > /dev/null 2>&1; then
  echo "$branche traîne sans proposition ouverte : on la retire avant de repousser"
  git push origin --delete "$branche"
fi

python3 -m outils etat --projet . --lot "$LOT" --etat "$ETAT" --ecrire > /dev/null

{
  printf "Le lot %s passe à « %s ».\n\n" "$numero" "$etat"
  printf "L'état d'un lot ne s'écrit que dans sa fiche, et rien n'entre dans\n"
  printf "%s sans proposition : celle-ci porte le changement, et rien d'autre.\n" "$BASE"
} > corps.txt
{ printf "Le lot %s passe à « %s ».\n\n" "$numero" "$etat"; cat corps.txt; } > message.txt

# La même connexion que pour un palier : GitHub doit pouvoir relier ce
# commit à quelqu'un, sinon la relecture refuse avant de regarder quoi que
# ce soit — « aucun auteur de commit connu ».
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git checkout -b "$branche"
git add ROADMAP.md
git commit --file message.txt
git push -u origin "$branche"
lien=$(gh pr create --repo "$DEPOT" --base "$BASE" --head "$branche" \
  --title "Le lot $numero passe à « $etat »" --body-file corps.txt)
numero_pr=${lien##*/}

# Une proposition ouverte par le jeton d'Actions ne déclenche aucun
# contrôle : on les demande nommément.
gh workflow run tests.yml --ref "$branche" -f base="$BASE" -f branche="$branche" -f pr="$numero_pr"
gh workflow run security.yml --ref "$branche"
gh workflow run relecture.yml --ref "$BASE" -f pr="$numero_pr"
echo "proposition $numero_pr ouverte : lot $numero → $etat"
