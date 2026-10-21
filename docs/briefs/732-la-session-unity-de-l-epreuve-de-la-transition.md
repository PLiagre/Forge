# Lot #732 — La session Unity de l'épreuve de la transition
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
L'aller-retour du joueur entre la carte et Biskra devient rejouable dans Unity, avec les ticks et les vitesses réellement lus au service avant et après chaque transition.

## Le joueur
Le joueur passe de la carte à sa capitale d'un geste, puis retrouve ses terres avec C : il sent que la ville et la carte appartiennent au même monde, dont le rythme suit la vue. Ce lot de fond prépare la preuve de ce geste de J4, porté par #410 et rendu visible par #729 et #730. Il fournit la session Unity au verdict de l'épreuve de transition, sous-lot suivant de #410 ; ce verdict jugera les observations, comme #703 juge celles de #702.

Dépend de : #729 et #730, présents sur la base : `SurvolDeCarte.Cliquer`, `PassageALaCapitale.SiegeLu`, la transition par défaut et C dans `DesertRoadTool.Update`. `ClientHorloge`, les réglages des vues, les aides de #702 et `Captures.Frappe` de #730 existent aussi. Ni la preuve de J3, ni #731, ni un autre lot à venir ne sont nécessaires : le service est préparé à part.

## Règle du monde
Sans objet : outil d'épreuve, sans changement de simulation, de niveau de fidélité ou de règle du monde. Le service tient seul les jours. La session ne choisit pas de terre, ne pousse aucun tick, ne règle aucune vitesse et n'actionne pas Espace ; seuls les gestes livrés peuvent provoquer les POST de vitesse des transitions.

Créer `ForgeLocal3D.EpreuveTransition.Jouer`, sur le modèle de #702 : `[InitializeOnLoad]`, `SessionState`, `EditorApplication.update`, ouverture de `CarteBuilder.Chemin` en Play, rapport avant sortie du Play, vidange bornée de 12 s puis `CitadelEditorBridge.Finish`. Réutiliser sans les modifier `EpreuveChoix.Argument/DossierDeLancement`, `Lot690.Jusqua/Attendre` et `Captures.Frappe`. Chaque attente est bornée à 30 s ; chaque lecture HTTP se fait hors du fil principal avec un client disposé et un délai de 5 s.

Entrée : `Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveTransition.Jouer -forgeEpreuve <rapport.json> [-logFile <journal>]`, sans `-quit` ni `-nographics`. Aucun siège, tick ou vitesse attendus ne sont transmis à la session.

