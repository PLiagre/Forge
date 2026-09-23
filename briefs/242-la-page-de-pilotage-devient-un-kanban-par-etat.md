# Brief 242 — La page de pilotage devient un kanban par état

## But

Dans le bloc « L'avancement » de la page de pilotage, remplacer la table de
fiches de chaque couche — et celle des lots hors couche — par un kanban :
une colonne par état, dans l'ordre où les états s'enchaînent, une carte par
fiche, dans la colonne de son état.

État de départ à mesurer :

```bash
grep -n "colonne\|kanban" outils/tableau.py outils/tests/test_tableau.py
python3 -m pytest outils/tests/test_tableau.py -q
```

Aujourd'hui, `outils/tableau.py::_couche` rend, pour chaque couche, un seul
`<table>` où l'état de chaque fiche n'est qu'une colonne parmi d'autres
(lot, titre, état, dans cet état, dépend de, PR) — il faut lire toute la
ligne pour le voir. Le bloc « Hors couche » fait de même. Ce lot ne change
aucune donnée : il change la façon dont les mêmes fiches, avec les mêmes
champs, sont groupées à l'écran — par état d'abord, pas seulement par
couche.

Ce qui rend ce lot caduc : si la commande `grep` ci-dessus montre déjà une
mise en page en colonnes par état dans `outils/tableau.py`. Ce qui le rend
bloqué : si `outils/palier.py::etapes`, `outils/palier.py::FINIS`, ou les
champs de `Fiche` (`numero`, `titre`, `etat`, `couche`, `depend_de`, `prs`)
changent de contrat sous ce lot.

## Règle du monde

Ce lot ne touche aucune règle du monde simulé : `sim/` n'est pas concerné,
et la fidélité est **sans objet**. Sa règle est celle de l'atelier, écrite
dans [`docs/WORKFLOW.md`](../docs/WORKFLOW.md) § « Les six états d'une
fiche » : `idee`, `a-briefer`, `pret`, `livre`, `abandonne`, `archive`, dans
cet ordre — c'est l'ordre des colonnes du kanban, et il ne s'invente pas
une seconde fois : `outils/tableau.py::TONS` énumère déjà ces six mêmes
états (pour leur donner un ton) ; le nouvel ordre de colonnes est une
constante distincte, et un test compare son ensemble à celui des clés de
`TONS` pour que les deux ne divergent jamais en silence.

Un principe déjà en vigueur dans `outils/tableau.py` gouverne ce lot, et il
ne le contourne pas : **elle ne calcule aucun état.** L'état d'une fiche,
sa couche, ses dépendances, ses PR, son âge dans l'état — tout vient déjà
du registre et de `Etat` (`outils/tableau.py::Etat`), inchangés. Ce lot ne
fait que réorganiser à l'écran des champs déjà lus ; une page qui
recalculerait quoi que ce soit pour son affichage finirait par montrer
autre chose que ce que la machine décide, et c'est le mode de défaillance
n°4 du dépôt.

**La couche reste l'axe qui regroupe les sections, l'état devient l'axe qui
regroupe les cartes à l'intérieur.** La jauge, le compte « N lot(s) sur M »,
le badge « finie » / « palier dû » / « N lot(s) en cours » et le lien de
demande d'un lot, déjà rendus par `_couche`, ne changent pas : ce sont des
données de couche, pas de kanban, et rien dans ce lot n'a de raison d'y
toucher. Seule change la façon dont les fiches d'une couche — puis celles
sans couche — sont listées en dessous.

Une colonne n'apparaît que si au moins une fiche du groupe affiché (la
couche, ou le hors-couche) est dans cet état : un kanban dont les colonnes
vides s'affichent quand même serait un mur de vide pour une couche qui
commence. Les cartes d'une colonne gardent l'ordre des fiches reçues par
`tableau.rendre` — un tri stable, jamais un tri nouveau par numéro, par âge
ou par priorité : ce genre de tri n'existe nulle part ailleurs sur la page,
et lui en inventer un ici serait une décision que ce lot ne doit pas
prendre.

## Périmètre

En écriture : `outils/tableau.py` (la fonction de rendu du kanban, la
constante d'ordre des colonnes, le remplacement du contenu de `_couche` et
du bloc hors couche, et les classes CSS ajoutées à `STYLE` — en réutilisant
les couleurs déjà nommées dans `:root`, sans en ajouter une seule) et
`outils/tests/test_tableau.py`, pour y **ajouter** des cas. Aucun test déjà
vert n'est modifié.

Tout autre chemin est interdit, nommément : `outils/attention.py`,
`outils/actions.py`, `outils/histoire.py`, `outils/palier.py`,
`outils/integration.py`, `outils/registre.py`, `outils/__main__.py`,
`atelier/` en entier, `atelier.toml`, `ROADMAP.md`, `docs/WORKFLOW.md`,
`AGENTS.md`, tout `sim/`, `vues/`, `forge/`, `.github/`, et les autres
briefs — en particulier `briefs/243-chaque-carte-du-kanban-nomme-son-geste-suivant.md`,
qui dépend de celui-ci mais n'en fait pas partie. La fiche 242 relève du
périmètre implicite de la PR de lot ; aucune autre fiche ni prose de la
feuille de route ne change.

