#!/usr/bin/env bash
# Déposer la fiche du lot de stabilisation d'une couche finie, en PR.
#
# Ce script n'a rien décidé : `outils palier --ecrire` a lu le registre,
# posé la fiche en tête, et rendu une ligne. Ici on l'emballe dans une
# branche, un commit et une PR — et on redemande les contrôles, parce
# qu'une PR ouverte par un jeton d'Actions n'en déclenche aucun.
#
#   DEPOT    proprietaire/nom
#   LIGNE    « palier NNN <souche> couche=N », ou « RIEN »
#   BASE     la branche d'arrivée (master)
#   COMPTE_RENDU  ce que `outils palier` a dit, repris dans le corps de la PR
set -euo pipefail

: "${DEPOT:?DEPOT manquant}"
: "${LIGNE:?LIGNE manquante}"
BASE="${BASE:-master}"
COMPTE_RENDU="${COMPTE_RENDU:-palier.log}"

if [ "$LIGNE" = "RIEN" ]; then
  echo "aucune couche finie n'attend son palier"
  exit 0
fi

numero=$(echo "$LIGNE" | cut -d' ' -f2)
souche=$(echo "$LIGNE" | cut -d' ' -f3)
couche=$(echo "$LIGNE" | cut -d' ' -f4 | cut -d= -f2)
branche="feuille/$souche"

# La garde d'idempotence porte sur une PR OUVERTE de cette COUCHE.
#
# Sur la couche, pas sur le numéro : tant que la PR du palier n'est pas
# fusionnée, sa fiche n'est pas dans la base et chaque tour la
# reproposerait ; et si une PR de feuille passe entre-temps, le numéro
# libre a changé — la même couche repartirait sous un autre nom.
#
# Sur une PR ouverte, pas sur une branche : une branche poussée dont la PR
# a été fermée bloquerait le palier de cette couche pour toujours, en
# silence. Refuser un palier se fait en passant sa fiche à `abandonne` —
# la fiche couvre alors ses lots et la couche cesse d'en réclamer un.
ouverte=$(gh pr list --state open --base "$BASE" --json number,headRefName \
  --jq ".[] | select(.headRefName | endswith(\"-stabilisation-couche-$couche\")) | .number" \
  | head -1)
if [ -n "$ouverte" ]; then
  echo "la PR $ouverte porte déjà le palier de la couche $couche : rien à faire"
  exit 0
fi

# Une branche restée d'une PR fermée porte une fiche qui n'a jamais atterri.
# Elle ne vaut plus rien, et elle empêcherait la poussée d'aboutir.
if git ls-remote --exit-code --heads origin "$branche" > /dev/null 2>&1; then
  echo "$branche traîne sans PR ouverte : on la retire avant de repousser"
  git push origin --delete "$branche"
fi

{
  printf "La couche %s est finie : la fiche du lot %s entre au registre,\n" "$couche" "$numero"
  printf "état « a-briefer ». Chaque lot de cette couche a prouvé sa règle ;\n"
  printf "aucun n'a prouvé qu'ils tiennent ensemble. C'est ce que le lot de\n"
  printf "stabilisation et QA va mesurer.\n\n"
  printf "Ce que le registre dit :\n\n"
  sed "s/^/    /" "$COMPTE_RENDU"
  printf "\nLe brief reste à écrire : le poste d'écriture le fera, et sa PR\n"
  printf "passera la fiche à « pret ».\n"
} > corps.txt
{ printf "Palier couche %s : le lot %s entre au registre.\n\n" "$couche" "$numero"
  cat corps.txt; } > message.txt

# L'identité du commit doit être une connexion que GitHub sait relier, et
# pas un nom inventé : `auteurs_du_code` lit les connexions des commits, et
# une adresse que GitHub ne relie à personne rend cette liste vide. La
# relecture refuse alors avant même de regarder les approbations — « aucun
# auteur connu » — et la PR du palier ne pourrait jamais devenir
# intégrable. L'adresse `noreply` du robot d'Actions est celle qui se relie
# à la connexion `github-actions[bot]`.
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git checkout -b "$branche"
git add ROADMAP.md
git commit --file message.txt
git push -u origin "$branche"
lien=$(gh pr create --base "$BASE" --head "$branche" \
  --title "Palier couche $couche : stabilisation et QA (lot $numero)" \
  --body-file corps.txt)
numero_pr=${lien##*/}
gh workflow run tests.yml --ref "$branche" -f base="$BASE" -f branche="$branche"
gh workflow run security.yml --ref "$branche"
gh workflow run relecture.yml --ref "$BASE" -f pr="$numero_pr"
echo "PR $numero_pr de palier ouverte sur $branche"
