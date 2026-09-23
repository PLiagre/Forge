#!/usr/bin/env bash
# Les profils de la console, un par rôle, chacun dans son répertoire.
#
# Pourquoi un profil par rôle : la console garde un répertoire courant
# par profil. Sans ça, le coder et le briefer travailleraient dans le
# même arbre, et deux lots se marcheraient dessus — ce que les verrous
# de fichiers empêchent *à l'intérieur* d'un arbre, pas entre deux rôles
# qui partagent le même.
#
# `--dry-run` imprime et n'écrit rien. C'est le mode par défaut : une
# commande qui touche la configuration d'un outil ne s'exécute pas parce
# qu'on l'a tapée sans argument.
set -euo pipefail

_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"

mode="${1:---dry-run}"
case "$mode" in
  --dry-run|--run) ;;
  *) dire "usage : installer-profils.sh [--dry-run|--run]"; exit 2 ;;
esac

projet="${ATELIER_PROJET:-/srv/ForgeHistory}"

# Qui travaille où. Le pilote et le relecteur lisent : le clone leur
# suffit. Le coder et le briefer écrivent : ils ont leur arbre.
repertoire_du_role() {
  case "$1" in
    coder)   printf '%s-coder\n' "$projet" ;;
    briefer) printf '%s-briefer\n' "$projet" ;;
    *)       printf '%s\n' "$projet" ;;
  esac
}

faire() {
  if [[ "$mode" == "--run" ]]; then
    "$@"
  else
    printf '%s\n' "$*"
  fi
}

if [[ "$mode" == "--run" ]] && ! command -v hermes >/dev/null 2>&1; then
  dire "hermes est introuvable dans le PATH : rien n'a été écrit"
  exit 1
fi

for role in pilote briefer coder relire; do
  cible="$(repertoire_du_role "$role")"
  # `--clone-from default` part de la session déjà authentifiée : on ne
  # redemande jamais de se connecter, et aucune clé n'entre ici.
  faire hermes profile create "$role" --clone-from default
  faire hermes --profile "$role" config set terminal.cwd "$cible"
done

if [[ "$mode" != "--run" ]]; then
  echo
  echo "# l'environnement que le profil du jour pose, pour mémoire :"
  echo "ATELIER_PROJET=$projet"
  echo "ATELIER_WORKDIR_coder=$(repertoire_du_role coder)"
  echo "ATELIER_WORKDIR_briefer=$(repertoire_du_role briefer)"
  echo
  echo "# rien n'a été écrit. Rejoue avec --run pour appliquer."
fi
