# Lot #1075 — Le tick publié passe sous 100 ms avec l'IA
Jalon : J5 · Machine : pc · Taille prévue : 800 lignes

## But
Le service joue un jour du monde avec l'IA et le publie en moins de 100 ms sur le PC : le monde peut filer à 10 jours par seconde sans prendre de retard.

## Le joueur
Il lance la carte, laisse le monde vivre sans lui, et pousse le temps à 10 jours par seconde : le monde tient cette vitesse. Il voit passer un mois en trois secondes, sans à-coups, et la date affichée dit vrai.

Aujourd'hui, ce n'est pas le cas. Le tick et l'IA coûtent environ 50 ms sur le PC, mais la publication d'un jour en coûte plus du double : elle refait à chaque jour 2,5 Mo d'octets que personne ne lit. Le jour complet passe alors largement au-dessus du budget de 100 ms : à 10 jours par seconde, le service prend du retard et la vitesse affichée ment.

C'est un lot de fond. Il prépare le geste du jalon 5 : « il met en pause, choisit l'une des cinq vitesses et laisse filer les années ». Le lot #1030 (« Le jeu se lance en observateur, avec la pause et cinq vitesses ») le rend visible : sa vitesse la plus rapide vaut 10 jours par seconde, et sa session exige au moins 40 jours en 5 secondes. Il a été découpé pour ce lot : le tick qu'il croyait à 67 ms ne comptait pas la publication.

## Règle du monde
Sans objet : c'est un lot du service, sans règle du monde. Un tick reste un jour (`jeu/sim/MODELE.md`, « La base de temps »). Aucune donnée du monde ne change, aucune empreinte épinglée ne se recapture : le monde et chaque octet publié restent ceux de master.

Le lot récrit seulement, dans `MODELE.md`, les phrases qui disent quand naissent les octets publiés. Elles sont dans « Les foyers par métier », « Les maisons servies, vue dérivée » et « Ce que porte un lieu ». Ce qui reste vrai : les documents sont copiés à la publication, dans le même appel à `_construire_etat`, sans relire le monde vivant à la requête. Ce qui change : leurs octets naissent à la première lecture. C'est ce que font déjà les fiches des maisons (`octets_maisons`).

### Ce qu'on a mesuré
Mesures faites sur le VPS le 13 novembre 2026, sur master e90f4ca2, graine 0, IA active, au 60ᵉ jour. Ce VPS est environ 2,8 fois plus lent que le PC sur le tick du monde : 127 ms contre ≈ 45 ms (`docs/mesures/2026-11-07-refonte/RAPPORT.md`, section 7).

| | VPS | PC estimé |
|---|---|---|
| `jouer_un_tick()` complet | 485 à 530 ms | ≈ 175 ms |
| dont tick et IA (`duree_dernier_tick_ms`) | 129 à 150 ms | ≈ 50 ms |
| dont la publication (`_construire_etat`) | ≈ 350 ms | ≈ 125 ms |

Ce que coûte la publication, poste par poste, au 60ᵉ jour sur le VPS :

| poste | ms | ce qu'on en sait |
|---|---|---|
| `document_des_modificateurs` | 94 | `detail` refait `_tenus` (1,6 ms) pour chacun des 22 lieux touchés ; une seule fois suffit (prototype : **3 à 8 ms**, octets identiques) |
| sérialiser les 596 lieux | 70 | 2,5 Mo par jour ; aucun lieu n'est le même d'un jour à l'autre (0 sur 596, hors `tick` et `date`) ; Unity n'en lit qu'un ou deux |
| `flux_des_lieux` | 66 | 30 jours × 2 289 lieux routés |
| `matiere_des_maisons` | 42 | 30 jours × 5 vecteurs × 2 289 ; sommée par colonne : **26 ms**, octets identiques |
| `lieux_en_photographie` × 596 | 28 | |
| `lieux_avec_bourg` | 5 | recopie les 2,5 Mo des lieux |
| plans et occupations | ≈ 5 | 596 plans sur 596 inchangés, 596 occupations sur 596 aussi |
| le reste (monde, cellules, noms, chantiers) | ≈ 40 | |

