# Brief 243 — Chaque carte du kanban nomme son geste suivant

## But

Sur chaque carte du kanban que le lot 242 dessine, ajouter la phrase qui dit
ce qu'il faut faire ensuite pour cette fiche, et le lien qui y emmène — et
enrichir la carte des informations qu'elle ne montre pas encore : le lien
vers son brief, le lien vers sa proposition ouverte, ses contrôles (n verts
sur le nombre déclaré dans `atelier.toml`), la raison brute que
l'intégration retient pour elle, et ses dépendances rendues cliquables.

État de départ à mesurer :

```bash
grep -n "geste\|suivante\|lien_fichiers" outils/actions.py outils/tableau.py
python3 -m pytest outils/tests/test_tableau.py -q
```

Aujourd'hui, une carte (celle que le lot 242 introduit, ou la ligne de
table qu'elle remplace tant que 242 n'est pas codé) montre un numéro, un
titre en texte brut, l'état, l'âge, une liste de numéros de dépendances et
une liste de numéros de PR — tous en texte brut, sans lien. Rien sur la
page ne dit ce qu'il faut faire ensuite ; les sept liens de la table « Ce
qu'on peut déclencher d'ici » sont génériques, aucun rattaché à une carte
précise, et l'utilisateur doit deviner quel numéro y coller.

Ce qui rend ce lot caduc : si `outils/tableau.py` porte déjà, sur une
carte, un lien vers son brief et une phrase de geste suivant. Ce qui le
rend bloqué : si le lot 242 n'est pas fusionné (ce lot dépend de la
disposition en colonnes et des cartes qu'il introduit), ou si les
signatures de `integration.examiner`, `integration.manque`,
`relecture.juger` ou `outils/github.py::auteurs_du_code` changent de
contrat sous ce lot.

## Règle du monde

Ce lot ne touche aucune règle du monde simulé : `sim/` n'est pas concerné,
et la fidélité est **sans objet** — comme pour le lot 242 dont il dépend.

