# sim/

Moteur de simulation ForgeHistory — **le produit vivant**. Il tourne
seul, sans moteur de rendu :

```
py -m sim
py -m sim --ticks 0 --json
py -m sim --ticks 0 --seed 0 --snapshot-json /tmp/world.json
python3 -m sim --ticks 4 --seed 0 --gestes gestes.json --monde-json monde.json
py -m sim.service --seed 0 --port 8000 --jours-par-seconde 1
```

Le service avance par défaut d'un jour par seconde. L'option
`--jours-par-seconde` choisit cette cadence (`0` le met en pause). À chaud,
`POST /vitesse?jours_par_seconde=X` change la vitesse et `GET /horloge` rend
le tick, la date, la vitesse, la durée du dernier tick et son budget. Les vues
`GET /monde`, `GET /lieu?cell=...` et `GET /plan?cell=...` restent lisibles
pendant qu'un tick est calculé. Le plan du bourg porte ses rues, parcelles et
bâtiments en mètres locaux ; il part vide, puis ses chantiers prennent des bras aux champs.

`python3 -m sim.service --ia` fait jouer les maisons avant chaque tick, sous le
même verrou que le joueur. `GET /ia` rend le tick, la date, le relevé des dépôts
et `maisons_actives_30j` (−1 avant trente jours) ; sans option, il rend 404.
Un refus IA annule ses dépôts : le tick manuel rend 500, l'horloge se met en pause.
La durée publiée inclut l'IA ; les autres routes gardent leur forme.

`POST /intention` reçoit `{"type": "choisir_depart", "seigneurie": ID}`,
`{"type": "tracer_route", "cell": X, "points": [[0, 0], [40, 0]], "largeur_m": 4}`,
`{"type": "decouper_parcelle", "cell": X, "rue": 0, "segment": 0,
"debut_m": 5, "facade_m": 10, "profondeur_m": 20, "cote": "gauche"}`
ou `{"type": "poser_batiment", "cell": X, "parcelle": 0, "nature": "maison"}`.
Le dépôt validé reste en attente jusqu’au tick suivant : le choix devient
la maison du joueur, la route, la parcelle ou le bâtiment entre au plan en chantier.
La parcelle borde une rue déjà au plan ; son contour est figé au dépôt.
Le bâtiment occupe le contour d'une parcelle déjà au plan, même en chantier ;
sa nature est maison, scierie ou four. Une parcelle déjà bâtie ou promise est
refusée. Le coût en journées est calculé à l'application ; le bâtiment prend
ses bras après les routes et les parcelles, une fois sa parcelle achevée au
début du tick. Achevé, il ne fait encore rien.
Routes et parcelles prennent ensuite des bras aux champs et comptent leurs
journées, les rues passant en premier. `foyers` vaut 1 par défaut. Le reçu accepté
est `{"acceptee": true, "appliquee_au_tick": T}`. Un type inconnu, un corps
ou un geste mal formés rendent 400 ; un second choix rend 409. Le reçu
refusé est `{"acceptee": false, "erreur": "<raison>"}`, sans effet sur le monde.
`--gestes` rejoue une liste `[{"tick": T, "intention": {…}}, …]` avant chaque
tick indiqué ; `--monde-json` écrit le monde final en JSON canonique.

`--snapshot-json` écrit une photographie cellulaire déterministe (schéma
`SNAPSHOT_SCHEMA_VERSION`) : géométrie, état simulé, province dérivée,
climat, puissance, maison tenante, densité, villes de 1400 et terre choisie.
Ce n'est pas une seconde simulation. Le snapshot déclare lui-même,
couche par couche, ce que le moteur consomme et ce qu'il ne consomme pas.

Le nom du schéma n'est pas recopié ici : il est dans `sim/constants.py`.
Un document qui porte une version morte piège le lot suivant (règle 12).

La vision du moteur est dans [`VISION.md`](../../docs/VISION.md), les règles dans
[`AGENTS.md`](../AGENTS.md), et le fonctionnement du monde — formules,
constantes, limites — dans [`MODELE.md`](MODELE.md).

