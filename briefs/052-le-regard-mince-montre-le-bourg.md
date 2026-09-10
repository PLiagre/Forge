# Brief 052 — Le regard mince montre le bourg

## But

Faire porter au bandeau du tableau de bord (`viewer/`) le partage bourg /
campagne que le lot 051 fait déjà porter à chaque cellule du snapshot,
exactement comme le bandeau porte déjà la population totale, le stock de
nourriture et le nombre de cellules affamées. Après ce lot, qui ouvre le
tableau de bord voit, à côté de la population totale, combien d'habitants du
monde vivent du bourg et combien vivent des champs ; avant, cette donnée
existe dans le document mais aucune vue ne la lit.

Ce lot ne calcule rien de nouveau : il **lit** le champ `bourg` que le lot
051 fait porter à chaque cellule du document (`cell["bourg"]["habitants_du_bourg"]`,
`cell["bourg"]["habitants_des_champs"]`) et l'**agrège** sur le monde, comme
`viewer/snapshot_loader.py` agrège déjà `population` en `agregats_monde`. Si
après ce lot `py -m sim`, `py -m sim --ticks 365 --seed 0 --json` ou le
contenu d'un snapshot rendent un résultat différent, le lot est faux : seul
`GET /dashboard.json` et le tableau de bord statique changent.

Ce qui rend ce lot caduc : si `viewer/snapshot_loader.py::agregats_monde`
rend déjà `habitants_du_bourg` et `habitants_des_champs`. Ce qui le rend
**bloqué** : si le champ `bourg` n'apparaît pas encore sur les cellules du
snapshot — c'est-à-dire tant que le lot 051 n'est pas fusionné.

```bash
grep -n "habitants_du_bourg\|habitants_des_champs" viewer/snapshot_loader.py
grep -n "bourg" sim/snapshot_export.py
grep -n "kpi-bourg\|kpi-champs" viewer/static/index.html
```

## Règle du monde

Ce lot n'ajoute et ne modifie aucune règle du monde. La règle qu'il affiche
est déjà écrite dans [`sim/MODELE.md`](../sim/MODELE.md) § « Ce qu'est une
ville, à l'échelle d'une cellule », sous-section « Ce que le moteur ne fait
toujours pas » : *« [le bourg] ne change aucun nombre du monde : c'est une
vue, et une vue ne décide rien »*. Le lot 051 a rendu cette vue lisible
depuis un fichier ; celui-ci se contente de l'agréger et de l'afficher, au
même titre que `viewer/` agrège déjà `population` sans la recalculer.

C'est aussi le motif que `sim/MODELE.md` § « La province dérivée et ses
centres », sous-section « Ce que l'agrégation ne fait pas — et le motif que
toute vue recopie », déclare général : *« elle vit hors de `sim.model`, elle
est pure, elle refuse de deviner (…) et le tick ne la lit pas »* — et que
`viewer/README.md` redit pour ce paquet précis : *« Aucune logique métier :
le paquet lit un snapshot et montre les cellules déjà photographiées. »*
`viewer/` est un second regard sur une vue déjà figée par 051 ; il ne la
recalcule pas une seconde fois (mode de défaillance n° 4 : « la présentation
réimplémente la simulation »).

**Fidélité : sans objet.** Ce lot ne touche à aucun fichier de `sim/` et ne
produit aucun nombre nouveau ; il n'y a rien à qualifier de niveau 1, 2 ou 3
au-delà de ce que 051 a déjà qualifié niveau 2 par transitivité avec le lot
047.

### La lecture, en une phrase

`viewer/snapshot_loader.py::agregats_monde` gagne deux entrées, au même
niveau que `population`, `cellules_affamees` et `stock_nourriture_kg` :

```
kpis["habitants_du_bourg"]    = {"etat": "mesure", "valeur": <int>, "cellules_lues": <int>}
kpis["habitants_des_champs"]  = {"etat": "mesure", "valeur": <int>, "cellules_lues": <int>}
```

