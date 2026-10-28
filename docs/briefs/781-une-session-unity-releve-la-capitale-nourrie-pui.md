# Lot #781 — Une session Unity relève la capitale nourrie puis affamée
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Une session Unity montre et relève la même place de Biskra nourrie puis affamée, avec des fumées, lumières et étals pilotés par les publications réelles du monde.

## Le joueur
Le joueur qui entre dans sa capitale voit ses maisons habitées fumer et s'éclairer le soir, et ses étals alimentaires se vider quand le bourg manque de vivres ; il sent que sa ville dépend de ses habitants et de son ravitaillement. Ce lot prépare la preuve de J4 et son arbitrage entre une route vers les champs et d'autres chantiers : la comparaison de la même place rend le manque visible. La demande fournie n'a pas de phrase « Le joueur » distincte ; celle-ci en explicite le bénéfice selon `CAP.md`. Le retrait alimentaire est un montage d'épreuve déclaré, pas une conséquence économique attribuée à un chantier.

## Règle du monde
Sans objet : session de vue et d'épreuve, sans nouvelle règle du monde. Elle lit les règles existantes de niveau 2 de `jeu/sim/MODELE.md`, « Le panier de marchandises » → « Absence contre zéro », « Ce que veut dire « affamée » », « Les lieux d'une cellule, vue dérivée » → « Ce que porte un lieu » et le montage jetable décrit avant « L'identité d'un lieu, et ce qui la change ». Dépend de : #777, #779, #780 ; les lecteurs #778 arrivent par ces composants.

Créer `EpreuveVieDuBourg.cs`, session commune aux deux scénarios de `Lot781.cs`. Réutiliser `Capture.Photographier` et son service possédé : ajouter seulement le drapeau explicite `-forgeServiceEpreuve`, qui ajoute `--epreuve` au lancement Python. Sans ce drapeau, comportement ordinaire inchangé. Le lot tourne graine 0, zéro tick, horloge arrêtée ; ne pas dupliquer le lancement, la surveillance ou l'arrêt du service. Les lectures et le POST ont un délai borné et s'exécutent hors du fil Unity ; seul le montage et le relevé des objets reviennent sur ce fil.

Trouver l'unique départ au siège nommé Biskra par `ClientDeparts`, dériver son `CellId`, ouvrir sa ville par `DesertRoadTool.Ouvrir` et son panneau de lieu. Lire réellement plan, bourg et occupation par les clients existants ; refuser absences, population nulle, base vide ou cellules/ticks discordants. L'état initial doit porter nourriture strictement positive et faim locale nulle. Ne fabriquer aucun `BourgLu`, aucune occupation ni aucun stock de remplacement.

Configurer `EffetsDeMaison` sur les maisons de base effectivement dessinées, associées sans ambiguïté aux couples rang/indice de `MaisonsDeLaBase.Poser` ; ne pas instancier des maisons témoins. Leur ajouter des particules et lampes avec les ressources existantes, comme #779. Monter sur la place servie au plan un comptoir alimentaire temporaire dont les denrées sont des enfants séparés, piloté par `EtalDuBourg`, comme #780 ; primitives et matériaux existants suffisent. La référence visuelle est le stock alimentaire initial lu, conservé aux deux passages. Aucun souk au maillage déjà garni ne sert de comptoir vide. Ces objets et effets restent propres à la session ; aucun branchement permanent ni asset enregistré.

Appliquer les trois lectures avec la même heure de présentation, 19.6 h, puis laisser les particules se former et relever les objets. Photographier cet état, ensuite appeler une seule fois `POST /epreuve/vider-panier?cell=X`, exiger HTTP 200 et cellule/tick concordants, puis relire les trois routes et réappliquer les composants aux mêmes objets. #777 republie sans avancer le tick : relire même si son numéro est identique. Le second bourg doit servir nourriture présente à zéro et faim strictement positive. Ne pas appeler `/tick`, `/vitesse`, déposer d'intention ou affecter une faim dans Unity. Les maisons restent habitées : la fumée disparaît, leurs lumières gardent leur intensité du soir.

