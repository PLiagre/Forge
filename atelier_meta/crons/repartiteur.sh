#!/usr/bin/env bash
# Le répartiteur : la seule ligne que root installe, et elle ne change
# plus jamais.
#
# `/etc/cron.d/forgeatelier` appartient à root. Tant qu'il portait les
# treize réveils, changer de cadence demandait le propriétaire et un
# `sudo`. Il n'appelle plus que ce script, chaque minute ; le profil
# actif vit dans un fichier que l'utilisateur écrit. Basculer de la
# cadence du jour à la boucle d'atelier n'est plus qu'une écriture.
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
  bash "$ATELIER_ROOT/crons/tour.sh" "$role" >> "$journal" 2>&1 || code=$?
  echo "=== $role : code $code" >> "$journal"
done
exit 0
