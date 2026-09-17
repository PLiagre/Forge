# Brief 243 — Chaque carte du kanban nomme son geste suivant

## But

Sur la page de pilotage, faire porter à la carte de chaque fiche la phrase
qui nomme ce qui doit se passer ensuite pour *elle*, et qui le tient —
jamais une étiquette générique de son état, jamais une seconde estimation :
la même donnée que celle déjà calculée ailleurs sur la page, reprise mot
pour mot.

État de départ à mesurer :

```bash
grep -n "geste" outils/tableau.py outils/tests/test_tableau.py
python3 -m pytest outils/tests/test_tableau.py -q
```

Aujourd'hui, `outils/tableau.py` § « Ce qui demande une décision maintenant »
ne nomme un geste que pour les fiches déjà en anomalie (proposition retenue,
conflit, palier dû, lot bloqué, brouillon oublié). Une fiche qui avance
normalement — `idee`, `a-briefer` ou `pret` sans blocage, ou dont la
proposition est simplement en cours de contrôle — n'affiche aucune
indication de ce qui la ferait avancer. Ce lot comble cet écart, pour
*toutes* les fiches, pas seulement celles qui bloquent déjà quelque chose.

Ce qui rend ce lot caduc : si la commande `grep` ci-dessus montre déjà
qu'une phrase de geste est associée à chaque fiche affichée, dérivée sans
recalcul. Ce qui le rend bloqué : si `outils/histoire.py::lot_de_la_branche`,
`outils/attention.py::LOT_BLOQUE`/`alertes`, `outils/palier.py::FINIS` ou
`atelier/feuille.py::TRANSITIONS` changent de contrat sous ce lot.

## Règle du monde

Ce lot ne touche aucune règle du monde simulé : `sim/` n'est pas concerné,
et la fidélité est **sans objet**. Sa règle est celle de l'atelier, écrite
dans [`docs/WORKFLOW.md`](../docs/WORKFLOW.md) § « Les six états d'une
fiche » : chaque transition d'état y est déjà nommée, avec qui la tient —
`atelier/feuille.py::TRANSITIONS` en est la version lue par la machine.
Ce lot ne réécrit pas ce tableau : il l'affiche, fiche par fiche, sur la
carte qui la concerne.

Deux principes déjà en vigueur dans `outils/tableau.py` et
`outils/attention.py` gouvernent ce lot, et il ne les contourne pas :

- **elle ne décide rien.** La cause qui retient une proposition est celle
  que `integration.examiner` a déjà rendue, reprise mot pour mot depuis
  `LignePR.raison` — la même donnée que celle déjà montrée dans « Le
  registre complet ». La cause qui bloque une fiche `pret` sur une
  dépendance non livrée est celle que `attention.alertes` a déjà calculée
  (catégorie `LOT_BLOQUE`) — la même donnée que celle déjà montrée dans
  « Ce qui demande une décision maintenant ». Aucune des deux n'est
  recalculée une seconde fois avec une formule différente ;
- **un texte qui duplique une prose extérieure porte l'aveu de sa source.**
  `outils/tableau.py::NOMS` copie déjà les noms de couche de `VISION.md`
  avec ce commentaire. Les trois phrases par défaut de ce lot — pour
  `idee`, `a-briefer` et `pret`, quand aucune proposition ouverte ni aucune
  dépendance bloquée ne les concerne — sont recopiées mot pour mot depuis
  `atelier/feuille.py::TRANSITIONS["idee"]["a-briefer"]`,
  `TRANSITIONS["a-briefer"]["pret"]` et `TRANSITIONS["pret"]["livre"]`,
  dans une constante nommée `GESTE_PAR_DEFAUT` de `outils/tableau.py`. Un
  test compare cette constante à `atelier.feuille.TRANSITIONS` pour que
  toute divergence future rougisse au lieu de se découvrir à l'œil.

### Ce que chaque carte nomme, dans l'ordre où ça se décide