Le ramasse-miettes de Python coûte en plus **91 ms par tick** (330 passes). Il en coûte 45 après un `gc.freeze()` du monde chargé.

Un piège trouvé en prototype : `sum()` de Python 3.12 compense ses arrondis sur les flottants, et ne rend pas les mêmes octets que la boucle `total += kilos` d'aujourd'hui. `math.fsum` non plus. Seules des additions dans le même ordre, à partir du même 0 entier, gardent les octets : `functools.reduce(operator.add, colonne, 0)`, ou une boucle.

## Périmètre
jeu/sim/service.py
jeu/sim/modificateurs.py
jeu/sim/maisons_servies.py
jeu/sim/flux.py
jeu/sim/MODELE.md
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_modificateurs.py
docs/mesures/1075-tick-publie/mesure_tick_publie.py
docs/mesures/1075-tick-publie/RAPPORT.md
docs/mesures/1075-tick-publie/master.json
docs/mesures/1075-tick-publie/branche.json
docs/briefs/1075-le-tick-publie-passe-sous-100-ms-avec-l-ia.md

Tout autre chemin est interdit, en particulier tout Unity (`3d/`), `pc/`, `jeu/sim/engine.py`, `jeu/sim/ia.py`, `jeu/sim/snapshot_export.py` et `jeu/sim/constants.py`. `BUDGET_TICK_MS` reste à 100.

### Ce que les tests existants figent, et que le code doit tenir
Aucun de ces tests ne change. Ils disent ce que le code a le droit de faire :
- **`flux_des_lieux` est appelé exactement une fois par `_construire_etat`** (`test_flux_des_lieux_publication_et_passe_unique`). Les flux des lieux se calculent donc à la publication, pas à la lecture.
- **`matiere_des_maisons` est appelée à chaque publication**, et sa matière est détachée du monde. Après le tick, `test_publication_figee_et_cache_a_la_demande` modifie un grenier, une part et le dernier jour des flux ; la fiche lue ensuite doit être celle d'avant. Aucun cache d'un tick à l'autre ne peut donc garder des sommes de jours.
- **`jouer_un_tick` appelle `time.perf_counter` deux fois, pas plus** : le test de `duree_dernier_tick_ms` (`instants = iter([0, .2, .5])`) le fige. `duree_dernier_tick_ms` garde son sens : le tick et l'IA, sans la publication.
- **Le tri des chantiers reste dans `_construire_etat`, exécuté à chaque appel**, avec le littéral `natures = ("rue", "parcelle", "batiment", "enceinte")` dans son source. `test_enceinte_plan_servi` exécute ce source sans `"enceinte"` dans l'espace de noms du module et exige un `ValueError` à l'appel. Tout nom que `_construire_etat` utilise est donc un nom du module `service`, ou un attribut de `self`.
- **Les octets publiés se lisent comme aujourd'hui** : `etat.lieux[cid]`, `.get`, `in`, `len`, l'itération, `.keys()`, `.values()`, `.items()`, et l'écriture `etat.lieux[cid] = octets`. Ce sont celles de `octets_plan`, qui complète un plan de sa base, et celles du test des flux, qui écrit un lieu forgé. `copy.deepcopy(etat)` doit marcher aussi (même test). Mêmes exigences pour `lieux_avec_bourg`, `plans` et `occupations`.
- **Les réponses figées** : `test_service_reponse_figee_du_pont_est_celle_du_service`, sa variante du tick 4, `test_service_reponse_figee_places_et_anciens_champs`, `…_maitres_et_anciens_champs`, `…_flux_et_origine` et `test_plan_vide_par_cellule_et_empreinte_sensible`. Elles gardent leurs fichiers et leurs hachages.

### Les leviers, dans cet ordre
Les quatre premiers sont obligatoires. Le 5 et le 6 ne se prennent que si la médiane du PC (SC1) dépasse encore 85 ms après les quatre premiers. Le rapport donne la médiane après chaque levier pris.