Sa règle est celle de l'atelier, écrite dans
[`docs/WORKFLOW.md`](../docs/WORKFLOW.md) : une fiche `idee` attend une
décision du propriétaire ; une fiche `a-briefer` ou `pret` attend un geste
mécanique, soit du propriétaire (approuver, rejouer un contrôle, sortir un
brouillon, relancer l'intégration), soit rien — la machine avance seule
tant qu'elle n'est pas bloquée. Ce lot ne change ni cet enchaînement, ni
qui a le droit de faire quoi ; il le rend visible, carte par carte.

**Elle ne décide jamais elle-même si une PR est mergeable, si un contrôle
est vert ou si une revue compte.** Le geste d'une carte se choisit sur ce
que `integration.examiner` (l'action et sa raison), `integration.manque`
et `relecture.juger` (via `outils/__main__.py`, qui les appelle déjà pour
construire la page) ont déjà décidé pour la PR ouverte de cette fiche — la
même donnée que celle que `_registre` affiche déjà dans la colonne
« pourquoi » du tableau des propositions ouvertes. Choisir un lien ou un
libellé à partir d'une raison déjà connue n'est pas recalculer un état :
tant que le texte affiché reste celui de la machine, mot pour mot, se
tromper de lien ne fait jamais dire à la page autre chose que ce qu'elle
sait — au pire elle propose un geste trop générique, jamais un geste faux.

**Le compte à utiliser pour approuver dérive des connexions qui ont écrit
le code**, pas d'un nom écrit en dur : `outils/github.py::auteurs_du_code`
lit déjà ces connexions pour que `relecture.juger` sache qui n'a pas le
droit de juger son propre travail
([docs/WORKFLOW.md](../docs/WORKFLOW.md), « le relecteur — jamais
l'auteur »). Si `github-actions[bot]` en fait partie, la carte propose le
compte principal ; sinon, elle propose le second compte — celui qui
signe les revues, comme le disent les commentaires de
`atelier_meta/crons/tour.sh` et `atelier_meta/crons/profils/jour.sh` sur le
jeton du relecteur. Cette liste de connexions est lue une fois, là où la
page lit déjà tout le reste (`outils/__main__.py`), jamais recalculée dans
`outils/tableau.py`, qui ne parle pas à GitHub.

**Le dénominateur des contrôles ne s'écrit jamais en dur.** Il vient de la
liste déjà déclarée dans `atelier.toml` § `[integration]`, la même que
`outils/tableau.py::_sante` affiche déjà (« les N contrôles déclarés »
— `Etat.sante.requis`). Un lot qui écrirait `7` en dur referait l'erreur
que la règle 3 du dépôt interdit.

**Une carte ne devient pas un bouton.** La page reste statique, publiée
sur GitHub Pages, sans jeton, sans appel réseau, sans script — exactement
la contrainte de 242 et de `outils/tableau.py` depuis toujours. Un geste
est un lien vers la page GitHub qui le fait, ou vers la commande à taper
sur le VPS ; jamais un formulaire, jamais un `fetch`.

## Périmètre

En écriture : `outils/actions.py` (les nouveaux liens — vers l'onglet
Files d'une PR, et le paramètre `depend=` de `lien_demande` — et la
fonction qui décide le couple libellé/lien d'un geste), `outils/tableau.py`
(le rendu de la carte : lien du titre vers le brief, lien des PR, contrôles
n/N, raison mot pour mot, dépendances cliquables, geste suivant) et
`outils/tests/test_tableau.py`, pour y **ajouter** des cas. Aucun test
déjà vert n'est modifié.

`outils/__main__.py` entre aussi dans ce périmètre, mais seulement pour
transmettre à la page une donnée qu'elle lit déjà pour un autre usage : les
connexions auteurs du code d'une PR ouverte (`github.auteurs_du_code`,
déjà appelée par `_verdict` pour juger la relecture de cette même PR). Ce
n'est ni un nouvel appel GitHub de nature différente, ni une nouvelle
décision : c'est une valeur déjà lue, portée jusqu'à la carte qui la montre.

**Écart avec la demande d'origine (issue #24) à noter dans la PR** : la
demande cite `outils/kanban.py` et `outils/relecture.py::auteurs_du_code`.
Le premier n'existe pas — le lot 242, dont celui-ci dépend, garde toute la
logique du kanban dans `outils/tableau.py`, sans nouveau module ; la
seconde fonction vit réellement dans `outils/github.py`. Ce brief suit le
code tel qu'il est, pas la citation approximative de la demande.

Tout autre chemin est interdit, nommément : `outils/attention.py`,
`outils/histoire.py`, `outils/palier.py`, `outils/integration.py`,
`outils/relecture.py`, `outils/github.py`, `outils/registre.py`,
`atelier/` en entier, `atelier.toml`, `ROADMAP.md`, `docs/WORKFLOW.md`,
`AGENTS.md`, `.github/` en entier, tout `sim/`, `vues/`, `forge/`, et les
autres briefs. La fiche 243 relève du périmètre implicite de la PR de lot ;
aucune autre fiche ni prose de la feuille de route ne change.

## Conditions de succès

Comparaisons « avant / après » contre `master` rejoué au démarrage du lot.

### SC1 — Une carte `idee` propose de demander le brief

Une fiche `idee`, sans PR. Sur sa carte : un lien dont le texte contient
« demander le brief », dont la cible contient
`actions/workflows/etat-lot.yml`, et le couple à taper (le numéro du lot,
l'état visé `a-briefer`) apparaît à côté, en clair.

`python3 -m pytest outils/tests/test_tableau.py -k kanban_geste_idee -q`.
Rouge d'abord : aucune carte ne porte de geste sur `master`.

### SC2 — Une carte `a-briefer` ou `pret` lit la raison de sa PR ouverte

Trois fiches, chacune `pret`, chacune avec une seule PR ouverte dans
`lignes_pr` :

- l'une dont la décision porte la raison « contrôle absent : outils » —
  sa carte porte un lien dont le texte contient « rejouer les contrôles »,
  la cible contient `actions/workflows/controles.yml`, et le numéro de la
  PR apparaît à côté ;
- l'une dont la PR est un brouillon — sa carte porte un lien dont le texte
  contient « sortir du brouillon », la cible contient
  `actions/workflows/brouillon.yml` ;
- l'une dont la décision porte une raison qui ne correspond à aucun des
  gestes nommés par ce lot (« en conflit avec master ») — sa carte porte
  un lien vers la proposition elle-même (`pull/<numéro>`), jamais un lien
  mort ni une carte sans geste.

Une fiche sans dépendance et sans ambiguïté par scénario, pour que le
geste observé revienne sans détour à la PR qui l'a produit.

`python3 -m pytest outils/tests/test_tableau.py -k kanban_geste_pr -q`.
Rouge d'abord : sur `master`, la raison d'une PR n'apparaît nulle part sur
sa carte, et aucun de ces trois liens n'existe.

### SC3 — Le compte à approuver dérive des auteurs du code, jamais d'un nom écrit en dur

Deux fiches `pret`, chacune avec une PR ouverte dont la décision signale
l'absence de relecture d'un tiers :

- l'une dont les auteurs du code sont `("github-actions[bot]",)` — le
  geste de sa carte contient « compte principal » ;
- l'une dont les auteurs du code sont `("pliagre",)` (n'importe quelle
  connexion qui n'est pas `github-actions[bot]`) — le geste de sa carte
  contient « second compte ».

Dans les deux cas, le lien de la carte pointe vers l'onglet Files de la PR
(`pull/<numéro>/files`), pas seulement vers la PR.

`python3 -m pytest outils/tests/test_tableau.py -k kanban_geste_compte -q`.
Rouge d'abord : aucune carte ne distingue aujourd'hui un compte d'un
autre — la donnée n'existe même pas dans `tableau.rendre`.

### SC4 — La carte porte le brief, la PR, les contrôles et les dépendances, avec un dénominateur dérivé

Deux fiches `pret` de la même couche : la fiche `240` (sans dépendance),
et la fiche `241`, avec `depend_de=("240",)`, `prs=(226,)`, et une PR
ouverte dont les contrôles donnent 3 verts pour un règlage dont
`Etat.sante.requis` ne porte que 4 noms (délibérément différent de 7, la
longueur réelle de `atelier.toml`, pour prouver qu'aucun total n'est écrit
en dur). Sur la carte de `241` :

- son titre est un lien vers son brief (`fiche.chemin`) ;
- « 226 » est un lien vers `pull/226` ;
- « 3/4 » apparaît, jamais « 3/7 » ni un compte qui ignore `requis` ;
- la raison de la décision de la PR 226 apparaît mot pour mot ;
- « 240 » est un lien vers la carte de la fiche 240, présente sur la même
  page.

`python3 -m pytest outils/tests/test_tableau.py -k kanban_carte_enrichie -q`.
Rouge d'abord : sur `master`, aucun de ces éléments n'est un lien, et le
compte de contrôles n'existe pas.

### SC5 — Le formulaire de demande, pré-rempli depuis une carte

Un test direct, sans passer par `tableau.rendre` : `actions.lien_demande`
accepte un paramètre qui pré-remplit le champ `depend` du formulaire
GitHub (`.github/ISSUE_TEMPLATE/nouveau-lot.yml`, champ `id: depend`) ;
appelé avec le numéro d'une fiche, l'URL rendue porte `depend=<numéro>`
dans sa requête. Sur la carte d'une fiche quelconque, un lien vers ce
formulaire porte ce même paramètre, rempli avec le numéro de la fiche.

`python3 -m pytest outils/tests/test_tableau.py -k kanban_demande_depend -q`.
Rouge d'abord : `lien_demande` ne connaît que `couche`, jamais `depend`.

### SC6 — Rien d'autre ne régresse

```bash
python3 -m pytest outils/tests/ -q
python3 -m atelier feuille valider --projet .
```

La liste des tests en échec est vide, comparée à celle de `master` plutôt
que supposée. Le nombre de tests collectés est au moins celui de `master`.
Tous les tests déjà présents dans `outils/tests/test_tableau.py` restent
verts sans modification — en particulier ceux que 242 aura ajoutés sur
l'ordre des colonnes et des cartes, qu'un geste ajouté sur une carte ne
doit ni déplacer ni dédoubler.

## Hors périmètre

- dessiner les colonnes, leur ordre, ou la disposition des cartes : c'est
  le lot 242, dont celui-ci dépend et qu'il ne refait pas ;
- créer ou modifier un travail de `.github/` : les quatre gestes de ce
  lot pointent vers des travaux qui existent déjà
  (`etat-lot.yml`, `controles.yml`, `brouillon.yml`, `integration.yml`) ;
- nommer un geste dédié pour chaque raison que peuvent produire
  `integration.examiner`, `integration.manque` ou `relecture.juger` — au
  delà des quatre gestes que la demande nomme (demander le brief, rejouer
  les contrôles, sortir du brouillon, approuver), toute autre raison
  retombe sur le lien générique vers la proposition (SC2, troisième cas) ;
- rendre une carte cliquable pour agir directement, lui donner un
  formulaire, ou permettre de la faire glisser : la page reste statique,
  sans jeton, sans appel réseau, sans script, comme 242 ;
- recalculer si un contrôle est vert, si une PR est mergeable ou si une
  revue compte : ça reste `integration.py` et `relecture.py`, lus mot
  pour mot ;
- ajouter un appel GitHub de nature nouvelle (lire des issues, des
  labels, des fichiers changés) : la seule donnée neuve est
  `auteurs_du_code`, déjà lue par la page pour juger la relecture ;
- toucher `atelier/`, `atelier.toml`, `ROADMAP.md`, `docs/WORKFLOW.md`,
  `AGENTS.md`, ou tout autre brief ;
- calibrer un test existant après observation, ou modifier un test déjà
  vert.
