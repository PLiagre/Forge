#!/usr/bin/env bash
# Tout poser, en une commande, sur la machine qui fera tourner la chaîne.
#
# Il fait tout ce qui peut se faire sans personne : les arbres des rôles,
# la configuration, le cron, la commande dans le PATH, et il démarre. Il
# ne demande rien qu'il puisse deviner, et il ne demande jamais deux fois
# la même chose : on peut le rejouer autant qu'on veut.
#
# La seule chose qu'il ne peut pas faire à ta place, c'est connecter les
# agents : une session s'ouvre à la main, une fois. Il le dit à la fin,
# et il ne le dit que si ça manque vraiment.
set -euo pipefail

_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"
RACINE_ATELIER="$(dirname "$CRONS")"
DEPOT="$(dirname "$RACINE_ATELIER")"

ARGS_ORIGINE=("$@")

projet="$DEPOT"
demarrer="jour"
a_sec=0

while (( $# )); do
  case "$1" in
    --projet)  projet="$2"; shift 2 ;;
    --demarrer) demarrer="$2"; shift 2 ;;
    --sans-demarrer) demarrer=""; shift ;;
    --dry-run) a_sec=1; shift ;;
    -h|--help)
      echo "usage : installer.sh [--projet DIR] [--demarrer jour|atelier] [--sans-demarrer] [--dry-run]"
      exit 0 ;;
    *) echo "argument inconnu : $1" >&2; exit 2 ;;
  esac
done

projet="$(cd "$projet" && pwd)"
etape=0
dit() { etape=$((etape + 1)); printf '\n[%d] %s\n' "$etape" "$*"; }
ok()   { printf '    ok   %s\n' "$*"; }
note() { printf '    →    %s\n' "$*"; }
faire() { if (( a_sec )); then printf '    (à sec) %s\n' "$*"; else "$@"; fi; }

echo "═══ atelier : installation ═══"
echo "    dépôt   $projet"
echo "    atelier $RACINE_ATELIER"
(( a_sec )) && echo "    MODE À SEC : rien ne sera écrit"

# --------------------------------------------------------- 0. le dépôt
# Le dossier est peut-être déjà là, d'une version d'avant : c'est le cas
# le plus courant, pas une anomalie. On se met à jour d'abord — poser
# aujourd'hui la configuration d'hier est la panne la plus discrète,
# parce que tout a l'air d'avoir marché.
dit "le dépôt"
if [[ ! -d "$projet/.git" ]]; then
  note "$projet n'est pas un dépôt git — on continue avec ce qui est là"
elif (( a_sec )); then
  note "mettrait à jour $projet"
elif [[ -n "${ATELIER_DEJA_REJOUE:-}" ]]; then
  ok "déjà à jour (rejeu)"
else
  empreinte_avant="$(sha256sum "$_self" | cut -d" " -f1)"
  if git -C "$projet" pull --ff-only >/dev/null 2>&1; then
    ok "à jour — $(git -C "$projet" log --oneline -1)"
  else
    note "mise à jour impossible (travail local, ou pas de remote) — on continue"
  fi
  # Bash lit un script au fil de l'eau : celui qui tourne est l'ancien.
  # S'il vient de changer sous nos pieds, on rejoue le nouveau plutôt que
  # de finir l'installation avec deux moitiés de versions différentes.
  if [[ "$(sha256sum "$_self" | cut -d" " -f1)" != "$empreinte_avant" ]]; then
    echo "    →    l'installateur a changé : on rejoue la nouvelle version"
    ATELIER_DEJA_REJOUE=1 exec bash "$_self" "${ARGS_ORIGINE[@]+"${ARGS_ORIGINE[@]}"}"
  fi
fi

# ------------------------------------------------------------- 1. l'outillage
dit "l'outillage"
manque=()
for outil in python3 git flock timeout; do
  command -v "$outil" >/dev/null 2>&1 && ok "$outil" || manque+=("$outil")