1. **Les octets des lieux, des plans et des occupations naissent à leur première lecture** (`service.py`).
   - Une classe du module, par exemple `OctetsDifferes`, est une `collections.abc.MutableMapping[int, bytes]`. Elle garde les documents de chaque cellule, construits à la publication comme aujourd'hui. À la première lecture d'une cellule, elle les sérialise par `_serialiser`, lu dans le module à l'appel, puis garde les octets. Une écriture remplace les octets.
   - Elle ne garde ni le serveur, ni une méthode liée, ni un verrou : `copy.deepcopy` recopierait le serveur, ou tomberait sur le verrou. Deux lecteurs du même lieu en même temps le sérialisent deux fois, avec les mêmes octets : c'est permis. Une lecture ne prend jamais `verrou_tick`.
   - **`lieux`** : les documents d'aujourd'hui (`documents_lieux`), sérialisés à la lecture.
   - **`lieux_avec_bourg`** : à la lecture, `b'{"bourg":' + _serialiser(bourg) + b"," + lieux[cid][1:]`. Le document du bourg (`_bourg_du_lieu`) est construit à la publication. Les octets du lieu sont repris de `lieux`, sérialisés s'ils ne l'étaient pas.
   - **`plans`** : le document de chaque plan (`to_dict()`, `portes`, `cell_id`, `rang`, `tick`, `date`, `chantiers_du_jour`, `recolte_perdue_par_chantier`) est construit à la publication. Son préfixe aussi : `self._bases.get(cid, b"{")`, lu sous `verrou_base` comme aujourd'hui. Les octets sont `préfixe + _serialiser(document)[1:]`, à la lecture. `octets_plan` ne change pas.
   - **`occupations`** : le document de chaque cellule (`batiments`, `logement`…) est construit à la publication, et sérialisé à la lecture.
   - `EtatPublie` déclare ces quatre champs en `Mapping[int, bytes]` au lieu de `dict[int, bytes]`. Les routes `/epreuve/…` et `_monter_ville_dense` republient par `_construire_etat` comme aujourd'hui.
2. **Les modificateurs lisent les maîtres une fois** (`modificateurs.py`). `detail(monde, cell_id, rang, tenus=None)` et `facteurs_du_monde(monde, tenus=None)` prennent les tenus en paramètre facultatif. Sans lui, elles les calculent comme aujourd'hui : l'infobulle et l'IA qui les appellent ne changent pas. `document_des_modificateurs` calcule `_tenus(monde)` au plus une fois, seulement si une pose vise un pays, et le passe aux deux. Le document reste le même, octet pour octet.
3. **La matière des maisons somme ses vecteurs par colonne** (`maisons_servies.py`). Les cinq vecteurs de la fenêtre sont sommés colonne par colonne : `zip_longest(*vecteurs, fillvalue=0)`, et `functools.reduce(operator.add, colonne, 0)` ou une boucle, dans l'ordre des jours de `_jours_de_fenetre`. Jamais `sum()` ni `math.fsum` (voir le piège plus haut). Salaires et personnes restent tels quels. `MatiereMaisons` ne change pas.
4. **Plus aucune copie d'octets inutile.** `lieux_avec_bourg` ne recopie plus les 2,5 Mo des lieux à chaque tick (levier 1). `/monde`, l'IA et les modificateurs restent sérialisés à la publication : ce sont les trois seuls documents sérialisés par un tick.
5. **`flux_des_lieux` plus rapide**, si besoin (`flux.py`). Il reste une passe, appelée une fois. Le résultat est le même, avec pour chaque lieu les mêmes additions dans le même ordre des jours. La photographie l'appelle aussi : ses empreintes gardent la même valeur.
6. **Le ramasse-miettes**, si besoin (`service.py`). Une fonction du module, `regler_le_ramasse_miettes()`, fait `gc.collect()` puis `gc.freeze()`. `main()` l'appelle juste après avoir construit le `ServeurMonde`, avant `serve_forever`. Jamais dans `ServeurMonde.__init__` : les tests construisent des centaines de serveurs, qui ne seraient plus jamais ramassés.

