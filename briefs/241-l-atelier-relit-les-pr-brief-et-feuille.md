# Brief 241 — L'atelier relit les PR brief et feuille

## But

Toute proposition ouverte que la chaîne produit elle-même — le brief du
briefer, le code du coder, la fiche déposée par `github-actions[bot]` —
reçoit sa relecture du second compte, de sorte que le propriétaire ne soit
plus le tiers qu'il faut attendre.

Ce lot ne change pas la règle « jamais l'auteur ». Il change **qui la
satisfait**. Le verdict reste une revue GitHub signée d'un second compte,
jamais une fusion.

État de départ à mesurer :

```bash
git rev-parse HEAD
python3 - <<'PY'
from atelier import boite
print('SUIVANT[briefer] =', boite.SUIVANT["briefer"])
assert boite.SUIVANT["briefer"] == "a-relire", "le brief ne passe pas encore par la relecture"
PY
```

La dernière commande échoue avant ce lot : la carte du briefer va dans
`brief-a-fusionner`, boîte dont rien ne la sort qu'une fusion posée à la
main. Si une autre voie fait déjà relire les PR `brief/` et `feuille/` par
le compte de contrôle, le lot est caduc. Un propriétaire qui approuve plus
vite ne le rend pas caduc.

## Règle du monde

**Aucune règle nouvelle du monde : ce lot ne touche ni `sim/`, ni un nombre
du monde, ni une vue. Fidélité : sans objet.** Son fondement est la règle de
chaîne écrite dans `AGENTS.md` § « Le brief » et dans `docs/WORKFLOW.md`
§ « Ce qui ouvre la porte de `master` » : une PR entre quand tous les
contrôles déclarés sont verts sur sa révision courante **et qu'un tiers l'a
approuvée sur cette même révision**. `atelier.toml` § `[integration]`
déclare déjà les trois préfixes fusionnés : `agent/`, `brief/`, `feuille/`.
Deux d'entre eux n'ont aujourd'hui aucun tiers qui ne soit le propriétaire.

### Les trois cas d'une proposition qui attend un tiers

| préfixe | qui écrit les commits | ce qui existe aujourd'hui | ce que le lot doit obtenir |
|---|---|---|---|
| `agent/` | le coder (Cursor) | carte `a-relire`, prompt de relecture de code | inchangé |
| `brief/` | le briefer, sous `ATELIER_GIT_EMAIL` | carte `brief-a-fusionner`, « à fusionner par le propriétaire » | carte `a-relire`, prompt de relecture de brief |
| `feuille/` | `github-actions[bot]` | **aucune carte** | carte `a-relire`, prompt de relecture de fiche |

Pour `brief/`, le second compte n'est pas un confort : les commits portent
l'adresse du propriétaire, et `outils/relecture.py::juger` refuse une
approbation posée par un auteur des commits. Le propriétaire ne *peut* pas
approuver son brief depuis son compte principal. Pour `feuille/`, les
commits sont du jeton d'Actions, et le compte de contrôle est un tiers
valide.

### Ce que la carte doit se rappeler

C'est le cœur du lot, et ce qui le rend structurel plutôt que cosmétique.
Aujourd'hui une carte dans `a-relire` ne peut être qu'une carte de code, et
trois endroits en dépendent :

1. `atelier/feuille.py::verifier_cartes` traite `a-planifier`, `a-coder`,
   `a-relire` et `faite` comme un bloc, et exige `fiche.etat == "pret"` —
   « on ne code pas un lot dont le brief n'est pas fusionné ». Une carte de
   brief en `a-relire` a sa fiche en `a-briefer` : telle quelle, elle
   devient une incohérence, et `_cmd_piloter` renvoie `FAIL` **sans
   déposer aucune carte**. La chaîne entière s'arrête.
2. `atelier/feuille.py::rapprochements` ne sort une carte de brief que
   depuis `BOITE_BRIEF_A_FUSIONNER`, quand la fiche passe à `pret`. Une
   carte de brief qui finit dans `faite` n'a plus aucune sortie ; et
   `decider` ignore tout lot qui porte déjà une carte. Le lot serait alors
   bloqué pour toujours, brief fusionné mais coder jamais appelé. **C'est
   l'impasse à ne pas créer** : elle est de la même famille que la branche
   de palier restée d'une PR fermée, qui a bloqué sa couche pour toujours.