Chaque champ s'agrège séparément. `<valeur>` est la somme des entiers
mesurés du champ, et `cellules_lues` compte uniquement les cellules qui
ont contribué à cette somme. Un zéro est une mesure et compte ; une clé
absente, `bourg: null`, un sous-champ absent ou nul ne contribue pas ; la
sentinelle `-1` ne contribue pas non plus. En présence de mesures, l'état
est `"mesure"`. Sans mesure mais avec au moins une sentinelle pour ce
champ, l'état est `"non_calcule"`, sans `valeur`. Sans mesure ni
sentinelle, l'état est `"absent"`, sans `valeur`.

Cette lecture réutilise `viewer.classify.classify` ; elle ne convertit
jamais une absence en zéro. Un champ présent non entier, un booléen, un
entier négatif autre que la sentinelle, ou un `bourg` non nul qui n'est
pas un dictionnaire lève `ValueError` en nommant la cellule et le champ,
au lieu d'inventer une population par conversion. Les tests de documents
partiels appellent directement `agregats_monde` : `load_snapshot` garde
son refus des anciennes versions de schéma, il ne gagne pas de migration.

Les deux clés reprennent tels quels les champs de `RepartitionBourg`
(`sim/aggregation.py`) que 051 a déjà recopiés dans le document : aucun
second vocabulaire pour la même grandeur, dans le document comme dans le
tableau de bord.

### Le tableau de bord statique

`viewer/static/index.html` gagne deux cartes dans `#kpis`, sur le modèle des
sept déjà présentes : `id="kpi-bourg"` (libellé « Habitants du bourg ») et
`id="kpi-champs"` (libellé « Habitants des champs »). `viewer/static/app.js`
gagne, dans `showKpis()`, les deux appels correspondants :

```
remplirKpi("kpi-bourg", monde.habitants_du_bourg);
remplirKpi("kpi-champs", monde.habitants_des_champs);
```

`#kpis` est déjà une grille `auto-fit` (`viewer/static/style.css`, règle
`#kpis`) : deux cartes de plus s'y rangent sans qu'aucune règle CSS ne
bouge.

### Ce qui se refuse plutôt que se devine

- aucune seconde formule : ce module ne importe ni n'appelle
  `bourg_depuis_monde`, `RepartitionBourg`, ni aucun symbole de
  `sim.aggregation` — il lit le champ `bourg` du document déjà produit,
  exactement comme il lit déjà `population` ;
- aucun seuil, aucun drapeau « ceci est une ville » : le bandeau affiche
  deux nombres, il ne les interprète pas — la même retenue que 051
  documente pour le document lui-même ;
- aucune nouvelle couche sélectionnable sur la carte (le menu déroulant
  `#layer`, `proposed_layers`) : ce lot touche le bandeau de totaux, pas le
  système de couches par cellule — une carte colorée par bourg, si elle
  vient un jour, est un lot distinct, jugeable et livrable séparément.

### Où ça s'arrête

`viewer/snapshot_loader.py::proposed_layers`, `_valeur_couche` et
`agregats_couche` ne sont pas touchés : la couche par cellule n'est pas ce
lot. `viewer/server.py`, `viewer/classify.py`, `viewer/svg_proof.py` ne
changent pas : ils ne savent déjà rien du contenu d'un champ, seulement de
son état (absent / non calculé / zéro / valeur), et cet état ne change pas
de nature avec ce lot.

## Périmètre

En écriture : `viewer/snapshot_loader.py` (les deux entrées de
`agregats_monde`), `viewer/static/index.html` (les deux cartes de `#kpis`),
`viewer/static/app.js` (les deux appels dans `showKpis()`), et
`viewer/tests/test_viewer_v0b.py` pour y **ajouter** des cas — c'est le
fichier qui porte déjà les invariants du bandeau
(`test_agregats_monde_derivent_du_snapshot`, `test_absence_declaree_pas_inventee`,
`test_zero_mesure_n_est_pas_absent_dans_les_agregats`,
`test_dashboard_html_porte_les_kpis`). Aucun test déjà vert n'est modifié ;
un **nouveau** cas vérifie `"kpi-bourg"` et `"kpi-champs"`, sans étendre
le test existant. Les nouveaux cas portent `bourg` dans leur nom.

