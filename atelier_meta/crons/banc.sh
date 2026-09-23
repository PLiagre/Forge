#!/usr/bin/env bash
# Le banc : un produit pour de faux, des agents pour de faux, et de quoi
# voir une carte traverser les quatre rôles sans dépenser un quota.
#
# Il est idempotent : on le rejoue autant qu'on veut. Il n'écrit que dans
# `$ATELIER_BANC`, et il ne sait rien du vrai produit.
set -euo pipefail

_self="${BASH_SOURCE[0]}"
[ -L "$_self" ] && _self="$(readlink -f "$_self")"
CRONS="$(cd -P "$(dirname "$_self")" && pwd)"
# shellcheck source=lib.sh
. "$CRONS/lib.sh"

banc="${ATELIER_BANC:-$HOME/.atelier/banc}"

neuf=0
case "${1:-}" in
  --neuf) neuf=1 ;;
  "") ;;
  *) dire "usage : banc.sh [--neuf]"; exit 2 ;;
esac

# Le banc est un bac à sable : tout ce qu'il contient est fabriqué ici, et
# rien de ce qu'il porte n'existe ailleurs. Le refaire à neuf est donc
# sans conséquence — c'est ce qui le distingue du dépôt produit, où
# l'atelier ne jette jamais rien.
#
# La garde n'est pas une politesse : `rm -rf` sur une variable vide ou
# sur un home efface autre chose que ce qu'on croyait.
if (( neuf )) && [[ -e "$banc" ]]; then
  # `$banc` ne peut pas être vide ici : le défaut s'applique avant. On ne
  # teste donc que ce qui peut vraiment arriver — un contrôle qui ne peut
  # pas rougir ne prouve rien.
  if [[ "$banc" == "/" || "$banc" == "$HOME" ]]; then
    dire "refus : ATELIER_BANC vaut « $banc » — ce n'est pas un banc"
    exit 2
  fi
  if [[ ! -d "$banc/produit" && ! -d "$banc/bin" ]]; then
    dire "refus : $banc ne ressemble pas à un banc (ni produit/ ni bin/)"
    dire "  efface-le toi-même si c'est bien ce que tu veux"
    exit 2
  fi
  rm -rf "$banc"
  echo "banc effacé : $banc"
fi

mkdir -p "$banc"/{bin,verrous,logs,etat}

# Les faux agents. Ils ouvrent une PR imaginaire — un numéro dans le
# canal — et rendent la main. C'est tout ce que la chaîne attend d'eux.
for nom in agent claude hermes codex; do
  cat > "$banc/bin/$nom" <<'AGENT'
#!/usr/bin/env bash
# Faux agent de banc. Il ne lit pas le prompt, il ne code rien.
printf 'banc: %s %s\n' "$(basename "$0")" "$*" >&2
mkdir -p atelier-echange
printf '%s\n' "$(( (RANDOM % 900) + 100 ))" > atelier-echange/pr.txt
exit 0
AGENT
  chmod +x "$banc/bin/$nom"
done

# Le faux GitHub : toute PR y est approuvée par un tiers imaginaire.
# C'est ce que le tour de relecture lit pour faire passer la carte.
cat > "$banc/bin/gh" <<'GH'
#!/usr/bin/env bash
# Faux gh de banc. Il n'atteint aucun dépôt.
printf 'banc: gh %s\n' "$*" >&2
case "$*" in
  *"--json reviews"*) echo "APPROVED" ;;
esac
exit 0
GH
chmod +x "$banc/bin/gh"

# Un produit minimal : l'atelier lit son branchement, pas son code.
produit="$banc/produit"
if [[ ! -d "$produit/.git" ]]; then
  mkdir -p "$produit/briefs"
  # Le banc porte la même garde que le vrai dépôt : sans elle il
  # prouverait une chaîne qui n'est pas celle qui tournera.
  cat > "$produit/.gitignore" <<'IGNORE'
.atelier/
atelier-echange/
IGNORE
  cat > "$produit/atelier.toml" <<'TOML'
[projet]
nom = "Banc"
briefs = "briefs"
tests = "true"
fumee = "echo fumee-banc"
branche_base = "master"
prefixe_branche = "agent/"
feuille = "ROADMAP.md"

[roles]
ecriture = "claude"
execution = "cursor"
controle = "claude"
TOML
  # Ce brief passe la porte mécanique — c'est le but : un banc qui
  # bloquerait au premier contrôle ne prouverait rien de la suite.
  cat > "$produit/briefs/001-banc.md" <<'BRIEF'
# Brief 001 — le lot de banc

## But
Après ce lot, une carte a traversé les quatre rôles de la boîte.

## Règle du monde
Aucun fondement produit : le banc ne touche à aucun nombre du monde.

## Périmètre
Écriture autorisée : `banc.txt`. Tout le reste est interdit.

## Conditions de succès

### SC1 — la chaîne se referme

```bash
python3 -m atelier feuille valider --projet .
```

## Hors périmètre
Aucune fusion, aucun autre fichier, aucun appel à un agent payant.
BRIEF
  cat > "$produit/ROADMAP.md" <<'ROADMAP'
# ROADMAP du banc

<!-- lots:debut -->

### [001 — Le lot de banc](briefs/001-banc.md)
état : pret · couche : 1 · dépend de : — · PR : —

<!-- lots:fin -->
ROADMAP
  git -C "$produit" init -q
  git -C "$produit" -c user.email=banc@atelier -c user.name=Banc \
      -c commit.gpgsign=false checkout -q -B master
  git -C "$produit" add -A
  git -C "$produit" -c user.email=banc@atelier -c user.name=Banc \
      -c commit.gpgsign=false commit -q -m "banc : produit d'essai"
fi

# Les worktrees des rôles qui écrivent. Jamais le clone du produit :
# l'atelier refuse de basculer la branche du produit lui-même.
for role in coder briefer; do
  if ! ajouter_worktree "$produit" "atelier/$role" "$banc/$role" master; then
    dire ""
    dire "Le banc est incohérent — un arbre d'un essai précédent tient encore"
    dire "la branche. Rien n'y est du vrai travail : refais-le à neuf."
    dire ""
    dire "    $0 --neuf"
    dire ""
    exit 1
  fi
done

echo "banc prêt : $banc"
echo "  atelier-boucle atelier   # quatre rôles en quatre minutes, zéro quota"