### `test_monde.py`
Les tests existants restent tels quels. Trois cas neufs :

- **`test_tick_publie_sous_le_budget_avec_l_ia`**, marqué `chronometre`, posé à côté de `test_tick_sous_le_budget_du_service`.
  - Hors Windows, il saute par `pytest.skip("mesure du PC : le tick publié se juge sur la machine du joueur")`. Il se joue quand `sys.platform == "win32"`. Les runners de la CI sont deux à trois fois plus lents que le PC, et jugeraient leur machine, pas le service.
  - Il construit `ServeurMonde(("127.0.0.1", 0), 0, 0, ia=True)` (graine 0, horloge à l'arrêt). Si le levier 6 est pris, il appelle `service.regler_le_ramasse_miettes()` comme `main()`, et `gc.unfreeze()` à la fin.
  - Il joue 30 ticks de chauffe par `jouer_un_tick()`, puis en chronomètre 60 un à un, par `time.perf_counter()` autour de l'appel entier : IA, tick et publication.
  - Il imprime la médiane et le maximum du tick entier, la médiane de `duree_dernier_tick_ms` et l'écart entre les deux médianes (la publication). Il exige 60 mesures et `médiane < BUDGET_TICK_MS`, importé de `sim.service`.
  - Contre-épreuves dans le même test, sur un serveur neuf, 5 ticks de chauffe et 10 mesurés. `ServeurMonde._construire_etat` ralenti de `BUDGET_TICK_MS / 1000` s fait lever `AssertionError` : la publication est dans la mesure. `service.jouer_ia` ralenti de même la fait lever aussi : l'IA y est.
- **`test_publication_differee_lit_le_tick_publie`** : ce test n'est pas `chronometre`, la CI le joue.
  - Deux serveurs identiques, graine 0, IA active, vitesse 0 : `tot` et `tard`. `_preparer_occupation_service(serveur)` pose sur les deux le même plan à maisons.
  - Une fonction `tout_lire(serveur, etat)` lit tous les octets d'un état publié : `monde`, `ia` et `modificateurs` ; `lieux[cid]` et `lieux_avec_bourg[cid]` de chaque cellule ; `serveur.octets_plan(etat, cid)` et `serveur.octets_occupation(etat, cid)` de chaque cellule ; `serveur.octets_de_maison(etat)` et `serveur.octets_de_maison(etat, m.id)` de chaque maison du registre.
  - Pendant 35 ticks, `tot` lit chaque état juste après son tick. `tard` garde l'état du jour k, joue le jour k + 1, puis lit l'état du jour k. Les deux lectures du jour k sont égales, octet pour octet.
  - Au dernier jour, avant de lire, `tard` modifie son monde en place : un habitant de plus dans un lieu, `plan.batiments.pop()` sur le plan posé, 1 000 kg dans un grenier, +1 au `preleve` du dernier jour des flux. Sa lecture reste celle de `tot`.
  - Échantillon non vide : au 35ᵉ jour, au moins une pose de modificateur, une maison achevée dans l'occupation du plan posé, et un relevé de l'IA non vide.
  - Contre-épreuve : `monkeypatch.setattr(service, "copier_panier", lambda entite: entite.stocks)`. Le bourg publié garde alors le panier vivant au lieu d'une copie. Sur 3 ticks, la lecture tardive de `lieux_avec_bourg` diffère et la comparaison lève `AssertionError`.
- **`test_un_tick_ne_serialise_que_le_monde_l_ia_et_les_modificateurs`** : la CI le joue.
  - Serveur IA, 3 ticks de chauffe ; `service._serialiser` compté par `monkeypatch`. Un `jouer_un_tick()` l'appelle au plus 3 fois, pour 596 cellules.
  - Sur l'état rendu, `etat.lieux[cid]` ajoute exactement un appel ; une seconde lecture du même lieu n'en ajoute aucun. Les octets lus sont égaux à `_serialiser(json.loads(octets))` : la forme canonique.
  - Contre-épreuve : `_construire_etat` enveloppé pour lire `list(etat.lieux.values())` avant de rendre. Le compte du tick passe alors 596, et le contrôle lève `AssertionError`.

### `test_modificateurs.py`
Un cas neuf, **`test_le_document_lit_les_maitres_une_fois`**. Le monde de `depart` reçoit une pose qui vise un pays, comme `test_prelevement_d_un_pays`, et une qui vise une cellule.
- `M._tenus` est compté par `monkeypatch`. `document_des_modificateurs(monde)` l'appelle au plus une fois.
- Son document est égal à celui qu'on rebâtit lieu par lieu avec `M.detail(monde, cid, rang)` sans tenus, les noms et mots compris (la façon d'avant).
- Contre-épreuve : un document qui appelle `detail` sans tenus pour chaque lieu fait passer le compte au-dessus de 1, et le contrôle lève `AssertionError`.

