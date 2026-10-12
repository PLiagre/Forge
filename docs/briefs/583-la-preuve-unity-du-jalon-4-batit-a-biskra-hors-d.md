# Lot #583 — La preuve Unity du jalon 4 bâtit à Biskra, hors des maisons de 1400
Jalon : J4 · Machine : pc · Taille prévue : 250 lignes

## But
La preuve Unity du jalon 4 joue la partie du joueur du Zab : le choix de l'émirat appliqué, puis une rue, une parcelle et une scierie posées dans Biskra par l'outil d'Unity, que le monde tient et que Python rejoue à l'octet ; une rue tracée à travers une maison de 1400 est refusée par le monde.

## Le joueur
Le joueur qui a pris l'émirat du Zab bâtit dans Biskra, sa capitale, et pas dans une ville d'essai : la rue, la parcelle et la scierie qu'il pose dans Unity sont des intentions que le monde accepte, qu'il retrouve à la relance et que le même journal refait. S'il trace une rue à travers une maison de 1400, le monde la refuse en nommant la maison : sa ville de 1400 ne se perd pas sous ses gestes. C'est un lot de fond pour le geste « trace des routes, découpe des parcelles, pose ses ateliers » du jalon J4 : il remet au vert la preuve Unity, rouge depuis #408 (cellule 1175, sans choix). Le joueur le verra à l'écran quand le jeu ouvrira sa capitale (#409) et que Unity dessinera la ville de 1400 (#412).

## Règle du monde
Sans objet : outil de preuve. Le lot éprouve deux règles déjà sur la base sans les changer : « on ne bâtit que sur ses terres » (#408) et « Rien ne se pose sur une maison de 1400 » (`jeu/sim/MODELE.md`, « Le plan du bourg », sous-section « Le plan de base », #566). Rien ne change dans `jeu/sim/`.

**Ce que le lot fait.** Mesuré sur master f081666, graine 0 : `depart_biskra()` rend la seigneurie 6, la maison `seigneurie-6`, la cellule 10103 ; la base servie de Biskra compte 33 maisons, entre -67 et +69 m sur les deux axes (le repère des gestes : `Lot362.Monde` envoie `(x, y)` en `(-x, -y)` pour les gestes comme pour le plan). Choix au tick 0 appliqué au tick 1, gestes aux ticks 1, 2 et 3, scierie appliquée au tick 4, sept ticks de plus : tick 11. Au tick 11, rue 50/200, parcelle 14/14 aux bornes, scierie 30/270 aux piquets. La recette ne touche aucune maison.

Dans `pc/epreuve_jalon4.py` :

1. **La recette lit la table.** Plus de 1175 ni de 10103 dans le script. `--cellule` et `--ticks` prennent `None` par défaut. Le parcours Python résout `--ticks` à 10 (inchangé, garde `<= 5` comprise). `--avec-unity` résout à 11 ticks et à la cellule de `depart_biskra()` ; une graine autre que 0, des ticks autres que 11 ou une cellule donnée autre que celle de Biskra rendent 2 (« la recette Unity fixe la graine 0, la cellule de Biskra et 11 ticks »). Une fois résolus, `args.ticks` et `args.cellule` portent ces valeurs : `juger_essai` compare toujours `rapport["cell"]` à `args.cellule`.
2. **Le choix dans `lancer_service`.** `lancer_service(sortie, seed, sourd, depart=None)` : quand `depart` (la seigneurie) est donné, après le démarrage du fil et la pose du crochet `recevoir`, il dépose `choisir_depart` par `http`, exige le reçu `{"acceptee": True, "appliquee_au_tick": 0}`, avance d'un tick, exige `maison_du_joueur` égale à la maison de Biskra, puis rend la main. Le journal porte alors le choix au tick 0. Le service des sessions jouer et relance le reçoit ; le service vierge ne le reçoit pas (le plan vierge reste au tick 0, comme `fautes_dessin` l'exige). Le parcours Python garde son propre dépôt et appelle `lancer_service` sans `depart`.
3. **`-forgeCell`.** `appeler_unity(aides, nom, sortie, cellule)` ajoute `-forgeCell <cellule>` à la ligne d'Unity, pour jouer, relance et vierge.
4. **La chronologie exacte.** `juger(servi, rejoue, temoin, journal, ticks, chronologie=(0, 2, 3, 5))` exige `numeros == list(chronologie)` ; `juger_essai` l'appelle avec `(0, 1, 2, 3)`. Les reçus Unity se comparent aux seules entrées du journal dont le type est dans `CONSTRUCTIONS`, et leurs ticks doivent être `[1, 2, 3]` (statut « gestes » : « journal identique aux reçus, ticks 1, 2 et 3 »).
5. **Le témoin rejoue le choix seul.** `rejouer(sortie, ticks, seed)` écrit `journal-temoin.json` (les entrées `choisir_depart` du journal) et passe `--gestes` à ce fichier pour `monde-sans-gestes.json`, comme le parcours Python.
6. **Le message** « le normal exige N ticks » prend N dans `args.ticks`.
7. **Une faute de session nomme ses défauts** : `"{nom} : {n} défaut(s)"` est suivi du texte des défauts, pour que le verdict dise pourquoi Unity a échoué.
8. **`--sur-une-maison`**, admis seulement avec `--avec-unity` (sinon 2, comme `--ville-locale`), inscrit dans la ligne « commande » du verdict. Dans le service des sessions jouer et relance, après le choix, le script lit `/plan?cell=<Biskra>`, prend sa clé `base`, et cherche une route : une fonction pure `route_sur_une_maison(base, h, largeur, P)` essaie, maison par maison, des segments droits qui passent par le centre de l'emprise (plusieurs caps, longueur de l'ordre de 40 m), et rend les premiers points dont `ville1400.maison_touchee(base, [emprise_de_rue(...)])` n'est pas `None` et que `routes.essai(h, points, largeur, P)` accepte (`h = routes.grille(implantation)`, `P` et la largeur de la route plaine du jeu de gestes). Rien trouvé : 2, « aucune route sur une maison que le relief accepte ». Trouvé : le script réécrit `consigne.json` avec la route, par une fonction à part (pas par `preparer_sessions`).