Pour une fiche dont l'état est `livre`, `archive` ou `abandonne`
(`outils/palier.py::FINIS`) : rien. Ces fiches n'attendent plus personne,
comme le dit déjà la ligne d'avancement d'une couche (« … ne demandent
plus rien ») ; la carte porte la phrase singulière « ne demande plus
rien ».

Sinon, dans cet ordre — le premier qui s'applique gagne, aucun cumul :

1. **une proposition ouverte porte le numéro de ce lot.** Le numéro se lit
   par `histoire.lot_de_la_branche(branche)` sur chaque `LignePR` reçue par
   `tableau.rendre`. S'il en existe plusieurs pour le même lot, celle dont
   le numéro de PR est le plus petit est retenue — un ordre stable, jamais
   celui d'énumération. La carte porte le champ `raison` de cette
   proposition, mot pour mot, quelle que soit l'action qu'il accompagne
   (`fusionner`, `rebaser` ou `rien`) ;
2. **la fiche est `pret` et `etat.alertes` porte une alerte `LOT_BLOQUE`
   dont le texte commence par `f"le lot {fiche.numero} "`.** La carte
   porte ce texte, mot pour mot ;
3. **sinon**, la carte porte `GESTE_PAR_DEFAUT[fiche.etat]`, un couple
   (état cible, texte de `TRANSITIONS`) : la phrase nomme les deux —
   l'état cible et qui tient le geste — par exemple pour `idee` : l'état
   cible `a-briefer` et le texte
   `"le propriétaire, dans une PR de feuille"`.

Une fiche `pret` avec à la fois une proposition ouverte et une dépendance
non livrée montre la proposition (cas 1) : c'est l'information la plus
fraîche, et celle qui bloque réellement l'avancement au moment où la page
est écrite.

## Périmètre

En écriture : `outils/tableau.py` (la constante `GESTE_PAR_DEFAUT` et le
calcul, par fiche, du texte affiché) et `outils/tests/test_tableau.py`,
pour y **ajouter** des cas. Aucun test déjà vert n'est modifié.

Tout autre chemin est interdit, nommément : `outils/attention.py`,
`outils/actions.py`, `outils/histoire.py`, `outils/palier.py`,
`outils/integration.py`, `outils/registre.py`, `outils/__main__.py`,
`atelier/` en entier, `atelier.toml`, `ROADMAP.md`, `docs/WORKFLOW.md`,
`AGENTS.md`, tout `sim/`, `vues/`, `forge/`, `.github/`, et les autres
briefs. Ce lot lit ce que ces modules rendent déjà ; il n'en change
aucun. La fiche 243 relève du périmètre implicite de la PR de lot ;
aucune autre fiche ni prose de la feuille de route ne change.

## Conditions de succès

Comparaisons « avant / après » contre `master` rejoué au démarrage du lot.

### SC1 — Une proposition ouverte remplace, sur sa seule carte, le geste par défaut

Deux fiches `pret` de même couche, sans dépendance : l'une sans
proposition ouverte, l'autre avec une proposition dont le motif est
distinct du texte par défaut de l'état `pret` (par exemple
`"contrôle rouge : sim"`). Sur la page rendue :

- le motif de la proposition apparaît, associé à la fiche qui la porte ;
- `GESTE_PAR_DEFAUT["pret"]` (le texte de `TRANSITIONS["pret"]["livre"]`)
  apparaît **exactement une fois** — celle de la fiche sans proposition —
  malgré deux fiches `pret` sur la page.

Une seconde épreuve couvre le départage : deux propositions ouvertes pour
le même lot, deux motifs distincts ; seul le motif de celle dont le numéro
de PR est le plus petit apparaît sur la page.

`python3 -m pytest outils/tests/test_tableau.py -k geste_remplace -q`.
Rouge d'abord : sur `master`, le texte par défaut de l'état `pret`
n'existe pas, la distinction n'a donc aucun sens à vérifier — le test
échoue par `AttributeError` ou par absence totale des deux textes.