1. Valider `-forgeEpreuve` (valeur présente, qui n'est pas une option), résoudre le chemin depuis le dossier de lancement et créer son dossier. Argument fautif : code 2, journal `EPREUVE_TRANSITION`, aucun rapport. Après validation, toute exception devient `defaut`, avec l'étape et la cause ; écrire les observations déjà recueillies, puis sortir avec 1. Une impossibilité d'écriture est annoncée au journal et rend 1.
2. Attendre une carte non vide et un cabinet dont `Partie` n'est pas occupée, avec `Monde` et `Maison` présents et une maison du joueur renseignée ; prendre son siège servi, sans constante Biskra/10103. Ne pas employer `Lot690.LecturePrete`, qui attend un monde sans joueur. Attendre `PassageALaCapitale.SiegeLu` renseigné. Une maison ou un siège absent interdit de fabriquer une destination. Le service contient déjà le Zab choisi : ne pas rejouer le choix. Mettre seulement le survol et le parcours en `automatique`, afin de jouer les clics explicitement.
3. Cadrer le siège servi dans la caméra de carte, comme #729 (`PositionSurLaCarte`, `Vue.Zoomer/Centrer`), obtenir son point écran, puis lire **une fois** `/horloge` dans `carte_avant`. Jouer deux `SurvolDeCarte.Cliquer(point)` dans la même image, comme #729. Conserver la transition créée avant que la carte disparaisse. Ne remplacer aucun `ChargerScene` : chargements réels, sans détour additif.
4. Attendre la fin de cette transition (référence détruite ou `!EnCours`) et une scène active portant un unique `DesertRoadTool` dont le plan est lu (`TickOuverture >= 0`). Relever sa cellule effective, puis lire **une fois** `/horloge` dans `ville_apres`. Attendre une seconde réelle et lire **une fois** dans `ville_avant` ; ne pas attendre un tick supplémentaire, ni une vitesse voulue.
5. Laisser `DesertRoadTool.automatique = false`. Créer `Captures.Frappe`, armer `Key.C`, laisser son `Update` injecter la pression, puis relâcher par une nouvelle frappe sans touche. Ne pas appeler `CommandesDeVille.Retour` à la place de C. Conserver la transition créée, attendre sa fin et une carte active non vide ; lire **une fois** `/horloge` dans `carte_apres`. Relâcher aussi le clavier lors d'un défaut.
6. Écrire le rapport JSON et une trace `EPREUVE_TRANSITION` nommant les quatre relevés et le défaut éventuel. Code 0 si les quatre lectures et l'aller-retour sont terminés, indépendamment des valeurs observées ; 1 si la session est impossible ; 2 si les arguments sont fautifs.

Contrat stable du rapport (`JsonUtility`, nombres jamais remplacés par des valeurs attendues) :
```csharp
[Serializable] public class Releve {
    public long tick = -1;
    public double jours_par_seconde = -1;
    public string scene = "";
}
[Serializable] public class Rapport {
    public long cellule = -1;
    public Releve carte_avant = new Releve(), ville_apres = new Releve(),
        ville_avant = new Releve(), carte_apres = new Releve();
    public string defaut = "";
}
```
`scene` est le nom actif à la lecture ; `tick` et `jours_par_seconde` viennent de `ClientHorloge.Lire`, jamais de `VitessePosee`, d'un panneau ou de la ressource. Une lecture manquée laisse ses nombres à −1 et nomme son absence dans `defaut` ; 0 reste une mesure. La cellule est celle de l'outil ouvert. La session ne compare ni les vitesses aux réglages, ni les ticks entre eux, ni la cellule au siège : une vitesse erronée ou une ville ouverte ailleurs est une observation, pas un défaut de session.

## Périmètre
docs/briefs/732-la-session-unity-de-l-epreuve-de-la-transition.md
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveTransition.cs
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveTransition.cs.meta
jeu/ville/README.md
docs/mesures/732-session-transition/rapport-marche.json
docs/mesures/732-session-transition/rapport-pause.json
docs/mesures/732-session-transition/controles.txt

Tout autre chemin est interdit. Budget, brief compris : environ 80 lignes de brief, 165 de code, 11 de `.meta` générée par Unity, 8 de notice, 12 pour les deux rapports et 9 de traces. Les JSON peuvent être compacts, sans retirer leurs champs.

## Conditions de succès
Depuis la racine sur le PC, PowerShell, éditeur fermé : `$u = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. La commande S est `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveTransition.Jouer -forgeEpreuve $rapport -logFile "$env:TEMP\lot732.log"`, sans `-quit` ni `-nographics`. Relever `$LASTEXITCODE` après chaque appel. Avant le code, S doit échouer car la méthode manque ; conserver cette trace rouge.

Préparation indépendante, service neuf pour chaque essai : depuis `jeu\`, `py -m sim.service --seed 0 --jours-par-seconde 0` (port 8000). Dans l'autre terminal, lire `/departs`, prendre la fiche au siège Biskra, puis POST `/intention` avec `{"type":"choisir_depart","seigneurie":<id servi>}` et POST `/tick?n=1`. Exiger le reçu accepté et la maison du joueur publiée dans `/monde`. Pour l'essai en marche seulement, POST `/vitesse?jours_par_seconde=<VITESSE_CARTE>` lue dans `Pont/Resources/ReglagesDesVues.json`. Ces opérations appartiennent à la préparation, jamais à la session. Arrêter le service après l'essai.

SC1 — **L'aller-retour réel produit quatre observations.** Préparation en marche, `$rapport = 'docs\mesures\732-session-transition\rapport-marche.json'`, puis S rend 0. Contrôle extérieur, qui peut échouer : `py -c 'import json,sys; r=json.load(open(sys.argv[1],encoding="utf-8")); v=json.load(open("3d/unity/Assets/ForgeLocal3D/Pont/Resources/ReglagesDesVues.json")); h=[r[k] for k in ("carte_avant","ville_apres","ville_avant","carte_apres")]; assert not r["defaut"] and r["cellule"]==10103; assert [x["jours_par_seconde"] for x in h]==[v["VITESSE_CARTE"],v["VITESSE_VILLE"],v["VITESSE_VILLE"],v["VITESSE_CARTE"]]; t=[x["tick"] for x in h]; assert min(t)>=1 and t==sorted(t) and t[-1]>t[0]; assert [x["scene"] for x in h]==["Forge_Carte","Forge_Desert_Ville_ksar_des_sept_puits","Forge_Desert_Ville_ksar_des_sept_puits","Forge_Carte"]' $rapport`. Aucune valeur exacte de tick n'est figée. Contre-épreuve : sur une copie temporaire du rapport, changer une vitesse ou retirer un relevé doit faire échouer ce contrôle. Ce contrôle de livraison n'est pas le futur verdict général de #410.

SC2 — **La pause est relevée sans réveil ni faux défaut.** Préparation sans le POST de vitesse, `$rapport = 'docs\mesures\732-session-transition\rapport-pause.json'`, puis S rend 0. Commande de contrôle : `py -c 'import json,sys; r=json.load(open(sys.argv[1],encoding="utf-8")); h=[r[k] for k in ("carte_avant","ville_apres","ville_avant","carte_apres")]; assert not r["defaut"] and r["cellule"]==10103; assert [x["tick"] for x in h]==[1]*4; assert [x["jours_par_seconde"] for x in h]==[0]*4; assert [x["scene"] for x in h]==["Forge_Carte","Forge_Desert_Ville_ksar_des_sept_puits","Forge_Desert_Ville_ksar_des_sept_puits","Forge_Carte"]' $rapport`. Contre-épreuve : une session qui exige une vitesse positive ou attend un jour en ville échoue ici ; une copie avec −1 à la place d'un 0 échoue au contrôle.

SC3 — **Une mauvaise vitesse reste une observation.** Localement seulement, dans `TransitionDeVue.Regler`, remplacer l'appel `client.Regler(v)` par `client.Lire()` : aucun réglage n'est alors envoyé, sans empêcher le chargement. Refaire la préparation en marche, puis S vers un rapport temporaire : sortie 0 et `defaut` vide, les quatre vitesses restent à la vitesse initiale de carte. Exécuter le contrôle SC1 sur ce rapport : il doit échouer. Restaurer immédiatement le fichier ; ni mutation ni rapport muté ne sont versés. Cette paire de commandes prouve que les valeurs sont lues et que la session ne juge pas. Contre-épreuve : une session qui fabrique la vitesse attendue fait passer SC1 malgré la mutation et refuse la livraison.

SC4 — **Une lecture impossible et un argument absent échouent clairement.** Service arrêté, S vers un chemin temporaire neuf rend 1, écrit un rapport avec `defaut` non vide nommant l'étape et la cause, et laisse à −1 les relevés non faits. Terminaison au plus 90 s après l'entrée en Play ; aucune attente infinie. Puis exécuter S sans `-forgeEpreuve`, et avec `-forgeEpreuve -logFile <journal>` : sortie 2 et aucun rapport neuf. Contrôle : `py -c 'import json,sys; r=json.load(open(sys.argv[1],encoding="utf-8")); assert r["defaut"] and r["carte_apres"]["tick"]==-1 and r["carte_apres"]["jours_par_seconde"]==-1' <rapport-sans-service>`. Contre-épreuve : servir à nouveau le monde préparé rend S verte ; un défaut transformé en quatre zéros fait échouer le contrôle.

SC5 — **Les preuves existantes restent intactes.** `& $u -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot732-pont.xml" -logFile "$env:TEMP\lot732-pont.log"` : sortie 0, XML présent sans échec, cas réellement exécutés, notamment `TransitionDeVueTests` et `PassageALaCapitaleTests`. Puis `py pc\epreuve_capitale.py --sortie "$env:TEMP\lot732-capitale"` rend 0. Contre-épreuve : XML absent, zéro cas ou ancien test assoupli refuse la livraison. Aucun test existant n'a à changer : les invariants de vitesse, pause, fondu et destination sont déjà portés par ces suites.

SC6 — **La livraison se rejoue et reste petite.** `git diff --check`, `git diff --name-only`, `git ls-files --others --exclude-standard` et `git diff --numstat` contrôlent le périmètre et moins de 300 lignes ajoutées et retirées, fichiers neufs compris. La notice donne la préparation, S, les quatre relevés et les codes 0/1/2. `controles.txt` conserve commandes, date, machine, révision, codes rouges puis verts, et distingue SC3 mutée des mesures réelles. Contre-épreuve : fichier hors périmètre, mutation résiduelle, faux relevé PC ou dépassement du budget refuse la livraison.

## Hors périmètre
Le verdict Python et son lanceur, le démarrage ou l'arrêt du service par Unity, le choix de terre, les règles de simulation, les réglages des vues, Espace et la preuve complète du jalon. Aucun changement aux scènes, aux commandes du joueur, aux transitions, au pont, aux tests existants ou aux captures #729/#730. Ne pas recopier ces captures ni transformer leurs substitutions de chargement en chemin de l'épreuve.

## Photo
Sans objet : outil d'épreuve uniquement, sans changement de ce qu'on voit à l'écran. Les gestes et leur apparence sont déjà livrés et photographiés par #729 et #730 ; ce lot ajoute leur rapport de session, pas une présentation nouvelle. Aucun scénario `Captures/Lot732.cs` à créer.
