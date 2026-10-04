# Lot #238 — Le tableau montre la cellule découpée en lieux
Jalon : J3 · Machine : vps · Taille prévue : 280 lignes

## But
Quand on clique une cellule du tableau de bord (ou qu'on la nomme à la commande), on voit cette cellule découpée en lieux — le bourg d'abord, puis les lieux de rang 1, 2… — chacun avec sa surface, ses habitants et son panier, tels que la photographie les porte : c'est le premier morceau de l'écran du jalon 3 (CAP.md : « la cellule découpée en lieux »), sur lequel viendront ensuite le seigneur de chaque lieu et les flux.

## Règle du monde
Sans objet : c'est un lot de vue. Le monde ne change pas, et la vue ne décide aucun nombre (AGENTS.md, principe 1 ; CAP.md, « Une vue ne décide jamais un nombre »).

Ce que la vue lit, et d'où : depuis le lot #235, chaque cellule de la photographie (`build_snapshot_document`, `sim/snapshot_export.py`) porte `"lieux"`, une liste dans l'ordre des rangs dont chaque entrée a exactement `rang`, `surface_km2`, `population`, `stocks` (kilogrammes par marchandise ; `jeu/sim/MODELE.md`, « Les lieux d'une cellule, vue dérivée », sous-section « Ce que porte un lieu », et « Le panier de marchandises »). Le rang 0 est le bourg. Les valeurs des lieux n'y sont **pas arrondies** (elles gardent la précision de la conservation) : la vue les montre telles quelles.

Trois interdits, qui font la preuve du lot :
- **aucun calcul** : la vue ne somme pas les lieux, ne divise pas la cellule par son nombre de lieux, ne recalcule pas le découpage (`sim.lieux`, `lieux_de_cellule`, `partager` ne sont pas importés) et ne relit pas le monde (`sim.world`, `sim.engine`) ; elle n'affiche aucun total de la cellule dans le dessin des lieux ;
- **absence déclarée** : une cellule dont la photographie ne porte pas `"lieux"` (clé absente, ou liste vide) se dessine avec la mention « lieux absents de la photographie » et aucun lieu — jamais des lieux devinés à partir de la cellule ;
- **refus de l'illisible** : des rangs qui ne valent pas exactement `0 … n − 1` dans l'ordre, une population qui n'est pas un entier ≥ 0 (un booléen n'est pas un entier), un `stocks` qui n'est pas un objet, un stock qui n'est pas un nombre fini ≥ 0, une `surface_km2` qui n'est pas un nombre fini > 0 sont refusés par `LieuxIllisibles(ValueError)`, dont le message nomme le `cell_id`. Un stock à `0` est un **zéro mesuré** et se dessine « 0 kg ».

### Ce que le codeur écrit

**1. `jeu/vues/tableau/cellule.py`** — nouveau module, bibliothèque standard seule :
- `LieuxIllisibles(ValueError)` ;
- `cellule_du_document(document, cell_id) -> dict` : la cellule dont `int(cell["cell_id"]) == cell_id` ; absente → `KeyError` dont le message contient le `cell_id` ;
- `lire_lieux(cellule) -> list | None` : `None` si `"lieux"` est absente ou vide ; sinon la liste, **validée** comme dit plus haut, rendue sans aucune transformation ;
- `formater(valeur) -> str` : la seule mise en forme du module (séparateur de milliers, deux décimales au plus) ; elle change l'écriture, jamais la valeur ;
- `render_cellule_svg(document, cell_id) -> str` : un SVG déterministe et du XML valide (noms de marchandises échappés). En tête : « cellule {cell_id} — tick {tick} graine {seed} ». Puis une carte par lieu, en grille, dans l'ordre des rangs : un `<g id="lieu-{rang}" data-rang="…" data-population="…" data-surface-km2="…">` contenant le texte « rang {rang} », « bourg » pour le seul rang 0, « {formater(surface_km2)} km² », « {formater(population)} habitants », puis une ligne par marchandise du panier du lieu, triées par nom : `<text data-marchandise="{nom}" data-kg="…">{nom} : {formater(kg)} kg</text>`. Les attributs `data-*` portent la valeur **exacte** lue de la photographie, écrite par `json.dumps(valeur)`, de sorte que `json.loads` de l'attribut rende la même valeur au bit près. Le nombre de colonnes et la taille d'une carte sont des constantes d'affichage nommées en tête de module (pas des cibles) ; la hauteur d'une carte suit le nombre de marchandises. Une cellule sans lieux rend l'en-tête et le texte « lieux absents de la photographie », et aucun `lieu-…`.

**2. `jeu/vues/tableau/__main__.py`** — une option `--cellule CELL_ID` (entier) : avec `--proof-svg`, elle écrit `render_cellule_svg` au lieu de la carte. Cellule inconnue ou `LieuxIllisibles` → message `refus : …` sur la sortie d'erreur et code 2. `--cellule` avec `--compare` → refus, code 2 (jamais ignoré en silence). Sans `--cellule`, rien ne change.

**3. `jeu/vues/tableau/server.py`** — une route `GET /cellule/<entier>.svg`, traitée avant les fichiers statiques : `render_cellule_svg` sur le snapshot A (document lu une fois, gardé comme le tableau de bord), `Content-Type: image/svg+xml; charset=utf-8`. Cellule inconnue ou chemin non entier (`/cellule/abc.svg`) → 404 ; `LieuxIllisibles` → 409 avec le message. Les routes existantes ne changent pas.

**4. `jeu/vues/tableau/static/index.html`** — dans la section `id="panel"`, après `id="details"`, un bloc `<div id="lieux"></div>` sous un titre « Lieux ».

**5. `jeu/vues/tableau/static/app.js`** — une fonction `showLieux(cell)`, appelée là où une cellule est sélectionnée, qui met dans `#lieux` une image dont la source est `"cellule/" + cell.cell_id + ".svg"` (largeur bornée à celle du panneau). Le JavaScript **ne lit pas** les lieux lui-même : le dessin vient du serveur, donc d'un seul code, éprouvé en Python. `showDetails` saute la clé `lieux` comme elle saute `geometry` (le dessin la montre). Aucune URL `http://` ni `https://`.

**6. `jeu/vues/tableau/static/style.css`** — au besoin, quelques lignes pour `#lieux`.

**7. `jeu/vues/tableau/README.md`** — une section courte « La cellule découpée en lieux » : la commande `--cellule`, la route `/cellule/<id>.svg`, et « la vue lit les lieux de la photographie, elle n'en calcule aucun ».

**8. `jeu/vues/tableau/tests/test_viewer_v0b.py`** — les cas des conditions ci-dessous, **ajoutés à la fin** ; aucun test existant ne change.

Avant de rendre : produire le SVG de la cellule qui a le plus de lieux (`--cellule`) et le **regarder** (AGENTS.md § 4) : les 37 cartes lisibles, le bourg reconnaissable, aucun texte qui déborde.

## Périmètre
jeu/vues/tableau/cellule.py
jeu/vues/tableau/__main__.py
jeu/vues/tableau/server.py
jeu/vues/tableau/static/index.html
jeu/vues/tableau/static/app.js
jeu/vues/tableau/static/style.css
jeu/vues/tableau/README.md
jeu/vues/tableau/tests/test_viewer_v0b.py

## Conditions de succès
Toutes se jouent depuis `jeu/` par `python3 -m pytest vues/tableau/tests/test_viewer_v0b.py -q -s -k <nom>`. Chaque test imprime ses compteurs ; un échantillon vide échoue ; aucun `cell_id` n'est écrit en dur (les cellules se choisissent par leurs données : la plus découpée, une à un seul lieu). Le document éprouvé est `json.loads(serialize_snapshot(build_snapshot_document(World.charger(0), 0, 0)))` — la photographie telle qu'un fichier la rend. Le SVG se lit avec `xml.etree.ElementTree`.

**SC1 — le dessin montre chaque lieu, tel que la photographie le porte** (`-k lieux_lus`). Pour **chaque** cellule du document : les groupes `lieu-…` sont exactement `lieu-0 … lieu-{n−1}`, dans l'ordre, `n = len(cell["lieux"])` ; pour chacun, `json.loads` de `data-population`, `data-surface-km2` et de chaque `data-kg` égale la valeur du lieu (égalité exacte, `==`), et l'ensemble des `data-marchandise` égale les clés de son panier ; le texte « bourg » apparaît dans `lieu-0` et dans aucun autre groupe. Compteurs : `cellules_dessinées == len(document["cells"])`, `lieux_dessinés` égal au total des lieux du document et strictement supérieur au nombre de cellules ; au moins une cellule dessinée a un seul lieu et une en a plusieurs. Deux rendus de la même cellule sont identiques à l'octet. Contre-épreuve, dans le même test : sur une copie profonde, ajouter 1 à la population d'un lieu de rang ≥ 1 change son `data-population` (qui vaut la nouvelle valeur) et laisse tous les autres groupes `lieu-…` identiques.

**SC2 — la vue ne calcule aucun nombre** (`-k lieux_sans_calcul`). Sur une copie profonde, changer pour la cellule la plus découpée `population`, `stocks`, `area_km2`, `densite_hab_par_km2` et `bourg` sans toucher à ses `lieux` laisse `render_cellule_svg` identique à l'octet : le dessin ne lit que les lieux. Tout attribut `data-*` numérique du SVG vaut une valeur d'un lieu de cette cellule. Contrôle des sources, fonction du test : `cellule.py` et `static/app.js` ne contiennent aucun de `sum(`, `sim.lieux`, `lieux_de_cellule`, `partager`, `sim.world`, `sim.engine` ; `app.js` ne contient ni `.lieux`, ni `["lieux"]`, ni `lieux[` ; et `_controle_tableau_pas_seconde_formule_bourg` (existant) passe sur `cellule.py`. Contre-épreuves, dans le même test : un rendu factice écrit dans le test, qui affiche pour chaque lieu `cell["population"] // n`, échoue à la comparaison « cellule changée, dessin identique » ; le contrôle des sources appliqué à `source + "\nsum(x)\n"` lève.

**SC3 — l'absence se déclare, l'illisible se refuse** (`-k lieux_absents`). Une cellule sans clé `"lieux"`, puis une à `"lieux": []` : le SVG contient « lieux absents de la photographie » et aucun groupe `lieu-…`. `render_cellule_svg` lève `LieuxIllisibles`, dont le message contient le `cell_id`, pour chacun de ces lieux écrits dans une copie : rangs `[1, 2]` (pas de bourg), rangs `[0, 0]`, population `-3`, `True`, `"12"`, `stocks` en liste, un stock `-5.0`, une `surface_km2` à `0` ; compteur `refus_observés` égal à la longueur de la liste (> 0). Un `cell_id` absent du document lève `KeyError`. Contre-épreuve, dans le même test : un lieu de population `0` et de stock `0.0` passe, et se dessine « 0 habitants » et « 0 kg » (zéro mesuré, pas absent) — le refus ne vise que l'illisible.

**SC4 — la commande dessine la cellule** (`-k lieux_commande`). Sur un snapshot écrit par `export_snapshot` : `python3 -m vues.tableau --snapshot s.json --cellule <cid> --proof-svg c.svg` (cid de la cellule la plus découpée) rend 0, et `c.svg` égale à l'octet `render_cellule_svg(load_snapshot(s.json), cid)` encodé en UTF-8. Un `cid` absent du document → code 2, et la sortie d'erreur contient ce `cid` ; `--cellule` avec `--compare` → code 2. Contre-épreuve : la même commande sans `--cellule` écrit la carte (le fichier contient `id="cell-` et pas `id="lieu-0"`).

**SC5 — le tableau web montre les lieux de la cellule cliquée** (`-k lieux_serveur`). Avec `_ouvrir_serveur` (existant) sur le snapshot : `GET /cellule/<cid>.svg` rend 200, un type qui commence par `image/svg+xml`, et les octets de `render_cellule_svg` ; `GET /cellule/<cid absent>.svg` et `GET /cellule/abc.svg` rendent 404 ; sur un snapshot dont un lieu de cette cellule a une population négative, la même route rend 409. `index.html` contient `id="lieux"` à l'intérieur de la section `id="panel"` ; dans `app.js`, le corps de `showLieux` contient `"cellule/"`, et `showLieux(` est appelée dans le gestionnaire qui sélectionne une cellule. Contre-épreuve : sur un snapshot dont cette cellule n'a plus de clé `"lieux"`, la route rend 200 avec « lieux absents de la photographie » — le serveur ne devine rien.

**SC6 — rien d'existant ne s'assouplit.** `python3 -m pytest jeu -q`, depuis la racine, est vert. `git diff master --numstat -- jeu/vues/tableau/tests/test_viewer_v0b.py` rend 0 ligne retirée ; `git diff master --name-only` ne sort pas du périmètre. `test_sources_sans_pipeline_ni_url`, `test_bourg_une_seule_voie_lecture_tableau`, `test_dashboard_html_porte_les_kpis`, `test_serveur_refuse_la_traversee_de_chemin` et `test_svg_deterministe_et_legend` restent tels quels et verts. Contre-épreuve : une URL `https://` glissée dans `app.js` rend `test_sources_sans_pipeline_ni_url` rouge.

## Hors périmètre
- Le seigneur de chaque lieu, son suzerain, le prélèvement et les flux vers le siège : ni le monde ni la photographie ne les portent encore ; ils viendront au tableau avec les lots qui les créent.
- La forme, la position et les frontières des lieux sur la carte (niveau 3, pas simulées) : le dessin est une grille de cartes, pas une géographie.
- `jeu/sim/` entier : le moteur, la photographie (`snapshot_export.py`, `SNAPSHOT_SCHEMA_VERSION`) et `MODELE.md` ne changent pas.
- La carte (`svg_proof.py`), le bandeau, les couches et les agrégats du tableau de bord (`snapshot_loader.py`) ne changent pas ; aucun total par lieu dans le bandeau.
- La comparaison de deux photographies lieu par lieu.
- La chronique, le relief, le service `/lieu` et le panneau Unity : aucun ne montre les lieux dans ce lot.
- Une capture du tableau au journal : elle viendra avec la preuve du jalon 3.