Tout autre chemin est interdit, nommément : tout `sim/` (y compris
`sim/MODELE.md`, `sim/aggregation.py`, `sim/snapshot_export.py`,
`sim/constants.py`), `viewer/server.py`, `viewer/classify.py`,
`viewer/svg_proof.py`, `viewer/static/style.css`, `viewer/README.md`,
`viewer/__main__.py`, la carte figée, `data/`, `ROADMAP.md` (au-delà de la
fiche 052, tenue par l'outillage), et les briefs 044, 046, 047, 051 et
celui-ci.

## Conditions de succès

Les comparaisons « avant / après » se font contre `master` rejoué (avec le
lot 051 déjà fusionné) au démarrage du lot, jamais contre un nombre recopié
d'ici.

### SC1 — Le bandeau porte le bourg, recalculé depuis le document, jamais stocké

Commande : `python3 -m pytest viewer/tests/test_viewer_v0b.py -k bourg -q`.

Sur le monde réel (`World.charger(0)`, `build_snapshot_document`),
`agregats_monde(document)["habitants_du_bourg"]["valeur"]` est égal à la
somme, sur toutes les cellules du document, de
`cell["bourg"]["habitants_du_bourg"]` ; `["cellules_lues"]` égale le nombre
de cellules qui portent le champ `bourg`. Même contrôle pour
`habitants_des_champs`. Le dénominateur (`cellules_lues`) est dérivé du
document ; un échantillon vide (aucune cellule ne porte `bourg`) rend l'état
`"absent"`, jamais une somme à zéro.

**Rouge prouvé d'abord** : sur `master` (051 fusionné, 052 pas encore),
`agregats_monde(document)["habitants_du_bourg"]` lève `KeyError`.

### SC2 — La conservation tient au niveau du bandeau

Commande : `python3 -m pytest viewer/tests/test_viewer_v0b.py -k bourg -q`.

Sur le monde réel, avec les trois agrégats à l'état `"mesure"` :
`kpis["habitants_du_bourg"]["valeur"] + kpis["habitants_des_champs"]["valeur"]
== kpis["population"]["valeur"]`, à l'entier près, et
`kpis["habitants_du_bourg"]["cellules_lues"] ==
kpis["habitants_des_champs"]["cellules_lues"] ==
kpis["population"]["cellules_lues"]`. C'est le contrôle transversal que
seul le bandeau peut faire : SC3 de 051 le prouve déjà par cellule, celui-ci
le reprouve après la somme.

### SC3 — Absence déclarée, jamais inventée

Sur un document construit à la main dont aucune cellule ne porte `bourg`
(le cas que `test_absence_declaree_pas_inventee` couvre déjà pour
`kg_transportes` et `stock_nourriture_kg`), `agregats_monde(document)`
rend `{"etat": "absent"}` pour `habitants_du_bourg` et
`habitants_des_champs`, sans clé `valeur`.

Commande : `python3 -m pytest viewer/tests/test_viewer_v0b.py -k bourg -q`.
Ajouter aussi les cas zéro mesuré, sentinelles seules, sous-champ absent,
valeurs nulles et mélange de mesures, absences et sentinelles. Dériver
chaque somme et son dénominateur des contributeurs réellement présents,
pour chacun des deux champs. Un document sans cellules continue de lever
`EchantillonVide`. Les valeurs invalides définies dans la règle lèvent
`ValueError` avec la cellule et le champ, jamais une somme plausible.

### SC4 — Le tableau de bord statique porte les deux nouvelles cartes

Un nouveau test vérifie que `"kpi-bourg"` et `"kpi-champs"` sont présents
dans `viewer/static/index.html`. `test_dashboard_html_porte_les_kpis`
reste inchangé. Un contrôle de code source vérifie en outre que
`viewer/static/app.js` référence `monde.habitants_du_bourg` et
`monde.habitants_des_champs` dans `showKpis()` — la carte existe et le
bandeau la remplit, pas seulement l'une des deux.

**Rouge prouvé d'abord** : sur `master`, ni `"kpi-bourg"` ni
`"kpi-champs"` n'apparaissent dans `index.html`.

Commandes : `python3 -m pytest viewer/tests/test_viewer_v0b.py -k bourg -q`,
puis `python3 -m viewer --snapshot /tmp/monde.json` avec un snapshot réel
produit après 051. Inspecter soi-même les captures à largeur de bureau et
sur mobile : libellés complets, cartes sans chevauchement, chiffres égaux
à `/dashboard.json`, zéro visible et absence distincte. Un contrôle de
présence dans le HTML ne remplace pas cette vérification visuelle. Le
document d'entrée reste identique après la lecture.

### SC5 — Une seule voie de lecture de la part non agricole

Commande : `python3 -m pytest viewer/tests/test_viewer_v0b.py -k bourg -q`.

Un contrôle parcourt le code source de `viewer/snapshot_loader.py` et de
`viewer/static/app.js`, et échoue si l'un des deux référence
`bourg_depuis_monde`, `RepartitionBourg`, `part_miniere_de`, ou importe
`sim.aggregation`. La seule façon d'obtenir la donnée est de lire le champ
`bourg` déjà présent sur chaque cellule du document.

**Rouge prouvé** en insérant temporairement un appel à
`bourg_depuis_monde` dans une copie de `viewer/snapshot_loader.py` :
le contrôle doit rougir dessus, sinon il ne protège rien.

### SC6 — Rien d'autre ne change dans le bandeau

Commande : `python3 -m pytest viewer/tests/test_viewer_v0b.py -k bourg -q`.

`agregats_monde(document)`, calculé sur le même monde avant et après ce
lot, rend des valeurs strictement identiques pour toutes les clés
existantes (`tick`, `jour_de_tick`, `population`, `cellules`,
`cellules_affamees`, `stock_nourriture_kg`, `kg_transportes`, `seed`) ; seule
l'apparition de `habitants_du_bourg` et `habitants_des_champs` distingue les
deux documents. `py -m sim --ticks 365 --seed 0 --json` rend par ailleurs
une sortie identique octet pour octet à celle de `master` : cette commande
ne passe jamais par `viewer/`.

### SC7 — Les invariants existants restent intacts, et la suite reste verte

```bash
py -m pytest sim/tests/ viewer/tests/ -q
```

- vert, et la liste des tests en échec est **vide**, comparée à celle de
  `master` plutôt que supposée ;
- tous les contrôles déjà présents dans `viewer/tests/test_viewer_v0b.py`
  restent verts **sans modification**, y compris
  `test_agregats_monde_derivent_du_snapshot`,
  `test_zero_mesure_n_est_pas_absent_dans_les_agregats`,
  `test_agregats_melangent_mesure_sentinelle_et_absence` et
  `test_couches_derivees_du_document` (ce dernier reste vert précisément
  parce que ce lot ne touche pas `proposed_layers`) ;
- le nombre de tests collectés est au moins celui de `master`.

## Hors périmètre

- la carte colorée par bourg, une nouvelle couche sélectionnable dans
  `#layer` / `proposed_layers` / `agregats_couche` : une extension possible,
  mais un lot distinct, jugeable séparément ;
- tout mécanisme, tout nouveau nombre de monde : ce lot ne lit que ce que
  051 a déjà exporté ;
- un seuil, un drapeau, une classification « ceci est une ville » dans le
  tableau de bord ;
- la preuve SVG (`viewer/svg_proof.py`), le serveur (`viewer/server.py`),
  la classification des états (`viewer/classify.py`) : aucun ne change de
  comportement, le bourg suit le même contrat `absent / non_calculé / zéro /
  valeur` que tout autre champ du bandeau ;
- `viewer/README.md` : sa description du tableau de bord (« bandeau de
  totaux lus du snapshot ») reste vraie sans modification, ce lot ajoute
  deux totaux au bandeau qu'elle décrit déjà ;
- `sim/MODELE.md` : aucune règle nouvelle n'est écrite, il n'y a rien à y
  documenter ;
- toute correction du message d'aide périmé de `--snapshot-json` dans
  `sim/__main__.py` : dette antérieure, hors de ce lot comme elle l'était
  hors de celui de 051.
