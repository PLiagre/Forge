# Le profil du jour : la cadence réelle, sur le VPS, avec de vrais agents.
#
# Un profil répond à trois choses, et à rien d'autre : quel environnement,
# quels rôles à cette minute, quel réveil ensuite. Il ne lance rien — le
# répartiteur s'en charge.
#
# Les heures sont celles de Paris. Treize réveils : le pilote ouvre,
# le coder et le relecteur alternent, le briefer prend les deux creux.
# Deux heures séparent deux tours du même rôle — c'est ce délai qui
# tient lieu d'horloge de reprise quand une carte retombe.

# Le chemin des agents, et l'heure de la cadence. Les deux vivent ici
# parce qu'un profil pose l'environnement, et qu'ils ne peuvent pas
# dépendre d'une ligne de crontab que personne ne relit.
#
# Mesuré le 15 septembre 2026 : le crontab de root, retiré parce qu'il
# faisait double emploi, portait seul le PATH. Celui de cron vaut
# /usr/bin:/bin, où aucun agent ne vit. Le réveil de 07:30 a lancé le
# coder, le shell n'a pas trouvé `agent`, et le tour a rendu 127 sur un
# lot parfaitement sain. La veille de 06:45 l'avait dit une heure plus
# tôt : « binaire agent — introuvable dans le PATH ».
case ":$PATH:" in
  *":$HOME/.local/bin:"*) : ;;
  *) PATH="$HOME/.local/bin:$PATH" ;;
esac
export PATH

# Les heures du registre sont celles de Paris. Le répartiteur et
# `atelier-boucle etat` sourcent ce fichier avant de lire l'heure : la
# cadence dit donc elle-même son fuseau, au lieu de l'emprunter au
# crontab. Sans cette ligne, un terminal en UTC annonce le prochain
# réveil avec deux heures d'écart — et c'est la seule ligne d'état que
# le propriétaire regarde.
export TZ="${TZ:-Europe/Paris}"

# Le défaut est dans le home, jamais sous /srv : un chemin qui exige
# root pour être créé n'est pas un défaut, c'est une panne qui attend.
# `installer.sh` écrit les vrais chemins dans ~/.atelier/config, et la
# config passe avant ces lignes.
export ATELIER_PROJET="${ATELIER_PROJET:-$HOME/Forge}"
export ATELIER_WORKDIR_coder="${ATELIER_WORKDIR_coder:-$HOME/Forge-coder}"
export ATELIER_WORKDIR_briefer="${ATELIER_WORKDIR_briefer:-$HOME/Forge-briefer}"
export ATELIER_VERROUS="${ATELIER_VERROUS:-$HOME/.atelier/verrous}"
export ATELIER_LOGS="${ATELIER_LOGS:-$HOME/.atelier/logs}"
export ATELIER_TIMEOUT="${ATELIER_TIMEOUT:-2400}"
# Le jeton du relecteur : un second compte GitHub, collaborateur du
# dépôt. GitHub refuse qu'un compte approuve sa propre PR.
export ATELIER_RELIRE_TOKEN="${ATELIER_RELIRE_TOKEN:-$HOME/.atelier/relire.token}"
# La console du pilote (Hermes) ne s'appelle que sur demande : la
# décision est calculée en Python et déjà dans le journal.
export ATELIER_CONSOLE="${ATELIER_CONSOLE:-0}"

# L'armement vit ici, et non dans le crontab de root : sinon désarmer
# redemanderait root, et ce qu'on ne peut pas désarmer seul, on ne
# l'arme pas.
export ATELIER_INVOQUER="${ATELIER_INVOQUER:-1}"

_REVEILS=(
  # La veille ouvre la journée, avant le pilote : elle n'invoque
  # personne et ne coûte rien, et c'est elle qui voit un agent qui ne
  # démarre plus. Sans elle, la panne se découvre une semaine plus tard,
  # sur une file qui a l'air vide.
  "06:45 veille"
  "07:00 pilote"
  "07:30 coder"
  "09:00 relire"
  "10:00 coder"
  "11:30 relire"
  "12:30 briefer"
  "14:00 coder"
  "15:30 relire"
  "16:30 coder"
  "18:00 briefer"
  "19:00 relire"
  "20:00 coder"
  "21:30 relire"
)

# Qui se réveille à cette minute précise. Une minute sans réveil ne
# réveille personne : c'est le cas courant, et il est silencieux.
roles_du_moment() {
  local quand="${1:-}" entree
  for entree in "${_REVEILS[@]}"; do
    [[ "${entree%% *}" == "$quand" ]] && printf '%s\n' "${entree#* }"
  done
  # Une minute sans réveil n'est pas une erreur : sans ce `return`, la
  # fonction rendrait le code du dernier test, et le répartiteur lirait
  # un échec là où il n'y a qu'un silence.
  return 0
}

# Ce qui vient, sans qu'on lise la table. « HH:MM rôle ».
prochain_reveil() {
  local quand="${1:-}" entree
  for entree in "${_REVEILS[@]}"; do
    if [[ "${entree%% *}" > "$quand" ]]; then
      printf '%s\n' "$entree"
      return 0
    fi
  done
  # Après le dernier, c'est le premier de demain.
  printf '%s (demain)\n' "${_REVEILS[0]}"
}
