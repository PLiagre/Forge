# Lot #860 — Le jeu s'ouvre en pause et dit quoi faire
Jalon : J5 · Machine : pc · Taille prévue : 700 lignes

## But
Le jeu s'ouvre sur un monde en pause, en ville comme sur la carte. Sans maison, les six terres de départ s'éclairent sur la carte, et un clic sur l'une la propose dans « Votre maison ». Une ligne de la barre dit le prochain geste, et Espace lance le temps à la vitesse de la vue.

## Le joueur
Il ouvre le jeu : le monde attend, au jour 1 de 1400, et le bouton du temps dit « Reprendre ». Sur la carte, les six terres de départ conseillées s'éclairent en or. En haut, à droite de la barre, une ligne lui dit : « Choisissez votre maison : cliquez une terre en surbrillance ». Il clique la Morée : elle passe au rouge de la terre gardée, et « Votre maison » la lui propose (« Despotat de Morée · Mistra », ses habitants, son suzerain). Il confirme par « Choisir cette maison ». La ligne dit alors : « Espace : lancer le temps ; le monde applique votre choix au jour suivant ».

Il appuie sur Espace : le temps file à la vitesse de la carte (6 jours par seconde). La maison est la sienne, les terres cessent de s'éclairer, la ligne se tait. S'il remet en pause, elle lui redit : « Espace : lancer le temps ». Au Zab, le seul pays qui a sa ville, elle ajoute : « · double-clic sur votre siège : entrer dans votre ville ».

