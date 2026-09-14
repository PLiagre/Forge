#!/usr/bin/env bash
# Un tour d'un rôle : une carte, un agent, et la carte rangée. Puis on sort.
#
# Personne n'attend personne : boîte vide, on sort 0 sans rien dire. Le
# rôle courant n'appelle jamais le rôle suivant — c'est le réveil suivant
# qui le fait, et c'est ce qui rend un tour interrompu sans conséquence.
#
# Ce script ne tient aucune table : ni modèle, ni abonnement, ni garde de
# lecture seule. Il les demande à `python3 -m atelier`. La règle 13 du
# dépôt produit tient ici : sous `set -e`, le seul moyen de lire un `$?`
# est `cmd || code=$?` — la ligne d'après n'est jamais atteinte.
set -euo pipefail

_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"
atelier_defauts
atelier_pythonpath

role="${1:-}"
if [[ -z "$role" ]]; then
  dire "usage : tour.sh <briefer|planifier|coder|relire|pilote>"
  exit 2
fi

# Le pilote n'a pas de boîte : il lit la feuille de route. Il a son
# script, et le cron n'a pas à connaître la différence.
if [[ "$role" == "pilote" ]]; then
  exec bash "$ATELIER_ROOT/crons/pilote.sh"
fi

if [[ -z "${ATELIER_PROJET:-}" ]]; then
  dire "tour $role : ATELIER_PROJET n'est pas posé — l'atelier ne devine pas le dépôt produit"
  exit 2
fi
projet="$ATELIER_PROJET"

# --------------------------------------------------------------- le verrou
# Un verrou par rôle, pas un verrou global : un briefer doit pouvoir
# passer pendant qu'un coder tient encore sa carte.
mkdir -p "$ATELIER_VERROUS"
exec 9>"$ATELIER_VERROUS/atelier-$role.lock"
if ! flock -n 9; then
  dire "tour $role : un tour tourne encore — celui-ci passe son tour"
  exit 0
fi

# ------------------------------------------------------------- la carte
# `rappeler` ne tourne que sous drapeau : à sec, on ne déplace rien.
if [[ "${ATELIER_INVOQUER:-0}" == "1" ]]; then
  atelier rappeler --projet "$projet" --role "$role" >&2 || true
fi

code=0
lot="$(atelier prochain --projet "$projet" --role "$role" --champ lot)" || code=$?
if (( code != 0 )); then
  # Une carte illisible ou incomplète ne lance rien : `prochain` a déjà
  # nommé le fichier à réparer sur stderr.
  exit 1
fi
[[ "$lot" == "RIEN" ]] && exit 0

brief="$(atelier prochain --projet "$projet" --role "$role" --champ brief)" || exit 1

# ----------------------------------------------------------- le mode à sec
# Sans drapeau, on imprime la ligne de commande exacte et on s'arrête. La
# carte ne bouge pas, aucun quota n'est dépensé.
if [[ "${ATELIER_INVOQUER:-0}" != "1" ]]; then
  atelier invocation --role "$role" --projet "$projet" --lot "$lot" --brief "$brief"
  echo "branche du lot : $(atelier branche --projet "$projet" --lot "$lot")"
  # `pret` dit ce qui manquerait pour armer — dont l'armement lui-même.
  # Son code ne gouverne pas celui du tour : à sec, regarder ne rate pas.
  atelier pret --projet "$projet" || true
  exit 0
fi

# --------------------------------------------------------------- l'échec
# Ranger la carte et rendre le verrou, sur tous les chemins de sortie.
# La cause est le mot que la machine compare ; la raison, la phrase pour l'œil.
echouer() {
  local cause="$1" raison="$2"
  if [[ "$role" == "coder" ]]; then
    atelier lever --projet "$projet" --lot "$lot" >&2 || true
  fi
  atelier echouer --projet "$projet" --role "$role" --lot "$lot" \
    --cause "$cause" --raison "$raison" >&2 || true
  dire "tour $role : $lot → echec ($raison)"
  exit 1
}

