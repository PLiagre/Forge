# Lot #729 — Un double-clic sur son siège descend dans sa ville
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
Sur la carte, un double-clic du joueur sur la cellule du siège de sa terre à kit le fait descendre dans sa ville par le fondu au noir de #728 ; la confirmation de #689 prend le même fondu.

## Le joueur
Sous-lot 2 de #410 « Le joueur passe de la carte à sa capitale, et l'horloge suit la vue ». Il sert le geste du J4 de `CAP.md` : le joueur **passe de la carte à sa ville d'un geste**. Au Zab, déjà maître de Biskra, le joueur gouverne depuis la carte, puis double-clique sur son siège : l'écran s'assombrit et il se retrouve dans Biskra, sur la cellule de son siège. Si le monde avance, le temps y ralentit à la vitesse de la ville (une année dure environ une heure). Quand il confirme sa terre, il entre aussi dans sa ville par ce fondu, au lieu d'une coupe sèche. Un clic seul, deux clics trop espacés, une autre cellule, ou Bar (terre sans kit) : rien. Il sent que la carte et la ville sont deux vues d'un même monde, entre lesquelles il passe quand il veut. Le retour à la carte (touche C) vient au sous-lot 3 de #410.

## Règle du monde
Sans objet : c'est un lot de vue. Le monde, `jeu/sim/MODELE.md` et le niveau de fidélité ne changent pas. Le siège vient de l'aiguillage de #679 (`AiguillageDeCapitale.Lire` : `GET /monde`, puis `siege.cell_id` de `/maison?id=`), jamais d'une constante ; les terres à kit, de `TerresAvecKit`. La vitesse de la ville, `VITESSE_VILLE` = 0,1 jour par seconde, est lue dans `Pont/Resources/ReglagesDesVues.json` par `TransitionDeVue` (#728, sur master depuis 05307bf ; le chantier part de master à jour). La règle de #728 tient : un monde en pause reste en pause.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/PassageALaCapitale.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/PassageALaCapitaleTests.cs
3d/unity/Assets/ForgeLocal3D/Carte/SurvolDeCarte.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot729.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot729.cs.meta
docs/briefs/729-un-double-clic-sur-son-siege-descend-dans-sa-vil.md

Tout autre chemin est interdit ; le `.meta` est généré par Unity. `TransitionDeVue.cs` et ses tests, `CabinetDeCarte`, `ReperesDeDepart`, `EpreuveCapitale`, `Lot690.cs` et `Lot701.cs` ne changent pas. Dans `PassageALaCapitaleTests.cs`, les cas s'ajoutent après les cas existants : aucune ligne existante n'est modifiée ni retirée. Budget : environ 25 lignes dans le passage, 5 dans le survol, 55 de tests, 100 de capture, 100 de brief, dans le style dense du pont.

## Conditions de succès
`PONT` = `Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults <temp>/pont.xml -logFile <temp>/pont.log`, sans `-quit` : sortie 0, XML sans échec, cas nommés réellement exécutés (zéro cas est un échec). `CAPTURE` = `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeSeed 0`, sans `-quit` ni `-nographics`, comme au #701. Les tests s'écrivent d'abord et se voient rouges avant le code.

