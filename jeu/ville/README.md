# ville/ — le contrat entre le monde et sa vue ville

La frontière de données entre `jeu/sim/`, qui possède le monde, et `3d/unity/`,
qui le montre. Elle est du texte : schémas, exemples, matrice d'autorité — donc elle
se lit, se versionne et se teste sans ouvrir Unity.

| fichier | ce qu'il dit |
|---|---|
| `FORGEHISTORY_CITY_MODE_CONTRACT.md` | la décision, la matrice d'autorité, le protocole v1 |
| `CITY_MODE_HOST_API.md` | ce que l'hôte expose |
| `Schemas/forgehistory-city-mode-v1.schema.json` | le schéma filaire, JSON Schema 2020-12 |
| `Schemas/forgehistory-city-mode-v1.examples.json` | cinq exemples cohérents |
| `UNITY_RENDER_DEPENDENCY_MATRIX.md` | ce que le rendu exige de chaque côté |
| `cellule_du_desert.py` | la cellule par défaut des épreuves, dérivée de la carte |

## La règle qui tient tout

**Une seule simulation.** Le monde appartient à `sim/` : les identités, le
temps, l'économie, la sauvegarde. La vue ville rend des snapshots versionnés,
collecte des intentions, et présente les reçus. Elle ne possède jamais une
seconde source de vérité.

Une intention est corrélée, idempotente, ordonnée par tick et révision, et
explicitement acceptée ou refusée. Rien ne s'applique en optimiste dans la vue.

## Ce que ce contrat attend encore

Rien que le moteur ne produise déjà : chaque message porte `cell_id`, l'entier
de `data/world-1400.json` et la seule clé spatiale de `sim/`
([`sim/MODELE.md`](../sim/MODELE.md)). Aucune identité de ville n'y figure.
`tests/` juge les exemples d'après le schéma lu.

Le lieu, subdivision de la cellule, existe : `GET /lieu?cell=N` porte `lieux`,
la liste des lieux de la cellule rangée par rang, chacun avec `rang`,
`surface_km2`, `population`, `stocks`, `maitre` (identifiant de maison, ou
`None` pour un état manuel), `point`, `nom` (repris du bloc `noms`) et
`flux_30j` (`preleve_kg`, `partis_personnes`, `arrives_personnes` sur trente
jours, sans arrondi). Sans noms ou flux fournis, ces deux champs valent `None`. Son identité est le couple (`cell_id`
de la réponse, `rang`) : **dérivée** de `cell_id`, jamais une seconde clé ; un
lieu publié ne porte ni `cell_id` recopié ni `lieu_id`.

Le bloc frère `noms` publie `lieux` (`rang`, `nom`) et `maisons`, dictionnaire par identifiant de `maitre` avec `nom` et `prenom_chef` (`null` si historique). Il égale celui de la photographie ; les lectures HTTP utilisent les octets figés.

## La cellule par défaut des épreuves

`pc\Jouer.cmd` démarre le service de `sim/`, puis le jeu. Il ne passe
`-forgeCell <cell_id>` qu'avec `--cellule <cell_id>`. Sans cette option, le jeu
lit la maison du joueur au service : il ouvre sa capitale si sa terre a un kit,
sinon la carte de 1400 ; une donnée absente est dite par le jeu.
Chaque lancement démarre un service neuf, sans choix : il ouvre donc la carte,
où le joueur choisit sa terre.

Les épreuves `pc/epreuve_jalon1.py` et `pc/epreuve_carte.py` gardent leur cellule
par défaut, calculée par `cellule_du_desert.py` :

- **la règle** : la cellule dont `climat.insolation_annuelle_mj_m2` est la plus
  forte ; à égalité, le plus petit `cell_id` ;
- **pourquoi l'insolation** : la carte ne porte aucune température ; l'insolation
  annuelle est sa seule mesure de chaleur. La cellule la plus ensoleillée tombe
  au sud de la carte (niveau de fidélité 1) ;
- **les refus** : une cellule sans cette clé, ou une carte sans cellule, lève une
  `ValueError` qui nomme la clé et le `cell_id` ; aucune valeur par défaut,
  aucune cellule écrite à la main.

Le numéro n'est écrit nulle part : il se recalcule depuis les données.