---

## Modules

| Fichier | Rôle |
|---|---|
| `sim/__init__.py` | Paquet Python, expose `__version__` |
| `sim/constants.py` | Constantes paramétriques nommées (voir `sim/MODELE.md`) |
| `sim/model.py` | Dataclass `Cell` — entité géographique de base |
| `sim/foyers.py` | Foyers par métier : rangement réversible et répartition entière des habitants |
| `sim/plan.py` | Plan du bourg : rues, parcelles et bâtiments validés, sérialisation triée |
| `sim/chantiers.py` | Journées de route, parcelle et bâtiment, passage des paysans aux ouvriers puis retour aux champs |
| `sim/intentions.py` | Dépôt commun des choix de départ, routes, parcelles et bâtiments, en attente du tick |
| `sim/world.py` | `World` — chargement depuis les artefacts G3, sérialisation |
| `sim/engine.py` | `tick(world, rng)` — avance le monde d'un pas de temps (production + consommation + commerce + faim + mortalité) |
| `sim/aggregation.py` | Agrégation dérivée : regroupe les cellules par centre administratif le plus proche. Ne modifie rien, n'écrit rien |
| `sim/__main__.py` | `py -m sim` — lance le monde |
| `sim/snapshot_export.py` | Photographie cellulaire déterministe (`--snapshot-json`) |
| `sim/service.py` | Service JSON local du monde courant (`127.0.0.1` uniquement) |
| `sim/MODELE.md` | Comment le monde fonctionne : formules, constantes, limites |

---

## Source des données d'entrée

Les artefacts G3 sont générés par le pipeline géographique :

- `data/world-1400.json` — la carte figée : cellules (cell_id, area_km2, centroid,
  geometry, relief, climat, gisements) et adjacence, dans un seul fichier

`sim/aggregation.py` lit deux sources supplémentaires, toujours en lecture
seule :

- `data/world-1400.json` — la position géographique de chaque
  cellule (`centroid.lat`, `centroid.lon`, repère WGS84) ;
- `data/province-centres-1400.json` — les centres
  administratifs hérités du jeu (tableau `coordinates` : `id`, `name`, `lon`,
  `lat`) et le paramètre de projection `projection.mid_latitude`.

Ces centres sont un proxy hérité, pas des frontières historiques : leur
provenance et les limites de ce qu'ils prouvent sont décrites dans
`sim/MODELE.md`, section « La province dérivée et ses centres ».

Le nombre exact de cellules et d'arêtes n'est recopié nulle part : il se lit
dans `data/world-1400.json` et se dérive du chargement. La commande qui le
donne est `py -m sim --ticks 0 --json`.

Ces fichiers sont suivis par git et lisibles depuis un clone frais.

---

## Lancer les tests

```
py -m pytest sim/tests/ -v
```

Depuis la racine du dépôt. La suite attend tous les tests PASSED,
exit code 0. Les fichiers `proof_red/*.txt` ne font pas partie de la
suite de tests (artefacts de preuve, non collectés par pytest).

---

## Règles architecturales importantes

- **Une seule clé spatiale** : `cell_id`. `Province` est une agrégation
  dérivée — jamais un champ stocké. `sim/aggregation.py` met cette règle en
  œuvre : la vue dérivée `Regroupement` y est déclarée, hors de `sim.model`,
  et le déplacement d'un centre administratif recalcule l'appartenance sans
  réécrire aucune cellule.
- **Commerce inter-cellules physique** : les arêtes d'adjacence (leur
  nombre se lit dans `data/world-1400.json`, jamais recopié ici) sont lues
  par `_apply_commerce` à chaque tick. Transfert borné par la capacité de
  l'arête. Conservation stricte de la masse.
- **Population agrégée** : pas encore de familles ou de personnes individuelles.
- **stdlib uniquement** : le moteur n'a aucune dépendance tierce (pytest est
  réservé aux tests).
