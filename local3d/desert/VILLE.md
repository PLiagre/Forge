# La ville du désert — plan et analyse

Ce fichier garde l'analyse de la vertical slice « ville du désert » pour qu'elle
survive aux sessions. Les lots eux-mêmes vivent dans le registre de
[ROADMAP.md](../../ROADMAP.md) (fiches) et dans `briefs/` (bons de travail) : ce
fichier ne dit jamais l'état d'un lot, il dit **pourquoi** et **comment**.

Contexte imaginaire, fidélité 2. Travail de présentation : rien dans `sim/`,
aucune économie, aucun besoin, aucune ressource.

## Objectif

Transformer le ksar du désert en **vertical slice visuelle d'un city builder**,
au niveau d'une partie avancée de *Manor Lords* : une ville médiévale dense et
vivante, qui a l'air d'avoir poussé dans le décor. Seulement les outils de pose
du joueur et le rendu.

**Critère final, vérifiable à l'œil** : une ville de **400 à 600 maisons**, rues,
remparts, souk, palmeraie, jardins et **au moins 800 habitants animés**, à
**60 images/s** (95ᵉ centile sous 16,7 ms) sur RTX 3070 Ti 8 Go en 1920×1080.
Manor Lords sert de référence de densité, pas de style.

## Architecture

| hier | désormais |
|---|---|
| Blender fabrique une scène figée (terrain maillé, placements dans un manifeste) | Blender, l'IA et les packs sont une **usine à pièces** : kit modulaire de pisé sur trame de 0,75 m, accessoires, matériaux. La chaîne reste : 3 LOD, catalogue, vérification à l'import. |
| terrain = maillage FBX | **Unity Terrain** tiré de `paysage.field`, creusé et peint à l'exécution (étape 1, faite) |
| la ville est dans le manifeste | **Unity assemble la ville à l'exécution** à partir des gestes du joueur, graines déterministes : même graine + mêmes gestes = même ville |

Règles héritées d'[AGENTS.md](../../AGENTS.md) qui pèsent ici : `py`, jamais
`python` ; un contrôle dérive sa référence des données ; un échantillon vide
échoue ; chaque contrôle a sa contre-épreuve ; on regarde les captures soi-même ;
packs payants et clés d'API jamais versionnés (le dépôt est public).

Les contrôles de ces lots sont **locaux** : ils demandent Blender 5.2, Unity
6000.0.43f1 et les packs de `unity/Assets/Vendor/`. La CI GitHub (Linux) ne les
joue pas ; chaque brief nomme la commande `py local3d/atelier_desert.py …` qui
peut échouer, et le compte rendu de PR joint son rapport JSON et ses captures.

## Étape 1 — Terrain Unity (faite, dans la V0)

`py local3d/atelier_desert.py terrain` — détail dans [README.md](README.md),
section « La ville du désert — étape 1 ».

Mesuré sur ≈ 4 950 points dérivés du plan (rues, seuils, jardins, un point par
carré de 16 m), sur les deux implantations : médiane 0,7 mm, 95ᵉ centile
1,1–1,2 cm, max 8–11 cm ; sol marchable ≤ 4,2 cm (tolérance 5 cm fixée avant
mesure) ; six contre-épreuves qui échouent puis repassent.

### Ce que l'étape 1 a appris (pièges à ne pas refaire)

1. **Unity n'interpole pas en bilinéaire.** `GetInterpolatedHeight`, `SampleHeight`
   et la collision découpent chaque carreau le long de la diagonale
   (i, j)–(i+1, j+1). Toute référence Python doit suivre ce découpage
   (`terrain.interpolee`). Mesuré à 0,01 mm.
2. **Créer l'asset TerrainData avant d'y poser les couches.** Sinon leurs
   textures de contrôle ne sont pas des sous-assets et disparaissent au
   changement de scène.