Dans `DesertCityPreuve.cs` : `Consigne` gagne une route facultative (`x`, `y`, `largeur`). Quand elle est présente, l'étape « la route » de la session jouer clique ces points au lieu de la route plaine ; sinon rien ne change (la capture du lot 388 et `atelier_desert.py preuve` écrivent une consigne sans route). Le refus du monde s'inscrit déjà comme défaut (« refusée par le monde : … ») ; la session s'arrête là, Unity rend 1, le rapport est écrit.

**Pièges des tests existants, qui ne changent pas :**
- `test_une_panne_unity_ecrit_le_verdict_et_nettoie` remplace `lancer_service` et `appeler_unity` par `lambda *a` / `lambda *_a`, et `preparer_sessions` par `lambda a, _l` : nouveaux arguments **positionnels** seulement ; aucun appel HTTP hors de `lancer_service` sauf sous `--sur-une-maison` ; `preparer_sessions` garde deux arguments. Ce test appelle `main(["--avec-unity", "--sortie", …])` sans `--ticks` : la résolution à 11 doit le laisser passer jusqu'à la panne attendue.
- `_essai()` rend un `args` qui n'a que `ticks`, `cellule`, `service_sourd`, `seed` : `juger_essai` lit tout autre drapeau par `getattr(args, …, False)`.
- `test_des_rapports_au_tick_10_et_un_monde_au_tick_9` remplace `rejouer` par `lambda _s, ticks, _seed` et exige « le normal exige 10 ticks » avec `args.ticks = 10`.
- La fixture `preuve` appelle `juger(*mondes, journal, 10)` : la chronologie Python reste le défaut.
- `test_un_recu_unity_different_du_journal` passe un journal de trois constructions sans choix : le filtrage par `CONSTRUCTIONS` le garde vrai.

## Périmètre
pc/epreuve_jalon4.py
jeu/ville/tests/test_epreuve_jalon4.py
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityPreuve.cs
jeu/ville/README.md
docs/mesures/583-preuve-unity-biskra/verdict.txt
docs/mesures/583-preuve-unity-biskra/verdict-service-sourd.txt
docs/mesures/583-preuve-unity-biskra/verdict-ville-locale.txt
docs/mesures/583-preuve-unity-biskra/verdict-sur-une-maison.txt

