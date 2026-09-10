#!/usr/bin/env bash
# Faire le geste que l'intégration a décidé : fusionner, rejouer, ou rien.
#
# La décision vient de `outils` et tient sur une ligne. Ce script ne décide
# rien : il ne sait même pas ce qu'est un contrôle. Il agit, et il échoue
# bruyamment sur une ligne qu'il ne comprend pas — une décision illisible
# traitée comme « rien » serait une file qui s'arrête sans le dire.
#
#   DEPOT      proprietaire/nom
#   DECISION   « fusionner N », « rebaser N » ou « RIEN »
#   BASE       la branche d'arrivée (master)
#   SORTIE     le fichier où écrire le numéro fusionné, s'il y en a un
set -euo pipefail

: "${DEPOT:?DEPOT manquant}"
: "${DECISION:?DECISION manquante}"
BASE="${BASE:-master}"
SORTIE="${SORTIE:-/dev/null}"

action=${DECISION%% *}
pr=${DECISION#* }

case "$action" in
  fusionner)
    branche=$(gh pr view "$pr" --json headRefName -q .headRefName)
    garde=()
    if [ -n "${REVISION_ATTENDUE:-}" ]; then
      garde+=(--match-head-commit "$REVISION_ATTENDUE")
    elif [ "${EXIGER_REVISION:-}" = true ]; then
      echo "révision jugée absente : fusion interdite" >&2
      exit 1
    fi
    gh pr merge "$pr" --merge "${garde[@]}"
    echo "fusionnee=$pr" >> "$SORTIE"
    # Le rangement de la branche vient après, et son échec ne compte pas :
    # une branche protégée ou déjà partie n'annule pas une fusion faite.
    # Grouper les deux gestes aurait fait d'un rangement raté un tour perdu.
    gh api -X DELETE "repos/$DEPOT/git/refs/heads/$branche" > /dev/null 2>&1 \
      || echo "branche $branche non supprimée (protégée, ou déjà partie)"
    # Le tour suivant prend la PR d'après. `workflow_dispatch` est l'un des
    # deux seuls événements qu'un jeton d'Actions a le droit de déclencher :
    # sans lui, la file attendrait le réveil de l'heure.
    gh workflow run integration.yml --ref "$BASE"
    echo "PR $pr fusionnée dans $BASE"
    ;;
  rebaser)
    branche=$(gh pr view "$pr" --json headRefName -q .headRefName)
    avant=$(gh pr view "$pr" --json headRefOid -q .headRefOid)
    gh api -X PUT "repos/$DEPOT/pulls/$pr/update-branch" -f expected_head_sha="$avant" > /dev/null

    # `update-branch` rend 202 : GitHub accepte, et pousse plus tard. Les
    # contrôles se demandent par un nom de branche, que GitHub résout à
    # l'instant de l'appel — les demander tout de suite les épinglerait sur
    # l'ANCIENNE révision, et la nouvelle n'aurait jamais de contrôle. On
    # attend donc que la tête ait bougé, et on ne suppose pas qu'elle a
    # bougé parce qu'on l'a demandé.
    apres=$avant
    for _ in $(seq 1 "${ATTENTE_REJEU:-30}"); do
      sleep "${PAS_REJEU:-2}"
      apres=$(gh pr view "$pr" --json headRefOid -q .headRefOid)
      [ "$apres" != "$avant" ] && break
    done
    if [ "$apres" = "$avant" ]; then
      echo "PR $pr : la tête n'a pas bougé après le rejeu ; contrôles non demandés" >&2
      exit 1
    fi

    # Le rejeu est une poussée du jeton d'Actions : GitHub ne déclenche rien
    # dessus. Sans ces trois appels, la PR changerait de révision et perdrait
    # tous ses contrôles — bloquée pour toujours, sans rien de rouge à
    # montrer.
    gh workflow run tests.yml --ref "$branche" -f base="$BASE" -f branche="$branche" -f pr="$pr"
    gh workflow run security.yml --ref "$branche"
    gh workflow run relecture.yml --ref "$BASE" -f pr="$pr"
    echo "PR $pr rejouée sur $BASE ($apres) ; ses contrôles repartent"
    ;;
  RIEN)
    echo "rien à intégrer ce tour-ci"
    ;;
  *)
    echo "décision illisible : « $DECISION »" >&2
    exit 1
    ;;
esac
