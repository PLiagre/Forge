# Lot #957 — Le service d'épreuve monte la ville dense de la mesure
Jalon : J4 · Machine : vps · Taille prévue : 260 lignes

## But
Avec `--epreuve` et l'horloge à l'arrêt, `POST /epreuve/ville-dense?cell=C` porte le bourg de la cellule à 800 habitants pris aux autres lieux, puis sert, au même tick, dans `/plan` et `/occupation` de cette cellule, une base de 600 maisons d'un foyer sans îlots, calculée par une fonction pure de `sim/ville1400.py`. Hors épreuve, rien ne change.

## Le joueur
C'est un lot de fond. Il prépare le geste du jalon J4 « le joueur entre dans sa capitale en 3D et y marche », dans une ville vivante dont chaque fumée, chaque étal et chaque passant suit le monde. Cette ville doit rester fluide quand elle est pleine. Le propriétaire a choisi (réponse **B** sur #422) de mesurer les 60 images par seconde sur une ville d'épreuve : 600 maisons et un bourg de 800 habitants, soit environ 80 passants, servis par le vrai service et non inventés par Unity. Ce lot fournit cette ville. Le sous-lot 3 de #422 (pc) la monte à Biskra et la mesure, et la preuve de #422 montre que le joueur traverse une capitale dense sans saccade. Le joueur ne voit jamais cette ville d'épreuve dans sa partie : sans `--epreuve`, sa capitale reste sa ville de 1400.

## Règle du monde
Aucune règle du monde ne change. C'est un outil d'épreuve, décrit dans **« ## Le plan du bourg »**, sous-partie **« ### Le plan de base »** de `jeu/sim/MODELE.md` (écrite par #564, #565, #566). Le lot y ajoute un paragraphe.

**La fonction pure.** Dans `sim/ville1400.py` :
- `base_sans_ilots(n_maisons, directions)` rend `{place, rues, maisons}`, avec `n_maisons` maisons d'un foyer. Elles sont posées par la règle des maisons sous le seuil : même forme, même recul, même tri, même grille, même allongement des rues. Aucun îlot, quel que soit `FOYERS_SANS_ILOTS`. Elle ne lit ni le monde ni la population.
- `base_dense_de_cellule(monde, cell_id, n_maisons)` fait comme `base_de_cellule` : elle lit les directions par `_directions_terre`, lève `BaseAbsente` si un centroïde manque, et pose `cell_id`. Elle ne lit pas `populations_bourg_amorcage` : SC7 de #564 ne bouge pas.

`base_d_une_population` et `base_sans_ilots` partagent la boucle de pose et d'allongement. Le codeur peut extraire une aide privée, par exemple `_base_des_groupes(groupes, directions, parametres)`. `base_d_une_population` reste identique à l'octet.

**Les constantes.** Elles vont dans le bloc « Plan du bourg » de `jeu/sim/constants.py` : `HABITANTS_BOURG_VILLE_DENSE = 800` et `MAISONS_VILLE_DENSE = 600`. Leur commentaire dit « épreuve de mesure de #422, réponse B du propriétaire ; jamais lue par le monde ». Le service les relit par `_constantes.X` à chaque requête. `test_no_hardcoded` interdit 800 et 600 en dur dans une fonction.

**La route.** `POST /epreuve/ville-dense?cell=C` est servie seulement avec `--epreuve`, comme `/epreuve/vider-bourg`. Elle tient `verrou_tick` et `condition_vitesse`. Dans cet ordre, sans rien écrire avant le dernier contrôle :
1. sans `--epreuve` : 404 « chemin inconnu », comme aujourd'hui ;
2. horloge en marche : 409 « l'horloge doit être à l'arrêt » ;
3. `cell` absent, vide, répété ou non entier : 400 ; cellule inconnue : 404 ;
4. `_valider_epreuve(cellule)` échoue : 400 ;
5. `cellule.population < HABITANTS_BOURG_VILLE_DENSE` : 400. Le message nomme la cellule, ses habitants et le seuil (« cellule 10103 : 799 habitants, il en faut 800 ») ;
6. cellule à un seul lieu : 400 « aucun autre lieu pour le bourg » ;
7. bourg déjà au-dessus de `HABITANTS_BOURG_VILLE_DENSE` : 400, avec les habitants du bourg. L'épreuve agrandit un bourg, elle ne le vide jamais. C'est le choix du chef : la demande dit « pris aux autres lieux » ;
8. `base_dense_de_cellule` lève `BaseAbsente` : 500, qui la nomme.