done
if (( ${#manque[@]} )); then
  echo "    Il manque : ${manque[*]}" >&2
  echo "    sudo apt-get install -y ${manque[*]}" >&2
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "    python3 ≥ 3.11 est nécessaire (tomllib)." >&2
  exit 1
fi
ok "python3 $(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"

# ------------------------------------------------- 2. les arbres des rôles
# Le coder et le briefer écrivent : chacun son arbre. L'atelier refuse de
# basculer la branche du clone du produit, et c'est ce qui empêche deux
# lots de se marcher dessus.
dit "les arbres des rôles qui écrivent"
base="$(git -C "$projet" symbolic-ref --quiet --short HEAD 2>/dev/null || echo master)"
for role in coder briefer; do
  cible="$projet-$role"
  if [[ -d "$cible" ]]; then
    ok "$role — déjà là ($cible)"
  elif (( a_sec )); then
    note "$role — serait créé ($cible)"
  elif ajouter_worktree "$projet" "atelier/$role" "$cible" "$base"; then
    ok "$role — en place ($cible)"
  else
    echo "    Répare-le à la main, puis rejoue-moi." >&2
    exit 1
  fi
done

# ------------------------------------------------------ 3. la configuration
# Un seul fichier de chemins, lu par le cron comme par la main. Deux
# sources de chemins finissent toujours par dire deux choses.
dit "la configuration de cette machine"
config="$HOME/.atelier/config"
faire mkdir -p "$HOME/.atelier"/{etat,verrous,logs}
corps="# Écrit par crons/installer.sh. Rejoue-le pour le refaire.
# Chaque ligne cède à l'environnement : un banc reste maître chez lui.
: \"\${ATELIER_PROJET:=$projet}\"
: \"\${ATELIER_ROOT:=$RACINE_ATELIER}\"
: \"\${ATELIER_WORKDIR_coder:=$projet-coder}\"
: \"\${ATELIER_WORKDIR_briefer:=$projet-briefer}\"
export ATELIER_PROJET ATELIER_ROOT ATELIER_WORKDIR_coder ATELIER_WORKDIR_briefer
"
if (( a_sec )); then
  note "écrirait $config"
else
  printf '%s' "$corps" > "$config"
  ok "$config"
fi

# --------------------------------------------------- 4. la commande à taper
dit "la commande atelier-boucle"
bin="$HOME/.local/bin"
faire mkdir -p "$bin"
faire ln -sf "$CRONS/atelier-boucle" "$bin/atelier-boucle"
ok "$bin/atelier-boucle"
case ":$PATH:" in
  *":$bin:"*) : ;;
  *) note "ajoute $bin à ton PATH :  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc" ;;
esac

# ------------------------------------------------------------- 5. l'horloge
# Le crontab de l'utilisateur, pas celui de root : il n'y a rien ici qui
# demande des privilèges, et ce qu'on peut désarmer seul est ce qu'on ose
# armer. Une ligne, chaque minute ; c'est le profil qui décide du reste.
dit "l'horloge"
ligne="* * * * * $CRONS/repartiteur.sh"
marque="# atelier : le répartiteur lit le profil actif et réveille les rôles"
cron_manquant=0
if ! command -v crontab >/dev/null 2>&1; then
  # Pas de cron sur cette machine. Ce n'est pas une panne de l'installation :
  # tout le reste est posé, et la cadence se rebranche en une ligne.
  cron_manquant=1
  note "aucune commande crontab ici — l'horloge reste à brancher"
  note "sur une machine avec cron :  (crontab -l; echo '$ligne') | crontab -"
elif crontab -l 2>/dev/null | grep -qF "$CRONS/repartiteur.sh"; then
  ok "le cron appelle déjà le répartiteur"
elif (( a_sec )); then
  note "ajouterait au crontab : $ligne"
else
  { crontab -l 2>/dev/null || true; printf '%s\n%s\n' "$marque" "$ligne"; } | crontab -
  ok "crontab de $(whoami) : une ligne, chaque minute"
fi

# -------------------------------------------------------------- 6. la veille
dit "la veille (personne n'est invoqué, rien n'est dépensé)"
veille=0
rapport="$HOME/.atelier/veille.txt"
ATELIER_PROJET="$projet" bash "$CRONS/veille.sh" > "$rapport" 2>&1 || veille=$?
if (( veille == 0 )); then
  ok "le branchement est lisible"
  note "rapport complet : $rapport"
else
  echo "    Le branchement ne se lit pas :" >&2
  sed 's/^/    /' "$rapport" >&2
  exit 1
fi

# --------------------------------------------------------- 7. les agents
# La seule chose qui ne s'automatise pas : une session se connecte à la
# main. On regarde le PATH, on ne lance rien.
dit "les agents"
absents=()
for binaire in claude agent hermes; do
  if ! command -v "$binaire" >/dev/null 2>&1; then
    absents+=("$binaire")
    note "$binaire — absent du PATH"
    continue
  fi
  # Présent n'est pas connecté, et c'est la panne qui ressemble le plus à
  # une file vide : le réveil part, l'agent refuse, le tour rend zéro.
  # Claude sait le dire ; on le lui demande, et on le montre.
  if [[ "$binaire" == "claude" ]]; then
    if etat="$(claude auth status --text 2>&1)"; then
      ok "claude — $(printf '%s' "$etat" | head -1)"
    else
      absents+=("claude")
      note "claude — installé mais PAS connecté"
    fi
  else
    ok "$binaire — $(command -v "$binaire")"
  fi
done

# ------------------------------------------------------------- 8. démarrer
dit "démarrage"
if [[ -z "$demarrer" ]]; then
  note "non demandé (--sans-demarrer)"
elif (( ${#absents[@]} )); then
  note "pas encore : ${absents[*]} manque(nt). Rien ne tournerait."
  demarrer=""
else
  faire bash "$CRONS/atelier-boucle" "$demarrer"
  ok "profil « $demarrer »"
fi

# ---------------------------------------------------------------- le mot
echo
echo "═══════════════════════════════════════════════"
if (( ${#absents[@]} )); then
  cat <<MESSAGE
Presque. Il reste UNE chose, et elle ne peut pas se faire sans toi :
connecter ${#absents[@]} agent(s). Une session s'ouvre à la main, une fois.

MESSAGE
  for binaire in "${absents[@]}"; do
    case "$binaire" in
      claude) echo "  claude  →  claude setup-token   (jeton longue durée, machine sans écran)" ;;
      agent)  echo "  agent   →  Cursor CLI, puis :  agent login" ;;
      hermes) echo "  hermes  →  la console ; sans elle, tout marche sauf le compte rendu du matin" ;;
    esac
  done
  cat <<'MESSAGE'

Puis, une seule commande :

    atelier-boucle jour

MESSAGE
elif (( cron_manquant )); then
  cat <<MESSAGE
Tout est posé, sauf l'horloge : cette machine n'a pas de cron.

    (crontab -l 2>/dev/null; echo '$ligne') | crontab -

MESSAGE
else
  cat <<'MESSAGE'
C'est en marche. Tu n'as plus rien à faire.

  atelier-boucle etat     ← où ça en est
  atelier-boucle arret    ← tout arrêter (attend le tour en cours)
  atelier-boucle jour     ← repartir

MESSAGE
fi
echo "Les journaux : $HOME/.atelier/logs/"