3. Une carte `feuille/` n'a pas de fiche du tout au moment où sa PR est
   ouverte : c'est cette PR qui crée la fiche. `verifier_cartes` répond
   « aucune fiche ne porte ce lot » et fait tomber le même `FAIL`.

La carte doit donc porter de quoi distinguer ces cas, et les trois
fonctions doivent le lire. Le mécanisme est au choix du coder ; ce qui est
exigé, c'est que `python3 -m atelier piloter` reste vert dans chacun des
trois cas, et que la carte de brief relue et fusionnée **libère** le lot
pour le coder.

Une carte `feuille/` ou `brief/` porte le numéro de sa PR à son dépôt :
`crons/tour.sh` lit ce champ (`atelier prochain --champ pr`) pour passer
`--pr` au rôle, et sans lui le relecteur ne sait pas quoi relire.
`atelier/boite.py::CHAMPS_MODIFIABLES` autorise déjà `pr`.

### Pourquoi ce n'est pas deux lots

Faire relire `brief/` et faire relire `feuille/` pourraient sembler
séparables. Ils ne le sont pas : le premier impose à lui seul toute la
transformation ci-dessus — la carte qui se rappelle ce qu'elle est, et les
trois fonctions qui la lisent. Le second n'ajoute qu'une branche à une
structure déjà payée, et rouvrirait exactement les mêmes fichiers, donc
sous le même verrou de périmètre. Les livrer séparément coûterait deux fois
la même relecture pour une seule règle.

### Le prompt n'est pas le même selon le préfixe

`atelier/backends.py::prompt_du_role` construit aujourd'hui un seul texte de
relecture, écrit pour du code : périmètre, conditions de succès, tests non
modifiés, `gh pr checks`. Rendu tel quel sur un brief ou sur une fiche, il
demande au relecteur de juger des choses qui n'existent pas, et le fait
passer à côté de ce qui compte. Chaque cas reçoit donc son prompt :

- **`brief/`** — les cinq sections attendues, les six façons de rater un
  brief (`AGENTS.md` § « Le brief »), un périmètre nommé fichier par
  fichier, et chaque condition de succès qui nomme une commande pouvant
  échouer ;
- **`feuille/`** — le diff ne touche que la fiche nommée et rien d'autre de
  `ROADMAP.md`, la transition d'état est permise, et
  `python3 -m atelier feuille valider --projet .` est vert ;
- **`agent/`** — le prompt actuel, mot pour mot.

Les trois gardent ce qui fait la relecture : le relecteur n'écrit rien, ne
pousse rien, ne fusionne pas, et termine par **une** revue GitHub sur la PR.
`OUTILS_REFUSES_AU_RELECTEUR` ne bouge pas.

### La décision reste hors ligne

La liste des propositions ouvertes vient de GitHub, mais la décision de
déposer une carte n'a pas le droit d'en dépendre : c'est ce qui rend
`feuille.py` testable sans réseau, et c'est la coupure « décider ≠ faire »
du dépôt. La liste **entre** dans la décision comme une donnée ; l'appel à
`gh` vit dans une fonction à part, sur le modèle de
`atelier/traces.py::_gh` et de `atelier/echange.py::verifier_pr_branche_optionnel`,
qui se taisent quand `gh` est absent au lieu de faire tomber le tour. Aucun
test de ce lot n'ouvre une socket.

## Périmètre

En écriture : `atelier/boite.py` (le routage des cartes et ce qu'une carte
retient), `atelier/feuille.py` (`decider`, `verifier_cartes`,
`rapprochements`, `etat_effectif`), `atelier/backends.py`
(`prompt_du_role` pour le rôle `relire`), `atelier/__main__.py` — la seule
fonction `_cmd_piloter`, et seulement pour lui passer les propositions
ouvertes — et **un** nouveau module `atelier/propositions.py` pour l'appel
à `gh`. Côté harnais : `atelier_meta/crons/tour.sh` si le rôle `relire` a
besoin d'un argument de plus, `atelier_meta/tests/test_boite.py` et
`atelier_meta/tests/test_feuille.py`, qui portent déjà les invariants
concernés, et `atelier_meta/tests/test_invocation.py` et
`atelier_meta/tests/test_roles.py`, où SC3 ajoute ses cas — en ajout
seulement.