Écrire `vie-bourg.json` dans le dossier de `-forgeCaptures`, avec `cellule`, `port`, `contre_epreuve`, `defaut` et exactement deux `etats`, nommés `nourrie` et `affamee`. Chaque état porte `tick`, `tick_local`, `heure`, `population`, `nourriture_kg`, `faim_ticks`, la matrice `camera` et des listes non vides : `maisons` avec `rang`, `indice`, `emission`, nombre réel `particules`, `lampe_active` et `intensite` ; `etals` avec `marchandise`, référence en kg, hauteur réelle et `visible`, visibilité effective des rendus de garniture. Ajouter `garnitures_visibles`, nombre mesuré des garnitures alimentaires rendues, et les causes des composants. Compter en parcourant les objets de la session, jamais d'après les listes attendues ou `EtalDuBourg.Rapport` seul. Une valeur non calculée reste −1 ; aucune liste vide ne vaut preuve. Écrire aussi le défaut nommé si la session est interrompue ; les fichiers partiels ne sont pas des succès.

Le drapeau `-forgeGarderEtalPlein` conserve après le POST la garniture alimentaire issue du premier passage, en sautant uniquement sa seconde application ; toutes les lectures, les fumées et les lampes suivent normalement le second état. Ne falsifier ni le rapport ni le service. La session relève cette anomalie et termine normalement : le contrôle indépendant ci-dessous doit la rejeter. Les défauts de lecture, montage ou capture, eux, font échouer Unity. Le verdict complet de #420 et son lanceur Python restent pour la suite.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveVieDuBourg.cs
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveVieDuBourg.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot781.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot781.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/ForgeCapture.cs
docs/briefs/781-une-session-unity-releve-la-capitale-nourrie-pui.md

## Conditions de succès
Depuis la racine sur le PC Windows, éditeur fermé, définir ces commandes PowerShell ; attendre chaque lancement jusqu'à sa fin, avec rendu, sans `-quit` ni `-nographics` :
```powershell
$unity = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'
$normal = Join-Path $env:TEMP ('lot781-normal-' + [guid]::NewGuid())
$contre = Join-Path $env:TEMP ('lot781-contre-' + [guid]::NewGuid())
$commun = @('-batchmode','-projectPath','3d/unity','-executeMethod','ForgeLocal3D.Capture.Photographier','-forgeLot','781','-forgeSeed','0','-forgeTicks','0','-forgeServiceEpreuve')
```
`NORMAL` : `& $unity @commun -forgeCaptures $normal -logFile "$normal.log"`.
`CONTRE` : `& $unity @commun -forgeGarderEtalPlein -forgeCaptures $contre -logFile "$contre.log"`.
Les deux dossiers sont neufs. `CONTROLE` désigne `py -3 -c $controle $dossier`, avec `$dossier` égal au dossier à examiner et le code indépendant suivant :
```powershell
$controle = @'
import json,sys
from pathlib import Path
r=json.loads((Path(sys.argv[1])/'vie-bourg.json').read_text(encoding='utf-8-sig')); a,b=r['etats']
assert not r['defaut'] and a['nom']=='nourrie' and b['nom']=='affamee'
assert a['maisons'] and b['maisons'] and a['etals'] and b['etals']
assert a['camera']==b['camera'] and a['heure']==b['heure']==19.6 and a['population']==b['population']>0
assert a['tick']==a['tick_local']==b['tick']==b['tick_local']>=0
ids=lambda e:[(m['rang'],m['indice']) for m in e['maisons']]
assert ids(a)==ids(b) and len(set(ids(a)))==len(ids(a))
assert all(m['emission'] and m['particules']>0 and m['lampe_active'] and m['intensite']>0 for m in a['maisons'])
assert all(not n['emission'] and n['particules']==0 and n['lampe_active'] and n['intensite']==m['intensite'] for m,n in zip(a['maisons'],b['maisons']))
assert a['nourriture_kg']>0 and a['faim_ticks']==0 and a['garnitures_visibles']>0
assert b['nourriture_kg']==0 and b['faim_ticks']>0 and b['garnitures_visibles']==0 and all(not e['visible'] for e in b['etals'] if e['marchandise']=='nourriture')
'@
```

