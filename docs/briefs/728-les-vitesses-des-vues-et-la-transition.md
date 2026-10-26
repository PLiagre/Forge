# Lot #728 — Les vitesses des vues et la transition
Jalon : J4 · Machine : pc · Taille prévue : 295 lignes

## But
Le pont sait passer d'une vue à l'autre par un fondu au noir et donner au monde la vitesse de la vue d'arrivée : 0,1 jour par seconde en ville, 6 sur la carte, prises dans un seul fichier de réglages, sans jamais sortir un monde de sa pause.

## Le joueur
Lot de fond, sous-lot 1 de #410 « Le joueur passe de la carte à sa capitale, et l'horloge suit la vue ». Il prépare le geste du J4 de `CAP.md` : le joueur **passe de la carte à sa ville d'un geste**. En ville, une année dure environ une heure : il a le temps de regarder ses chantiers et ses gens. Sur la carte, elle dure environ une minute : il voit ses lieux se remplir ou se vider. Le passage se fait dans le noir, sans saut d'image. S'il a mis le jeu en pause, il la retrouve en arrivant. Ce lot écrit les réglages et la transition, sans les poser sur un geste. Les sous-lots 2 (double-clic sur le siège) et 3 (touche C, retour à la carte) de #410 les rendront visibles.

Dépend de : rien qui manque. `ClientHorloge.Lire/Regler`, `GET /horloge` et `POST /vitesse` sont sur la base (56f8dfd).

## Règle du monde
Sans objet : c'est un lot de vue. Aucune règle ni constante du monde ne change. La vitesse dit combien de ticks le service joue par seconde réelle, pas ce que dure un tick : « La base de temps » de `jeu/sim/MODELE.md` (un tick = un jour) reste intacte. Le service tient seul l'horloge. Unity lui demande une vitesse et ne compte jamais le temps à sa place.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/TransitionDeVue.cs
3d/unity/Assets/ForgeLocal3D/Pont/TransitionDeVue.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Resources.meta
3d/unity/Assets/ForgeLocal3D/Pont/Resources/ReglagesDesVues.json
3d/unity/Assets/ForgeLocal3D/Pont/Resources/ReglagesDesVues.json.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TransitionDeVueTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TransitionDeVueTests.cs.meta
docs/briefs/728-les-vitesses-des-vues-et-la-transition.md

Tout autre chemin est interdit. Unity génère les `.meta`. Budget indicatif : 95 lignes de composant et de réglages, 105 de tests, 4 de JSON, une vingtaine de `.meta`, le reste pour ce brief. Ajouts et retraits restent sous 300 lignes : écrire serré, dans le style dense du pont. Modèles à suivre : `HorlogeDeCarte` pour `Pas(double)`, la tâche en vol et `Arreter()`. `PassageALaCapitale` pour `ChargerScene`. `HorlogeDeCarteTests` pour le faux service `HttpListener`.

Ce que le code expose, dans `TransitionDeVue.cs` :
- **Le fichier** `Resources/ReglagesDesVues.json` contient exactement `{"VITESSE_VILLE": 0.1, "VITESSE_CARTE": 6}`. Pas d'autre clé : le lanceur Python (sous-lot 4 de #410) lira le même fichier.
- `enum VueDuJeu { Ville, Carte }`.
- `ReglagesDesVues` (classe scellée, `VitesseVille`, `VitesseCarte`, `Vitesse(VueDuJeu)`) :
  - `Lire(string json)` passe par `LecteurJson.LireObjet` ;
  - il lève une exception qui nomme la clé quand une clé manque, n'est pas un nombre, ou vaut ≤ 0, NaN ou l'infini. Une vitesse de vue nulle mettrait le monde en pause : refusée ;
  - `Charger()` lit `Resources.Load<TextAsset>("ReglagesDesVues")`, et lève en nommant la ressource si elle manque. Aucune valeur de repli écrite dans le code.
- `TransitionDeVue` (`MonoBehaviour`) :
  - `port` (défaut `PanneauLieu.DEFAULT_SERVICE_PORT`), `DUREE_FONDU_S` = 0,4 ;
  - `ChargerScene` (`Action<string>`, défaut `SceneManager.LoadScene`), que les tests remplacent ;
  - `bool Commencer(string scene, VueDuJeu vue, double maintenant)` : `false` si une transition est déjà en cours, et rien ne change alors ; lit les réglages au départ ;
  - `Pas(double maintenant)`, `Arreter()` ;
  - lectures : `Opacite` (0 à 1), `EnCours`, `RequeteEnVol`, `SceneChargee` (nulle avant le chargement), `VitessePosee` (`double?`, nulle si aucun POST), `Absence` ;
  - `static TransitionDeVue Lancer(string scene, VueDuJeu vue, int port)` : crée l'objet « Transition de vue », `DontDestroyOnLoad` en jeu seulement, et commence sur `Time.realtimeSinceStartupAsDouble`. Il rend `null` si une transition lancée est encore en cours. `Update` appelle `Pas` sur la même horloge réelle ; l'objet se détruit une fois fini.