Tout autre chemin est interdit, nommément : `outils/` en entier — dont
`outils/relecture.py`, `outils/integration.py` et `outils/tableau.py` —,
`.github/` en entier, `atelier.toml`, `AGENTS.md`, `docs/WORKFLOW.md`,
`VISION.md`, `sim/`, `vues/`, `forge/`, `data/`, et les autres briefs. La
fiche 241 relève du périmètre implicite de la PR de lot ; aucune autre
fiche ni prose de la feuille de route ne change.

**Six tests existants énoncent la règle que ce lot remplace** : ce sont
tous ceux de `master` qui nomment la boîte `brief-a-fusionner` ou y posent
une carte. Les modifier est autorisé, pour eux seuls, et nommément :

| test | ce qu'il affirme aujourd'hui |
|---|---|
| `atelier_meta/tests/test_boite.py::test_avancer_briefer_attend_la_fusion_du_brief` | la carte du briefer atterrit dans `brief-a-fusionner` |
| `atelier_meta/tests/test_feuille.py::test_le_brief_en_pr_attend_le_proprietaire` | `etat_effectif` répond « à fusionner par le propriétaire » |
| `atelier_meta/tests/test_feuille.py::test_le_brief_fusionne_libere_la_carte_du_briefer` | le rapprochement du brief part de `brief-a-fusionner` |
| `atelier_meta/tests/test_feuille.py::test_le_lot_dont_le_brief_est_fusionne_part_au_coder` | la carte du brief fusionné part de `brief-a-fusionner` avant que le pilote dépose celle du coder |
| `atelier_meta/tests/test_feuille.py::test_cli_piloter_un_lot_brief_par_la_chaine_va_jusqu_a_sa_fusion` | `piloter` imprime « rapproché  046-mer : brief-a-fusionner → fusionnee » |
| `atelier_meta/tests/test_feuille.py::test_le_briefer_range_sa_carte_avec_le_numero_de_sa_pr` | la carte rangée par le briefer se lit dans `brief-a-fusionner` |

Leur nom comme leur corps portent l'ancienne règle : ils doivent dire la
nouvelle, et rester des contrôles qui peuvent rougir. Chacun garde ce
qu'il vérifie ; seule change la boîte d'où part la carte, et la ligne
imprimée qui la nomme. **Aucun autre test
existant n'est modifié** — ni son corps, ni ses valeurs attendues. Ce lot
ajoute ses cas aux fichiers qui portent déjà l'invariant concerné.

## Conditions de succès

### SC1 — La carte du briefer passe par la relecture

```bash
cd atelier_meta && PYTHONPATH="$(git rev-parse --show-toplevel)" python3 -m pytest tests/test_boite.py tests/test_feuille.py -q
```

Un cas montre qu'une carte de briefer avancée par `boite.avancer` atterrit
dans `a-relire`, et non dans une boîte qui attend une main. Un cas montre
que sur le même banc `python3 -m atelier piloter --projet <banc>` sort avec
le code 0 et n'imprime aucun `FAIL` alors que la fiche du lot est encore
`a-briefer` — c'est la garde du point 1 de la règle. Rouge d'abord sur la
base : le premier cas échoue sur `brief-a-fusionner`, le second sur
« on ne code pas un lot dont le brief n'est pas fusionné ».

### SC2 — Une PR `feuille/` ouverte sans approbation reçoit une carte

```bash
cd atelier_meta && PYTHONPATH="$(git rev-parse --show-toplevel)" python3 -m pytest tests/test_feuille.py -q
```

Un cas passe à la décision une liste de propositions ouvertes contenant une
PR `feuille/NNN-…` sans approbation, et vérifie qu'une carte `a-relire` est
déposée, portant le numéro de cette PR. Un second cas passe la même PR
**avec** une approbation d'un tiers et vérifie qu'aucune carte n'est
déposée : sans ce second cas, le premier ne prouve rien. Une liste vide de
propositions **échoue** au lieu de passer silencieusement — le nombre de
cartes attendues dérive de la liste, jamais d'un entier écrit en dur. Le
cas doit aussi tenir quand la fiche du lot n'est pas encore sur `master`,
puisque c'est la PR qui la dépose.

### SC3 — Le prompt du relecteur diffère selon le préfixe

