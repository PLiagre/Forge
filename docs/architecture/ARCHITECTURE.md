# Architecture — la carte du code

Ce que le jeu doit devenir : [VISION.md](../VISION.md). Les règles du monde,
formule par formule : [jeu/sim/MODELE.md](../../jeu/sim/MODELE.md). Ce
fichier dit où vit quoi, qui dépend de qui, et ce que la simulation et Unity
se promettent.

## Les quatre morceaux

```
 jeu/data/           la carte figée de 1400 et les chiffres du jeu
     │ lus par
     ▼
 jeu/sim/            LE MONDE : une seule simulation, un tick = un jour
     │
     ├─ photographie (snapshot_export) ──▶ jeu/vues/   tableau, chronique, relief
     │                                     jeu/forge/  la commande de bout en bout
     │
     └─ service local (service.py, HTTP sur 127.0.0.1) ──▶ 3d/unity/  la carte,
                                                            l'interface, la ville
 pc/                 les lanceurs Windows : le service, puis le jeu
 atelier/            la chaîne d'agents ; elle ne connaît pas le jeu
```

Une vue lit ; elle ne décide jamais un nombre. Rien ne remonte d'Unity vers
le monde sinon des intentions, par le service.

## Le moteur : `jeu/sim/`

Bibliothèque standard seule. Par couches, du socle vers le haut ; un module
ne dépend que de couches plus basses, sauf les boucles dites plus bas.

| couche | modules | ce qu'ils font |
|---|---|---|
| le socle | `constants`, `projection`, `villes` | les constantes du moteur, la projection de la carte, les villes de 1400 ; ils ne dépendent de rien |
| le modèle | `model`, `foyers`, `plan`, `flux`, `modificateurs`, `lieux`, `aggregation` | ce qu'est une cellule, un lieu, un foyer, un plan de ville ; les flux d'un jour ; le registre des modificateurs ; les agrégations conservatives |
| l'Europe de 1400 | `puissances`, `maisons`, `seigneuries`, `capitales`, `places`, `noms`, `personnages`, `registre_maisons`, `maitres`, `jouables`, `pays_servis`, `villes_3d`, `pluie`, `fleuve` | qui tient quoi au premier jour, lu dans `jeu/data/` |
| les règles d'un jour | `engine`, avec `prelevement`, `greniers`, `ateliers`, `chantiers`, `batiments`, `routes_interieures`, `convois`, `departs`, `logement`, `portes`, `ville1400` | la fabrication, l'extraction, la récolte, le commerce, la faim, la mort, les naissances, la migration, les chantiers |
| le monde | `world` | l'état entier, construit depuis la carte, et sa sérialisation |
| les gestes | `intentions`, `jauges`, `evenements`, `pays` | ce que le joueur et l'IA déposent ; les jauges du pays ; les événements à choix |
| l'IA | `ia`, `programme_ia` | les décisions des autres maisons, par les mêmes intentions |
| les sorties | `snapshot_export`, `carte_servie`, `maisons_servies`, `service`, `__main__` | la photographie d'un tick, et le service local que lit Unity |

Ce qui pèse : `engine` (2 150 lignes, tout le jour), `service` (1 040),
`constants` (830, importé par 32 modules), `intentions` (675).

Les règles de dépendance qui tiennent aujourd'hui :

- `constants` n'importe aucun module du moteur ;
- rien n'importe `service` ni `__main__` : ce sont les deux entrées ;
- `engine` n'importe ni `ia`, ni `service`, ni `snapshot_export` : le monde
  tourne sans IA et sans personne qui le regarde ;
- l'IA ne touche le monde que par `intentions`.

Les boucles qui existent, à connaître avant de découper : `world` ↔ `engine`,
`engine` ↔ `departs`, `seigneuries` → `engine`, `intentions` ↔ `evenements`,
`ia` ↔ `programme_ia`. Deux lots du monde qui touchent `engine` se marchent
dessus : ils se font l'un après l'autre.

### Un jour (`engine.tick`)

1. les intentions déposées s'appliquent ;
2. les greniers perdent leur part, les chantiers avancent, les artisans
   s'affectent ;
3. les modificateurs du jour sont lus une fois ;
4. dans chaque cellule : la fabrication, l'extraction, la récolte ;
5. le commerce, par les routes et les chemins intérieurs ;
6. dans chaque cellule : la faim, la mort, les naissances ;
7. les famines posent leurs modificateurs, les gens migrent et partent ;
8. le compteur de jours avance.

Le service joue, avant le tick, le mois des jauges puis l'IA
(`ServeurMonde.jouer_un_tick`), et publie l'état après.

### Les données : `jeu/data/`

- **La carte et l'Europe de 1400** (`world-1400.json`, `puissances`,
  `seigneuries`, `capitales`, `villes`, `noms`, `personnages`,
  `province-centres`, `nil-cours`, `pluie-releves`, `reference-jalon2`) : des
  fichiers figés. Le hachage de `world-1400.json` entre dans chaque
  photographie, et les textes de `personnages-1400.json` dans des empreintes
  épinglées : on n'y change pas un octet sans recapturer ces empreintes.
- **Les chiffres du jeu** (`batiments.toml`, `modificateurs.toml`,
  `jauges.toml`, `evenements.toml`, `commerce.toml`) : lisibles et
  modifiables sans toucher au code. Le moteur et l'IA lisent les mêmes.