## Conditions de succès
SC1. `python3 -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q` passe, et `git diff origin/master -- jeu/ville/tests/test_epreuve_jalon4.py | grep '^-[^-]'` ne sort rien : aucune ligne existante retirée ni changée. Cas ajoutés, chacun avec sa contre-épreuve :
  - la chronologie est exacte : sur la fixture, `juger(*mondes, journal, 10, chronologie=(0, 1, 2, 3))` lève « journal : ticks invalides » ; un journal Unity (choix 0, gestes 1, 2, 3) jugé avec la chronologie Python lève aussi ;
  - `juger_recus` accepte un journal à quatre entrées (choix compris) contre trois reçus ; un reçu de plus ou un type changé lève ;
  - `juger_essai` avec `args.ticks = 11` et un monde à 10 ticks nomme « le normal exige 11 ticks » ;
  - un vrai `lancer_service(sortie, 0, False, seigneurie)` laisse le monde au tick 1, `maison_du_joueur` égale à la maison de `depart_biskra()`, et le journal `[choix au tick 0]` ; sans `depart`, tick 0 et journal vide ;
  - `epreuve_unity` (Unity et service moqués) passe à `appeler_unity` la cellule de `depart_biskra()` pour jouer, relance et vierge, et la seigneurie au seul service de jouer et relance ; `--avec-unity --cellule <une autre cellule>` rend 2 ;
  - `route_sur_une_maison` sur une grille plate et la base servie de Biskra rend une route que `maison_touchee` touche ; déposée au vrai service (`lancer_service` avec le choix), elle est refusée en 400 avec « maison de 1400 » ; sur une grille où le relief refuse tout (pente bien au-delà de `pente_max`), elle rend `None`, et `epreuve_unity --sur-une-maison` avec cette recherche rend 2 et « aucune route » dans le verdict ;
  - `juger_essai` avec un défaut de jouer « … maison de 1400 3 (… foyers) touchée » rend 1, et le statut « relancement » nomme « maison de 1400 ».
SC2. `grep -nE "1175|10103" pc/epreuve_jalon4.py` ne sort rien. Contre-épreuve : sur master, il sort `RECETTE_UNITY` et le défaut de `--cellule`.
SC3. `python3 pc/epreuve_jalon4.py --sortie <d>` rend 0 et `--service-sourd` rend 1, comme avant (le parcours Python ne change pas).
SC4. Sur le PC, éditeur fermé, après `py local3d/atelier_desert.py terrain` depuis `3d/` :
  - `py pc\epreuve_jalon4.py --avec-unity --sortie <d>` rend **0** ; le verdict dit « octets égaux sur 11 ticks » et « ticks 1, 2 et 3 », les rapports portent la cellule de Biskra. Le codeur relève dans le README, sur `monde-service.json`, la rue à 50/200, la parcelle 14/14 aux bornes, la scierie 30/270 aux piquets. Rouge d'abord : la même commande sur master rend 1 (« journal : … »), à dire dans la PR ;
  - `--service-sourd` rend **1** et nomme « bâtiment absent » ;
  - `--ville-locale` rend **1** et nomme « empreinte des rues » ;
  - `--sur-une-maison` rend **1** et nomme « maison de 1400 » (pas une panne : un 2 ne vaut pas contre-épreuve).
  Les quatre verdicts réels sont copiés dans `docs/mesures/583-preuve-unity-biskra/`.
SC5. `jeu/ville/README.md`, section « L'épreuve du jalon 4 » : les quatre commandes, ce qu'elles rendent, les liens vers les nouveaux verdicts ; la phrase qui annonce « un lot PC distinct » disparaît, remplacée par ce que fait maintenant `--avec-unity` (choix du Zab, Biskra lue dans la table, gestes 1, 2, 3, tick 11, témoin = choix seul).
SC6. `python3 -m pytest jeu -q` passe en entier.

## Hors périmètre
- `jeu/sim/` : aucune règle ne change ; la garde des maisons de 1400 est celle de #566.
- La capture du lot 388 (`JouerLesGestes`), `atelier_desert.py preuve` et `DesertRoadTool.Ouvrir` restent à 1175 sans choix ; la photo de la ville relancée à Biskra est l'autre sous-lot de #567.
- Dessiner les maisons de 1400 dans Unity (#412) ; ouvrir la capitale depuis le jeu (#409).
- La preuve complète du jalon (#508) : salaire, enceinte, ville vivante.
- Les verdicts de `docs/mesures/264-preuve-du-jalon-4/` restent tels quels (historique).

## Photo
sans objet : outil de preuve ; les sessions Unity ne capturent rien et rien de ce que voit le joueur ne change. La photo de la ville bâtie à Biskra est celle de l'autre sous-lot de #567.