### SC2 — Une fiche `pret` bloquée par une dépendance non livrée nomme ce blocage

Une fiche `a-briefer` et une fiche `pret` qui en dépend, aucune proposition
ouverte pour aucune des deux. `etat.alertes` est calculée par
`attention.alertes(fiches=…, brouillon_jours=…, maintenant=…)`, comme le
fait déjà `outils/__main__.py`. Sur la page rendue, le texte porté par la
carte de la fiche `pret` est identique, caractère pour caractère, à celui
de l'alerte `LOT_BLOQUE` correspondante ; `GESTE_PAR_DEFAUT["pret"]`
n'apparaît pas sur cette carte.

`python3 -m pytest outils/tests/test_tableau.py -k geste_bloque -q`.

### SC3 — Une proposition ouverte l'emporte sur une dépendance bloquée

Même fiche `pret` bloquée qu'en SC2, mais avec en plus une proposition
ouverte pour son lot. Le texte affiché est le motif de la proposition ;
la phrase de blocage par dépendance (« … qui est « a-briefer » ») n'est
pas celle qui apparaît pour cette carte.

`python3 -m pytest outils/tests/test_tableau.py -k geste_priorite -q`.

### SC4 — Les trois gestes par défaut couvrent `idee`, `a-briefer` et `pret`, et ne divergent pas du registre des transitions

Trois fiches, une par état `idee`, `a-briefer` et `pret`, sans proposition
ni blocage : la page rendue porte les trois textes de
`GESTE_PAR_DEFAUT`, chacun associé à l'état cible qu'il nomme.

Un second test, sans passer par `tableau.rendre`, compare directement
`outils.tableau.GESTE_PAR_DEFAUT` à `atelier.feuille.TRANSITIONS` importé
(comme le fait déjà `outils/tests/test_lecture.py`) : les trois textes
sont égaux, caractère pour caractère, à
`TRANSITIONS["idee"]["a-briefer"]`, `TRANSITIONS["a-briefer"]["pret"]` et
`TRANSITIONS["pret"]["livre"]`.

`python3 -m pytest outils/tests/test_tableau.py -k geste_defaut -q`.
Rouge d'abord : `GESTE_PAR_DEFAUT` n'existe pas sur `master`.

### SC5 — Une fiche terminée ne nomme aucun geste

Trois fiches, une par état `livre`, `archive` et `abandonne`, sans
proposition ouverte. La page rendue porte, pour chacune, la phrase
singulière « ne demande plus rien » ; aucune des trois valeurs de
`GESTE_PAR_DEFAUT` n'apparaît sur la page.

`python3 -m pytest outils/tests/test_tableau.py -k geste_termine -q`.

### SC6 — Rien d'autre ne régresse

```bash
python3 -m pytest outils/tests/ -q
python3 -m atelier feuille valider --projet .
```

La liste des tests en échec est vide, comparée à celle de `master` plutôt
que supposée. Le nombre de tests collectés est au moins celui de
`master`. Tous les tests déjà présents dans `outils/tests/test_tableau.py`
restent verts sans modification.

## Hors périmètre

- construire le kanban par état lui-même, ses colonnes, sa mise en page —
  c'est le lot 242, dont celui-ci dépend ;
- ajouter une nouvelle catégorie d'alerte, changer `RANGS`, ou modifier ce
  que `integration.examiner` ou `attention.alertes` décident ;
- rendre une carte cliquable ou actionnable : la page reste statique, sans
  jeton ni appel réseau ;
- nommer un geste pour les propositions qui ne portent aucun numéro de
  lot (branches d'expérience hors préfixes) ;
- toute modification de `atelier/feuille.py::TRANSITIONS`, de
  `docs/WORKFLOW.md` ou de `AGENTS.md` : ce lot les lit, il ne les réécrit
  pas ;
- calibrer un test existant après observation, ou modifier un test déjà
  vert.
