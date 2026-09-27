# Ce que tous les scripts de crons/ partagent. Rien ici ne décide :
# Python décide (`python3 -m atelier`), le shell fait le geste.
#
# Ce fichier est sourcé, jamais exécuté. Il ne pose pas `set -euo
# pipefail` : c'est au script appelant de le faire, avant de sourcer.

# Ce que l'installateur a écrit sur cette machine : où est le dépôt, qui
# signe les commits. Un seul fichier, lu par le cron comme par la main qui
# tape une commande — sinon les deux divergent. Il n'écrase jamais ce que
# l'environnement pose déjà : un test reste maître de ses chemins.
atelier_config() {
  local fichier="${ATELIER_CONFIG:-$HOME/.atelier/config}"
  # shellcheck source=/dev/null
  [[ -f "$fichier" ]] && . "$fichier"
  return 0
}

# Les chemins que tout le monde lit. Aucun n'est créé ici : regarder ne
# crée rien.
atelier_defauts() {
  atelier_config
  : "${ATELIER_PROJET:="$(cd -P "$CRONS/../.." && pwd)"}"
  : "${ATELIER_ETAT:="$HOME/.atelier/etat"}"
  : "${ATELIER_VERROUS:="$HOME/.atelier/verrous"}"
  : "${ATELIER_LOGS:="$HOME/.atelier/logs"}"
  export ATELIER_PROJET ATELIER_ETAT ATELIER_VERROUS ATELIER_LOGS
  # Le PATH de cron vaut /usr/bin:/bin : aucun agent n'y vit (mesuré le
  # 15 septembre 2026, un tour a rendu 127 sur un lot sain).
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) : ;;
    *) PATH="$HOME/.local/bin:$PATH" ;;
  esac
  # L'environnement Python de la chaîne (pytest, numpy, pillow), posé par
  # l'installateur : le Python du système ne les a pas, et apt demande root.
  if [[ -x "$HOME/.atelier/venv/bin/python3" ]]; then
    PATH="$HOME/.atelier/venv/bin:$PATH"
  fi
  export PATH
  export TZ="${TZ:-Europe/Paris}"
}

# Le paquet `atelier` vit à la racine du dépôt.
atelier_pythonpath() {
  PYTHONPATH="$ATELIER_PROJET${PYTHONPATH:+:$PYTHONPATH}"
  export PYTHONPATH
}

# Le seul chemin par lequel un script parle à l'atelier.
atelier() { python3 -m atelier --projet "$ATELIER_PROJET" "$@"; }

# Ce qu'on retire avant tout : une clé d'API bascule la facture de
# l'abonnement vers l'unité. Python les retire aussi, agent par agent.
sans_cles() { env -u ANTHROPIC_API_KEY -u CURSOR_API_KEY -u OPENAI_API_KEY "$@"; }

# Un mot pour le journal, sur stderr : stdout appartient à ce que le script
# rend, et un cron qui bavarde sur stdout envoie un courriel.
dire() { printf '%s\n' "$*" >&2; }