### `docs/mesures/1075-tick-publie/mesure_tick_publie.py`
- Un script lancé depuis la racine du dépôt : `--jeu <dossier jeu à importer>`, `--ticks N` (90 par défaut), `--sortie <json>`, `--alterer K` (facultatif), `--comparer A B`.
- Il ajoute le dossier `--jeu` en tête de `sys.path` et s'y place. Il construit `ServeurMonde(("127.0.0.1", 0), 0, 0, ia=True)` et joue N ticks par `jouer_un_tick()`.
- Il chronomètre chaque appel. Après la mesure, hors du chrono, il lit tous les octets de l'état rendu, comme `tout_lire` plus haut, par les seuls noms qui existent déjà sur master. Pour chaque jour, il écrit dans le JSON le temps du tick, `duree_dernier_tick_ms` et le SHA-256 de tous ces octets, joints dans un ordre fixé.
- Il écrit aussi la médiane et le maximum des ticks 30 à 89. Avec `--alterer K`, il ajoute un octet au `/monde` du jour K avant de hacher.
- `--comparer A B` sort 0 si les deux fichiers ont les mêmes jours, chacun avec la même empreinte. Sinon il sort 1 et nomme le premier jour qui diffère, ou manque.
- Le script ne lance jamais `regler_le_ramasse_miettes` : il mesure le tick tel que les tests le jouent. Le levier 6, s'il est pris, se mesure par SC1.

### `RAPPORT.md`
Il donne :
- la machine et les deux commits ;
- les médianes et maxima de master et de la branche, tick entier et `duree_dernier_tick_ms` ;
- la médiane de SC1 après chaque levier pris ;
- la sortie des deux `--comparer`.

## Conditions de succès
Sur le PC, en PowerShell, depuis la racine du chantier, éditeur Unity fermé et sans autre calcul en parallèle. La machine du VPS ou de la CI ne juge pas SC1 et SC2.

**SC1 — Le tick complet, avec l'IA et la publication, tient sous 100 ms sur le PC.** `cd jeu; py -m pytest sim/tests/test_monde.py -m chronometre -k tick_publie_sous_le_budget -q -s -rs` affiche `1 passed`, sans `skipped`. La médiane imprimée est sous 100 ms et va dans le rapport. Contre-épreuves, dans le test lui-même : une publication ralentie de 100 ms et une IA ralentie de 100 ms font chacune lever `AssertionError`. Le rouge d'abord : le même tick sur master, mesuré par SC2, a sa médiane au rapport ; on l'attend au-dessus de 100 ms (≈ 175 ms estimés).