```bash
py ville/cellule_du_desert.py      # depuis jeu/ : écrit le cell_id seul
```

Pour ouvrir une autre cellule : `pc\Jouer.cmd --cellule <cell_id>`.

Pour ouvrir le jeu sur la carte de 1400 : `pc\Jouer.cmd --carte`. Le
lanceur passe `-forgeCarte` au jeu, qui quitte la ville au lancement pour la scène
`Forge_Carte`. On s'y déplace en glissant (bouton gauche ou du milieu) et on
zoome à la molette, vers le point sous la souris, sans sortir de la carte servie.
En haut à droite, la date et la vitesse du monde, lues au service :
Espace ou « Pause » arrête le monde et le relance à sa vitesse, + et − (ou les
boutons) passent d'un palier à l'autre (0,5 à 20 jours par seconde).
En bas à gauche, la fiche de la cellule sous la souris : ses villes,
sa puissance et sa maison lues dans `/carte`, ses habitants, sa faim et sa dette
lus dans `/monde`, avec le tick de cette lecture. Ce que le monde ne nomme pas ou
ne calcule pas, la fiche le dit.

## L'épreuve du panneau de lieu

Le panneau du lieu doit montrer les mêmes nombres que la photographie de `sim/`,
pour la même graine, le même tick et la même cellule. Depuis la racine du dépôt :

```bash
py pc\epreuve_jalon1.py --sortie <dossier>
```

La capture Unity lance le service de `sim/`, ouvre la scène du désert en Play,
écrit le texte du panneau, et le script le compare nombre par nombre à
`py -m sim --ticks N --seed S --snapshot-json`.

- **0** — égalité exacte : `verdict.txt` commence par `ÉGALITÉ` ;
- **1** — un écart : le verdict nomme chaque champ, la valeur du panneau et celle de la photographie ;
- **2** — l'épreuve n'a pas pu se jouer (Unity introuvable, port déjà pris, photographie ou capture absente ou antérieure à l'essai, service laissé ouvert).

La contre-épreuve pousse le service un tick plus loin que la photographie ; elle doit sortir **1** :

```bash
py pc\epreuve_jalon1.py --sortie <dossier> --decalage 1
```

La capture que la chaîne prend ensuite lance ce même service (sans choisir de cellule) : le panneau publié au journal porte les chiffres du monde, pas une absence.

## L'épreuve de la route à Biskra
Unity joue une route, une parcelle et une scierie à Biskra, après le choix de l'émirat du Zab ; Python rejoue leur journal. Ce n'est pas la preuve complète. L'éditeur est fermé ; la scène et les données viennent de `py local3d/atelier_desert.py terrain` (depuis `3d/`).

`--avec-unity` fixe la graine 0 et 11 ticks. La cellule de Biskra est lue dans la table. Le script dépose le choix du Zab au tick 0, appliqué au tick 1 ; Unity pose la route, la parcelle et la scierie aux ticks 1, 2 et 3. Le témoin rejoue le choix seul. Au tick 11, sur `monde-service.json`, la rue est à 50/200, la parcelle 14/14 aux bornes, la scierie 30/271 aux piquets.

```powershell
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-biskra-normal"
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-biskra-sourd" --service-sourd
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-biskra-locale" --ville-locale
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-biskra-maison" --sur-une-maison
```

**0** preuve valide : le verdict dit « octets égaux sur 11 ticks » et « ticks 1, 2 et 3 » ; les rapports portent la cellule de Biskra. **1** invariant violé : le service sourd nomme « bâtiment absent » et « écart entre monde servi et monde rejoué » ; la ville locale nomme « empreinte des rues », « c'est le redessin qui échoue » et « l'égalité Python peut rester vraie » ; `--sur-une-maison` nomme « maison de 1400 » (le monde refuse la rue). **2** essai impossible (Unity, scène, port, délai, rapport absent ou ancien, exception dans les défauts, aucune route sur une maison que le relief accepte) : une panne ne vaut pas contre-épreuve.

Le parcours Python, sans Unity, bâtit à Biskra après le choix appliqué de l'émirat du Zab. La cellule est celle du siège, lue dans la table. Le journal garde ce choix au tick 0, puis la route, la parcelle et le bâtiment aux ticks 2, 3 et 5. Le rejeu complet reprend les quatre entrées ; le témoin rejoue seulement le choix, au même tick.

```bash
python3 pc/epreuve_jalon4.py --sortie <dossier>
python3 pc/epreuve_jalon4.py --sortie <dossier> --service-sourd
```

**0** le départ est le même dans les trois mondes, Biskra porte les trois gestes, le service et le rejeu sont égaux à l'octet. **1** le service sourd : le bâtiment manque.

## L'épreuve de la carte

Le joueur peut se fier à sa carte : elle dessine autant de cellules
que `/carte` en sert, et la fiche d'une cellule dit `/carte` (villes, puissance,
maison) et `/monde` au même tick (habitants, faim, dette), nombre par nombre.
Depuis la racine du dépôt :

