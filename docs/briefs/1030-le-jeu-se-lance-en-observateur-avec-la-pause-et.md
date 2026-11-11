# Lot #1030 — Le jeu se lance en observateur, avec la pause et cinq vitesses
Jalon : J5 · Machine : pc · Taille prévue : 650 lignes

## But
Le joueur regarde le monde de 1400 vivre sans prendre de pays. Le bandeau de la carte lui donne la pause et cinq vitesses, de 0,5 à 10 jours par seconde ; la plus rapide est bornée par le budget du tick. Il prend un pays quand il veut, même après des semaines de monde.

## Le joueur
Il ouvre la carte sans choisir de pays. « Votre maison » le lui dit : « Vous observez le monde, sans maison. Prenez-en une quand vous voulez. » Le monde attend, en pause. Il appuie sur « Accélérer » : le temps part à un demi-jour par seconde. Il appuie encore, et dans le bandeau cinq marques s'allument une à une, de la plus basse à la plus haute, jusqu'à 10 jours par seconde. Un appui de plus ne va pas au-delà. « Ralentir » éteint une marque. Les maisons de l'IA prélèvent, ouvrent leurs greniers et bâtissent sans lui. Il met en pause : les marques s'éteignent, la date dit « En pause » et ne bouge plus.

Au bout d'un mois et demi de monde, il clique la Morée, puis « Choisir cette maison », et relance le temps : le pays est à lui au jour suivant.

C'est le geste du jalon 5 : « il lance la partie sans prendre de pays, met en pause, choisit l'une des cinq vitesses et laisse filer les années ». C'est aussi sa décision : « quel pays prendre, et quand y entrer, après l'avoir vu vivre ».

## Règle du monde
Sans objet : c'est un lot de vue et d'horloge. Rien de `jeu/sim/` ne change. Un tick reste un jour (`jeu/sim/MODELE.md`, « La base de temps »). La vitesse en jours par seconde est celle de l'horloge du service, hors du modèle.

Le monde permet déjà l'observateur ; le lot le rend jouable et le prouve :
- **Sans maison du joueur, le service joue toutes les maisons.** `ia.py` n'écarte que la maison du joueur (« ou celle qu'il vient de choisir »).
- **Un pays se prend à tout jour.** `intentions.choisir_depart` ne refuse un départ que s'il est déjà choisi : rien ne le borne au jour 1. `/departs` sert les fiches du jour courant. Le choix s'applique au tick suivant, comme aujourd'hui.

**La borne de la vitesse la plus rapide.** Le service déclare `BUDGET_TICK_MS = 100` (`jeu/sim/service.py`) et le sert dans `/horloge` (`budget_tick_ms`). Le tick avec IA, mesuré sur le PC le 7 novembre 2026 (`docs/mesures/2026-11-07-refonte/RAPPORT.md`, sections 6 et 7), vaut 67 ms de médiane : il tient dans ce budget. La vitesse la plus rapide vaut donc `1000 / BUDGET_TICK_MS = 10` jours par seconde : un jour toutes les 100 ms, au-dessus des 67 ms du tick.

Le palier d'aujourd'hui, 20 jours par seconde, demande un jour toutes les 50 ms. Un tick de 67 ms ne le tient pas : le service prend du retard, et la vitesse affichée ment. Il disparaît.

**Les cinq paliers** : 0,5 ; 1 ; 2 ; 5 ; 10. Les tests d'aujourd'hui restent verts sans changer :
- `Les_paliers_montent_et_descendent_sans_jamais_mettre_en_pause` est générique sur `PALIERS`. Il exige aussi `Suivante(2.5, +1) == 5` et `Suivante(2.5, -1) == 2` ;
- `Pause_reprise_et_paliers_partent_au_service` passe de 2,5 à 5, puis à 2, puis à 1.

**La vitesse de la carte, 6 jours par seconde.** Elle n'est pas un palier. C'est la vitesse de la première reprise depuis la pause d'ouverture (#860, `ReglagesDesVues.json`), et le test du lanceur la borne entre 5,2 et 7,3. Elle ne change pas. À 6, quatre marques s'allument : une marque par palier atteint. « Accélérer » mène à 10, « Ralentir » à 5.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/HorlogeDeCarte.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/HorlogeDeCarteTests.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1030.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1030.cs.meta
docs/briefs/1030-le-jeu-se-lance-en-observateur-avec-la-pause-et.md