```bash
cd atelier_meta && PYTHONPATH="$(git rev-parse --show-toplevel)" python3 -m pytest tests/test_invocation.py tests/test_roles.py -q
```

Un cas construit le prompt du rôle `relire` pour une branche de chacun des
trois préfixes déclarés dans `atelier.toml` § `[integration]`, lus depuis
ce fichier et non recopiés. Il vérifie que les trois textes sont deux à
deux différents, que le préfixe vide ou inconnu est refusé, et que chacun
nomme ce qui est propre à son cas : les cinq sections pour `brief/`, la
transition de fiche et `feuille valider` pour `feuille/`, `gh pr checks`
pour `agent/`. Il vérifie aussi que les trois interdisent d'écrire, de
pousser et de fusionner, et finissent sur une revue GitHub. Une liste de
préfixes vide **échoue**.

### SC4 — Le brief relu et fusionné ne laisse pas le lot en impasse

```bash
cd atelier_meta && PYTHONPATH="$(git rev-parse --show-toplevel)" python3 -m pytest tests/test_feuille.py tests/test_cycle.py -q
```

Un cas joue la suite complète sur un banc : carte de brief déposée, avancée
jusqu'à la relecture, approuvée, fiche passée à `pret` — puis vérifie que
`feuille.rapprochements` sort la carte de sa boîte et que `feuille.decider`
dépose la carte du coder pour ce lot au tour suivant. C'est le point 2 de
la règle : sans ce cas, le lot peut livrer une chaîne qui bloque après le
premier brief. Le contrôle échoue sur une base où la carte reste dans sa
boîte.

### SC5 — L'atelier reste vert, et hors ligne

```bash
cd atelier_meta && PYTHONPATH="$(git rev-parse --show-toplevel)" python3 -m pytest tests/ -q
cd atelier_meta/crons && shellcheck -x -s bash ./*.sh atelier-boucle profils/*.sh
python3 -m atelier feuille valider --projet .
```

La suite entière de l'atelier passe, `shellcheck` reste vert si `tour.sh`
a bougé, et le registre reste cohérent. Les tests ajoutés ne lancent ni
`gh` ni `git` distant : l'appel à GitHub est isolé dans sa fonction, et
celle-ci se tait quand `gh` est absent au lieu de faire tomber le tour, ce
qu'un cas vérifie en rendant `gh` introuvable.

### SC6 — Le lot n'a touché qu'à l'atelier

```bash
git diff --name-only origin/master
git diff --exit-code origin/master -- outils/ .github/ atelier.toml AGENTS.md docs/ VISION.md sim/ vues/ forge/ data/
git diff --name-only origin/master -- atelier_meta/tests/ briefs/
```

La deuxième commande sort avec 0 : aucun chemin interdit n'a bougé. La
troisième ne nomme que des fichiers de test, et la relecture vérifie que
les seules modifications de tests existants portent sur les six cas
nommés au périmètre ; tout le reste y est ajouté. Aucun brief n'est
modifié, celui-ci compris.

## Hors périmètre

Ce lot **ne fait pas** :

- **il ne fusionne rien, et ne donne à personne le droit de fusionner.**
  `integration.yml` fusionne déjà `brief/` et `feuille/` quand les
  conditions sont réunies ; la règle « jamais l'auteur » et la liste des
  contrôles déclarés ne changent pas ;
- **il ne touche pas au verdict.** `outils/relecture.py::juger` et
  `outils/integration.py` restent tels quels : ce lot dépose des cartes et
  écrit des prompts, il ne calcule aucune approbation ;
- **il ne touche pas à la page de pilotage.** Les colonnes du kanban sont
  le lot 242, le geste suivant de chaque carte le lot 243 ;
- **il ne pose ni la protection de `master`, ni Pages.** Ce sont les deux
  gestes qui ne sont pas du code, et c'est le lot 102 ;
- **il ne relit pas les branches hors préfixe.** Une branche d'expérience
  qui passe au vert n'est pas un lot et continue d'attendre le
  propriétaire ;
- **il n'ajoute aucun rôle et aucun compte.** Le rôle `relire` et le jeton
  `relire.token` du second compte existent : ce lot leur donne deux cas de
  plus, pas un successeur ;
- **il ne change pas le format du brief.** Les cinq sections restent celles
  d'`AGENTS.md`.
