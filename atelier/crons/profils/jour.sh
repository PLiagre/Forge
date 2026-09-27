# Le profil du jour : la cadence réelle, sur le VPS, avec de vrais agents.
#
# Un profil répond à deux questions, et à rien d'autre : quels rôles à cette
# minute, quel réveil ensuite. Il ne lance rien — le répartiteur s'en charge.
# Les heures sont celles de Paris (lib.sh pose TZ).
#
# Le pilote passe toutes les dix minutes, jour et nuit : un tour n'invoque
# qu'un agent, et un tour qui tourne encore fait passer le suivant (verrou).
# Le journal s'écrit à 07:15 ; la boussole, le lundi à 07:45 ; la veille
# regarde les outils à 06:45, avant tout le monde.

roles_du_moment() {
  local quand="${1:-}" minute
  minute="${quand#*:}"
  [[ "$minute" =~ ^[0-9]+$ ]] || return 0
  [[ "$quand" == "06:45" ]] && printf 'veille\n'
  [[ "$quand" == "07:15" ]] && printf 'journal\n'
  [[ "$quand" == "07:45" && "$(date +%u)" == "1" ]] && printf 'boussole\n'
  (( 10#$minute % 10 == 0 )) && printf 'pilote\n'
  # Une minute sans réveil n'est pas une erreur : sans ce `return`, la
  # fonction rendrait le code du dernier test.
  return 0
}

prochain_reveil() {
  local quand="${1:-}" heure minute suivante
  heure="${quand%%:*}"
  minute="${quand#*:}"
  [[ "$minute" =~ ^[0-9]+$ ]] || return 0
  suivante=$(( (10#$minute / 10 + 1) * 10 ))
  if (( suivante > 59 )); then
    printf '%02d:00 pilote\n' $(( (10#$heure + 1) % 24 ))
  else
    printf '%s:%02d pilote\n' "$heure" "$suivante"
  fi
}