SC1 — **Le service atteint les objets.** Commandes : `NORMAL`, puis `CONTROLE` avec `$dossier=$normal`, toutes deux de sortie 0. Constater le rouge de ce contrôle avant le branchement, puis son vert. Vérifier dans le rapport les identités des maisons inchangées, leur émission et leurs particules positives avant, nulles après, leurs lampes actives d'intensité identique, les causes sans refus, la garniture réellement pleine puis invisible, et les comptoirs conservés. Contre-épreuves : application oubliée, lecture du seul panier cellulaire, référence manquante ou tableau vide interdisent la réussite ; supprimer le service ou son activation doit donner une erreur nommée, jamais un bourg inventé.

SC2 — **L'étal mensonger se voit dans la mesure.** Commandes : `CONTRE` de sortie 0, puis le même `CONTROLE` avec `$dossier=$contre`, attendu non nul sur le dernier contrôle. Le second rapport porte toujours nourriture zéro et faim positive, mais `garnitures_visibles > 0`, une hauteur alimentaire positive et le drapeau déclaré ; les deux captures existent. Contre-épreuves : forcer ce compteur à zéro ou simplement recopier l'attendu détruit la preuve et refuse le lot ; une session qui échoue avant d'avoir photographié et relevé l'anomalie ne prouve rien.

SC3 — **La même place permet la comparaison.** Commande : `NORMAL`. Exiger deux PNG de scénarios neufs et leurs traces `CAPTURE_SCENARIO_OK`, avec exactement les mêmes matrice, heure, population et tick entre relevés ; le tick local concorde à chaque passage. Au moins une maison avec son toit, sa fumée puis son absence, sa lampe et le comptoir doivent être dans le champ et sans obstacle. Ouvrir soi-même les deux images. Contre-épreuves : cadrage changé, comptoir masqué par l'auvent, fumée hors champ, images illisibles ou seconde image prise avant le POST refusent la photo même si les chiffres passent.

SC4 — **Les acquis et le budget tiennent.** Commandes : `& $unity -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot781-tests.xml" -logFile "$env:TEMP\lot781-tests.log"`, puis `py -3 -m pytest jeu/ville/tests/test_epreuve_jalon1.py -q`, `git diff --check`, `git diff --name-only`, `git diff --numstat` et `git ls-files --others --exclude-standard`. Exiger XML neuf non vide sans échec, et tous les tests existants inchangés, notamment `ClientLieuTests`, `KitDesBatimentsTests`, `EtalDuBourgTests` et le port du lanceur de capture. Budget : environ 172 lignes de session, 12 de scénarios, 8 de lanceur, 4 de métadonnées et 74 de brief ; compter ajouts et suppressions, fichiers neufs compris, strictement moins de 300. Contre-épreuves : test assoupli, ancien test rouge, autre chemin modifié ou total ≥ 300 refuse la livraison.

## Hors périmètre
Tout autre chemin est interdit. Aucun changement de simulation, service, contrat, lecteur, composant #779/#780, test existant, plan, occupation, consommation ou horloge. Pas de famine naturelle provoquée par des chantiers, de nouveau geste de jeu, de branchement permanent de toute la capitale, de passant, d'optimisation ou de verdict Python complet. Aucun prefab, scène, matériau, maillage, image ou rapport enregistré dans git ; les objets de démonstration sont jetables.

## Photo
`Lot781.cs` expose deux méthodes `static IEnumerator ...(Camera camera)` avec `[ScenarioDeCapture(781, "01-place-nourrie")]` et `[ScenarioDeCapture(781, "02-place-affamee")]`, qui déroulent la session commune sans recopier son montage. Le premier scénario ouvre Biskra et montre ses vraies maisons autour de la place, leurs fumées et lampes, ainsi que le comptoir temporaire garni sur cette place. Le second joue le retrait de #777 et montre exactement le même endroit : denrées disparues, fumées arrêtées et effacées, lampes conservées. Positionner le comptoir près du bord de place faisant face à une maison, dans l'emprise libre du plan ; cadrer par `DesertCityCamera.Poser` pour lire simultanément denrées, façade et toit. Garder la caméra et l'heure à 19.6 h ; régler une fumée et un éclairage lisibles à cette heure avec les ressources existantes. Le scénario vérifie les objets dans le champ avant chaque photo. Les effets décoratifs sans lien au monde ne sont pas des témoins. Avec le drapeau de contre-épreuve, la seconde image doit montrer l'étal alimentaire encore garni au milieu des fumées éteintes ; l'examiner aussi. Captures, journaux et rapport restent dans les dossiers temporaires des commandes.