3. **Unity en mode batch qui plante à la compilation laisse
   `unity/Temp/UnityLockfile`.** L'atelier croit alors qu'un éditeur est ouvert
   (« L'éditeur ouvert ne répond pas »). Vérifier qu'aucun processus Unity ne
   tourne, puis supprimer ce fichier.
4. **Une grille fine révèle les motifs réguliers de la source.** Le produit de
   sinus de `raw_height` dessinait une boîte à œufs ; la crête vive des dunes se
   crénelait. Corrigés dans `paysage.py` (bruit, crête arrondie sur 1,5 m).
5. Les textures procédurales à motif (sillons de `terre_jardin`) font du moiré
   sur un terrain vu de loin : prendre une texture sans motif régulier.

### Ce que V1 (les routes) a appris

1. **Une moyenne glissante bornée en mètres saute.** Sur un axe à pas égaux, les
   bornes `s ± 5 m` tombent pile sur des échantillons. Selon l'arrondi, la
   fenêtre en prend 20 ou 21, et la moyenne saute : 38 % de pente mesurés sur la
   descente de l'oasis, dont le terrain n'en a que 22. Compter la fenêtre en
   échantillons, et la rétrécir des deux côtés aux bouts.
2. **Un talus se définit par ce qu'il touche.** Raboter tout ce qui dépasse le
   cône 1:2 autour de l'axe taille aussi les buttes voisines, et fait refuser des
   routes que rien n'empêche. Le talus est la composante connexe des sommets
   rabotés qui touche la chaussée.
3. **`chemin_sable` et `chemin_dalle` sont des bandes de route**, avec une
   chaussée au centre et du sable sur les côtés. Répétées comme couches de
   terrain, elles rayent la route tous les 2,5 m. Seules les captures l'ont
   montré : le terrain était juste au millimètre. Prendre une texture qui se
   répète sans bord (`souk_dalles`, `sable_ombre`).
4. **Deux calculs de distance qui doivent choisir le même point de l'axe** (C# et
   numpy) : mêmes opérations dans le même ordre, `sqrt(x*x+y*y)` et non `hypot`,
   segments parcourus dans l'ordre, et seul un écart strictement plus petit
   remplace le précédent. La grille d'Unity vaut alors la référence à 2 mm près.

### Ce qui reste visible après l'étape 1

- `paysage.field` porte la **rampe d'accès du ksar et les terrasses de l'ancien
  bourg**, sans ksar dessus. **Décision** : on garde `paysage.field` ; le ksar sur
  sa table de grès redevient le **noyau historique** de la ville (lot des
  bâtiments singuliers), et la démo retrace les anciennes rues.
- **Plaine constructible ≈ 350 m de diamètre** (dunes à partir de 175 m du
  centre). 500 maisons demandent ≈ 0,11 km² avec rues, souk et jardins, soit un
  disque de 190 m de rayon : juste. Le lot des parcelles mesure la surface libre
  et, si elle manque, élargit la plaine par un paramètre de `paysage.dunes`.
- Pointillés d'ombre sur les crêtes lointaines (cascades d'ombre) → lot lumière.
- Le reg se lit comme une tache à mi-distance → lot matériaux PBR.

## Les lots

Neuf étapes, seize lots : une étape qui mêle des choses jugeables séparément
devient plusieurs lots (AGENTS.md, « un lot = un changement »). Chaque lot tient
en une session de travail. Les fiches 263 à 278 sont entrées au registre par une
PR de feuille du propriétaire (le formulaire ne sait pas déclarer une dépendance
vers un lot pas encore fusionné, et seize dépôts simultanés se seraient
bloqués en conflit).

| # | étape | lot | dépend de | n° |
|---|---|---|---|---|
| V1 | 2 | Le joueur trace une route qui épouse le relief | V0 | 263 |
| V2 | 2 | Les routes se croisent en carrefours et forment un graphe | V1 | 264 |
| V3 | 8 | La caméra de city builder survole la ville et descend dans la rue | V0 | 265 |
| V4 | 3 | Le kit de pisé s'emboîte sur la trame de 0,75 m | V0 | 266 |
| V5 | mat. | Les matériaux photographiés remplacent les procéduraux | V0 | 267 |
| V6 | 3 | Une parcelle se découpe en lots, chaque lot reçoit sa maison | V1, V4 | 268 |
| V7 | 3 | L'arrière-cour se remplit de vie | V6 | 269 |
| V8 | 4 | L'enceinte suit le tracé du joueur, ses portes naissent des routes | V1, V4 | 270 |
| V9 | 5 | Les bâtiments singuliers se posent à la main, le ksar redevient le noyau | V1 | 271 |
| V10 | 6 | Le chantier se voit pousser | V6 | 272 |
| V11 | 7 | Un habitant animé par textures se dessine mille fois | V0 | 273 |
| V12 | 7 | Les habitants et les bêtes circulent sur le graphe des routes | V2, V6, V11 | 274 |
| V13 | 7 | La ville fume, sèche son linge, garnit ses étals et s'éclaire la nuit | V6 | 275 |
| V14 | 8 | La ville dense tient 60 images/s (GPU Resident Drawer, occlusion, imposteurs) | V6 | 276 |
| V15 | 8 | La lumière du désert : APV, SSAO, brume de chaleur, heure du jour | V5 | 277 |
| V16 | 9 | La démo rejoue la partie et mesure la ville de fin de partie | tous | 278 |