- **Le déroulé**, à suivre tel quel :
  1. Assombrir : `Opacite` monte de 0 à 1 en `DUREE_FONDU_S`. Aucune requête ne part.
  2. Au premier `Pas` où l'opacité atteint 1, `ChargerScene(scene)` est appelé, une seule fois.
  3. Puis une seule tâche (`Task.Run`, client de 2 s, disposé) lit `GET /horloge`. Si la vitesse lue est > 0, elle envoie `POST /vitesse` avec `Vitesse(vue)`. Si elle vaut 0, ou si la lecture manque, rien n'est envoyé : `Absence` porte la cause, préfixe `horloge : `.
  4. L'opacité redescend à 0 en `DUREE_FONDU_S` à partir du chargement, sans attendre la requête. `EnCours` reste vrai tant que l'opacité n'est pas nulle ou qu'une requête est en vol.
  - Le noir est une toile `ScreenSpaceOverlay`, `sortingOrder` 32767, et une `Image` noire plein écran dont l'alpha vaut `Opacite`. Elle bloque les clics pendant la transition et est cachée au repos. Rien ne lance, n'arrête ni ne relance le service : aucune autre requête que les deux nommées.

## Conditions de succès
Sur le PC, éditeur fermé, depuis la racine : `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot728.xml" -logFile "$env:TEMP\lot728.log"`, sans `-quit`. Il faut une sortie 0, un XML sans échec, et des cas `TransitionDeVueTests` réellement exécutés : zéro cas est un échec. Écrire les tests et les voir rouges avant le code. Les pas des tests suivent `HorlogeDeCarteTests.Pas` : instants donnés, et attente bornée (10 s) de la requête en vol.

**SC1 — les réglages.**
- `ReglagesDesVues.Charger()` rend 0,1 pour la ville et 6 pour la carte. Le test exige aussi que 365 / vitesse soit entre 50 et 70 minutes pour la ville, et entre 50 et 70 s pour la carte : c'est la phrase de l'issue.
- `Lire` lève pour une clé absente, `"6"` en texte, 0 et −1, et le message nomme la clé.
- Hors Unity : `python3 -c "import json; d = json.load(open('3d/unity/Assets/ForgeLocal3D/Pont/Resources/ReglagesDesVues.json', encoding='utf-8')); assert d == {'VITESSE_VILLE': 0.1, 'VITESSE_CARTE': 6}, d"` sort 0.
- Contre-épreuve : le fichier changé à 0 ou privé d'une clé fait rougir le cas Unity et la commande Python.

**SC2 — un monde qui avance prend la vitesse de la vue, après le chargement.**
Le faux service sert `/horloge` à 2,5 j/s, et `/vitesse` change sa vitesse.
- `Commencer("Desert_City", Ville, t)`, puis des pas jusqu'à la fin. On exige :
  - l'opacité croissante jusqu'à 1, puis décroissante jusqu'à 0 ;
  - `ChargerScene` appelé une fois, avec `Desert_City`, et zéro requête reçue au moment de cet appel (compté dans le remplaçant) ;
  - les requêtes reçues, dans l'ordre : exactement `GET /horloge`, puis `POST /vitesse?jours_par_seconde=0.1` ;
  - la vitesse du faux service égale à `Charger().VitesseVille`, `VitessePosee` égale à 0,1, et `EnCours` faux à la fin.
- Le même cas en `Carte`, avec 6.
- Un second `Commencer` pendant l'assombrissement rend `false`, et le chargement ne se fait toujours qu'une fois.
- Contre-épreuves : une vitesse posée avant le chargement fait rougir « zéro requête » ; une vue inversée fait rougir la valeur.

**SC3 — un monde en pause reste en pause.**
Le faux service sert 0 j/s. Après la transition entière, on exige :
- la scène chargée ;
- les requêtes reçues réduites à `GET /horloge` : aucun POST ;
- la vitesse du faux service toujours 0, `VitessePosee` nulle.

Contre-épreuve : une transition qui pose la vitesse sans lire l'horloge fait rougir ce cas.

**SC4 — une absence ne bloque ni le passage ni l'image.**
- Sans service : la scène est chargée, l'opacité revient à 0, `Absence` commence par `horloge : `, et aucun POST n'est reçu. Même chose quand le service répond 500.
- Avec un faux service qui attend 500 ms avant de répondre : dix `Pas` espacés retournent en moins de 200 ms au total.
- La toile est en `ScreenSpaceOverlay` et à `sortingOrder` 32767. Elle est active pendant la transition, inactive au repos.
- Contre-épreuve : une requête faite dans `Pas` même fait rougir la borne de 200 ms.

**SC5 — rien d'autre ne bouge.**
- La commande de SC1 à SC4, sur toute l'assemblée `Forge.Pont.Tests` : `HorlogeDeCarteTests` et `PassageALaCapitaleTests` restent verts, sans retouche. Aucun test existant n'est retiré, renommé ou assoupli.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le périmètre.
- Contre-épreuve : une scène, une capture, `HorlogeDeCarte`, `PassageALaCapitale` ou `jeu/` touchés refusent la livraison.

## Hors périmètre
- Brancher la transition sur un geste : double-clic sur le siège et confirmation par la transition (sous-lot 2 de #410), touche C et pause en ville (sous-lot 3).
- Le lanceur qui démarre le service à `VITESSE_CARTE` (sous-lot 4) ; la session et le verdict de l'épreuve (sous-lots 5 et 6).
- Changer `HorlogeDeCarte`, ses paliers, `PassageALaCapitale`, `ClientHorloge`, le service, `ForgeCapture` ou une scène.
- Toute épreuve ou capture : elles tournent en pause (`--jours-par-seconde 0`) et restent ce qu'elles sont.

## Photo
Sans objet : la transition n'est posée dans aucune scène et aucun geste ne la lance encore, donc rien ne change à l'écran. Aucun `Lot728.cs` n'est ajouté. Le noir est une toile `Overlay`, que la caméra photographiée ne voit pas : les sous-lots 2 et 3 photographieront la vue d'arrivée, une fois le fondu fini.
