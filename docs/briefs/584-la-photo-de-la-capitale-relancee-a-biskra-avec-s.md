# Lot #584 — La photo de la capitale relancée à Biskra avec ses gestes
Jalon : J4 · Machine : pc · Taille prévue : 250 lignes

## But
La photo de Biskra retrouve, après réouverture depuis le service, la rue, la parcelle aux bornes et la scierie aux piquets que le joueur y a déposées par ses gestes.

## Le joueur
Le joueur qui choisit l'émirat du Zab retrouve dans Biskra la rue qu'il a tracée, la parcelle qu'il a découpée et la scierie qu'il a posée : quitter puis rouvrir sa capitale ne perd pas son travail. La photo lui montre ces trois gestes ensemble, vus de haut, sans les chiffres d'un autre lieu. Ce lot rapproche les gestes « trace des routes, découpe des parcelles, pose ses ateliers » de J4 de leur preuve à l'écran ; l'ouverture depuis le jeu reste le lot #409.

## Règle du monde
Sans objet : vue et scénario de capture. Aucune règle ni constante du monde ne change. Les intentions et leur application au tick suivant sont celles de `jeu/sim/MODELE.md`, « Les intentions du joueur » ; le plan relu appartient au monde (« Le plan du bourg »). Le choix du Zab, la garde de propriété, la protection des maisons de 1400 et la recette Unity à Biskra sont déjà sur la base (#407, #408, #566, #583). Ce lot n'attend aucune livraison restante de J3.

**Réalisation bornée.**

- Ajouter `public bool Ouvrir(long cellule)` à `DesertRoadTool`. La cellule reçue devient celle des lectures de plan et des dépôts suivants ; réutiliser le dessin de `Ouvrir()` sur un terrain remis à neuf. Conserver `Ouvrir()` et `Start` pour les appelants existants. Lors d'un changement de cellule réussi, effacer les points, modes, reçus et dépôts en attente de l'ancienne cellule, ainsi que les relevés de pose devenus caducs. Une cellule invalide ou un plan absent rend faux et nomme l'absence, sans dessiner un plan de secours. Le port reste celui du service local.
- Dans `Lot584.cs`, déclarer `[ScenarioDeCapture(584, "biskra-relancee")]`. Lire réellement `GET /departs`, exiger une unique fiche dont `siege.nom == "Biskra"`, puis prendre son `id` et son `cell_id`. Ne coder en dur ni la seigneurie 6 ni la cellule 10103 ; une fiche absente, ambiguë ou incomplète est un échec. Les requêtes attendues tournent hors du fil de l'éditeur, comme dans `Lot362`.
- Déposer `choisir_depart` avec cet `id`, exiger son reçu, faire exactement un tick et vérifier dans `/monde` que le choix est appliqué. Attention : `maison` dans `/departs` est le nom de la maison ; `maison_du_joueur` est son identifiant de registre `seigneurie-<id>`, déjà défini par le contrat.
- Appeler `outil.Ouvrir(celluleBiskra)`, puis `DesertCityPreuve.JouerLesGestes(outil)` sans recopier sa recette. Exiger zéro défaut et les trois gestes attendus, avec leurs identifiants. La recette fait ses trois ticks de dépôt puis sept ticks : avec une capture commencée au tick 0, le plan final est au tick 11. Ne pas ajouter de ticks pour attendre les murs.
- Relever le plan, les rues dessinées, les états et les empreintes du terrain, des parcelles et des bâtiments. Rappeler `Ouvrir()` comme au lancement, sans dépôt ni tick supplémentaire, puis comparer au relevé et au plan relu. Exiger des collections non vides, la rue acceptée, la parcelle aux bornes et la scierie aux piquets, reliées par les identifiants des reçus. Les étapes attendues se déduisent du travail publié, pas du seul texte de l'outil ; aucun objet ne doit être doublé à la seconde ouverture.
- Masquer le panneau du lieu dans ce scénario : arrêter ses lectures, désactiver le composant et ses toiles, y compris le texte des foyers. Désactiver seulement le composant laisserait sa toile visible. Vérifier après les images de pose qu'aucune de ses toiles n'est visible. Garder le panneau des gestes, qui décrit le plan dessiné. Ne pas modifier `PanneauLieu`, son défaut 1175 ni ses tests.
- Ajouter dans ce seul scénario trois drapeaux de contre-épreuve : `-forge584SansChoix` omet le choix ; `-forge584OublierRue` remet le terrain à neuf après la réouverture ; `-forge584PanneauEtranger` garde visible le panneau initial. Ils doivent provoquer les contrôles ordinaires, sans les court-circuiter. Le journal donne cellule, tick, reçus, états, égalité des empreintes et état des toiles.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot584.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot584.cs.meta
docs/mesures/584-photo-biskra.txt

Tout autre chemin est interdit. Le relevé de mesure reste court : commandes, codes, défauts des contre-épreuves et observations de la photo, sans recopier les journaux entiers.

## Conditions de succès
SC1. Sur le PC, éditeur fermé, depuis la racine, définir `$u = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Avant les changements, `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 388 -forgeSeed 0 -forgeTicks 0 -forgeCaptures "$env:TEMP\forge584-avant" -logFile "$env:TEMP\forge584-avant.log"` rend 1 : la recette sans choix ne peut pas bâtir sur la cellule 1175. Inscrire ce rouge réel dans la mesure. Après changements, la même commande avec `-forgeLot 584` et un dossier neuf rend 0, le journal dit Biskra, trois reçus, tick 11, bornes, piquets et réouverture identique. Contre-épreuve : la commande #584 augmentée de `-forge584SansChoix` rend 1 et nomme le choix absent ou le refus du monde ; une compilation impossible ou un service absent ne vaut pas ce rouge.

SC2. `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 584 -forgeSeed 0 -forgeTicks 0 -forge584OublierRue -forgeCaptures "$env:TEMP\forge584-rue-absente" -logFile "$env:TEMP\forge584-rue-absente.log"` rend 1 et nomme l'empreinte des rues différente du relevé conservé. Contre-épreuve du contrôle : retirer uniquement ce drapeau donne 0 et une ville redessinée identique ; un relevé vide ne passe pas.

SC3. `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 584 -forgeSeed 0 -forgeTicks 0 -forge584PanneauEtranger -forgeCaptures "$env:TEMP\forge584-panneau-etranger" -logFile "$env:TEMP\forge584-panneau-etranger.log"` rend 1 et nomme la toile du lieu encore visible. Contre-épreuve du contrôle : sans ce drapeau, aucune toile du lieu ne reste visible après dix images ; le scénario rend 0. Le panneau des gestes reste lisible sur la photo normale.

SC4. `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 584 -forgeSeed 0 -forgeCaptures "$env:TEMP\forge584-defaut" -logFile "$env:TEMP\forge584-defaut.log"` rend 0 aussi avec les 30 ticks initiaux du harnais : vérifier le tick final depuis le tick de départ, sans supposer 11. La photo `*--biskra-relancee.png` existe, n'est pas vide et le codeur puis le relecteur la regardent eux-mêmes : rue entière, contour et bornes distincts, scierie aux piquets, aucun chiffre de 1175. Contre-épreuve : une image du plan fixe seul ou un cadrage qui coupe l'un des trois gestes ne satisfait pas ce contrôle visuel, même avec un code 0.

SC5. `py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge584-preuve"` reste à 0 ; avec `--service-sourd` et un autre dossier, elle reste à 1 et nomme le bâtiment absent. `& $u -batchmode -projectPath 3d/unity -runTests -testPlatform EditMode -testResults "$env:TEMP\forge584-tests.xml" -logFile "$env:TEMP\forge584-tests.log"` conserve tous les tests existants, dont ceux du panneau. Aucun test existant n'est réécrit ni rendu moins exigeant ; les nouveaux cas de défaut sont ceux du scénario qui porte la capture.

## Hors périmètre
Le moteur Python, les règles de propriété et de chantier, la table des départs, le harnais de capture et les scénarios historiques ne changent pas. Pas de dessin des maisons de 1400 (#412), d'ouverture interactive de la capitale (#409), de transition carte-ville (#410), ni de preuve complète du jalon (#508). La réouverture du plan dans cette capture ne prétend pas prouver une sauvegarde ni un redémarrage du service. Aucun kit, scène ou asset du désert n'est refait.

## Photo
Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot584.cs`. Le scénario choisit le Zab lu dans `/departs`, laisse le tick appliquer le choix, ouvre Biskra, joue les trois gestes existants, puis rouvre depuis le service avant la prise. Il utilise `DesertCityCamera.Poser`, avec une inclinaison d'environ 50°, et `Lot362.Monde` pour convertir les points du plan : centre près de la scierie, distance calculée d'après les points de la rue et le contour de la parcelle pour cadrer leur ensemble en 1600 × 900 avec une marge. Attendre dix images de pose et vérifier que le cadrage tient. La photo montre la rue de terre, les bornes de la parcelle et les piquets de la scierie ; le panneau du lieu est masqué. La commande SC1 prend cette photo au tick 11 ; SC4 éprouve aussi le lancement habituel du pilote. Les PNG restent dans le dossier de capture, hors du diff ; `docs/mesures/584-photo-biskra.txt` rapporte leur inspection et les quatre essais normaux ou faussés.