**Le montage.** Ensuite seulement : `manque = HABITANTS_BOURG_VILLE_DENSE − bourg`, puis `parts = partager(manque, [population des autres lieux, par rang])`. Une part ne dépasse jamais la population de son lieu, puisque `manque ≤ somme`. Chaque autre lieu perd sa part et le bourg passe à 800. Ni migration ni flux : seules les populations des lieux changent. `cellule.population`, `habitants_par_metier`, les stocks, la faim, les maîtres, le tick et l'aléa restent intacts. Puis, sous `verrou_base`, les trois caches de la cellule sont remplacés : `_bases`, `_rues_de_base` et `_occupations_base` (`{rang, foyers: 1}` dans l'ordre de `maisons`). Enfin, `etat_publie` est reconstruit par `_construire_etat`, au même tick. Attention : l'ancien `EtatPublie` garde dans `plans` les octets assemblés avec la base de 1400. Il ne doit plus être servi. La réponse est `{cell_id, tick}`, comme `vider-bourg`. Les ticks suivants gardent la base dense, puisqu'ils assemblent depuis `_bases`. Un second appel sur la même cellule est admis et ne change rien : manque nul, même base.

**Ce qui ne change pas.** Les dépôts (`recevoir_intention`) et l'IA éprouvent toujours la base de 1400 de `base_de_cellule`. La ville d'épreuve sert la mesure seule, et aucun geste n'y est joué. Le paragraphe de MODELE.md le dit. Ni `World`, ni `to_dict`, ni l'empreinte, ni `populations_bourg_amorcage` ne portent la base dense.

**Mesure du chef** (graine 0, prototype ; à re-mesurer, et jamais recopiée dans un test sauf la borne de la demande) : Biskra (10103) compte 3 459 habitants en 21 lieux, et 165 au bourg. 600 maisons sur ses 7 directions donnent 77 voies, en 0,03 s, pour un rayon maximal de 155,4 m (la base de 1400 : 33 maisons, 85 m). 118 cellules habitées ont moins de 800 habitants ; 459 ont un bourg au-dessus de 800 ; 76 n'ont qu'un lieu et au moins 800 habitants.

## Périmètre
jeu/sim/ville1400.py
jeu/sim/service.py
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/tests/test_ville_dense.py

## Conditions de succès
Toutes se lancent par `cd jeu && python3 -m pytest sim/tests/test_ville_dense.py -q`, sauf SC6. Le fichier est neuf. Aucun test existant n'est modifié. Le service est lancé en mémoire, `ServeurMonde(('127.0.0.1', 0), 0, 0, epreuve=True)`, comme `_service_epreuve` de `test_monde.py` : l'aide est importée ou recopiée. Biskra se trouve par `/departs` (siège « Biskra ») ; on affirme qu'elle vaut 10103. Chaque compteur est dérivé et affiché par `print`.

- **SC1 — La fonction pure suit la règle sous le seuil, sans îlots.** Avec les directions de Biskra : `base_sans_ilots(MAISONS_VILLE_DENSE, dirs)` rend 600 maisons, toutes `foyers == 1`, d'aire `SURFACE_M2_PAR_FOYER_LOGE` à la tolérance d'arrondi de #564. Aucun chevauchement (aide `_controler_chevauchements` de `test_ville1400.py`, ou grille ; paires affichées, > 0). Chaque coin est à moins de 156 m de l'origine, et le rayon est affiché. Pour `n = FOYERS_SANS_ILOTS` : `base_sans_ilots(n, dirs) == base_d_une_population(n × TAILLE_FOYER, dirs)`. Contre-épreuves :
  - pour `n = FOYERS_SANS_ILOTS + 1`, les deux diffèrent, puisque la seconde a des îlots ;
  - avec `FOYERS_SANS_ILOTS` à 0 (`monkeypatch`), `base_sans_ilots` rend les mêmes octets, alors que `base_d_une_population` change ;
  - une copie de la base dont une maison est décalée de 200 m vers l'est échoue au contrôle du rayon (`pytest.raises(AssertionError)`).