```bash
py pc\epreuve_carte.py --sortie <dossier> [--cellule C] [--ticks N] [--seed S]
```

Le script lance le service (en pause, poussé au tick N) et lit `/carte` et
`/monde` ; Unity ouvre `Forge_Carte` en Play (`ForgeLocal3D.EpreuveCarte.Jouer`),
survole la cellule C (par défaut celle du lanceur) et écrit `rapport.json` ; le
verdict, dans `verdict.txt`, cite chaque valeur des deux côtés. **0** égalité,
**1** écart, **2** épreuve impossible (Unity introuvable, port pris, référence
illisible, Unity en erreur, rapport absent ou antérieur à l'essai).

Les trois contre-épreuves doivent sortir **1** : `--decalage 1` (le service lu
par Unity a un tick d'avance), `--retirer-une-cellule` (Unity retire une cellule
du dessin) et `--sans-service` (le service s'arrête avant Unity : la carte dit
que le monde ne répond pas).

## La session du choix de la terre

Le joueur clique sur une terre de la carte de 1400, puis sur une autre, et le
monde refuse le second choix (moitié Unity de l'épreuve du choix).
Depuis la racine du dépôt :

```bash
Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveChoix.Jouer \
      -forgeEpreuve <rapport.json> -forgeTerre N -forgeSecondeTerre M [-logFile <journal>]
```

Le service se lance à la main dans un second terminal, depuis `jeu/` :
`py -m sim.service --seed 0 --jours-par-seconde 0` (port 8000, tick 0, en
pause), et s'arrête après chaque essai. Unity ouvre `Forge_Carte` en Play,
attend les six repères des terres de départ, lit `/departs`, clique comme le
joueur (par `SurvolDeCarte`) sur le repère de la terre N, attend son reçu, puis
clique aussitôt sur celui de M, avant tout tick : la session ne touche jamais
`/tick` ni `/vitesse`. Un rapport relatif se lit depuis le dossier de lancement.

Le rapport porte `terre`, `seconde_terre`, `reperes` (repères posés),
`tick_avant` et `tick_apres` (le tick de `/departs` avant le premier clic et
après le second reçu), `premier` et `second` (chaque reçu : `statut` 200, 400 ou
409, ou −1 absent ; `tick` du dépôt accepté, −1 sinon ; `raison` du refus ou de
l'absence), `premier_texte` et `second_texte` (le panneau du choix, tel
qu'affiché) et `defaut`. **0** les deux reçus relevés, quels qu'ils soient ;
**1** session impossible (`defaut` dit pourquoi ; le rapport est écrit) ; **2**
arguments fautifs (aucun rapport). La session ne juge rien : le jugement est
celui de [l'épreuve du choix](#lépreuve-du-choix), qui compare au monde.

## La session de l'épreuve de la capitale

Le joueur choisit sa terre dans le cabinet de la carte et, au tick suivant,
passe à sa ville ou lit « Pas encore de kit pour cette terre »
(moitié Unity de l'épreuve de la capitale). Depuis la racine du dépôt :

```bash
Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveCapitale.Jouer \
      -forgeEpreuve <rapport.json> -forgeTerre N [-logFile <journal>]
```

Le service se lance à la main comme pour la session du choix (`py -m
sim.service --seed 0 --jours-par-seconde 0` depuis `jeu/`), neuf pour chaque
essai. Unity ouvre `Forge_Carte` en Play, attend que le cabinet ait lu le monde
et les départs, choisit la terre N, laisse le passage voir le départ, pousse un
seul `POST /tick?n=1` (jamais `/vitesse`), puis relève ce que le passage fait :
la ville qu'il charge lui-même, comme dans le jeu, ou son message. Rien n'est
remplacé dans le chargement.

Le rapport porte `terre`, `tick_avant` et `tick_apres` (le tick du monde avant
le choix et après le passage), `choix` (le reçu, comme dans la session du
choix), `scene_active`, `cellule` et `tick_ouverture` (lus sur l'outil de la
ville, −1 sans ville), `panneau_lieu` (la première ligne du panneau du lieu),
`message_passage` et `defaut`. **0** une ville ou un message relevé, quel qu'il
soit ; **1** session impossible (`defaut` dit pourquoi ; le rapport est écrit) ;
**2** arguments fautifs (aucun rapport). Le rapport écrit, Unity sort du Play et
laisse 12 s aux lectures de la carte avant de rendre son code : sans service, il
pendait sinon à sa fermeture. La session ne juge rien : le jugement est
celui de [l'épreuve de la capitale](#lépreuve-de-la-capitale).

## L'épreuve de la capitale

Le joueur se fie au passage. Depuis la racine, éditeur fermé :

```bash
py pc\epreuve_capitale.py --sortie <dossier> [--seed S] [--unity CHEMIN]
```

Un service neuf par terre, trouvée par son nom. Unity seul pousse le tick ;
Python ne poste ni intention, ni tick, ni vitesse, et n'envoie à Unity que
l'id de la terre. La cellule attendue est `siege.cell_id` de
`GET /maison?id=seigneurie-<id>`. **0** égalité, **1** écart, **2** épreuve
impossible. Contre-épreuve sans PC :
`python3 -m pytest jeu/ville/tests/test_epreuve_capitale.py -q -k contre_epreuve -s`.

## L'épreuve de la part

Le joueur se fie à sa part et à son grenier. Éditeur fermé, port 8000 libre, depuis la racine :
`py pc\epreuve_part.py --sortie <dossier> [--part-forte P] [--part-faible P] [--unity CHEMIN]` (entiers de 0 à 60, défauts 50 et 10).
Deux services neufs en pause, graine 0, l'un après l'autre : forte puis faible, la Morée trouvée par son nom. Unity (`ForgeLocal3D.EpreuvePart.Jouer`) joue le curseur, la confirmation et les trente ticks ; Python lit seulement `/monde` et le corps brut de `/maison` avant d'arrêter le service, puis le [juge](../../pc/epreuve_part.py) compare. **0** égalité, **1** écart, **2** épreuve impossible (Unity absent, port pris, part illisible, session, rapport ou lecture en panne ; l'essai est nommé).
Contre-épreuve : `--part-forte 10` rend **1**, seul `grenier` en écart.

## La session de l'épreuve de la ville de 1400

Unity ouvre quatre villes de 1400 comme le joueur et relève, maison par maison, ce qu'il a posé (moitié Unity
de l'épreuve de la ville de 1400). Éditeur fermé, depuis la racine : `Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveVille1400.Jouer
-forgeEpreuve <dossier> [-forgeSauter | -forgeAjouter] [-logFile <journal>]` ; `Relancer` prend les mêmes arguments, seuls le
champ `session` (« jouer », « relance ») et le nom des fichiers changent. Le service se lance à la main depuis `jeu/`
(`py -m sim.service --seed 0 --jours-par-seconde 0`), **neuf avant chaque session**. Les cellules sont, dans l'ordre, 10103,
1175, 1232 et 10337 (Biskra, le ksar de l'éditeur, 493 maisons seules, 28 îlots). `-forgeSauter` détruit la première maison
posée, `-forgeAjouter` la double à +10 m. Chaque cellule écrit `<dossier>/<session>-<cellule>.json` sur une ligne : `session`,
`contre_epreuve`, `cellule`, `tick`, `foyers`, `posees`, `absence`, `refus`, `rues_dessinees`, `empreinte_rues`, `duree_dessin_ms`,
`images` et `image_ms` (300 images, une mesure, pas la preuve des 60 images/s), `maisons`, `empreinte` et `defaut`. Une maison est
la ligne `"<rang> <indice> <variante> <x> <y> <sol> <lacet>"` (rang et indice de son nom, variante du kit ou −1, centre de sa
boîte dans le repère du plan, y de sa base, lacet ; en `F2`) ; `empreinte` est le SHA-256 des lignes, chacune suivie de `\n`.
Codes : **0** aucun défaut ; **1** un défaut (sans service par exemple ; les rapports sont écrits) ; **2** arguments fautifs,
aucun rapport. Le jugement est celui de [l'épreuve de la ville de 1400](#lépreuve-de-la-ville-de-1400).

## L'épreuve de la ville de 1400

Le joueur se fie à sa capitale : relancé, le jeu redessine la même Biskra d'après le monde. Éditeur fermé, port 8000 libre, depuis la racine : `py pc\epreuve_ville1400.py --sortie <dossier> [--seed S] [--unity CHEMIN] [--sauter | --ajouter]`. Deux services neufs de même graine, en pause, l'un après l'autre : Unity joue `Jouer` puis `Relancer`, Python lit les quatre `/plan` avant d'arrêter chaque service, sans rien envoyer qui change le monde. Le juge dérive de `plan.base.maisons` un couple (rang, indice) par foyer : partition exacte, variante `(rang + indice) % 6`, centre dans l'emprise (0,05 m), empreinte recalculée, relance égale. Les refus (`Maison <rang> indice <indice> : <raison>`) sont comptés et affichés à part, jamais comme maisons posées ; Biskra n'en accepte aucun. Durée du dessin en ms et images/s, sans seuil. **0** égalité, **1** écart (couple manquant, doublon, inconnu, variante, hors emprise, empreinte, relance), **2** épreuve impossible (Unity absent ou non nul, port pris, service jamais prêt, HTTP, rapport absent ou ancien, champ absent, −1, défaut, absence, temps nul) : une panne ne prouve aucun rouge. Contre-épreuves : `--sauter` (une maison détruite) et `--ajouter` (une maison doublée) rendent **1** par les comparaisons de maisons, jamais par le drapeau. Sans PC : `python3 -m pytest jeu/ville/tests/test_epreuve_ville1400.py -q`.

## La session de l'épreuve de la transition

Le joueur va de la carte à Biskra par un double-clic et revient par C (moitié Unity de l'épreuve de la transition).
Préparation, service neuf à chaque essai : `py -m sim.service --seed 0 --jours-par-seconde 0` depuis `jeu/`, la terre au siège Biskra
choisie par `POST /intention`, puis `POST /tick?n=1` ; en marche seulement, `POST /vitesse` à `VITESSE_CARTE`. Puis, éditeur fermé :
`Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveTransition.Jouer -forgeEpreuve <rapport.json> [-logFile <journal>]`.
La session ne choisit rien, ne pousse ni tick ni vitesse : elle lit `/horloge` une fois dans `carte_avant`, `ville_apres`, `ville_avant`
(une seconde plus tard) et `carte_apres` (`tick`, `jours_par_seconde`, `scene`), et `cellule` sur l'outil de la ville. **0** les quatre
lectures et l'aller-retour finis, quoi qu'ils valent ; **1** session impossible (`defaut` dit l'étape et la cause, −1 aux relevés non
faits) ; **2** arguments fautifs, aucun rapport.

## L'épreuve de la transition

Le joueur se fie à l'aller-retour entre la carte et sa capitale. Éditeur fermé, port 8000 libre, depuis la racine :
`py pc\epreuve_transition.py --sortie <dossier> [--seed S] [--unity CHEMIN]`. Un service neuf **à 1 j/s** ; le Zab, trouvé par son nom, est choisi par `POST /intention`, seule requête qui change le monde, et le jour naturel suivant l'applique (30 s au plus). Le siège attendu est `siege.cell_id` de `/maison`. Unity joue sa session sans rien d'attendu ; le juge exige les vitesses 1, `VITESSE_VILLE`, `VITESSE_VILLE`, `VITESSE_CARTE` lues dans `ReglagesDesVues.json`, les scènes carte, ville, ville, carte, et deux inégalités : **`ville_apres.tick > carte_avant.tick`** et **`carte_apres.tick > ville_avant.tick`** (les deux lectures en ville peuvent être égales).
**0** égalité, **1** écart, **2** épreuve impossible (défaut, −1, champ absent, réglage, port, Unity, rapport ou HTTP en panne). Contre-épreuves sans PC : `python3 -m pytest jeu/ville/tests/test_epreuve_transition.py -q -k contre_epreuve -s`.

## L'épreuve de la vie du bourg

Le joueur lit sur la place de Biskra si son bourg mange. Éditeur fermé, port 8000 libre, depuis la racine : `py pc\epreuve_vie_bourg.py --sortie <dossier> [--seed S] [--unity CHEMIN] [--garder-etal-plein]`.
Unity joue sa session : `Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeScenario vie-du-bourg -forgeSeed S -forgeTicks 0 -forgeServiceEpreuve -forgeCaptures <dossier> -logFile <dossier>\unity.log [-forgeGarderEtalPlein]`, qui écrit `vie-bourg.json` et les images `*--01-place-nourrie.png`, `*--02-place-affamee.png`.
Puis un service neuf `py -m sim.service --epreuve --seed S --jours-par-seconde 0` (déterministe) sert la référence : l'unique départ au siège Biskra (`/departs`), `/lieu?cell=X&bourg=1` et `/occupation?cell=X`, le seul `POST /epreuve/vider-panier?cell=X` qui change le monde, puis les deux mêmes lectures.
Le juge compare, aux états nourri puis affamé : cellule, `tick` et `tick_local`, population, nourriture (égalité exacte) et faim du bourg ; un couple (rang, indice) par foyer de la base ; fumées N/N puis 0/N ; lampes actives, d'intensité égale aux deux états ; l'étal garni à la nourriture servie, puis sans garniture visible (« étal plein en famine ») ; causes vides, même caméra, 19,6 h.
**0** égalité, **1** écart, **2** épreuve impossible (Unity absent ou non nul, port pris, image ou rapport absent ou ancien, champ absent, −1, défaut, échantillon vide, référence inutilisable) : une panne ne prouve aucun rouge, et le drapeau `contre_epreuve` n'est qu'affiché. Sans PC : `python3 -m pytest jeu/ville/tests/test_epreuve_vie_bourg.py -q`.

## L'épreuve des passants

Le joueur voit dans Biskra autant de passants par métier que le bourg servi en donne, l'ouvrier sur son chantier, puis la rue vide. Éditeur fermé, port 8000 libre, depuis la racine : `py pc\epreuve_passants.py --sortie <dossier> [--seed S] [--unity CHEMIN] [--contre en-trop|ailleurs|anciens]`. Unity joue sa session : `Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeScenario passants -forgeSeed S -forgeTicks 0 -forgeServiceEpreuve -forgeCaptures <dossier> -logFile <dossier>\unity.log [-forgePassantEnTrop | -forgeOuvriersAilleurs | -forgeGarderAnciens]`, qui écrit `passants-bourg.json` et les images `*--01-ouvriers-au-chantier.png`, `*--02-bourg-vide.png`.
Puis un service neuf `py -m sim.service --epreuve --seed S --jours-par-seconde 0` (déterministe) rejoue les gestes de `ScenarioPassants.cs` : l'unique départ au siège Biskra, `choisir_depart`, un tick, trois `tracer_route` de (0 ; d) à (40 ; d) pour d = 0, 8, 16, quatre ticks ; il sert `/lieu?cell=X&bourg=1` et `/plan?cell=X` au tick 5, le seul montage `POST /epreuve/vider-bourg?cell=X`, un tick, et les mêmes lectures au tick 6.
Le juge compte lui-même les passants de `liste` : cellule, ticks et bourg servis ; **le nombre** par métier égal à la règle des passants du bourg recalculée sur le `/lieu` servi, `id` distincts ; **les ouvriers** vers une « rue N » servie à bras, à 0,05 m au plus de sa polyligne ; **le vidage** : liste vide au tick 6, aucun ancien `id` maintenu ; même caméra. **0** égalité, **1** écart, **2** épreuve impossible (Unity absent ou non nul, port pris, image ou rapport absent ou ancien, champ absent, −1, défaut, référence inutilisable, échantillon vide sans chantier à bras ni ouvrier attendu) ; le drapeau `contre_epreuve` n'est qu'affiché. Sans PC : `python3 -m pytest jeu/ville/tests/test_epreuve_passants.py -q`.

## L'épreuve de l'enceinte

Le mur que le joueur paie autour de Biskra est celui que le monde bâtit, et sa porte est là où le monde la sert. Éditeur fermé, port 8000 libre, depuis la racine : `py pc\epreuve_enceinte.py --sortie <dossier> [--seed S] [--unity CHEMIN] [--contre ignore|sans-porte]`. Unity joue sa session : `Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeScenario enceinte -forgeSeed S -forgeTicks 0 -forgeServiceEpreuve -forgeTravailEnceinte 0.01 -forgeCaptures <dossier> -logFile <dossier>\unity.log [-forgeEnceinteSansPorte]`, qui écrit `enceinte.json` et les images `*--1-enceinte-en-chantier.png`, `*--2-enceinte-finie.png`.
Puis un service neuf `py -m sim.service --epreuve --travail-enceinte 0.01 --seed S --jours-par-seconde 0` (déterministe) rejoue les gestes de `ScenarioEnceinte.cs` : l'unique départ au siège Biskra, `choisir_depart`, un tick, `tracer_route` de (−66 ; 2,2) à (−120 ; 2,2) large de 4 m, un tick, `tracer_enceinte` sur les coins du rapport (acceptée au tick 2), puis douze fois un tick et `/plan?cell=X`. Sous `--contre ignore`, ce service accepte `tracer_enceinte` sans l'appliquer (`ignorante`) ; sous `--contre sans-porte`, la session retire ses portes dessinées.
Le juge compare chaque relevé au plan servi au même tick : cellule, **contour** égal aux coins, **travail requis** de la session et du service égal au périmètre fois J recalculé, fourni, chantier et étape servis, **portes servies** identiques, **portes dessinées** recomptées dans `portes_dessinees`, chaque servie à 0,05 m au plus d'une dessinée ; **l'achèvement** au premier tick servi hors chantier, dernier relevé. **0** égalité, **1** écart, **2** épreuve impossible (Unity absent ou non nul, port pris, image ou rapport absent ou ancien, champ absent, −1, défaut, reçu autre qu'accepté au tick 2, autre J, moins de trois coins, ticks qui ne se suivent pas depuis 3 ou passent 14, échantillon sans porte servie, référence hors des ticks 3 à 14) ; `contre_epreuve`, `ecart_porte_m`, `tours` et `pans` ne sont jamais jugés. Sans PC : `python3 -m pytest jeu/ville/tests/test_juge_enceinte.py -q`.

## L'épreuve du choix

Le joueur peut se fier à son geste : la terre qu'il
clique sur la carte de 1400 est celle que le monde retient, et le second choix
est refusé pour la raison que le panneau lui affiche. Depuis la racine du dépôt,
éditeur fermé :

```bash
py pc\epreuve_moree.py --sortie <dossier> [--terre N] [--seed S] [--unity CHEMIN]
```

Le script lance le service (graine S, en pause) et lit `/departs` ; il y trouve
la Morée par son nom (« Despotat de Morée », jamais par son id), la terre
cliquée (N, la Morée par défaut) et la seconde terre (la première servie d'un
autre id). Il joue la [session du choix](#la-session-du-choix-de-la-terre)
telle quelle, lit `/monde` avant le tick, pousse un tick et relit `/monde`.

Le verdict, dans `verdict.txt`, juge contre la Morée servie et le monde, jamais
contre la terre demandée : la session n'a pas fait avancer le monde ;
`/monde` ne porte pas `maison_du_joueur` avant le tick ; le premier reçu est
accepté au tick de `/departs` ; le second est refusé (409) par « départ déjà
choisi : seigneurie-<id de la Morée> » ; le tick poussé est le suivant et la
maison retenue après lui est la seigneurie de la Morée ; les deux textes du
panneau sont ceux attendus, mot pour mot. **0** égalité, **1** écart, **2**
épreuve impossible (Unity introuvable, port pris, référence illisible, session
en erreur, rapport absent ou antérieur à l'essai, monde illisible après la
session).

La contre-épreuve `--terre 6` fait cliquer le Zab puis Bar : le monde retient
`seigneurie-6`, le verdict sort **1**.
