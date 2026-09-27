#!/usr/bin/env bash
# Le répartiteur : la seule ligne de la crontab de l'utilisateur, appelée
# chaque minute. Il lit le profil actif (~/.atelier/etat/profil), demande au
# profil quels rôles se réveillent à cette minute, et lance leurs tours.
# Changer de cadence, ou tout arrêter, n'est qu'une écriture de fichier :
# `atelier-boucle jour` ou `atelier-boucle arret`.
#
# Le défaut n'arme jamais : pas de fichier, pas de réveil.
set -euo pipefail

_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"
atelier_defauts

fichier="$ATELIER_ETAT/profil"
[[ -f "$fichier" ]] || exit 0

profil="$(tr -d '[:space:]' < "$fichier")"

# Un profil vide vaut l'arrêt : on ne devine pas une cadence.
[[ -z "$profil" || "$profil" == "arret" ]] && exit 0

if [[ ! -f "$CRONS/profils/$profil.sh" ]]; then
  dire "profil inconnu : $profil"
  exit 2
fi

# Le profil pose l'environnement et répond à deux questions. Il est
# sourcé, pas exécuté : c'est lui qui décide du PATH et des chemins.
# shellcheck source=/dev/null
. "$CRONS/profils/$profil.sh"

maintenant="$(date +%H:%M)"
roles="$(roles_du_moment "$maintenant")"
[[ -n "$roles" ]] || exit 0

mkdir -p "$ATELIER_LOGS"
for role in $roles; do
  journal="$ATELIER_LOGS/$role.log"
  {
    echo "=== $(date) — $profil $maintenant : $role"
  } >> "$journal"
  code=0
  bash "$CRONS/tour.sh" "$role" >> "$journal" 2>&1 || code=$?
  echo "=== $role : code $code" >> "$journal"
done
exit 0