## Conditions de succès

Comparaisons « avant / après » contre `master` rejoué au démarrage du lot.

### SC1 — Dans une couche, seuls les états représentés ont une colonne, triés dans l'ordre du pipeline, jamais l'ordre d'entrée

Trois fiches de la couche 1, données à `tableau.rendre` dans cet ordre :
l'une `livre`, l'une `idee`, l'une `pret` — délibérément hors de l'ordre du
pipeline. Dans le bloc HTML de la couche 1 (entre son titre « Couche 1 —
… » et le titre du bloc suivant), les marqueurs des trois colonnes
apparaissent dans cet ordre : `idee`, `pret`, `livre` ; aucun marqueur pour
`a-briefer`, `abandonne` ou `archive` n'apparaît dans ce bloc, puisqu'aucune
fiche de la couche ne les porte.

Un second test, sans passer par `tableau.rendre`, compare l'ensemble de la
constante d'ordre des colonnes à `set(tableau.TONS)` : les deux ensembles
sont égaux.

`python3 -m pytest outils/tests/test_tableau.py -k kanban_ordre -q`.
Rouge d'abord : sur `master`, `_couche` rend une seule table sans colonnes
— les trois marqueurs ne se trouvent pas dans un ordre à comparer, ou pas
du tout.

### SC2 — Chaque carte porte les informations déjà montrées, et n'apparaît que dans la colonne de son propre état

Deux fiches de la couche 1 : l'une `pret`, avec `depend_de=("040",)` et une
PR `prs=(226,)` ; l'autre `livre`, sans dépendance ni PR. `etat.ages` porte
5 jours pour la première. Dans le bloc de la couche 1 : le numéro, le
titre, « 040 », « 226 » et « 5 j » de la première fiche apparaissent tous
dans la portion du bloc comprise entre le marqueur de colonne `pret` et le
marqueur de colonne suivant (`livre`) ; aucun de ces éléments n'apparaît
dans la portion `livre`, ni avant le marqueur `pret`.

`python3 -m pytest outils/tests/test_tableau.py -k kanban_carte -q`.
Rouge d'abord : les marqueurs de colonne n'existent pas encore sur
`master`.

### SC3 — Les lots hors couche suivent la même mise en page en colonnes

Deux fiches sans couche, d'états `idee` et `livre`. Le bloc « Hors couche »
présente les mêmes marqueurs de colonne qu'un bloc de couche, dans le même
ordre, et chaque fiche apparaît dans la colonne de son état. Le titre
« Hors couche » reste présent : `test_les_lots_sans_couche_ne_sont_pas_perdus`,
déjà vert, continue de passer sans modification.

`python3 -m pytest outils/tests/test_tableau.py -k kanban_hors_couche -q`.

### SC4 — L'ordre des cartes dans une colonne suit l'ordre d'entrée, pas un tri nouveau

Trois fiches `pret` de la même couche, numérotées `010`, `005`, `020`, dans
cet ordre d'entrée — délibérément pas trié par numéro. Dans la colonne
`pret`, elles apparaissent dans cet ordre : `010`, puis `005`, puis `020`.

`python3 -m pytest outils/tests/test_tableau.py -k kanban_stable -q`.
Rouge d'abord : sans colonnes, il n'y a pas d'ordre interne à une colonne à
observer.

### SC5 — Rien d'autre ne régresse

```bash
python3 -m pytest outils/tests/ -q
python3 -m atelier feuille valider --projet .
```

La liste des tests en échec est vide, comparée à celle de `master` plutôt
que supposée. Le nombre de tests collectés est au moins celui de `master`.
Tous les tests déjà présents dans `outils/tests/test_tableau.py` restent
verts sans modification — en particulier ceux qui portent sur la
progression par couche (« N lot(s) sur M », « en cours », « finie »,
« palier dû », le lien de demande), sur l'échappement d'un titre, et sur
les deux thèmes de couleur : ces derniers scannent la page entière et
couvrent donc aussi le nouveau balisage, sans qu'il faille leur ajouter un
cas.

## Hors périmètre

- ajouter sur une carte la phrase qui nomme le geste suivant pour la fiche
  qu'elle porte : c'est le lot 243, qui dépend de celui-ci ;
- changer les champs montrés par une carte au-delà de ceux déjà montrés par
  la table qu'elle remplace (numéro, titre, dépend de, PR, âge dans
  l'état) ;
- rendre une carte cliquable ou actionnable, ou permettre de la faire
  glisser d'une colonne à l'autre : la page reste statique, sans jeton, sans
  appel réseau, sans script ;
- trier les cartes d'une colonne autrement que par l'ordre d'entrée (par
  priorité, par âge, par numéro) ;
- toucher « Ce qui demande une décision maintenant », « La santé de la
  chaîne », « Le journal des fusions », « Le registre complet », ou tout
  bloc de la page autre que « L'avancement » ;
- changer `palier.etapes`, `attention.alertes`, `integration.examiner`, ou
  tout seuil de `[tableau]` dans `atelier.toml` ;
- calibrer un test existant après observation, ou modifier un test déjà
  vert.