Le passage ajoute :
- `DELAI_DOUBLE_CLIC_S` = 0,5 ;
- `long? SiegeLu` : la cellule de la dernière lecture servie si elle rend `Ville` ; nulle après `Depart` ou `PasDeKit` ; inchangée après une absence ;
- `bool Cliquer(long? cellule, double maintenant)` : le second de deux clics sur la même cellule, au plus `DELAI_DOUBLE_CLIC_S` après le premier, sur `SiegeLu`, sans scène déjà demandée, descend comme la confirmation (`SceneDemandee`, remise de #701, `ChargerScene(scène)`) et rend `true`. Un clic qui a servi à un double-clic n'en commence pas un autre.

`ChargerScene` jamais assigné, ou remis à `null`, appelle `TransitionDeVue.Lancer(scène, VueDuJeu.Ville, port)` avec le port du passage ; assigné, il n'appelle que ce qu'on lui donne. La règle « une lecture `Depart`, puis une lecture `Ville` » de #689 reste telle quelle. `SurvolDeCarte.Cliquer`, dans `Libre`, après `reperes.Choisir` : `fiche.Survoler(position)`, puis `fiche.Survolee?.CellId` et `Time.realtimeSinceStartupAsDouble` au `PassageALaCapitale` du même objet s'il y en a un, cherché au clic (#690 le pose après l'`Awake`).

**SC1 — Un double-clic sur le siège descend, une seule fois.** `PONT`. Zab servi dès la première lecture (comme `UnZabDejaConfirmeNeRenvoiePasEnVille`) ; après quelques pas, `SiegeLu` égale le `siege.cell_id` lu dans la fixture du Zab. Deux clics sur ce siège à 0,2 s d'écart : le second rend `true`, `chargees` vaut exactement la scène de `TerresAvecKit`, `PrendreCelluleRemise(scène)` rend le siège, aucun `GET /monde` après la descente malgré d'autres pas, et un troisième puis un quatrième clic ne chargent rien de plus. Contre-épreuve : un passage qui ignore la cellule, ou recharge à chaque double-clic, rougit.

**SC2 — Rien d'autre ne descend.** `PONT`. Un cas paramétré : `un-clic` (un clic sur le siège), `lent` (deux clics espacés de `DELAI_DOUBLE_CLIC_S` + 0,01), `autre-cellule` (deux clics sur siège + 1), `bar` (Bar confirmé, double-clic sur le siège de sa fixture), `depart` (sans maison, double-clic sur le siège du Zab), `absence` (sans service, idem). Chacun exige `chargees` vide, `SceneDemandee` nulle, aucun `Cliquer` à `true`, aucune remise. Contre-épreuve : un double-clic jugé sur le seul nombre de clics rougit `autre-cellule` ou `lent`.

**SC3 — Par défaut, le passage prend la transition.** `PONT`. Un cas paramétré `confirmation` (sans maison, puis Zab) et `double-clic` (Zab dès l'ouverture, puis deux clics) met `ChargerScene = null` après `Poser()`. Il exige exactement un `TransitionDeVue` dans la scène, `EnCours`, au port du passage, `SceneChargee` nulle, et `SceneDemandee` égale à la scène du ksar. Il remplace ensuite le `ChargerScene` de la transition par un compteur, appelle `Pas` au-delà de `DUREE_FONDU_S`, et exige exactement la scène du ksar ; il arrête et détruit la transition dans un `finally`. Contre-épreuve : un défaut resté sur `SceneManager.LoadScene` ne crée aucune transition et rougit les deux cas.

**SC4 — Les invariants existants restent verts.** `PONT` vert sur toute l'assemblée (`TransitionDeVueTests`, cas #689/#690/#701 compris) ; `python3 -m pytest jeu -q` passe. `git diff -U0 origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/PassageALaCapitaleTests.cs` ne montre aucune ligne retirée ; `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le périmètre ; `git diff --numstat` reste sous 300 lignes, brief compris. Contre-épreuve : un cas existant modifié refuse la livraison.

**SC5 — L'épreuve de la capitale passe par la transition.** `py pc\epreuve_capitale.py --sortie "$env:TEMP\lot729-capitale"` rend 0 (Biskra au siège 10103 au tick 1, Bar avec son message) : la session #702 charge désormais par le défaut, donc par le fondu. `CAPTURE -forgeLot 701 -forgeTicks 3 …` sort 0 : son chargement remplacé n'a pas bougé. Contre-épreuve : une transition qui perdrait la remise ouvre 1175, et le verdict #703 rend 1.

**SC6 — La photo, et sa contre-épreuve.** `CAPTURE -forgeLot 729 -forgeTicks 3 -forgeCaptures "$env:TEMP\lot729" -logFile "$env:TEMP\lot729.log"` sort 0 avec deux PNG, `*--1-siege-du-zab.png` et `*--2-biskra-apres-la-transition.png`, et des traces `CAPTURE_729`. Contre-épreuve : `CAPTURE -forgeLot 729 -forge729UnSeulClic …` (un seul clic au scénario 2, drapeau lu dans `Lot729.cs` seul) sort 1 et dit qu'aucune transition n'est partie.

## Hors périmètre
- Le retour à la carte (C) et la pause en ville (Espace) : sous-lot 3 de #410 ; le lanceur à `VITESSE_CARTE` : sous-lot 4 ; la session et le verdict de l'épreuve de la transition : sous-lots 5 et 6.
- Changer `TransitionDeVue`, `ReglagesDesVues`, l'aiguillage, `TerresAvecKit`, le cabinet, les repères, le parcours ou une scène.
- Un repère ou un curseur qui signale le siège ; un message au double-clic sur une terre sans kit (le panneau de #689 le dit déjà).
- Un double-clic pendant une transition : le noir de #728 prend les clics, et `Libre` les écarte.

## Photo
Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot729.cs` : deux scénarios joués dans l'ordre de leur nom, dans la même session. Il réutilise `Lot549.Ouvrir/Photographier/FORME` et les aides `internal` de `Lot690` sans les changer. Chaque attente est bornée à 30 s au plus ; toute absence échoue en nommant sa cause.

`[ScenarioDeCapture(729, "1-siege-du-zab")]` :
- avant d'ouvrir la carte, il lit `/departs`, prend la terre au siège « Biskra », dépose `choisir_depart` par `ClientIntention` (reçu accepté exigé) et pousse un tick par `Lot690.PousserTick` ;
- il ouvre la carte, met survol et parcours en `automatique`, attend `passage.SiegeLu` égal au `CellId` de la fiche (10103), et exige aucune `SceneDemandee` pendant deux périodes : une terre déjà confirmée ne descend pas seule ;
- il cadre la carte sur le siège (`carte.Vue.Zoomer` ancré au point de `PositionSurLaCarte(Siege.Position, ReperesDeDepart.HAUTEUR_LIEU)`), puis `Lot549.Photographier`. Photo : le Zab sur la carte, Biskra lisible au centre.

`[ScenarioDeCapture(729, "2-biskra-apres-la-transition")]` :
- au point du siège à l'écran, il exige `FicheDeCellule.Survolee.CellId` égal au siège après `survol.Survoler` ;
- un `survol.Cliquer` seul, puis `DELAI_DOUBLE_CLIC_S` + 0,3 s d'attente : ni `TransitionDeVue` ni `SceneDemandee` ;
- deux `survol.Cliquer` dans la même image (un seul avec `-forge729UnSeulClic`) : une seule `TransitionDeVue`, `EnCours`, et `SceneDemandee` égale à la scène du ksar. Son `ChargerScene` est aussitôt remplacé par le chargement additif de Lot701, pour garder la caméra reçue ;
- il attend la scène chargée et la transition finie, et exige une opacité de 1 atteinte et une seule scène chargée ;
- comme Lot701, étapes 5 et 6 : scène active, carte déchargée, `DesertRoadTool.Cellule` égal au siège, panneau « Cellule 10103 · tick N », vue d'ensemble, toile du panneau rebranchée sur la caméra reçue et dans le champ. Trace `CAPTURE_729` : siège, scène, opacité maximale, `VitessePosee` ou `Absence` de la transition. Photo : Biskra en vue d'ensemble, avec le panneau du siège.

Le codeur ouvre les deux PNG : une carte sans Biskra, une ville sur 1175 ou une image noire refusent la livraison, même avec sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve et ce que montre chaque image.
