# sim/

Moteur de simulation ForgeHistory — **le produit vivant**. Il tourne
seul, sans moteur de rendu :

```
py -m sim
py -m sim --ticks 0 --json
py -m sim --ticks 0 --seed 0 --snapshot-json /tmp/world.json
python3 -m sim --ticks 10 --seed 0 --gestes sim/gestes-exemple.json --monde-json monde.json
py -m sim.service --seed 0 --port 8000 --jours-par-seconde 1
```

Le service avance par défaut d'un jour par seconde. L'option
`--jours-par-seconde` choisit cette cadence (`0` le met en pause). À chaud,
`POST /vitesse?jours_par_seconde=X` change la vitesse et `GET /horloge` rend
le tick, la date, la vitesse, la durée du dernier tick et son budget. Les vues
`GET /monde`, `GET /lieu?cell=...` et `GET /plan?cell=...` restent lisibles
pendant qu'un tick est calculé. Le plan du bourg porte ses rues, parcelles et
bâtiments en mètres locaux ; il part vide, puis ses chantiers prennent des bras aux champs.
`/plan` ajoute `chantiers_du_jour` uniquement si la cellule a des observations du dernier jour joué : liste triée rue/parcelle/bâtiment puis identifiant, avec `nature`, `identifiant`, `bras` (personnes affectées ce jour), `grain_paye_kg` (kilogrammes effectivement payés, sans arrondi), `motif_arret` (`null` si travail).
`/plan` ajoute `recolte_perdue_par_chantier` seulement si un coût est strictement positif : liste triée rue/parcelle/bâtiment puis identifiant, avec `nature`, `identifiant` et `recolte_perdue_kg` (kilogrammes, sans arrondi). Le champ est absent pour une autoconstruction, un chantier sans bras ou un coût nul. Le partage se fait par lieu, au prorata des bras pris ; la somme égale l'écart mesuré. Le relevé est figé avec le tick et la date et ne se recalcule pas à la lecture.
Un arrêt garde deux zéros et sa cause ; un achèvement garde son paiement ce jour puis disparaît. À l'ouverture ou sans observation, le champ est absent : aucun salaire nul n'est inventé. Le tick et la date sont ceux de fin de journée ; plusieurs ticks ne publient que le dernier. Les lectures servent des octets figés, sans recalcul du salaire.
`GET /maisons` liste toutes les maisons ; `GET /maison?id=X` sert leur siège,
leurs lieux, leur part, leur grenier et leurs flux sur trente jours (kilos et
personnes). Un identifiant inconnu reçoit 404 ; les absences sont déclarées.
`flux_30j.salaires_payes_kg` apparaît seulement si la maison a payé des salaires
de chantier dans la fenêtre : kilos réellement débités, sans arrondi. Son absence
signifie aucun paiement enregistré dans cette fenêtre depuis l'ouverture, sans
mesure des jours antérieurs au démarrage ; le champ disparaît à expiration.

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
`{"type": "tracer_enceinte", "cell": C, "points": [[x, y], …]}` suit les mêmes règles : refus « enceinte : contour qui se croise », « enceinte : place de 1400 non entourée », « enceinte déjà tracée », « enceinte déjà promise » ; assise `ASSISE_ENCEINTE_M` ; entrée au plan au tick suivant.
Les trois constructions exigent un bourg tenu par la maison déposante : sinon « ce lieu n'est pas à toi : <maître> ».
HTTP exige un départ appliqué et impose sa maison au JSON copié, même si le client en fournit une autre.
Avec `--gestes`, chaque construction exige `maison`, identifiant explicite du registre, même sans départ choisi ; l'exemple construit à Biskra pour `seigneurie-6`.
Le dépôt validé reste en attente jusqu’au tick suivant : le choix devient
la maison du joueur, la route, la parcelle ou le bâtiment entre au plan en chantier.
La parcelle borde une rue déjà au plan ; son contour est figé au dépôt.
Le bâtiment occupe le contour d'une parcelle déjà au plan, même en chantier ;
sa nature est maison, scierie ou four. Une parcelle déjà bâtie ou promise est
refusée. Le coût en journées est calculé à l'application ; le bâtiment prend
ses bras après les routes et les parcelles, une fois sa parcelle achevée au
début du tick. Achevés, scierie et four emploient les paysans restants comme artisans ; la maison loge des foyers d’artisans dans `/lieu`, sans effet sur le tick. Les artisans façonnent davantage de matière après les 5 % sans bras, avec un budget commun.
Routes et parcelles prennent ensuite des bras aux champs et comptent leurs
journées, les rues passant en premier. `foyers` vaut 1 par défaut. Le reçu accepté
est `{"acceptee": true, "appliquee_au_tick": T}`. Un type inconnu, un corps
ou un geste mal formés rendent 400 ; un second choix rend 409. Le reçu
refusé est `{"acceptee": false, "erreur": "<raison>"}`, sans effet sur le monde.
Les foyers d'artisans sans logis bâtissent aussi leurs maisons sur les parcelles libres achevées du bourg doté d'un maître : une ouverture par jour, places des maisons en chantier déjà réservées. L'autoconstruction prend un artisan par maison, sans salaire ni transfert de grain ; ces bras reviennent aux artisans le lendemain et restent indisponibles aux ateliers ce jour. Seules les maisons finies logent ; la pose manuelle reste salariée.
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
| `sim/logement.py` | Places des maisons finies, artisans logés et sans logis, dérivés sans effet sur le tick |
| `sim/foyers.py` | Foyers par métier : rangement réversible et répartition entière des habitants |
| `sim/plan.py` | Plan du bourg : rues, parcelles et bâtiments validés, sérialisation triée |
| `sim/routes_interieures.py` | Route achevée vers un lieu de la cellule : elle quadruple le chemin de ce lieu vers le bourg |
| `sim/ville1400.py` | Ville de 1400 dérivée des foyers du bourg : place, rues, ruelles, maisons individuelles jusqu'à 500 foyers puis îlots, sans effet sur le tick ; `/plan` sert la base |
| `sim/ateliers.py` | Emploi des artisans par surface des scieries et fours achevés, pris aux champs |
| `sim/chantiers.py` | Journées de route, parcelle et bâtiment payées en grain du grenier au bourg, paysans devenus ouvriers puis retour aux champs |
| `sim/intentions.py` | Dépôt commun des choix de départ, routes, parcelles, bâtiments, parts et `ouvrir_grenier` ; refuse un geste sur une maison de 1400 avant mise en attente du tick |
| `sim/world.py` | `World` — chargement depuis les artefacts G3, sérialisation |
| `sim/convois.py` | Route de chaque lieu jusqu'au grenier de son maître, calculée une fois au chargement |
| `sim/engine.py` | `tick(world, rng)` — avance le monde d'un pas de temps (production + consommation + commerce + faim + mortalité) |
| `sim/aggregation.py` | Agrégation dérivée : regroupe les cellules par centre administratif le plus proche. Ne modifie rien, n'écrit rien |
| `sim/__main__.py` | `py -m sim` — lance le monde |
| `sim/snapshot_export.py` | Photographie cellulaire déterministe (`--snapshot-json`) |
| `sim/service.py` | Service JSON local du monde courant (`127.0.0.1` uniquement) |
| `sim/maisons_servies.py` | Matière publiée et documents des maisons, dérivés sans modifier le monde |
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

`sim/prelevement.py` retire la part de la récolte, fait voyager les charges, livre les greniers et les secours aux lieux.

`sim/flux.py` observe trente jours de prélèvements, convois, secours et départs
par maison et par lieu. Ce registre reste hors de `to_dict` et des règles ;
ses lecteurs préparent les vues du jalon 3.