## Le contrat entre la simulation et Unity

Le service (`python3 -m sim.service`, ou `pc\jouer.py` qui le lance avec le
jeu) écoute sur `127.0.0.1`. Tout ce qu'Unity sait du monde vient de lui.

| route | sens | ce qu'elle rend ou reçoit | client Unity (`Forge.Pont`) |
|---|---|---|---|
| `GET /monde` | lit | le monde léger du tick : date, cellules, maison du joueur | `ClientMonde` |
| `GET /carte`, `GET /departs` | lit | la carte figée et les terres de départ | `ClientCarte`, `ClientDeparts` |
| `GET /lieu?cell=`, `GET /plan?cell=`, `GET /occupation?cell=` | lit | les lieux d'une cellule, le plan de sa ville, qui loge où | `ClientLieu`, `ClientPlan`, `ClientVieDuBourg` |
| `GET /maison?id=` | lit | une maison | `ClientMaison` |
| `GET /pays?maison=` | lit | le pays et ses jauges | `ClientPays` |
| `GET /maisons`, `GET /ia`, `GET /modificateurs` | lit | toutes les maisons, le relevé des décisions de l'IA, les modificateurs et leur détail | lus par les écrans de `Forge.Interface` (dossiers du pays et des voisins, infobulle) |
| `GET /jouables`, `GET /evenement` | lit | les pays jouables, chacun avec son pays, ses règnes, son siège, son suzerain et sa ville en 3D ; l'événement en attente | pas encore de client |
| `GET /horloge` | lit | la vitesse, la pause, la durée du dernier tick | `ClientHorloge` |
| `POST /intention` | écrit | un geste du joueur ; rend un reçu : accepté, ou refusé avec sa raison | `ClientIntention` |
| `POST /vitesse?jours_par_seconde=` | écrit | la vitesse de l'horloge ; 0 est la pause | `ClientHorloge` |
| `POST /tick?n=` | écrit | pousse des jours à la main (les épreuves, les captures) | — |
| `POST /epreuve/…` | écrit | un monde d'épreuve jetable ; seulement avec `--epreuve` | — |

Ce que les deux côtés se promettent :

- **Un état publié est la photographie d'un tick.** Tout ce qu'on lit d'un
  même état date du même jour ; une lecture ne consulte jamais le monde en
  train de changer. Les octets d'un lieu, d'un plan ou d'une occupation
  naissent à leur première lecture, à partir de documents copiés à la
  publication.
- **Un geste est une intention.** Unity ne change rien au monde : il dépose
  une intention et lit le reçu. Les types d'intention sont ceux de
  `intentions.py` (choisir son départ, fixer la part, ouvrir le grenier,
  tracer une route, découper une parcelle, poser un bâtiment, tracer une
  enceinte, dépenser une jauge, bâtir ou améliorer dans une province,
  répondre à un événement). L'IA dépose les mêmes.
- **Une absence se dit.** Une cellule sans ville, une maison sans pays, un
  service qui ne répond pas : la réponse le dit, et l'écran l'affiche ; le
  client ne devine rien.
- **Changer une réponse se fait des deux côtés, dans la même PR** : la forme
  servie, les réponses figées des tests du service
  (`jeu/sim/tests/test_monde.py`), le client du pont et ses tests EditMode.
  Le contrat de la ville a ses schémas dans `jeu/ville/Schemas/`.
- **`cell_id` est la seule clé spatiale** dans toutes les routes.

## Unity : `3d/unity/`

Un seul projet. Quatre assemblies, et le reste dans l'assembly par défaut :

```
 Forge.Interface  (Assets/Interface/)        les écrans de la carte : cabinet, barre du pays, dossiers
        │ dépend de
        ▼
 Forge.Pont       (Assets/ForgeLocal3D/Pont/) les clients du service, la carte dessinée, le panneau du
                                              lieu, le passage de la carte à la ville
 Forge.Interface.Tests, Forge.Pont.Tests      les tests EditMode
```

| dossier de `Assets/ForgeLocal3D/` | quoi |
|---|---|
| `Pont/` | ce qui lit le service et le montre ; aucune règle du monde |
| `Carte/` | la vue de la carte : parcours, survol, commandes du temps |
| `Desert/` | la ville du désert bâtie à la main : terrain, routes, parcelles, bâtiments, enceinte, caméra |
| `Editor/` | les constructeurs de scènes, le build (`Build.Nuit`), la capture (`Capture.Photographier`) et les épreuves jouées sans écran |
| `Editor/Captures/` | les scénarios de capture (`[ScenarioDeCapture("groupe", "nom")]`), joués par `-forgeScenario groupe`, et leurs aides (`GestesDeCapture`, `AttentesDeCapture`) |
| `Alpin/`, `Citadelle/` | les décors qui dorment |

`pc/` porte les lanceurs : `jouer.py` démarre le service puis le jeu, les
`epreuve_*.py` jouent une session Unity sans écran et la jugent contre un
service de référence.

## La chaîne : `atelier/`

Elle ne connaît pas le jeu : elle lit `atelier.toml`, GitHub et les fiches
des lots. Son chemin et ses rôles : [WORKFLOW.md](../WORKFLOW.md) ; ses
règles : [atelier/CLAUDE.md](../../atelier/CLAUDE.md).