Tout autre chemin est interdit, en particulier :
- tout `jeu/sim/` (`service.py`, `ia.py`, `intentions.py`) et `pc/jouer.py` ;
- `ReglagesDesVues.json`, `TransitionDeVue.cs`, `CommandesDuTemps.cs`, `CommandesDeVille.cs`, `LecturePartie.cs`, `SocleInterface.cs`, `BarreDuPays.cs` ;
- les scénarios existants, dont `Lot525`, `Lot549`, `Lot690`, `Lot730`, `Lot860`, `Lot883`, `Lot1004`, `Lot1045`.

Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master 06412e0f, où #860 est livré (#1055).

### `HorlogeDeCarte.cs`
- `PALIERS = { 0.5, 1, 2, 5, 10 }`. Le commentaire dit la borne : le dernier vaut `1000 / BUDGET_TICK_MS` du service (100 ms), que le tick avec IA mesuré à 67 ms le 7 novembre 2026 tient.
- `public static int Rang(double joursParSeconde)` rend le nombre de paliers inférieurs ou égaux à la vitesse, à 1e-9 près : 0 en pause, 1 à 0,5, 3 à 2,5, 4 à 6, 5 à 10 et au-delà.
- `Suivante`, `Basculer`, `Decrire` et la reprise de #860 ne changent pas.
- Le commentaire de tête ajoute : « Lot #1030 : cinq paliers, le plus rapide borné par le budget du tick. »

### `HorlogeDeCarteTests.cs`
Les tests existants restent tels quels. Deux cas neufs :
- **`Cinq_paliers_et_le_plus_rapide_tient_dans_le_budget_du_tick`**. Il exige :
  - `PALIERS.Length == 5`, strictement croissants, le premier > 0 ;
  - `1000 / PALIERS[4] >= budget`, où `budget` est lu dans `../../jeu/sim/service.py` (le répertoire courant des tests est `3d/unity`, comme `CabinetDeCarteTests` qui lit `Assets/Interface/CabinetDeCarte.cs`), par l'expression régulière `^BUDGET_TICK_MS = (\d+)$` en multiligne. Une ligne absente fait échouer le test ;
  - `PALIERS[4] == 1000.0 / budget`, à 1e-9 près : la plus rapide est à la borne, pas en dessous.
- **`Le_rang_compte_les_paliers_atteints`** : `Rang(0) == 0`, `Rang(0.5) == 1`, `Rang(1) == 2`, `Rang(2.5) == 3`, `Rang(ReglagesDesVues.Charger().VitesseCarte) == 4` (la carte à 6), `Rang(10) == 5`, `Rang(20) == 5`.

### `CabinetDeCarte.cs`
**Les constantes** :
- `VITESSES = "Vitesses"`, le nom du conteneur des marques ;
- `MARQUE = "Vitesse "`, le préfixe du nom de chaque marque (`Vitesse 1` à `Vitesse 5`) ;
- `OBSERVER = "Vous observez le monde, sans maison.\nPrenez-en une quand vous voulez."`.

**Les cinq marques.** Dans `Construire`, juste après `date`, un conteneur `VITESSES`, enfant direct du bandeau :
- ancré en haut à gauche comme `DOSSIERS`, en (968, -24), de 112 × 40. Il finit en x 1080, avant les dossiers (x 1112), et en y 64, au-dessus du filet ;
- cinq `Image` enfants, nommées `Vitesse 1` à `Vitesse 5`, de 16 px de large, à 24 px d'intervalle (x 0, 24, 48, 72, 96 dans le conteneur), posées sur son bas ;
- leurs hauteurs : 8, 16, 24, 32, 40 ;
- `raycastTarget = false`, sans `Button` : le bandeau garde ses trois boutons du temps enfants directs.

Dans `Afficher` :
- le conteneur est actif si et seulement si `horloge.Lue != null && horloge.Absence == null` ;
- la marque `i` (de 1 à 5) prend `SocleInterface.Couleur("or")` si `i <= HorlogeDeCarte.Rang(horloge.Lue.JoursParSeconde)`, sinon `SocleInterface.Couleur("secondaire")`.

La date, ses 600 px et `Decrire` ne changent pas. La date ne dépasse jamais x 968 : sa plus longue phrase servie fait moins de 488 px (cas neuf ci-dessous). Le message « Date indisponible… » peut aller plus loin, mais alors les marques sont éteintes.

**L'observateur dans « Votre maison ».** Dans `AfficherMaison`, sans maison du joueur, `maison.text` vaut `OBSERVER` au lieu de « Choisissez votre maison.\nLe choix sera appliqué par le monde. ». Aucun test ne figeait l'ancienne phrase. Le reste de la proposition (boutons des maisons, aperçu, « Choisir cette maison ») ne change pas.

