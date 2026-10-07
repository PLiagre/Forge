# Lot #322 — La carte montre les capitales voisines et ce que l'IA a fait
Jalon : J5 · Machine : vps · Taille prévue : 270 lignes

## But
Sur la carte de 1400 rendue avec l'IA, le joueur voit la capitale de chaque maison de l'IA, celles de ses voisines mises en avant, et lit dans un encadré, maison par maison et geste par geste, ce que l'IA a fait.

## Règle du monde
Sans objet : c'est un lot de vue. La carte lit le bloc `ia` de la photographie (#321, sections « Les maisons de l'IA et leurs capitales, vue dérivée » et « Les décisions et les gestes de l'IA » de `jeu/sim/MODELE.md`) et ne décide aucun nombre. Elle n'appelle ni `maisons_de_l_ia`, ni `jouer_ia`, ni aucune fonction de `sim/`.

**La décision du propriétaire (réponse A, issue #322).** Le jeu reste sans IA par défaut. Le propriétaire ajoute lui-même `--ia` à la commande de capture dans `atelier/captures.py`, en mode direct : ce n'est pas ce lot. Une photographie sans bloc `ia` rend donc la carte d'aujourd'hui, octet pour octet, et la capture actuelle ne change pas tant que ce mot n'est pas ajouté.

**Les voisines.** Ce sont les maisons qui tiennent une terre touchant la terre choisie. On part des cellules de `terre_choisie.voisins` (la cellule choisie elle-même n'en fait pas partie). Une ligne de `ia.maisons` est voisine si :
- elle est une `grande maison` et son `id` est le `maison.id` d'une de ces cellules ;
- ou elle est une `seigneurie` et son siège (`cell_id`) est une de ces cellules.
Sans terre choisie, il n'y a pas de voisine. Mesuré à la graine 0, au tick 1 : Bar → Valois, Valois-Bourgogne, Wittelsbach (Trèves, en 10437, n'a pas de maison) ; Wurtemberg → Wittelsbach ; Morée → Paléologue ; Branković → Osman, Lazarević et la seigneurie Evrenosoğulları ; Evrenos → Osman et la seigneurie Branković.

**Sur la carte**, seulement si le bloc `ia` est présent. Chaque capitale placée (`cell_id` non nul) reçoit un losange au centroïde de sa cellule, dessiné après les points des villes. Couleurs : `COULEUR_CAPITALE` pour les autres, `COULEUR_VOISINE`, plus grand, pour les voisines. Ces deux couleurs sont nouvelles, distinctes entre elles et des quatre couleurs existantes. Chaque voisine porte un cartouche « capitale (maison) », par exemple « Paris (Valois) ». Il passe par `etiqueter`, avant les villes et les puissances : la règle de non-chevauchement s'applique aux cartouches comme aux points, et les losanges entrent dans `boites_points`. Un cartouche de voisine omis est compté, jamais caché.

**L'encadré** est une fonction publique `lignes_de_l_ia(document)`. Elle rend `[]` sans bloc `ia`. Ses lignes, repliées par `_lignes_ajustees`, forment une seconde bande sous la fiche, sur le même fond.
1. L'en-tête : « L'IA : 34 maisons ; actives sur 30 jours : 4 ». Avec −1, on écrit « non mesuré (moins de 30 jours) », jamais 0.
2. Les voisines d'abord, dans l'ordre de `ia.maisons`, même sans geste : « Voisine Valois : capitale Paris, cellule 10322, bourg 39570 habitants ; aucun geste ». Si un geste existe : « … ; 1 geste ».
3. Puis les autres maisons qui ont au moins un geste, dans le même ordre et le même format, sans « Voisine ».
4. Sous chaque maison, une ligne par geste, dans l'ordre exact de ses `gestes`, sans tri ni dédoublonnage :
   - `tracer_route` : « tick 17 : trace une route de 40 m, large de 4 m, par 1 foyer, dans la cellule 10206 ». La longueur vaut `round(somme des math.dist entre points successifs)`.
   - tout autre type : « tick N : <type> » suivi de ses autres champs `clé=valeur`, dans l'ordre des clés, avec les valeurs telles quelles.
5. Une ligne « Sans geste : N autres maisons », qui compte les non-voisines sans geste.
6. Une ligne « Capitales hors carte : Saraï (Djötchides) », ou « aucune ».

Pas de troncature : une partie longue fait un encadré long.

**Le compte rendu de la carte** gagne, seulement avec `ia` :
- `capitales_dessinees` : le nombre de losanges ;
- `capitales_hors_carte` : les noms des maisons ;
- `voisines` : les noms des maisons, dans l'ordre ;
- `etiquettes_voisines_omises` ;
- `gestes_listes`.

Sans `ia`, les clés et les valeurs restent inchangées.

**Refus.** Avec `ia`, on lève `Carte1400Erreur` en nommant la maison et la donnée dans ces cas :
- `maisons` ou `maisons_actives_30j` absent ;
- une ligne sans l'une des clés `sorte`, `id`, `nom`, `capitale`, `cell_id`, `hors_carte`, `population`, `gestes` ;
- un `cell_id` non nul absent des cellules ;
- un geste sans `tick` ou sans `intention`.

## Périmètre
jeu/vues/relief/carte1400.py
jeu/vues/relief/tests/test_carte1400.py
docs/NOTICE.md

Tout autre chemin est interdit, notamment `atelier/captures.py` (le geste du propriétaire), `jeu/forge/`, `jeu/sim/`. `docs/NOTICE.md` : seulement la ligne de `carte.png`, qui ajoute « capitales de l'IA, voisines et gestes (avec --ia) ». Budget : environ 85 lignes de vue, 100 de tests, 84 de brief ; strictement sous 300 lignes ajoutées et supprimées.

## Conditions de succès
Les commandes se lancent depuis `jeu/`. Ajouter seulement des cas nommés `test_capitales_ia_*` à `test_carte1400.py`, sans modifier la fixture `photographies` ni aucun test existant. Une seule nouvelle fixture de module : un monde à la graine 0, Bar choisi, un tick. Elle construit `build_snapshot_document(monde, 0, 1, releve_ia=releve)` avec un relevé écrit à la main :
- un `tracer_route` de Valois, à deux segments, avec une coordonnée décimale ;
- deux gestes de Visconti au même tick, intercalés avec un geste de Stuart ;
- un geste d'un type inventé pour Stuart.

Montrer chaque test rouge avant l'implémentation. Une liste de voisines vide, ou de gestes vide, fait échouer le test.

- **SC1 — sans IA, la carte d'aujourd'hui.** `python3 -m pytest vues/relief/tests/test_carte1400.py -q -k test_capitales_ia_sans`. Avant tout changement, mesurer sur la base le sha256 de `image.tobytes()` pour les deux photographies de la fixture (900 px), et la liste des clés du compte rendu. Les écrire en dur dans le test, qui exige l'égalité après le changement. Le test vérifie aussi que `lignes_de_l_ia` rend `[]` et qu'aucun pixel n'a `COULEUR_CAPITALE` ni `COULEUR_VOISINE`. Contre-épreuve : ajouter à une copie un bloc `ia` avec zéro maison change l'empreinte.
- **SC2 — les voisines viennent de la fiche.** `python3 -m pytest vues/relief/tests/test_carte1400.py -q -k test_capitales_ia_voisines`. Le test dérive la référence des données (cellules voisines, `maison` des cellules, sièges) et trouve, pour Bar, exactement Valois, Valois-Bourgogne et Wittelsbach. Sur le rendu, le pixel du centroïde de chaque capitale voisine est `COULEUR_VOISINE`. Celui de chaque autre capitale placée est `COULEUR_CAPITALE`. `capitales_dessinees` vaut le nombre de `cell_id` non nuls. Trois contre-épreuves, sur des copies :
  - le siège d'une seigneurie déplacé dans une cellule voisine la rend voisine (pixel et ligne) ;
  - `terre_choisie = None` ne laisse aucune voisine et aucun pixel `COULEUR_VOISINE` ;
  - une voisine retirée de la référence fait échouer l'égalité.
- **SC3 — l'encadré dit tout, dans l'ordre.** `python3 -m pytest vues/relief/tests/test_carte1400.py -q -k test_capitales_ia_encadre`. Le test compare `lignes_de_l_ia` aux lignes attendues, construites depuis le bloc : en-tête, voisines puis maisons actives, une ligne par geste dans l'ordre du relevé, longueur arrondie de la route décimale, champs du type inventé, compte des maisons sans geste, Saraï hors carte. Une sonde sur `ImageDraw.text` montre que chaque ligne repliée est bien dessinée sous la fiche. `gestes_listes` vaut le total des gestes. Contre-épreuves : inverser les deux gestes de Visconti, retirer un geste, ou changer `maisons_actives_30j` en −1 fait échouer l'égalité (−1 doit produire « non mesuré »).
- **SC4 — refus nommés.** `python3 -m pytest vues/relief/tests/test_carte1400.py -q -k test_capitales_ia_refus`. Un cas paramétré par défaut : clé de bloc absente, clé de ligne absente, `cell_id` inconnu, geste sans `intention`. Chacun lève `Carte1400Erreur` avec le nom de la maison ou de la clé. Contre-épreuve : le bloc intact se rend sans erreur.
- **SC5 — la capture avec l'IA, de bout en bout.** Lancer `python3 -m forge --ticks 30 --seed 0 --ia --depart 1 --sans-chronique --largeur 900 --sortie /tmp/forge-322`, c'est-à-dire la capture plus `--ia`. Puis un script Python en ligne relit `monde.json` et `resume.json` et vérifie :
  - le code de sortie est 0 ;
  - `carte.voisines` vaut la référence dérivée de `monde.json` (mesurée : Valois, Valois-Bourgogne, Wittelsbach) ;
  - `gestes_listes` vaut la somme des gestes du bloc (mesurée : 4 — Anjou-Durazzo au tick 5, Stuart au 17, Nasrides au 22, Visconti au 29) ;
  - `capitales_dessinees` vaut 33 et `capitales_hors_carte` vaut `["Djötchides"]`.

  Le script affiche ce qu'il compte. Regarder ensuite `carte.png` soi-même : les trois losanges voisins se voient autour de Bar, avec leur cartouche, et l'encadré se lit sous la fiche. Contre-épreuve : la même commande sans `--ia` n'a aucune des nouvelles clés, et sa `carte.png` a le même sha256 que celle de la base, mesurée avant le changement.
- **SC6 — rien d'autre ne bouge.** `python3 -m pytest . -q` passe sans réécrire aucun test existant. En particulier, `test_forge_ia_sorties` rend sa carte à 64 px avec l'IA sans erreur, et les tests de chevauchement des villes passent. Depuis la racine, `git diff --stat origin/master` ne touche que les trois chemins du périmètre et le brief ; à 300 lignes ou plus, le lot échoue.

## Hors périmètre
- L'ajout de `--ia` à la capture (`atelier/`, propriétaire, mode direct).
- L'IA par défaut dans `forge` ou le service.
- Toute modification de `sim/`, de la photographie, de `forge`, du tableau, de la chronique ou de la planche.
- La croissance des capitales dans le temps (une série de photographies) et les prélèvements des voisines : ils attendent le jalon 3.
- Les flux vers les sièges.
- Une capitale dessinée hors de son centroïde.
- Unity et Blender.
