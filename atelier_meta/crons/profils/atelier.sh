# Le profil d'atelier : la boucle courte, sur un banc, sans un centime.
#
# Il sert à roder la chaîne — voir une carte traverser les quatre rôles
# en quatre minutes — sans toucher au produit et sans dépenser un quota.
#
# Les chemins ne sont pas des défauts : ils sont posés. Un profil de banc
# qui *choisit* de ne pas toucher au produit finit par y toucher une
# fois. Ici il ne le peut pas : le PATH commence par les faux agents du
# banc, et `command -v agent` ne peut rendre autre chose.

: "${ATELIER_BANC:=$HOME/.atelier/banc}"
export ATELIER_BANC

export PATH="$ATELIER_BANC/bin:$PATH"
export ATELIER_PROJET="$ATELIER_BANC/produit"
export ATELIER_WORKDIR_coder="$ATELIER_BANC/coder"
export ATELIER_WORKDIR_briefer="$ATELIER_BANC/briefer"
export ATELIER_VERROUS="$ATELIER_BANC/verrous"
export ATELIER_LOGS="$ATELIER_BANC/logs"
export ATELIER_TIMEOUT="${ATELIER_TIMEOUT:-60}"
export ATELIER_SANS_PULL=1
export ATELIER_INVOQUER=1

_CYCLE=(pilote coder relire briefer)

# Un rôle par minute, en boucle de quatre. Le tour complet passe donc en
# quatre minutes au lieu d'une journée : c'est ce qui permet de voir la
# chaîne se refermer avant de la lâcher sur du vrai code.
roles_du_moment() {
  local quand="${1:-}" minute
  minute="${quand#*:}"
  [[ "$minute" =~ ^[0-9]+$ ]] || return 0
  printf '%s\n' "${_CYCLE[$(( 10#$minute % ${#_CYCLE[@]} ))]}"
}

prochain_reveil() {
  local quand="${1:-}" heure minute suivante
  heure="${quand%%:*}"
  minute="${quand#*:}"
  [[ "$minute" =~ ^[0-9]+$ ]] || return 0
  suivante=$(( 10#$minute + 1 ))
  if (( suivante > 59 )); then
    printf '%02d:00 %s\n' $(( (10#$heure + 1) % 24 )) "${_CYCLE[0]}"
  else
    printf '%s:%02d %s\n' "$heure" "$suivante" "${_CYCLE[$(( suivante % ${#_CYCLE[@]} ))]}"
  fi
}