Il ne découvre plus le jeu en courant après lui : il choisit sur la carte, comme dans Europa Universalis IV, puis décide quand le monde repart. C'est la décision du jalon 5 : « quel pays prendre, et quand y entrer ». Le lot prépare aussi l'observateur et ses cinq vitesses (#1030), qui l'attend.

## Règle du monde
Sans objet : c'est un lot de vue et de lanceur. Aucun nombre du monde ne change, et rien de `jeu/sim/` n'est touché. Un tick reste un jour (`jeu/sim/MODELE.md`, « La base de temps »). La vitesse en jours par seconde est celle de l'horloge du service, hors du modèle. Le choix de la maison passe par l'intention `choisir_depart` qui existe déjà. Le monde l'applique au tick suivant, comme aujourd'hui.

**D'où vient la pause.** L'issue dit : « le cabinet dépose la pause au service avant le premier tick ». Mais le service tourne dès qu'il se dit prêt, et Unity met plusieurs secondes à s'ouvrir après lui : à 6 jours par seconde, le monde aurait avancé de plusieurs jours avant que la carte puisse poser une pause. Seul le lanceur peut arriver avant le premier tick. `pc/jouer.py` démarre donc le service à `--jours-par-seconde 0`, et la carte comme la ville s'ouvrent en pause.

La reprise se fait à la vitesse de la vue :
- en ville, `CommandesDeVille.Basculer` reprend déjà à `VitesseVille` depuis une pause. Rien ne change ;
- sur la carte, `HorlogeDeCarte.Basculer` reprenait à `VITESSE_DE_REPRISE = 1` quand elle n'avait jamais vu le monde avancer. Elle reprend désormais à `ReglagesDesVues.Charger().VitesseCarte`.

## Périmètre
pc/jouer.py
jeu/ville/tests/test_lanceur_jouer.py
3d/unity/Assets/ForgeLocal3D/Pont/HorlogeDeCarte.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/HorlogeDeCarteTests.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot860.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot860.cs.meta
docs/briefs/860-le-jeu-s-ouvre-en-pause-et-dit-quoi-faire.md

Tout autre chemin est interdit, en particulier :
- tout `jeu/sim/` : `service.py`, les intentions, les données ;
- `CommandesDeVille.cs`, `TransitionDeVue.cs` (et `ReglagesDesVues`, qu'il porte), `PassageALaCapitale.cs`, `ReperesDeDepart.cs`, `CommandesDuTemps.cs`, `CalquesCarte.cs`, `LecturePartie.cs`, `SocleInterface.cs`, `BarreDuPays.cs` ;
- `ReglagesDesVues.json` : les vitesses ne changent pas (ville 0,1, carte 6) ;
- les scénarios existants, dont `Lot549`, `Lot690`, `Lot730`, `Lot855`, `Lot944`, `Lot1004`.

Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master 1c5cb709. #859 est livré (#1004 fusionné).

### `pc/jouer.py`
- Une constante `PAUSE = 0`. Le service se lance avec `"--jours-par-seconde", repr(PAUSE)` au lieu de la vitesse de la vue.
- `_vitesse` ne change pas : le fichier de réglages est toujours lu et refusé avant le service s'il est faux. `test_vitesse_invalide_ne_lance_rien` reste vert sans changer.
- La ligne `vitesse de la {vue} : {vitesse} jours par seconde` s'écrit toujours : c'est la vitesse de la reprise. Juste après, une ligne neuve, constante `OUVERTURE = "le monde s'ouvre en pause : Espace lance le temps"`.
- La docstring dit que le monde s'ouvre en pause, et que la vitesse lue est celle que la vue prend à la reprise.

### `jeu/ville/tests/test_lanceur_jouer.py`
Le propriétaire a décidé (réponse A, 10 novembre 2026) que les tests du lanceur (#120, #731) deviennent « en pause à l'ouverture, à sa vitesse à la reprise ». Seuls changent `FAUX_JEU` et les trois tests nommés ici. Tous les autres restent tels quels.

**`FAUX_JEU`** accepte un 5ᵉ argument positionnel facultatif, `reprise`, un nombre. Sans lui, rien ne change : deux lectures de `/horloge` à `ECART` d'intervalle, et les mêmes clés écrites. Avec lui, après ces deux lectures :
- il fait `POST /vitesse?jours_par_seconde=<reprise>`, comme Unity à la reprise ;
- il attend `ECART`, puis relit `/horloge` une troisième fois ;
- il écrit aussi `"ticks"` à trois entrées et `"jours_par_seconde_repris"`, la vitesse de cette troisième lecture.

`_commande_du_faux_jeu` gagne un paramètre facultatif `reprise=None`.

**`test_vitesse_de_la_vue_d_ouverture`** devient `test_pause_a_l_ouverture_vitesse_de_la_vue_a_la_reprise`, avec les mêmes quatre paramètres. La vitesse attendue est lue dans le vrai `REGLAGES`, comme avant, et passée en `reprise` au faux jeu. Le test exige :
- code 0, et le port libéré ;
- `jours_par_seconde == 0` à l'ouverture, et `ticks[0] == ticks[1]` : rien ne bouge en 1,5 s ;
- `jours_par_seconde_repris == vitesse` ;
- sur la carte, `ticks[2] > ticks[1]` et `50 < 365 / vitesse < 70`, comme avant. En ville, à 0,1 jour par seconde, on n'exige pas de tick en 1,5 s ;
- les lignes `vitesse de la {vue} : {float(vitesse)} jours par seconde` et `OUVERTURE` dans la sortie.

**`test_vitesse_lue_dans_le_fichier_remplace`**, mêmes paramètres, gagne `capsys`. Il exige :
- `jours_par_seconde == 0` à l'ouverture ;
- la ligne `vitesse de la {vue} : {float(v)} jours par seconde` dans `capsys.readouterr().out`, où `v` est la valeur du fichier remplacé (4 ou 0,25).

**`test_chemin_nominal`** passe `reprise` = `VITESSE_CARTE` du vrai fichier. Il exige :
- `premier == second` (« le monde tourne avant la reprise ») ;
- puis `troisieme > second` (« l'horloge ne tourne pas après la reprise ») ;
- ses autres assertions, sans changer.

### `HorlogeDeCarte.cs`
- `VITESSE_DE_REPRISE` disparaît. Le champ `vitesseDeReprise` devient un `double?`, nul tant que l'horloge n'a jamais lu un monde qui avance.
- `Basculer`, sur un monde en pause, demande `vitesseDeReprise ?? ReglagesDesVues.Charger().VitesseCarte`.
- Le reste ne change pas : une vitesse servie > 0 est retenue, et la pause d'un monde qui avance retient sa vitesse.
- Le commentaire de tête dit la règle : à l'ouverture, en pause, Espace et « Reprendre » lancent le temps à la vitesse de la carte.

### `CabinetDeCarte.cs`
**Les constantes** :
- `GUIDE = "Prochain geste"`, le nom du texte ;
- `TERRES = "Terres conseillées"`, le nom de la racine des surbrillances ;
- `CHOISIR = "Choisissez votre maison : cliquez une terre en surbrillance"` ;
- `CHOIX_RECU = "Espace : lancer le temps ; le monde applique votre choix au jour suivant"` ;
- `LANCER = "Espace : lancer le temps"` ;
- `ENTRER = " · double-clic sur votre siège : entrer dans votre ville"`.

**La ligne du prochain geste.** Dans `Construire`, juste après `barre`, un texte `SocleInterface.Texte(bandeau, "", 1104, 72, 792)` :
- nommé `GUIDE`, de 792 × 26, aligné à droite (`TextAnchor.MiddleRight`) ;
- couleur `papier`, `raycastTarget = false`.

Il finit en x 1896 et en y 98 : dans le bandeau, à droite des comptes de la barre, au-dessus des jauges, sous les commandes du temps. Le bandeau garde ses trois boutons enfants directs.

`public static string Guide(Lecture<MondeAvecMaisonLu> monde, Lecture<DepartsLus> departs, RecuIntention recu, HorlogeLue horloge, bool siegeAvecVille)` rend la phrase, ou `null` quand la ligne se tait. Dans cet ordre :
1. monde nul ou absent : `null` ;
2. sans maison du joueur, et un reçu accepté (`recu?.Acceptee == true`) : `CHOIX_RECU` si l'horloge est lue et en pause, sinon `null` ;
3. sans maison du joueur, sans reçu accepté : `CHOISIR` si les départs sont présents, sinon `null`. Cela vaut même si le temps file ;
4. avec une maison : horloge nulle ou monde qui avance : `null`. En pause : `LANCER`, suivi de `ENTRER` si `siegeAvecVille`.

`Afficher` active le texte si et seulement si `Guide(...)` n'est pas nul, et y écrit la phrase. Ses arguments : `Partie.Monde`, `Partie.Departs`, `Partie.Recu` et `horloge.Lue`. `siegeAvecVille` vaut `GetComponent<PassageALaCapitale>()?.SiegeLu != null`, lu à chaque image, nul compris : seul le Zab sert une ville aujourd'hui.

**La surbrillance des terres conseillées.** `Afficher` tient à jour une racine `TERRES`, enfant direct de la carte (jamais sous « Cellules de la carte », dont `CalquesCarte` lit chaque enfant comme une cellule).

Tant que le monde est présent, sans maison du joueur, avec des départs présents, la racine porte une surbrillance par fiche servie (`FicheDeDepart.CellId`) :
- un objet nommé `Terre conseillée <CellId>`, avec `MeshFilter` et `MeshRenderer`, sans `Collider` ;
- le même maillage partagé que le rendu `Cellule <CellId>` de la carte, trouvé comme dans `Garder` ;
- un matériau copié de celui de la cellule, de couleur `SocleInterface.Couleur("or")` ;
- à la pose de la cellule, haussée d'une constante `HAUTEUR_TERRE` le long de `transform.up`. Elle reste au-dessus des cellules et de leurs contours, et sous les disques des lieux (`ReperesDeDepart.HAUTEUR_LIEU`) et les noms.

Les surbrillances ne se recréent que si l'ensemble des terres servies change. Une fiche dont la carte n'a pas la cellule n'a pas de surbrillance, sans erreur. La surbrillance de la terre gardée (`retenue`) est inactive, pour que son rouge se voie. Elle revient quand la terre est relâchée. Hors de ces conditions (maison choisie, monde absent, départs absents), la racine n'a plus d'enfant. Les matériaux copiés se détruisent avec leurs objets et dans `OnDestroy`.

**Le clic propose la terre.** Dans `Garder`, après la teinte : si le joueur n'a pas de maison et qu'une fiche servie a `CellId == cellule.CellId`, cette fiche devient `candidate`. L'aperçu et « Choisir cette maison » suivent comme pour un bouton de « Maisons proposées ». Ces boutons restent. Une terre qui n'est celle d'aucune fiche ne change pas `candidate`. Le cabinet n'envoie rien : seul « Choisir cette maison » dépose `choisir_depart`.

`AIDE` ne change pas.

### `Lot860.cs`
`static class Lot860`, dans le style de `Lot855` et `Lot1045`. Trois scénarios se jouent dans l'ordre de leur nom, sur le même service, en partageant leur état par des champs statiques, comme `Lot525`. La première faute lève une `InvalidOperationException` qui la nomme. Les constantes : `EN_MARCHE = "-forge860EnMarche"`, `HORS = "-forge860Hors"`, `SIEGE = "Mistra"`, `TERRE = "Despotat de Morée"`.

Le scénario écrit lui-même les phrases attendues, en littéraux. Il ne lit ni `CabinetDeCarte.Guide` ni ses constantes de phrase. La touche Espace passe par la `Frappe` de `Lot730` (même assemblage). Le scénario recopie localement les petites fonctions `Touche` et `Servie` de `Lot730`, qui y sont privées, et ne modifie pas `Lot730`. Le service se lit à part, par `ClientHorloge` hors du fil principal, comme `Servie`.

1. **`ouverture-1-en-pause`.**
   - Il ouvre la carte comme `Lot855` : `Lot549.Ouvrir`, survol et parcours en `automatique`, puis `Lot690.LecturePrete`, `Partie.Departs` présents et `horloge.Lue` non nulle. La toile passe en `ScreenSpaceCamera` sur la caméra photographiée, comme `Lot1045`. `CommandesDuTemps` doit être là et pas en `automatique`.
   - Avec `-forge860EnMarche`, il pose d'abord `VitesseCarte` au service (`ClientHorloge.Regler`) : c'est un jeu qui s'ouvrirait en marche.
   - Il juge ensuite :
     - le tick lu vaut 0 (`-forgeTicks 0`) ;
     - `horloge.Lue.JoursParSeconde == 0`, la date finit par `En pause`, et le bouton « Pause / Reprendre » dit `Reprendre`. Sinon : `à l'ouverture, le monde avance : …` ;
     - pendant 2 s de temps réel, le tick servi ne bouge pas. Sinon : `à l'ouverture, le tick passe de T à T'` ;
     - la racine `Terres conseillées` a exactement une surbrillance active par fiche servie (six), et aucune autre. Chacune porte la couleur `or`, n'a pas de collider, et son centre tombe dans la vue de la carte (viewport x dans [0 ; 0,67], y dans [0 ; 1]) ;
     - le texte `Prochain geste` est actif et vaut `Choisissez votre maison : cliquez une terre en surbrillance` ;
     - ce texte passe `TexteDuMonde.Interdit` et `SansUnite`, et son `preferredWidth` tient dans ses 792 ;
     - la boîte de ses glyphes (`cachedTextGenerator.verts`) ne touche pas celle de la barre des comptes.
   - Il laisse passer 10 images.
2. **`ouverture-2-terre-proposee`.**
   - Il trouve la fiche au siège `Mistra`, qui doit être `Despotat de Morée`. Il calcule le point d'écran de sa terre comme `Lot855`, et vérifie que `fiche.Survolee` y voit sa cellule.
   - Avec `-forge860Hors`, il vise plutôt une cellule de la carte qui n'est celle d'aucune fiche.
   - Il clique par `cabinet.Noter` (appui, relâché), comme `Lot855.Toucher`. Il juge :
     - la terre est gardée ;
     - l'aperçu de « Votre maison » commence par `Despotat de Morée · Mistra`, et « Choisir cette maison » est actif. Sinon : `aucune maison proposée après le clic sur …` ;
     - la surbrillance de la Morée est inactive, et les cinq autres sont actives ;
     - la ligne dit toujours `Choisissez votre maison : …`.
   - Il clique « Choisir cette maison » (`onClick.Invoke`), puis attend `Partie.Recu` accepté. Il juge :
     - la ligne vaut `Espace : lancer le temps ; le monde applique votre choix au jour suivant` ;
     - le monde est toujours en pause, au même tick, sans maison du joueur.
   - Il laisse passer 10 images.
3. **`ouverture-3-temps-lance`.**
   - Il appuie sur Espace. Il juge :
     - le service sert `jours_par_seconde == ReglagesDesVues.Charger().VitesseCarte` (à 1e-6 près), et `horloge.Lue` aussi. Sinon : `reprise à V jours par seconde, attendu la vitesse de la carte W` ;
     - le tick servi avance d'au moins 2 en 3 s ;
     - la maison du joueur est posée, et `Partie.Maison` dit le siège `Mistra` ;
     - la racine `Terres conseillées` n'a plus d'enfant actif ;
     - le texte `Prochain geste` est inactif tant que le temps file.
   - Il appuie de nouveau sur Espace et attend la pause servie. Il juge :
     - `PassageALaCapitale.SiegeLu` est nul : la Morée n'a pas de ville ;
     - la ligne vaut exactement `Espace : lancer le temps` ;
     - elle passe les mêmes juges qu'au scénario 1.
   - Il laisse passer 10 images.

Chaque scénario écrit une trace `CAPTURE_860 <nom> tick T, vitesse V, maison « <nom ou aucune> », terres éclairées N, ligne « <texte ou muette> »`.

## Conditions de succès
On lance depuis la racine. Sur le PC, éditeur fermé, en PowerShell, `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Deux commandes de tests :
- `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot860-interface.xml -logFile 3d/unity/Temp/lot860-interface.log` ;
- `P` = la même avec `-assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot860-pont.xml -logFile 3d/unity/Temp/lot860-pont.log`.

Chacune sort 0, sans échec ni cas ignoré, et ses cas neufs réussissent.

**SC1 — Le lanceur ouvre le monde en pause, et la reprise prend la vitesse de la vue.** `cd jeu && python3 -m pytest ville/tests/test_lanceur_jouer.py -q` passe en entier, avec les trois tests réécrits ci-dessus. `test_vitesse_invalide_ne_lance_rien` et tous les autres cas passent sans changer. Contre-épreuve : remettre `repr(vitesse)` à la place de `repr(PAUSE)` dans le lancement du service (un jeu qui s'ouvre en marche) fait échouer `test_pause_a_l_ouverture_…` (vitesse 6 au lieu de 0, ticks qui bougent sur la carte), `test_vitesse_lue_…` et `test_chemin_nominal`.

**SC2 — Sur la carte, la reprise d'une pause d'ouverture prend la vitesse de la carte (`HorlogeDeCarteTests.cs`, `P`).** Cas neuf `La_reprise_d_une_pause_d_ouverture_prend_la_vitesse_de_la_carte`. Le service témoin sert `jours_par_seconde = 0` dès la première lecture. Puis :
- `Basculer` envoie `POST /vitesse?jours_par_seconde=<V>`, où `V` = `ReglagesDesVues.Charger().VitesseCarte`, lu par le test et différent de 1 ;
- un second `Basculer` envoie 0, et un troisième `V` de nouveau ;
- un service qui avance d'abord à 2,5 puis passe en pause reprend toujours à 2,5.

`Pause_reprise_et_paliers_partent_au_service` et les autres cas passent sans changer. Contre-épreuve : l'ancienne reprise à 1 rougit le premier point.

**SC3 — La ligne suit l'état de la partie (`CabinetDeCarteTests.cs`, `I`).** Cas neuf `La_ligne_du_prochain_geste_suit_la_partie`.

D'abord `Guide`, cas par cas :

| État | Phrase rendue |
|---|---|
| monde nul ; monde absent | `null` |
| sans maison, départs présents ; même horloge à 6 j/s | `CHOISIR` |
| sans maison, départs nuls ou absents | `null` |
| sans maison, reçu accepté, horloge en pause | `CHOIX_RECU` |
| sans maison, reçu accepté, horloge nulle ou à 6 j/s | `null` |
| sans maison, reçu refusé, départs présents | `CHOISIR` |
| avec maison, en pause, `siegeAvecVille` faux | `Espace : lancer le temps` |
| avec maison, en pause, `siegeAvecVille` vrai | `Espace : lancer le temps · double-clic sur votre siège : entrer dans votre ville` |
| avec maison, horloge nulle ou à 6 j/s | `null` |

Puis le texte du cabinet :
- après `Proposer()`, `Prochain geste` est actif et dit `CHOISIR` ;
- reçu accepté au tick 7 et horloge `(7, 1400-8, 0)` : il dit `CHOIX_RECU` ;
- avec la maison publiée et une horloge en pause : `LANCER` ;
- à 6 j/s : le texte est inactif ;
- monde nul : le texte est inactif.

Chaque phrase non nulle passe `TexteDuMonde.Interdit(t, "10340", "42")` et `SansUnite`. La plus longue (avec `ENTRER`) a un `preferredWidth` ≤ 792. Le texte est un enfant du bandeau, en (1104, −72), de 792 × 26.

Contre-épreuve : un `Guide` qui ne regarde pas la pause dit `LANCER` à 6 j/s et rougit le cas.

**SC4 — Les terres conseillées s'éclairent, et un clic en propose une (`CabinetDeCarteTests.cs`, `I`).** Cas neuf `Les_terres_conseillees_s_eclairent_et_un_clic_propose_la_maison`. Le test pose deux rendus `Cellule 10340` et `Cellule 77` (`MeshFilter` avec un maillage, `MeshRenderer` avec un matériau). Puis il pose le monde sans maison et deux fiches, 42 sur 10340 et 43 sur 9999 (la carte n'a pas 9999), sans cliquer de bouton :
- `Terres conseillées` porte une seule surbrillance active, `Terre conseillée 10340` : même maillage partagé que sa cellule, couleur `or`, sans collider, et rien pour 9999 ;
- `cabinet.Noter` (appui puis relâché, sans mouvement) sur une `CelluleDeCarte` 10340 garde la terre. La surbrillance de 10340 devient inactive, et l'aperçu vaut celui de la fiche 42 (`Despotat témoin · Mistra…`). « Choisir cette maison » est actif ;
- `Relacher` rallume la surbrillance, et l'aperçu reste celui de la fiche 42 ;
- un clic sur la cellule 77, d'aucune fiche, ne change pas l'aperçu ;
- la maison publiée : `Terres conseillées` n'a plus d'enfant. Le monde remis sans maison : la surbrillance revient ;
- un second `Afficher` sans changement ne recrée pas l'objet : même instance.

`LeChoixDirectDuPrototypeEstArrete`, `UnClicSansMouvementGardeLaTerre`, `LApercuDuChoixDitLesHabitantsAutourDuSiege`, `LeRecuNEstDateQuAuTickDeLHorloge`, `Aucun_dossier_ne_recouvre_la_barre`, `SansHorlogeRecueLesCommandesDuTempsRestentInactives` (trois boutons enfants directs) et `Sans_maison_la_barre_le_dit` passent sans changer, comme tous les autres cas. Contre-épreuve : un `Garder` qui ne pose pas `candidate` rougit le deuxième point.

**SC5 — Sur le vrai service, la photo et ses deux contre-épreuves.** Les trois commandes de la section Photo.
- `PHOTO` sort 0, avec `*--ouverture-1-en-pause.png`, `*--ouverture-2-terre-proposee.png`, `*--ouverture-3-temps-lance.png` et trois traces `CAPTURE_860`. La 1ʳᵉ dit `vitesse 0`, `terres éclairées 6` et la ligne `Choisissez votre maison…`. La 3ᵉ dit la maison des Paléologue et la ligne `Espace : lancer le temps`.
- `EN_MARCHE` sort 1, sans image, et son journal dit `à l'ouverture, le monde avance` (ou `à l'ouverture, le tick passe`).
- `HORS` sort 1, avec la seule image `*--ouverture-1-en-pause.png`, et son journal dit `aucune maison proposée`.

Le codeur ouvre chaque image lui-même et dit ce qu'il y voit : les six terres en or, la ligne entière, à droite de la barre, sans recouvrir les comptes.

**SC6 — Les scénarios qui lisent la carte, le bandeau et l'horloge restent verts.** Chacune de ces commandes sort 0 :
- `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1004 -forgeCaptures 3d/unity/Temp/lot860-1004 -logFile 3d/unity/Temp/lot860-1004.log` : rien de coupé ni de recouvert dans le bandeau, la ligne `Espace : lancer le temps` comprise ;
- la même avec `-forgeLot 944`, son dossier `lot860-944` et son journal : aucun identifiant ni nombre nu dans le cabinet ;
- la même avec `-forgeLot 855`, son dossier `lot860-855` et son journal : le clic gauche garde toujours la Morée ;
- la même avec `-forgeLot 525`, son dossier `lot860-525` et son journal : l'horloge en marche puis en pause.

**SC7 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `I`, `P` et `python3 -m pytest -q` (depuis `jeu/`) passent en entier.
- `git diff origin/master -- 3d/unity/Assets/Interface/Tests 3d/unity/Assets/ForgeLocal3D/Pont/Tests` ne montre que des lignes ajoutées.
- Dans `jeu/ville/tests/test_lanceur_jouer.py`, le diff ne touche que `FAUX_JEU`, `_commande_du_faux_jeu` et les trois tests nommés. Aucune assertion n'y est retirée sans la règle nouvelle qui la remplace : pause à l'ouverture, vitesse de la vue à la reprise.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 1 500 lignes, brief compris.

## Hors périmètre
- Le mode observateur, et les cinq vitesses du jalon (#1030) : les paliers de l'horloge ne changent pas.
- Choisir un autre pays que les six terres de départ (#1037) : seules les fiches servies par `/departs` s'éclairent.
- Entrer dans sa ville ailleurs qu'au Zab : pas de kit. La ligne ne le promet qu'au Zab.
- Toucher le service, l'intention `choisir_depart`, ou le jour où elle s'applique (toujours le tick suivant).
- Changer la reprise en ville (`CommandesDeVille`, déjà à `VitesseVille`) ou la vitesse posée au changement de vue (`TransitionDeVue`).
- Rallumer le prototype `ReperesDeDepart`, qui reste arrêté par le cabinet.
- La langue visuelle de la carte (#849, #850) au-delà des couleurs du socle (`or`, `papier`).
- La définition du PNG : la chaîne l'écrit à 1600 × 900.

## Photo
Trois images, la carte de 1400 et son cabinet en entier, au jour 1 de 1400 (`-forgeTicks 0`).

1. **L'ouverture en pause** (la photo du lot) :
   - sur la carte, les six terres de départ en or : Bar, Wurtemberg, la Morée, les Branković, l'Uç d'Evrenos, le Zab ;
   - dans le bandeau, la date `… En pause` et le bouton `Reprendre` ;
   - à droite de la barre, la ligne `Choisissez votre maison : cliquez une terre en surbrillance`.
2. **La Morée proposée puis choisie** : sa terre en rouge, les cinq autres en or, « Votre maison » qui dit le choix reçu. La ligne dit `Espace : lancer le temps ; le monde applique votre choix au jour suivant`.
3. **Le temps lancé puis remis en pause** : plus aucune terre en or, la maison des Paléologue dans la barre, et la ligne `Espace : lancer le temps`.

Le scénario `Lot860.cs` (Périmètre) joue ces étapes, et la chaîne écrit chaque image à la fin de son scénario.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 860 -forgeTicks 0 -forgeCaptures 3d/unity/Temp/lot860-photo -logFile 3d/unity/Temp/lot860-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 860 -forgeTicks 0 -forge860EnMarche -forgeCaptures 3d/unity/Temp/lot860-en-marche -logFile 3d/unity/Temp/lot860-en-marche.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 860 -forgeTicks 0 -forge860Hors -forgeCaptures 3d/unity/Temp/lot860-hors -logFile 3d/unity/Temp/lot860-hors.log
```

Les trois sessions :
- **`PHOTO`**, la première, donne la photo : elle sort 0 avec ses trois images ;
- **`EN_MARCHE`** est la contre-épreuve de la pause : un monde qui avance quand la carte s'ouvre. Elle sort 1, sans image ;
- **`HORS`** est la contre-épreuve du clic : une terre hors des six ne propose aucune maison. Elle sort 1 après la première image.

Leurs journaux sont joints au compte rendu. Les PNG restent hors du dépôt.
