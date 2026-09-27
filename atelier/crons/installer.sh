#!/usr/bin/env bash
# Installer la chaîne sur une machine (le VPS), sans sudo. Rejouable.
#
#   atelier/crons/installer.sh [--demarrer jour] [--a-sec]
#
# 1. met le dépôt à jour (la copie principale reste sur la base) ;
# 2. vérifie l'outillage : python3 ≥ 3.11, git, flock, timeout, gh ;
# 3. écrit ~/.atelier/config (dépôt, identité git : garde celle qui existe) ;
# 4. pose LA ligne de crontab qui appelle le répartiteur, et retire les
#    anciennes (un répartiteur d'avant la refonte) ;
# 5. pose le profil (arret par défaut ; --demarrer jour pour armer) ;
# 6. joue la veille.
set -euo pipefail
_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"
DEPOT="$(cd -P "$CRONS/../.." && pwd)"

demarrer=""
a_sec=0
while (( $# )); do
  case "$1" in
    --demarrer) demarrer="$2"; shift 2 ;;
    --a-sec) a_sec=1; shift ;;
    -h|--help) sed -n '2,13p' "$_self"; exit 0 ;;
    *) dire "argument inconnu : $1"; exit 2 ;;
  esac
done
faire() { if (( a_sec )); then printf '    (à sec) %s\n' "$*"; else "$@"; fi; }

echo "═══ la chaîne de Forge : installation ═══"
echo "    dépôt $DEPOT"

echo "[1] le dépôt"
if git -C "$DEPOT" pull --quiet --ff-only 2>/dev/null; then
  echo "    à jour — $(git -C "$DEPOT" log --oneline -1)"
else
  echo "    mise à jour impossible (travail local ?) — on continue"
fi

echo "[2] l'outillage"
manque=()
for outil in python3 git flock timeout gh; do
  if command -v "$outil" >/dev/null 2>&1; then
    echo "    ok   $outil"
  else
    manque+=("$outil")
  fi
done
if (( ${#manque[@]} )); then
  dire "    il manque : ${manque[*]}"
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  dire "    python3 ≥ 3.11 est nécessaire (tomllib)"
  exit 1
fi

echo "[3] ~/.atelier/config"
config="$HOME/.atelier/config"
email="$(grep -oP 'ATELIER_GIT_EMAIL:=\K[^}"]+' "$config" 2>/dev/null || git -C "$DEPOT" config user.email || true)"
nom="$(grep -oP 'ATELIER_GIT_NOM:=\K[^}"]+' "$config" 2>/dev/null || git -C "$DEPOT" config user.name || true)"
contenu="# Écrit par atelier/crons/installer.sh. Rejoue-le pour le refaire.
# Chaque ligne cède à l'environnement : un test reste maître chez lui.
: \"\${ATELIER_PROJET:=$DEPOT}\"
export ATELIER_PROJET
: \"\${ATELIER_GIT_EMAIL:=$email}\"
: \"\${ATELIER_GIT_NOM:=$nom}\"
export ATELIER_GIT_EMAIL ATELIER_GIT_NOM"
if (( a_sec )); then
  printf '    (à sec) écrirait %s\n' "$config"
else
  mkdir -p "$HOME/.atelier"
  printf '%s\n' "$contenu" > "$config"
  echo "    écrit ($nom <$email>)"
fi

echo "[4] la crontab"
ligne="* * * * * $CRONS/repartiteur.sh"
actuelle="$(crontab -l 2>/dev/null || true)"
nouvelle="$(printf '%s\n' "$actuelle" | grep -v 'repartiteur.sh' || true)"
nouvelle="$(printf '%s\n%s\n' "$nouvelle" "$ligne" | sed '/^$/d')"
if [[ "$actuelle" == *"$ligne"* ]] && [[ "$(printf '%s\n' "$actuelle" | grep -c 'repartiteur.sh')" == "1" ]]; then
  echo "    déjà posée : $ligne"
else
  faire sh -c "printf '%s\n' \"\$1\" | crontab -" _ "$nouvelle"
  echo "    posée : $ligne"
fi

echo "[5] le profil"
mkdir -p "$HOME/.atelier/etat"
if [[ -n "$demarrer" ]]; then
  faire sh -c "printf '%s\n' \"\$1\" > \"\$2\"" _ "$demarrer" "$HOME/.atelier/etat/profil"
  echo "    $demarrer"
elif [[ ! -f "$HOME/.atelier/etat/profil" ]]; then
  faire sh -c "printf 'arret\n' > \"\$1\"" _ "$HOME/.atelier/etat/profil"
  echo "    arret (armer : atelier/crons/atelier-boucle jour)"
else
  echo "    inchangé : $(cat "$HOME/.atelier/etat/profil")"
fi

echo "[6] la veille"
atelier_defauts
atelier_pythonpath
python3 -m atelier --projet "$DEPOT" veille || true