- **SC2 — Le bourg passe à 800, rien d'autre ne bouge dans le monde.** Après le POST sur Biskra : réponse `(200, {cell_id, tick})` au tick d'avant. `pickle.dumps(serveur.world)` est égal à celui d'une référence `deepcopy` où seules les populations des lieux ont reçu `partager(manque, populations des autres lieux)`. `serveur.rng.getstate()` et `ticks_ecoules` sont inchangés. Le bourg vaut `HABITANTS_BOURG_VILLE_DENSE`. La somme des lieux et `cellule.population` sont inchangées, comme `habitants_par_metier`. `/lieu?cell=C&bourg=1` sert 800 au même tick. Contre-épreuves (`pytest.raises(AssertionError)`) : la comparaison échoue contre une référence où le bourg vaut 799, une où `population` perd un habitant, une où `habitants_par_metier` est vidé, et une où le manque est pris au seul lieu de rang 1.
- **SC3 — `/plan` et `/occupation` servent la ville dense au même tick.** Après le POST, `/plan?cell=C` porte `base == json.loads(json.dumps(base_dense_de_cellule(monde, C, MAISONS_VILLE_DENSE)))`, avec 600 maisons. `rues`, `parcelles` et `batiments` des gestes sont égaux à ceux d'avant le POST. `/occupation?cell=C` porte `base == [{rang: i, foyers: 1}]` pour i de 0 à 599, avec `batiments` et `logement` inchangés. Les deux documents ont le tick du POST. Après `POST /tick?n=2`, la base est identique. Un second POST rend la même base, et le monde est égal à l'octet (pickle). Les octets de `/plan` d'une autre cellule sont inchangés. Deux services neufs donnent les mêmes octets de `/plan` pour C. Contre-épreuves : si `base_dense_de_cellule` est remplacée par `base_de_cellule` (`monkeypatch`), la base servie a moins de 600 maisons et l'assertion échoue ; si `/plan` est lu avant le POST (l'état met alors en cache les octets de la base de 1400) et que le POST ne reconstruit pas l'état (`monkeypatch` de `_construire_etat` qui rend l'état courant), la base de 1400 resservie fait échouer l'assertion.
- **SC4 — Chaque refus est nommé et n'écrit rien.** Pour chaque refus 1 à 8 de la règle, `_memoire_epreuve` (monde, aléa, état publié) et `serveur._bases` sont égaux avant et après. Le statut est attendu, et le message contient ce qu'il nomme :
  - sans `--epreuve` : 404 ;
  - horloge à 1 jour/s : 409 ;
  - `cell` vide, répété ou non entier : 400 ; cellule inconnue : 404 ;
  - une cellule de moins de 800 habitants (la première triée par `cell_id`) : 400, avec son nombre d'habitants et 800 ;
  - une cellule à un seul lieu d'au moins 800 habitants : 400 ;
  - une cellule dont le bourg dépasse 800 : 400 ;
  - un centroïde retiré de `monde.carte` (`monkeypatch`) : 500 « centroïde absent ».

  Contre-épreuve : une cellule de 800 habitants tout juste, fabriquée par `monkeypatch` des populations d'une cellule à plusieurs lieux (le bourg reste ≤ 800), est acceptée.
- **SC5 — Hors épreuve, rien ne change.** Un service sans `--epreuve` sert, à Biskra, `/plan` et `/occupation` avec une base égale à `base_de_cellule` (33 maisons, nombre dérivé et affiché), et le bourg reste à 165. `base_d_une_population` rend, pour Biskra et pour Paris (10322), les mêmes octets que la base calculée par la boucle d'avant le lot. Si le codeur extrait la boucle, il compare à une copie figée dans le test du SHA-256 mesuré sur la base, avant de toucher le code ; il le dit dans la PR. `FOYERS_SANS_ILOTS` vaut toujours 500. Contre-épreuve : cette empreinte, calculée avec `FOYERS_SANS_ILOTS` à 0 (`monkeypatch`), diffère pour Paris.
- **SC6 — Tout le reste passe, et le modèle le dit.** `cd jeu && python3 -m pytest sim -q` passe en entier, sans test modifié. Cela couvre tout `test_ville1400.py` (SC3 de #565 et son empreinte des bases sous le seuil, SC7 de #564 et son égalité d'importeurs `{ville1400.py, intentions.py, service.py}`), `test_monde.py` (`vider-bourg`, `vider-panier`, `/plan`, `/occupation`), `test_no_hardcoded.py` et `test_write_coverage.py` (les deux constantes déclarées et lues). Dans `test_ville_dense.py`, un test lit « ### Le plan de base » (par `_sous_partie` de `test_ville1400.py` ou une lecture équivalente) et y trouve `/epreuve/ville-dense`, `HABITANTS_BOURG_VILLE_DENSE`, `MAISONS_VILLE_DENSE` et « sans îlots ». Contre-épreuve : un texte sans la sous-partie échoue (« échantillon vide »).

## Hors périmètre
- Monter, dessiner ou mesurer la ville dense dans Unity, le banc du temps d'image, les fumées, les étals, les lampes, les passants : sous-lots 2 à 6 de #422 (pc). La règle d'un passant pour dix habitants ne change pas.
- Faire éprouver la base dense par les dépôts ou par l'IA ; jouer des gestes dans la ville d'épreuve.
- Vider un bourg au-dessus de 800, déplacer des habitants entre cellules, toucher les stocks, la faim ou les métiers.
- Changer la ville de 1400, le seuil de 500 foyers, les îlots, ou toute constante de #564 et #565.
- Mettre la base dense dans `World`, `to_dict`, l'empreinte, le snapshot, `/monde` ou `/lieu` (au-delà de la population du bourg).
- Toucher `jeu/sim/intentions.py`, `jeu/sim/ia.py`, `jeu/sim/world.py`, `jeu/sim/README.md`, tout fichier `ville/` ou `pc/`, ou tout test existant.