**SC2 — Le monde publié reste celui de master, octet pour octet, jour après jour.** Depuis la racine du chantier :
```
git worktree add ../forge-1075-master origin/master
py docs/mesures/1075-tick-publie/mesure_tick_publie.py --jeu ../forge-1075-master/jeu --ticks 90 --sortie docs/mesures/1075-tick-publie/master.json
py docs/mesures/1075-tick-publie/mesure_tick_publie.py --jeu jeu --ticks 90 --sortie docs/mesures/1075-tick-publie/branche.json
py docs/mesures/1075-tick-publie/mesure_tick_publie.py --comparer docs/mesures/1075-tick-publie/master.json docs/mesures/1075-tick-publie/branche.json
```
La dernière commande sort 0 : les 90 empreintes sont égales. Contre-épreuve : `py docs/mesures/1075-tick-publie/mesure_tick_publie.py --jeu jeu --ticks 90 --alterer 20 --sortie ../forge-1075-altere.json`, puis `py docs/mesures/1075-tick-publie/mesure_tick_publie.py --comparer docs/mesures/1075-tick-publie/master.json ../forge-1075-altere.json`. La comparaison sort 1 et nomme le jour 20 (les jours 1 à 19 sont égaux). Le worktree se retire ensuite (`git worktree remove ../forge-1075-master`).

**SC3 — Les octets différés lisent le tick publié, jamais le monde d'après.** `cd jeu; py -m pytest sim/tests/test_monde.py -q -k "publication_differee_lit_le_tick_publie or ne_serialise_que_le_monde"` passe, deux cas, avec leurs contre-épreuves (le panier vivant, le tick qui sérialise tout). La CI les joue aussi sous Linux.

**SC4 — Les modificateurs lisent les maîtres une fois.** `cd jeu; py -m pytest sim/tests/test_modificateurs.py -q` passe en entier, `test_le_document_lit_les_maitres_une_fois` et sa contre-épreuve compris. Les empreintes du 365ᵉ jour gardent leur valeur.

**SC5 — Aucun test existant ne bouge, et tous passent.**
- `git diff origin/master -U0 -- jeu/sim/tests | Select-String '^-[^-]'` ne sort rien : on ajoute des lignes de test, on n'en retire ni n'en change aucune.
- `cd jeu; py -m pytest sim/tests/test_monde.py sim/tests/test_maisons_servies.py sim/tests/test_flux.py sim/tests/test_chantiers.py sim/tests/test_epreuve_enceinte.py sim/tests/test_modificateurs.py -q -n auto -m "not chronometre"` passe (`-n auto` demande `pytest-xdist`, comme la CI). On y trouve les réponses figées du pont, `test_enceinte_plan_servi`, `test_flux_des_lieux_publication_et_passe_unique` et `test_publication_figee_et_cache_a_la_demande`.
- `cd jeu; py -m pytest -m chronometre sim/tests/ -q` passe aussi sur le PC.
- La CI entière est verte : son travail `chronometre` saute le cas neuf, hors Windows, et joue tous les autres.

**SC6 — Rien d'autre ne bouge.** `git diff --name-only origin/master` ne liste que des chemins du Périmètre. `BUDGET_TICK_MS = 100` reste à sa ligne.

## Hors périmètre
- Les cinq vitesses, l'observateur et leur session Unity : c'est #1030, qui reprend après ce lot.
- Le coût du tick et de l'IA eux-mêmes (`engine.tick`, `jouer_ia`, `avant_le_tick`) : ce lot ne touche que la publication.
- Le sens de `duree_dernier_tick_ms` et de `/horloge`. Le service ne borne toujours pas la vitesse demandée.
- Le budget sur les runners de la CI : il n'est pas tenu là-bas, et ne l'est pas non plus pour le tick seul avec l'IA. La CI garde les deux comptes de SC3, qui ne dépendent pas de la machine.
- Le relevé de l'IA publié en entier (`/ia`), qui grandit avec les années : 0,2 ms au 60ᵉ jour, laissé tel quel.
- Toute bibliothèque hors de la bibliothèque standard dans `jeu/sim/` (pas de `numpy`).
- Unity, le pont et les routes HTTP : leurs réponses ne changent pas d'un octet.

## Photo
sans objet : le lot ne change rien de ce qu'on voit à l'écran. Chaque octet que Unity lit reste celui de master (SC2) ; seul le temps d'un jour change, et il se mesure par SC1. Le monde à 10 jours par seconde se voit dans la photo de #1030, qui reprend après ce lot.
