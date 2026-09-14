# Ce que tous les scripts de crons/ partagent. Rien ici ne décide.
#
# La coupure est la même que dans le dépôt produit : Python décide
# (`python3 -m atelier`), le shell fait le geste. Un shell qui tient une
# table finit par tenir deux tables qui divergent — c'est pourquoi ni le
# nom d'un modèle, ni celui d'un abonnement, ni la liste des rôles n'est
# écrite ici. On les demande.
#
# Ce fichier est sourcé, jamais exécuté. Il ne pose pas `set -euo
# pipefail` : c'est au script appelant de le faire, avant de sourcer.

# Le répertoire de *ce* script, en suivant les liens. Une commande qu'on
# tape vit dans ~/bin et c'est un lien : `dirname "$0"` rendrait alors
# ~/bin, et la racine deviendrait son parent. Mesuré sur le VPS.
crons_de() {
  local source="${1:?crons_de attend un chemin}" dir
  while [ -L "$source" ]; do
    dir="$(cd -P "$(dirname "$source")" && pwd)"
    source="$(readlink "$source")"
    [[ "$source" != /* ]] && source="$dir/$source"
  done
  cd -P "$(dirname "$source")" && pwd
}

# Ce que l'installateur a écrit sur cette machine : où est le dépôt, où
# sont les arbres des rôles. Un seul fichier, lu par le cron comme par la
# main qui tape une commande — sinon les deux divergent, et on débogue
# une cadence qui marche dans un terminal et pas dans l'autre.
#
# Il n'écrase jamais ce que l'environnement pose déjà (`:=`) : c'est ce
# qui laisse un banc ou un test rester maître de ses propres chemins.
atelier_config() {
  local fichier="${ATELIER_CONFIG:-$HOME/.atelier/config}"
  # shellcheck source=/dev/null
  [[ -f "$fichier" ]] && . "$fichier"
  return 0
}

# Les quatre chemins que tout le monde lit. Aucun n'est créé ici :
# regarder ne crée rien.
atelier_defauts() {
  atelier_config
  : "${ATELIER_ROOT:="$(dirname "$CRONS")"}"
  : "${ATELIER_ETAT:="$HOME/.atelier/etat"}"
  : "${ATELIER_VERROUS:="$HOME/.atelier/verrous"}"
  : "${ATELIER_LOGS:="$HOME/.atelier/logs"}"
  export ATELIER_ROOT ATELIER_ETAT ATELIER_VERROUS ATELIER_LOGS
}

# L'atelier vit à côté de crons/ ; son runtime est le paquet `atelier` de
# la racine du dépôt produit qui l'embarque. On ajoute les deux candidats
# en queue de PYTHONPATH : en queue, parce qu'un PYTHONPATH déjà posé
# sait mieux que nous.
atelier_pythonpath() {
  local parent
  parent="$(dirname "$ATELIER_ROOT")"
  PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$ATELIER_ROOT:$parent"
  export PYTHONPATH
}

# Le seul chemin par lequel un script parle à l'atelier.
atelier() { python3 -m atelier "$@"; }

# Ce qu'on retire avant de lancer un agent. Une clé d'API bascule la
# facture de l'abonnement vers l'unité : l'agent doit trouver sa session,
# pas une clé.
sans_cles() { env -u ANTHROPIC_API_KEY -u CURSOR_API_KEY -u OPENAI_API_KEY "$@"; }

# Un mot pour le journal, sur stderr : stdout appartient à ce que le
# script rend, et un cron qui bavarde sur stdout envoie un courriel.
dire() { printf '%s\n' "$*" >&2; }
