# Lot #251 — La caméra de la capitale survole la ville et descend y marcher
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Dans la scène de ville du désert (`Forge_Desert_Ville_<implantation>`), le joueur survole sa capitale avec une caméra de city builder : il tourne autour, glisse et zoome de la vue d'ensemble jusqu'à la rue, sans jamais passer sous le terrain. D'une touche, il descend marcher à hauteur d'homme sur le terrain et les routes, puis remonte là où il était.

## Règle du monde
Sans objet : c'est un lot de vue. La caméra et le marcheur ne lisent pas `sim/` et n'y écrivent rien. Aucune section de `jeu/sim/MODELE.md` n'est concernée. Le lot sert le geste « il entre dans sa capitale en 3D, y marche » du jalon J4 de `CAP.md`. Il ne dépend de rien que J2 ou J3 doivent livrer : la scène, son terrain, les routes du joueur (lot 263) et le marcheur `CitadelTraversal` sont déjà sur master.

Ce que la vue fait, vérifié sur master le 30/09/2026 :

- **Aujourd'hui**, `DesertCityTerrain.Build` pose dans chaque scène de ville une « Caméra de la ville » fixe. Elle n'a ni orbite ni zoom, et la scène n'a pas de marcheur pour le joueur. Le contrôle en Play du lot 263 (`DesertCityRoads`, lancé par `py 3d/local3d/atelier_desert.py routes`) fait déjà marcher un « Marcheur du contrôle » sur chaque route posée, et le bloque par un mur en contre-épreuve. Ce lot ne refait pas ce marcheur-là : il ajoute celui du joueur, que l'on atteint par la caméra.
- **Nouveau composant `DesertCityCamera`**, sur la caméra de la ville. Il porte :
  - un point visé, posé au sol ;
  - un cap, une inclinaison et une distance ;
  - une seule méthode publique qui pose la caméra à partir de ces quatre valeurs. Elle borne la distance (au plus 8 m pour la rue, au moins 400 m pour la vue d'ensemble), borne l'inclinaison, garde le point visé sur le terrain et applique la **garde**. La garde place la caméra au moins 1 m au-dessus du terrain et de son plan proche, en lisant la hauteur du terrain **vivant** (la copie que les routes modifient), jamais une hauteur figée.
  - Les entrées du joueur passent par cette même méthode, sans autre chemin : clic droit pour tourner, clic milieu, flèches ou ZQSD/WASD pour glisser, molette pour zoomer (à une vitesse proportionnelle à la distance), F pour revenir à la vue d'ensemble.
  - Un drapeau `garde`, vrai par défaut, n'existe que pour la contre-épreuve. Un drapeau `automatique` coupe le clavier et la souris pendant le contrôle.
- **Le marcheur du joueur** est un `CitadelTraversal` sur un corps `CharacterController` (1,8 m, rayon 0,3 m), créé par le composant. Tab (ou `Descendre()`) le pose au sol sous le point visé, l'œil à hauteur d'homme. Tab encore (ou `Remonter()`) rend la vue d'orbite exacte qu'il avait quittée. Pendant la marche, la caméra d'orbite ne bouge plus. `CitadelTraversal` cherche aujourd'hui un `VillageV2Visit` sans vérifier qu'il existe : cette recherche devient tolérante à son absence. Le comportement des scènes du ksar et de la citadelle ne change pas.
- **Branchement sans réécrire les scènes** : le composant s'attache lui-même au chargement de toute scène qui porte un `DesertRoadTool`, sur la caméra `view` de cet outil. Ce branchement passe par `RuntimeInitializeOnLoadMethod` et `SceneManager.sceneLoaded`. Les fichiers `.unity` et les assets du terrain ne sont pas touchés. L'outil de routes garde le clic gauche, Entrée, Échap et T, sans conflit avec les touches de la caméra.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertCityCamera.cs
3d/unity/Assets/ForgeLocal3D/Desert/DesertCityCamera.cs.meta
3d/unity/Assets/ForgeLocal3D/Citadelle/CitadelTraversal.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityRoads.cs
3d/local3d/desert/routes.py
3d/local3d/atelier_desert.py
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/routes/gestes.json
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/routes/unity-routes.json
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/routes/jugement.json
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/routes/captures/plaine.png
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/routes/captures/bord.png
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/routes/captures/flanc_de_dune.png
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/routes/captures/refus.png
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/camera/ensemble.png
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/camera/rue.png
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/camera/marcheur.png
3d/local3d/desert/sorties/ville/oued_des_vents/routes/gestes.json
3d/local3d/desert/sorties/ville/oued_des_vents/routes/unity-routes.json
3d/local3d/desert/sorties/ville/oued_des_vents/routes/jugement.json
3d/local3d/desert/sorties/ville/oued_des_vents/routes/captures/plaine.png
3d/local3d/desert/sorties/ville/oued_des_vents/routes/captures/bord.png
3d/local3d/desert/sorties/ville/oued_des_vents/routes/captures/flanc_de_dune.png
3d/local3d/desert/sorties/ville/oued_des_vents/routes/captures/refus.png
3d/local3d/desert/sorties/ville/oued_des_vents/camera/ensemble.png
3d/local3d/desert/sorties/ville/oued_des_vents/camera/rue.png
3d/local3d/desert/sorties/ville/oued_des_vents/camera/marcheur.png
docs/briefs/251-la-camera-de-la-capitale-survole-la-ville-et-des.md

Les fichiers de `sorties/` sont refaits par la commande des conditions de succès : on ne les édite pas à la main. Tout autre chemin est interdit, en particulier :

- les scènes `.unity` et les assets `Desert/Ville/*.asset` ;
- `DesertCityTerrain.cs`, `DesertRoads.cs`, `DesertRoadTool.cs` et `VillageV2Visit.cs` ;
- `jeu/`.

## Conditions de succès
Toutes se lisent dans une seule commande, jouée sur le PC depuis la racine, Unity fermé :

```powershell
py 3d/local3d/atelier_desert.py routes
```

Si les grilles `.f32` ne sont pas là, lancer d'abord `py 3d/local3d/atelier_desert.py terrain`.

La commande finit en erreur dès qu'une implantation a un défaut. Les mesures viennent de `DesertCityRoads.Run`, qui met la caméra et le marcheur du joueur en `automatique`. Le jugement vient de `routes.juger`, qui les écrit dans `jugement.json`. Unity mesure, Python juge : c'est déjà la règle du contrôle 263. Chaque contre-épreuve entre dans le dictionnaire `contre_epreuves` : si l'une ne rougit pas, c'est un défaut.

- **SC1 — La caméra ne passe jamais sous le terrain.**
  - *Le balayage.* Il passe par la méthode publique du composant, la même que celle du joueur. Il couvre :
    - des points visés sur une grille 9 × 9 qui couvre le terrain, moins 60 m de marge ;
    - un cap tous les 30° ;
    - l'inclinaison au minimum, au milieu et au maximum ;
    - la distance, du maximum au minimum, avec un facteur d'au plus 0,75 par pas.
  - *La mesure.* Elle ne passe pas par la garde : un rayon vertical est lancé sur le `TerrainCollider`, depuis le dessus du terrain, à l'aplomb de la caméra.
  - *Le rapport.* Il écrit le nombre de poses prévues, le nombre de poses mesurées, le nombre de poses sous le terrain et la marge minimale.
  - *Le jugement exige* : autant de poses mesurées que de poses prévues (un échantillon vide échoue), 0 pose sous le terrain, et une marge minimale d'au moins 1 m.
  - *Contre-épreuve « terrain relevé »* :
    - sur la copie du terrain (`roads.Preparer`), un disque de 30 m de rayon est relevé de 40 m autour du milieu de la route de plaine ;
    - le même balayage autour de ce point, garde active, doit rester à 0 pose sous le terrain : la garde lit le terrain vivant ;
    - garde coupée, il doit trouver au moins une pose sous le terrain (`contre_epreuves.camera_sans_garde`) : la mesure sait rougir ;
    - l'asset du terrain reste intact (`asset_avant == asset_apres`).
- **SC2 — Le zoom va de la vue d'ensemble à la rue.**
  - Le rapport écrit la distance minimale et la distance maximale réellement obtenues par la méthode publique, et la hauteur de la caméra au-dessus du sol au zoom le plus court.
  - Le jugement exige une distance maximale d'au moins 400 m, une distance minimale d'au plus 8 m, et une hauteur d'au plus 10 m au zoom le plus court.
  - *Contre-épreuve* : le jugement, rejoué sur une copie du rapport dont la distance minimale est mise à 20 m, doit échouer (`contre_epreuves.zoom_court`).
- **SC3 — Le marcheur du joueur va d'un bout à l'autre d'une route.**
  - Sur la route de plaine posée, le point visé est mis au départ, puis on appelle `Descendre()`.
  - L'œil doit se trouver entre 1,5 et 1,9 m au-dessus du sol, mesuré par rayon sur le collider.
  - `DesertCityRoads.Walk` (rendu accessible, pas réécrit) mène ce marcheur-là jusqu'au bout. `juger_marche` s'applique tel quel : il s'arrête à 1 m du bout au plus, et aucun pas ne dépasse le pas permis.
  - `Remonter()` rend la pose d'orbite quittée, à 1 cm près.
  - *Contre-épreuve « mur en travers »* : le même mur que le contrôle 263, posé au milieu de la même route, doit arrêter ce marcheur. `juger_marche` doit y trouver un défaut (`contre_epreuves.mur_joueur`). Un marcheur non lancé est aussi un défaut.
- **SC4 — Ce qu'on voit.**
  - Trois captures par implantation, dans `sorties/ville/<implantation>/camera/`, prises par la caméra du joueur :
    - `ensemble.png`, au zoom maximal ;
    - `rue.png`, au zoom minimal, au bord de la route de plaine ;
    - `marcheur.png`, par l'œil du marcheur, sur la route.
  - Elles vont dans une liste `captures_camera`, séparée de `captures`. La liste des captures du lot 263 garde ses une à quatre images.
  - Le jugement refuse une liste vide et toute image uniforme (même seuil `ECART_CAPTURE`).
  - Le codeur regarde les six images lui-même et dit dans la PR ce qu'on y voit.
- **SC5 — Rien du contrôle 263 ne s'assouplit.** La même commande reste verte sur les deux implantations, avec :
  - tous les défauts qu'elle vérifiait déjà ;
  - toutes ses contre-épreuves (`mur`, `profil_releve`, `pente_40`…) ;
  - sa limite de captures.

  Les cas de ce lot s'ajoutent à `routes.juger`, et aucune tolérance existante ne change. *Contre-épreuve* : les contre-épreuves existantes, qui doivent toujours rougir.

## Hors périmètre
- Le geste « tracer une route » comme intention déposée dans `sim/`, et le plan de la ville tenu par le monde : la route reste celle du lot 263, connue de Unity seul. La preuve J4 contre « une ville que seul Unity connaît » est un autre lot.
- Les parcelles, les ateliers, les foyers par métier.
- Le lancement de la scène de ville par `pc\Jouer.cmd`, et le panneau du lieu dans cette scène.
- La collision de la caméra avec des bâtiments : la scène de ville n'a encore que le terrain et les routes.
- Les scènes du ksar (`Forge_Desert_<implantation>`), la citadelle, `VillageV2Visit`, et toute réécriture de scène ou de terrain.