# ------------------------------------------------------------ le brief
# Le briefer *écrit* le brief : le sien n'existe pas encore, et l'exiger
# parquerait tous les lots à briefer. Les trois autres le lisent — sans
# lui, l'agent dépenserait un quota sur une instruction qui n'existe pas.
if [[ "$role" != "briefer" ]]; then
  chemin_brief="$brief"
  [[ "$chemin_brief" != /* ]] && chemin_brief="$projet/$brief"
  if [[ ! -f "$chemin_brief" ]]; then
    echouer brief-absent "brief introuvable : $brief"
  fi
fi

# ------------------------------------------------------------- le quota
# L'abonnement vient du branchement du produit, jamais d'une table ici.
# Un quota qu'on n'a pas lu vaut -1, jamais 0 : un inconnu ne se compte
# pas pour un épuisement.
abo="$(atelier poste --projet "$projet" --role "$role" --champ abo)" || abo=""
restant=-1
mesure="${ATELIER_QUOTA_CMD:-llmquota}"
if command -v "$mesure" >/dev/null 2>&1; then
  brut="$("$mesure" "$abo" 2>/dev/null || true)"
  brut="${brut//[$' \t\r\n']/}"
  [[ "$brut" =~ ^[0-9]+$ ]] && restant="$brut"
fi

if (( restant == 0 )); then
  dire "tour $role : quota épuisé — la carte $lot reste en place"
  exit 0
fi

# Le planificateur est facultatif et partage l'abonnement de l'exécutant.
# Quand il ne reste qu'un tour et qu'une carte attend le coder, le
# facultatif cède : le critique passe d'abord.
if [[ "$role" == "planifier" ]] && (( restant >= 0 && restant <= 1 )); then
  attend="$(atelier prochain --projet "$projet" --role coder --champ lot 2>/dev/null)" || attend="RIEN"
  if [[ "$attend" != "RIEN" ]]; then
    dire "tour planifier : quota court ($restant) et $attend attend le coder — le facultatif cède"
    exit 0
  fi
fi

# ------------------------------------------------- la garde de lecture seule
# « Celui qui a écrit le code ne dit pas s'il est recevable » ne tient
# que si le relecteur n'a pas la main qui écrit. Quand le binaire ne sait
# pas qu'on la lui retire, on le dit — et on relit quand même : un
# relecteur bavard vaut mieux que pas de relecteur.
garde="$(atelier poste --projet "$projet" --role "$role" --champ lecture_seule)" || garde=""
if [[ "$role" == "relire" && "$garde" != "tenue" ]]; then
  dire "tour relire : garde de lecture seule non tenue — ce binaire garde la main qui écrit"
fi

# ------------------------------------------------------------ le périmètre
# Seul le coder écrit du code : lui seul tient des fichiers. Le verrou
# reste posé après le tour — c'est la fusion qui le rend, par le pilote.
if [[ "$role" == "coder" ]]; then
  atelier verrouiller --projet "$projet" --role "$role" --lot "$lot" >&2 \
    || echouer perimetre "périmètre indisponible ou vide pour $lot"
fi

# ------------------------------------------------------------- le worktree
nom_workdir="ATELIER_WORKDIR_$role"
workdir="${!nom_workdir:-$projet}"
[[ -d "$workdir" ]] || echouer worktree "worktree introuvable : $workdir"

# ------------------------------------------------------------ l'identité
# Un commit signé d'une adresse que GitHub ne relie à personne rend la
# liste des auteurs vide, et la relecture refuse avant de regarder quoi
# que ce soit : « aucun auteur connu ». L'adresse vient de la config de
# la machine ; sans elle, l'agent signe comme il sait, et on le dit.
if [[ "$role" == "coder" || "$role" == "briefer" ]]; then
  if [[ -n "${ATELIER_GIT_EMAIL:-}" ]]; then
    git -C "$workdir" config user.email "$ATELIER_GIT_EMAIL"
    git -C "$workdir" config user.name "${ATELIER_GIT_NOM:-atelier}"
  elif [[ -z "$(git -C "$workdir" config --get user.email 2>/dev/null)" ]]; then
    dire "tour $role : aucune identité git dans $workdir — pose ATELIER_GIT_EMAIL dans ~/.atelier/config, l'adresse d'un compte GitHub"
  fi
fi

# ------------------------------------------------------------- le jeton
# GitHub refuse qu'un compte approuve sa propre PR. Le relecteur signe
# donc avec un jeton à lui — un second compte, collaborateur du dépôt —
# et jamais avec la session qui a ouvert la PR. Sans jeton, la revue
# sera refusée par GitHub et la carte tombera en echec : on prévient.
if [[ "$role" == "relire" ]]; then
  jeton="${ATELIER_RELIRE_TOKEN:-$HOME/.atelier/relire.token}"
  if [[ -s "$jeton" ]]; then
    GH_TOKEN="$(tr -d '[:space:]' < "$jeton")"
    export GH_TOKEN
  else
    dire "tour relire : aucun jeton dans $jeton — GitHub refusera l'approbation d'un compte sur sa propre PR"
  fi
fi

# La base d'abord : un lot se code sur ce qui a été fusionné depuis.
if [[ "${ATELIER_SANS_PULL:-0}" != "1" ]]; then
  git -C "$projet" pull --ff-only >&2 2>&1 || dire "tour $role : base non rafraîchie — on continue"
fi

# Ranger n'appartient qu'au coder, et la distinction a été mesurée sur
# le banc : `ranger` enregistre ce qui traîne pour que `preparer_lot` ne
# refuse pas un worktree sale — c'est utile avant de basculer de branche,
# et seul le coder bascule. Joué pour les autres rôles, dont le worktree
# est le clone du produit resté sur la base, il enregistrait `.atelier/`
# et le canal d'échange dans un commit de `master`. Un tour de relecture
# n'écrit rien : c'est la règle, elle vaut aussi pour le shell qui
# l'invoque.
if [[ "$role" == "coder" ]]; then
  atelier ranger --worktree "$workdir" >&2 || true
  atelier branche --projet "$projet" --lot "$lot" --worktree "$workdir" --run >&2 \
    || echouer branche "branche du lot impossible dans $workdir"
fi

# Le canal d'échange, avec sa garde git. Un numéro périmé ne doit pas
# s'attacher au lot suivant : on l'efface avant, pas seulement après.
canal="$(atelier canal --worktree "$workdir")" || echouer worktree "canal impossible dans $workdir"
rm -f "$canal/pr.txt"

# ----------------------------------------------------------- l'invocation
# L'argv vient de Python, séparé par des NUL : le shell ne recompose
# aucune ligne de commande, il exécute celle-là.
arguments=(--role "$role" --projet "$projet" --lot "$lot" --brief "$brief")
pr_carte="$(atelier prochain --projet "$projet" --role "$role" --champ pr)" || pr_carte=""
[[ -n "$pr_carte" && "$pr_carte" != "RIEN" ]] && arguments+=(--pr "$pr_carte")

argv=()
mapfile -t -d '' argv < <(atelier invocation "${arguments[@]}" --nul)
(( ${#argv[@]} )) || echouer inconnue "l'atelier n'a rendu aucune commande pour $role"

delai="${ATELIER_TIMEOUT:-2400}"
code=0
( cd "$workdir" && sans_cles timeout -k 10 "$delai" "${argv[@]}" ) || code=$?

if (( code != 0 )); then
  if (( code == 124 || code == 137 )); then
    echouer timeout "délai dépassé après ${delai}s"
  fi
  echouer agent "l'agent a rendu le code $code"
fi

# ------------------------------------------------------- le numéro de PR
# Deux rôles ouvrent une PR, et le numéro ne pèse pas le même poids.
#
# Le coder : sans lui, `a-relire` n'est jamais alimentée et la chaîne
# s'arrête en silence — un code 0 ne suffit donc pas, la carte tombe.
# Le briefer : sa carte attend la fusion du brief, que le pilote
# rapproche depuis la feuille de route. Le numéro aide à suivre ; il ne
# porte rien. L'exiger parquerait un brief bel et bien écrit.
pr=""
if [[ "$role" == "coder" ]]; then
  # La branche n'est vérifiable que pour le coder : le briefer travaille
  # sur `brief/<lot>`, que `prefixe_branche` ne décrit pas.
  sonde=()
  attendue="$(atelier branche --projet "$projet" --lot "$lot")" || attendue=""
  [[ -n "$attendue" ]] && sonde=(--branche "$attendue" --worktree "$workdir")
  code=0
  pr="$(atelier pr --fichier "$canal/pr.txt" "${sonde[@]+"${sonde[@]}"}")" || code=$?
  (( code == 0 )) || echouer pr "aucun numéro de PR lisible dans atelier-echange/pr.txt"
elif [[ "$role" == "briefer" ]]; then
  pr="$(atelier pr --fichier "$canal/pr.txt" 2>/dev/null)" || pr=""
fi
rm -f "$canal/pr.txt"

# ------------------------------------------------------------- la revue
# Le relecteur ne rend pas compte au cron : il pose une revue sur la PR,
# et c'est elle qu'on lit. Approuvée, la carte passe et l'intégration
# fusionnera. Changements demandés, ou aucune revue : la carte tombe, et
# la cause ne se retente pas — le coder ne lit pas les revues, le brief
# est sa seule source, et rejouer paierait le même résultat.
if [[ "$role" == "relire" ]]; then
  if [[ -z "$pr_carte" || "$pr_carte" == "RIEN" ]]; then
    # Une carte sans numéro n'a nulle part où porter une revue : l'avis
    # est au journal, et on le dit plutôt que de faire semblant de lire.
    dire "tour relire : la carte $lot ne nomme aucune PR — avis au journal, aucune revue lue"
  else
    verdict="$(cd "$workdir" && gh pr view "$pr_carte" --json reviews \
      --jq '[.reviews[] | select(.state == "APPROVED" or .state == "CHANGES_REQUESTED")] | last | .state // ""' \
      2>/dev/null)" || verdict=""
    case "$verdict" in
      APPROVED) ;;
      CHANGES_REQUESTED)
        echouer relecture "changements demandés sur la PR $pr_carte — lire la revue, puis fermer la PR et \`atelier reprendre\`, ou repasser la fiche à a-briefer" ;;
      *)
        echouer relecture "aucune revue posée sur la PR $pr_carte — un avis qui n'est pas sur la PR n'existe pas" ;;
    esac
  fi
fi

# ---------------------------------------------------------- la carte passe
suite=()
[[ -n "$pr" ]] && suite=(--pr "$pr")
atelier avancer --projet "$projet" --role "$role" --lot "$lot" "${suite[@]+"${suite[@]}"}" >&2 \
  || echouer avancer "la carte $lot n'a pas pu passer au rôle suivant"

exit 0