Budget visé par image (1920×1080, 3070 Ti) : terrain 1 ms, bâtiments 4 ms, foule
2 ms, ombres 3 ms, post-traitement 2 ms, marge 4,7 ms.

### V1 — Le joueur trace une route qui épouse le relief

- **Quoi** : package `com.unity.splines` (registre Unity, gratuit). Le joueur pose
  des points ; la spline est échantillonnée tous les 0,5 m (le pas du terrain).
  Profil en long lissé qui suit le relief ; **pente > 12 % refusée** avec un
  message. Terrain aplani sous la largeur, talus 1:2 au-delà. Splatmap : deux
  couches de plus (terre battue, pavés), soit 6 couches (2 passes de terrain),
  bord irrégulier par bruit. Tout à l'exécution, sur une **copie** du TerrainData
  (l'asset reste intact), déterministe par graine.
- **Contrôle** (`py local3d/atelier_desert.py routes`) : un jeu de gestes fixe
  (dérivé des anciennes rues de `paysage.plan`) ; hauteur du terrain sous l'axe à
  ±3 cm du profil ; pente mesurée ≤ 12 % partout ; `CitadelTraversal` parcourt
  chaque route sans téléportation.
- **Contre-épreuves** : une route à 30 % doit être refusée ; un mur en travers
  doit arrêter le marcheur ; décaler le profil de 20 cm doit faire rougir.
- **Captures** : route sur la plaine, route à flanc de dune, talus, bord peint.
- ≈ 1 200 lignes C#.

### V2 — Les routes se croisent en carrefours et forment un graphe

- **Quoi** : accroche d'une extrémité à moins de 4 m d'une route existante ;
  coupure en T et en X ; placette au carrefour (profils mêlés comme
  `paysage.blend_profiles`) ; graphe nœuds/arêtes sérialisé (il servira aux
  trajets de V12).
- **Contrôle** : le graphe est connexe ; chaque carrefour a un seul niveau (écart
  ≤ 3 cm entre les profils qui s'y rejoignent) ; plus court chemin entre deux
  nœuds tirés au sort = parcouru par le marcheur.
- **Contre-épreuves** : une extrémité à 6 m ne s'accroche pas ; un carrefour
  désaligné de 30 cm rougit.

### V3 — La caméra de city builder

- Orbite, déplacement au clavier et au bord d'écran, zoom de 600 m à la rue (8 m),
  inclinaison qui suit le zoom, jamais sous le terrain ni au-delà de l'horizon de
  dunes. Rend toutes les captures suivantes comparables.
- **Contrôle** : 200 positions aléatoires de zoom/orbite → caméra toujours au-dessus
  du terrain + 1,5 m et dans la zone ; contre-épreuve : terrain relevé → rougit.

### V4 — Le kit de pisé s'emboîte sur la trame

- **Quoi** : dans `assets.py` / un nouveau `kit.py` Blender, ≈ 35 pièces sur trame
  0,75 m : murs 1,5 / 2,25 / 3 m, angles, porte, fenêtres (2 tailles), acrotère,
  merlons, escalier, auvent, soubassement de pierre 0,75 / 1,5 m, terrasse,
  parapet, gargouille, cheminée. 3 LOD, ≤ 1 500 triangles au LOD0 par pièce.
  **Pas d'IA** pour des pièces qui s'emboîtent.
- **Contrôle** : chaque pièce a ses cotes multiples de 0,75 m (à 1 mm), origine au
  sol, 3 LOD, budget tenu ; deux murs voisins n'ont ni trou ni recouvrement > 1 mm
  (mesuré sur leurs sommets d'about).
- **Contre-épreuve** : une pièce décalée de 5 cm rougit.

### V5 — Les matériaux photographiés

- **Quoi** : PBR **CC0** (Poly Haven, ambientCG ; gratuits, sans compte, mais c'est
  un téléchargement à confirmer par le propriétaire) : sable, pisé, enduit, grès,
  gravier, terre sèche, bois de palmier, ≈ 12 matériaux en 2K ; **trim sheet** pour
  encadrements, poutres, merlons. Megascans via Fab = compte, en option.
- **Contrôle** : chaque matériau a couleur + normale + masque, textures ≤ 2048,
  aucune texture procédurale restante sur le terrain et le kit ; licence CC0
  notée dans un `LICENCES.md`.

### V6 — Parcelles à la Manor Lords

- **Quoi** : quadrilatère à 4 points le long d'une route ; découpe en lots de
  **5 à 9 m de façade**, profondeur 12–25 m ; chaque lot reçoit une maison tirée du
  kit : largeur et profondeur du lot, 1 à 3 niveaux, **soubassement de pierre côté
  aval** selon la pente, mitoyenneté (mur partagé non doublé), façade et porte vers
  la rue. Graine par lot. Maisons fusionnées en un maillage par LOD à la pose (peu
  d'appels de rendu). Mesure la surface constructible (voir « plaine » plus haut).
- **Contrôle** : porte à ≤ 1 m du bord de la rue ; aucun chevauchement de volumes ;
  aucun coin flottant > 2 cm ni enterré > 5 cm ; même graine + mêmes gestes → même
  empreinte (hash des maillages).
- **Contre-épreuves** : lot tourné de 180° → porte loin de la rue → rougit ;
  graine changée → empreinte différente.

### V7 — L'arrière-cour vivante

- Puits, jarres, bois, linge, enclos, palmier, petit jardin, selon la graine et la
  surface de la cour. Accessoires : kit existant + Polylised (matériaux convertis
  comme `DesertDecor.cs`) ; **IA** (Meshy, Tripo, Rodin — payants — ou Hunyuan3D
  local) : sans clé, livrer `local3d/desert/import_ia/` avec la **liste de
  prompts** et un contrôle d'import (mètres, origine au sol, 3 LOD, budget).
- **Contrôle** : aucun accessoire hors de sa cour ni sur un passage ; chaque cour a
  ≥ 3 accessoires ; dossier d'import vide → le contrôle d'import échoue.

### V8 — Remparts au tracé libre

- Spline ouverte ou fermée ; tronçons de 3 et 6 m posés sur le relief, en gradins ;
  tours aux angles > 25° et tous les 30 m ; porte automatique là où une route
  croise (la route est forcée par la porte).
- **Contrôle** : chaque croisement route/enceinte a sa porte ; le marcheur la
  traverse ; aucun trou > 10 cm entre tronçons. Contre-épreuve : porte retirée →
  rougit.

### V9 — Bâtiments singuliers et noyau du ksar

- Mosquée, souk, marabout, puits, greniers (modules actuels) posés à la main,
  rotation, plateforme aplanie. Le ksar sur sa table de grès (falaises, remparts,
  mosquée, pont) est reposé depuis le manifeste Blender comme **noyau historique**,
  raccordé à la rampe de `paysage.field`.
- **Contrôle** : accès praticable (marcheur jusqu'au seuil) ; aucun chevauchement ;
  pont ↔ rampe à ≤ 5 cm.

### V10 — Le chantier se voit pousser

- 4 étapes par maison : piquets, fondations, murs sous échafaudages (perches,
  planches, échelles : nouvelles pièces du kit), toit. Durées courtes, pour la
  démo.
- **Contrôle** : chaque maison passe par les 4 étapes dans l'ordre ; aucune ne
  reste en chantier en fin de démo.

### V11 — Un habitant animé par textures (VAT)

- Habitant riggé : **Mixamo** (compte Adobe gratuit) ou silhouette et marche
  fabriquées dans Blender (sans compte). Animations marcher, porter, travailler
  **cuites en textures** (VAT) par un script Blender ; shader URP qui les lit ;
  `Graphics.RenderMeshInstanced` ou BatchRendererGroup. Dromadaire et âne pareil.
- **Contrôle** : 1 000 instances dessinées en ≤ 1,5 ms GPU (mesuré) ; la pose
  cuite ≈ la pose squelette (écart de sommets ≤ 2 cm sur 10 images).

### V12 — Les trajets sur le graphe des routes

- 800 habitants + 60 bêtes : maisons ↔ souk, jardins, portes, puits ; A* sur le
  graphe de V2 ; aucune économie, des trajets plausibles.
- **Contrôle** : 800 agents vivants ; tous à ≤ largeur/2 d'une route ; > 95 % ont
  bougé en 10 s ; aucun ne traverse un mur. Contre-épreuve : route coupée →
  les agents concernés se replanifient.

### V13 — Fumées, linge, étals, lanternes

- ≈ 60 fumées de cuisine, linge au vent (shader), étals garnis au souk,
  lanternes la nuit (émissif + peu de vraies lumières, URP Forward+).
- **Contrôle** : compte par maison dérivé des parcelles ; lumière la nuit mesurée
  sur capture (pixels chauds > seuil dans les rues).

### V14 — 60 images/s avec la ville dense

- **GPU Resident Drawer** et **GPU Occlusion Culling** (Unity 6). Ils exigent le
  **SRP Batcher**, coupé aujourd'hui à cause d'un ancien défaut de matériaux :
  le retester d'abord. LOD + **imposteurs au-delà de 250 m** (générateur maison ;
  Amplify Impostors = payant, en option).
- **Contrôle** : rendu identique avec/sans (écart de pixels) ; temps GPU par
  passe ; 95ᵉ centile < 16,7 ms sur la vue d'ensemble chargée.

### V15 — La lumière du désert

- Adaptive Probe Volumes (cuits pour la démo à graine fixe : une ville posée à
  l'exécution ne peut pas être précuite en jeu), SSAO, brume de chaleur (passe
  plein écran), poussière, heure du jour, ombres (cascades : corrige les
  pointillés des crêtes).
- **Contrôle** : captures midi / soir / nuit ; aucune zone noire (APV présent) ;
  coût de chaque effet mesuré.

### V16 — La démo et la mesure finale

- Script qui rejoue ≈ 60 routes, 90 parcelles, une enceinte, 12 bâtiments sur une
  graine fixe → **400 à 600 maisons**. Mesure dans le **joueur autonome**
  (comme `CitadelQuality`) : 8 vues × 6 s, médiane et 95ᵉ centile. Captures :
  ensemble, rue, cour, souk, nuit.
- **Contrôle** : nombre de maisons dans [400, 600] ; ≥ 800 habitants ; 95ᵉ centile
  < 16,7 ms ; captures non uniformes, regardées.

## Ce qui coûte de l'argent ou demande un compte

| quoi | pour | alternative gratuite |
|---|---|---|
| Mixamo (compte Adobe, gratuit) | habitant riggé, animations | silhouette et marche fabriquées dans Blender |
| Meshy / Tripo / Rodin (payants) | accessoires | liste de prompts + dossier d'import ; Hunyuan3D local (poids de plusieurs Go à télécharger) |
| Fab / Megascans (compte) | matériaux | Poly Haven, ambientCG (CC0) |
| Amplify Impostors (payant) | imposteurs | générateur maison |
| GitHub LFS au-delà du quota | binaires | sorties refaites par l'atelier, gros diagnostics en archive de Release |

Téléchargements gratuits sans compte à confirmer au début du lot concerné :
`com.unity.splines` (V1), `com.unity.burst` et `com.unity.collections` (V12),
matériaux CC0 (V5).

## Reprendre une session

1. Lire ce fichier, puis la fiche et le brief du lot suivant dans `ROADMAP.md`.
2. Vérifier que la V0 reproduit : `py local3d/atelier_desert.py terrain` doit
   passer (≈ 3 min, grilles réutilisées).
3. Travailler sur `agent/NNN-slug`, finir par : ce qui marche, captures
   regardées, ce qui reste — dans la PR.