**Ce qui ne change pas** : la barre (« Aucune maison choisie » sans maison, figée par les tests de #1001) et la ligne du prochain geste. `Guide` rend toujours `CHOISIR` sans maison, « même si le temps file » : les tests de #860 le figent, et la phrase reste vraie pour l'observateur.

### `CabinetDeCarteTests.cs`
Les cas existants restent tels quels. Trois cas neufs :
- **`Les_cinq_marques_suivent_la_vitesse_servie`**. Une horloge témoin sert successivement 0 ; 0,5 ; 2,5 ; 6 ; 10. À chaque fois, le cas appelle `cabinet.Afficher()` et exige :
  - le conteneur `Vitesses` actif, avec exactement cinq `Image` nommées `Vitesse 1` à `Vitesse 5` ;
  - les `Rang(v)` premières en `or`, les autres en `secondaire` : 0, 1, 3, 4, 5 allumées.

  Sans horloge lue, ou avec une absence, le conteneur est inactif.
- **`Les_marques_tiennent_dans_le_bandeau_sans_rien_recouvrir`**. Le cas exige :
  - le rectangle monde du conteneur dans celui du bandeau, et son bas à 70 au plus du haut de la toile, comme les icônes dans `Aucun_dossier_ne_recouvre_la_barre` ;
  - il ne recouvre ni le conteneur `DOSSIERS`, ni l'icône du pays, ni la barre des comptes, ni `Ralentir`, `Pause / Reprendre`, `Accélérer`, `Menu` ;
  - pour `Decrire` à 0 ; 0,5 ; 1 ; 10 jours par seconde, au jour 365 de 1400, `date.preferredWidth <= 488` : la date finit avant les marques.
- **`Sans_maison_le_dossier_dit_l_observateur`**. Après `Proposer()`, le texte du dossier vaut `OBSERVER`, passe `TexteDuMonde.Interdit`, et son `preferredWidth` tient dans 536. Avec une maison publiée, il dit la maison comme avant.

### `Lot1030.cs`
`static class Lot1030`, dans le style de `Lot860` : trois scénarios joués dans l'ordre de leur nom, sur le même service, avec un état partagé par champs statiques. La première faute lève une `InvalidOperationException` qui la nomme.

Les constantes :
- `FUITE = "-forge1030Fuite"`, `SIEGE = "Mistra"`, `TERRE = "Despotat de Morée"`, `RAPPORT = "lot1030-observateur.json"` ;
- `MESURE_S = 5`, `TENUE = 0.8` : à 10 jours par seconde, au moins 40 jours en 5 s.

Le scénario écrit lui-même ses phrases attendues et ses paliers, en littéraux `{ 0.5, 1, 2, 5, 10 }`. Il ne lit ni `HorlogeDeCarte.PALIERS`, ni `Rang`, ni `CabinetDeCarte.OBSERVER`. Le service se lit à part, par `ClientHorloge` hors du fil principal (comme `Servie` dans `Lot860`). Les boutons du bandeau se pressent par `onClick.Invoke()`. Les petites fonctions privées de `Lot860` dont il a besoin sont recopiées ici, sans toucher `Lot860`. `Lot690.PousserTick`, `Lot690.Jusqua` et `Lot690.Attendre` (internes) servent tels quels.

1. **`observateur-1-cinq-vitesses`.**
   - Il ouvre la carte exactement comme l'étape 1 de `Lot860` : `Lot549.Ouvrir`, survol et parcours en `automatique`, `Lot690.LecturePrete`, horloge lue, toile en `ScreenSpaceCamera` sur la caméra photographiée.
   - Il juge l'ouverture en observateur :
     - tick lu 0 (`-forgeTicks 0`), monde en pause, aucune maison du joueur (`MaisonDuJoueur == null`) ;
     - la barre dit `Aucune maison choisie`, et le dossier `Vous observez le monde, sans maison.\nPrenez-en une quand vous voulez.` ;
     - le conteneur `Vitesses` est actif, ses cinq marques éteintes (`secondaire`).
   - Il presse `Accélérer` cinq fois. Après chaque appui, il attend que le service serve le palier attendu (0,5, puis 1, 2, 5, 10, à 1e-6 près), et que `horloge.Lue` le serve aussi. Il juge alors :
     - les `k` premières marques en `or`, les autres en `secondaire` (k = 1 à 5) ;
     - la date du bandeau égale à `HorlogeDeCarte.Decrire(horloge.Lue)`.

     Sinon : `après k appuis, le service sert V, attendu W`.
   - Un sixième appui : 2 s plus tard, le service sert toujours 10, et cinq marques sont allumées. Sinon : `au-delà de la plus rapide : V`.
   - `Ralentir` : 5 servi, quatre marques. `Accélérer` : 10, cinq marques.
   - **La tenue.** Il laisse 2 s s'écouler, note le tick servi `T0`, attend `MESURE_S` secondes de temps réel, note `T1`. Il exige `T1 - T0 >= TENUE × 10 × MESURE_S` (40). Sinon : `à 10 jours par seconde, T1 - T0 jours en 5 s : le tick ne tient pas la vitesse`.
   - Toujours aucune maison du joueur : le monde a vécu seul.
   - Il laisse passer 10 images. L'image est prise en marche, à 10 jours par seconde.
2. **`observateur-2-pause`.**
   - Il presse `Pause / Reprendre` et attend que le service serve 0. Il note le tick servi `T`, puis attend que `horloge.Lue.Tick == T` et que `Partie.Monde.Donnees.Monde.Tick == T`. Il exige `T >= 40`.
   - Avec `-forge1030Fuite`, il pousse ici un tick par `Lot690.PousserTick` : c'est une pause qui laisserait filer un jour.
   - **La pause tient.** Pendant 3 s de temps réel, relu toutes les 0,25 s :
     - le tick servi reste `T`. Sinon : `en pause, le tick du service passe de T à T'` ;
     - `horloge.Lue.Tick` reste `T`, et la date finit par `En pause` ;
     - le bouton dit `Reprendre`, et les cinq marques sont éteintes.
   - **Le même tick.** À la fin, il relit une dernière fois le service : tick servi, tick de l'horloge et tick du monde lu valent tous trois `T`.
   - Il écrit `RAPPORT` dans `Capture.DossierDesCaptures`, par `JsonUtility` et en UTF-8 sans BOM, comme `Lot1031`. Les champs : `tick_service`, `tick_horloge`, `tick_monde`, `jours_avances` (`T`), `jours_mesures` (`T1 - T0`), `secondes_mesurees` (5), `vitesse_la_plus_rapide` (10), `budget_tick_ms` (lu dans `/horloge`), `maison_du_joueur` (vide).
   - Il laisse passer 10 images : l'image montre le monde au tick `T`, celui du rapport.
3. **`observateur-3-prendre-un-pays`.**
   - Toujours en pause, au jour `T + 1`, il clique la terre de la Morée comme l'étape 2 de `Lot860` : fiche au siège `Mistra`, point d'écran de sa cellule, `cabinet.Noter` (appui, relâché). Il juge l'aperçu `Despotat de Morée · Mistra`, puis presse « Choisir cette maison ». Il attend `Partie.Recu` accepté.
   - Il presse `Pause / Reprendre`. Le service doit servir 10 : le monde a été vu en marche à 10, et la reprise de #860 rend sa vitesse.
   - Il attend que la maison du joueur soit posée et que `Partie.Maison` dise le siège `Mistra`. Il exige :
     - un tick du monde lu > `T` ;
     - la barre ne dit plus `Aucune maison choisie` ;
     - le dossier ne dit plus le texte de l'observateur.
   - Il presse `Pause / Reprendre` et attend 0 servi.
   - Il laisse passer 10 images.

Chaque scénario écrit une trace `CAPTURE_1030 <nom> tick T, vitesse V, marques allumées K, maison « <nom ou aucune> »`.

## Conditions de succès
On lance depuis la racine. Sur le PC, éditeur fermé, en PowerShell, `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Deux commandes de tests :
- `P` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot1030-pont.xml -logFile 3d/unity/Temp/lot1030-pont.log` ;
- `I` = la même avec `-assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot1030-interface.xml -logFile 3d/unity/Temp/lot1030-interface.log`.

Chacune sort 0, sans échec ni cas ignoré, et ses cas neufs réussissent.

**SC1 — Cinq paliers, le plus rapide à la borne du budget du tick.** `P` passe, avec `Cinq_paliers_et_le_plus_rapide_tient_dans_le_budget_du_tick` et `Le_rang_compte_les_paliers_atteints`. Tous les cas existants de `HorlogeDeCarteTests` passent sans changer. Contre-épreuves, chacune défaite avant le commit :
- remettre le palier 20 à la fin de `PALIERS` fait échouer `Cinq_paliers…` (six paliers, 50 ms sous le budget de 100) ;
- remplacer 10 par 8 le fait échouer aussi : la plus rapide n'est plus à la borne.

**SC2 — Le bandeau porte les cinq marques, et « Votre maison » dit l'observateur.** `I` passe, avec les trois cas neufs. Tous les cas existants de `CabinetDeCarteTests` passent sans changer, dont `Aucun_dossier_ne_recouvre_la_barre`, les cas du `Guide` de #860 et ceux de la barre de #1001. Contre-épreuves :
- allumer les marques par `i < Rang(v)` au lieu de `i <= Rang(v)` fait échouer `Les_cinq_marques_suivent_la_vitesse_servie` ;
- poser le conteneur en x 1100 fait échouer `Les_marques_tiennent_dans_le_bandeau…` : il recouvre les dossiers.

**SC3 — Une session en observateur avance, se met en pause au même tick que le service, et prend un pays en cours de partie.** La commande `PHOTO` de la section Photo sort 0, avec trois images et `lot1030-observateur.json`. Le rapport dit `tick_service == tick_horloge == tick_monde == jours_avances >= 40`, et `jours_mesures >= 40`. Contre-épreuve : la commande `FUITE` (une pause qui laisse filer un tick) sort 1 après la première image. Son journal dit `en pause, le tick du service passe de T à T+1`, et elle n'écrit pas de rapport.

**SC4 — Rien d'autre ne bouge.** `git diff --name-only master` ne liste que des chemins du Périmètre. `cd jeu && python3 -m pytest ville/tests/test_lanceur_jouer.py -q` passe sans changer : la vitesse de la carte (6) et la pause d'ouverture de #860 tiennent.

## Hors périmètre
- Aucune règle du monde, aucun fichier de `jeu/sim/`. Le service ne borne pas lui-même la vitesse demandée : seul le bandeau la borne. Un `POST /vitesse` à 20 reste accepté, comme aujourd'hui.
- La vitesse de la carte à l'ouverture (6 jours par seconde) et celle de la ville (0,1) : elles restent dans `ReglagesDesVues.json`.
- La ligne du prochain geste et la barre des comptes : leurs phrases sont figées par les tests de #860 et de #1001.
- Les marques ne sont pas cliquables : on change de vitesse par « Ralentir », « Accélérer », + et −.
- Les vitesses de la ville (`CommandesDeVille`).
- Les voisins et leurs gestes à l'écran (#429), le fil des nouvelles (#1028), le siècle sans joueur au journal (#324, mode direct).

## Photo
Trois images de la carte de 1400 et de son cabinet entier, sur un service avec l'IA (`-forgeServiceIa`), parti du jour 1 de 1400 (`-forgeTicks 0`).

1. **L'observateur à la vitesse la plus rapide** (la photo du lot) :
   - la carte qui tourne seule ;
   - dans le bandeau, la date `… 10 jours par seconde`, le bouton `Pause`, et les cinq marques allumées en or, de la plus basse à la plus haute ;
   - la barre qui dit `Aucune maison choisie`, et « Votre maison » : `Vous observez le monde, sans maison. Prenez-en une quand vous voulez.` ;
   - les six terres de départ en or : on peut en prendre une.
2. **La pause** : au jour `T + 1` (au moins le 41ᵉ jour), la date `… En pause`, le bouton `Reprendre`, les cinq marques éteintes. Le tick est celui que le service dit dans `lot1030-observateur.json`.
3. **Le pays pris en cours de partie** : la Morée gardée, la maison des Paléologue dans la barre et dans « Votre maison », plus aucune terre en or, le monde de nouveau en pause.

Le scénario `Lot1030.cs` (Périmètre) joue ces étapes ; la chaîne écrit chaque image à la fin de son scénario. La caméra est celle de la carte entière, posée par `Lot549.Photographier`, avec la toile du cabinet sur elle, comme `Lot860`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1030 -forgeTicks 0 -forgeServiceIa -forgeCaptures 3d/unity/Temp/lot1030-photo -logFile 3d/unity/Temp/lot1030-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1030 -forgeTicks 0 -forgeServiceIa -forge1030Fuite -forgeCaptures 3d/unity/Temp/lot1030-fuite -logFile 3d/unity/Temp/lot1030-fuite.log
```

Les deux sessions :
- **`PHOTO`**, la première, donne la photo. Elle sort 0 avec ses trois images et `3d/unity/Temp/lot1030-photo/lot1030-observateur.json` ;
- **`FUITE`** est la contre-épreuve de la pause : un tick poussé pendant la pause. Elle sort 1 après la première image, sans rapport.

Leurs journaux et le rapport `.json` sont joints au compte rendu. Les PNG restent hors du dépôt.
