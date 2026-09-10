# sim/

Moteur de simulation ForgeHistory — **le produit vivant**. Il tourne
seul, sans moteur de rendu :

```
py -m sim
py -m sim --ticks 0 --json
py -m sim --ticks 0 --seed 0 --snapshot-json /tmp/world.json
```

`--snapshot-json` écrit une photographie cellulaire déterministe (schéma
`SNAPSHOT_SCHEMA_VERSION`) : géométrie, état simulé, province dérivée,
climat. Ce n'est pas une seconde simulation. Le snapshot déclare lui-même,
couche par couche, ce que le moteur consomme et ce qu'il ne consomme pas.

Le nom du schéma n'est pas recopié ici : il est dans `sim/constants.py`.
Un document qui porte une version morte piège le lot suivant (règle 12).

La vision du moteur est dans [`VISION.md`](../VISION.md), les règles dans
[`AGENTS.md`](../AGENTS.md), et le fonctionnement du monde — formules,
constantes, limites — dans [`MODELE.md`](MODELE.md).

---

## Modules

| Fichier | Rôle |
|---|---|
| `sim/__init__.py` | Paquet Python, expose `__version__` |
| `sim/constants.py` | Constantes paramétriques nommées (voir `sim/MODELE.md`) |
| `sim/model.py` | Dataclass `Cell` — entité géographique de base |
| `sim/world.py` | `World` — chargement depuis les artefacts G3, sérialisation |
| `sim/engine.py` | `tick(world, rng)` — avance le monde d'un pas de temps (production + consommation + commerce + faim + mortalité) |
| `sim/aggregation.py` | Agrégation dérivée : regroupe les cellules par centre administratif le plus proche. Ne modifie rien, n'écrit rien |
| `sim/__main__.py` | `py -m sim` — lance le monde |
| `sim/snapshot_export.py` | Photographie cellulaire déterministe (`--snapshot-json`) |
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
