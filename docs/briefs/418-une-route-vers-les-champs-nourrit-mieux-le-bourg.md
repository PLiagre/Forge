# Lot #418 — Une route vers les champs nourrit mieux le bourg
Jalon : J4 · Machine : vps · Taille prévue : 280 lignes

## But
Une route achevée qui part du bourg vers un lieu de sa cellule quadruple le chemin de ce lieu vers le bourg : le bourg affamé à côté d'un champ plein mange plus tôt.

## Le joueur
Une route vers les champs rapproche les récoltes du bourg ; une route vers le voisin fait venir le commerce (#259, déjà livré). Le joueur choisit laquelle d'abord : c'est la seconde décision du jalon 4 (« une route vers les champs, ou vers le marché »).

Après ce lot, le geste existant `tracer_route` (déposé depuis Unity, #374–#377, ou par le service) a un second effet. Une fois la route achevée, si elle part dans la direction d'un champ de la cellule, ce champ envoie quatre fois plus de grain au bourg. Le panneau du jalon 1 montre déjà la faim et la dette de la cellule : le joueur voit la faim tomber plus vite qu'avant la route. S'il trace vers le désert, rien ne change, et le monde dit qu'aucun lieu n'est dans cette direction. Une route a donc un prix (des bras pris aux champs pendant le chantier, #257) et deux usages qui s'excluent : une porte vers le voisin, ou un chemin vers ses champs. Le panneau qui dira ce qu'un chantier coûte et rapporte est #419.

## Règle du monde
Section de `jeu/sim/MODELE.md` : « La distribution à l'intérieur de la cellule » (la route), avec une phrase dans « Le plan du bourg ». Niveau 2 : plausible, jamais sourcé.

**Quelle route compte.** Une rue du plan du bourg (`World.plans[cell_id]`) qui est achevée (`en_chantier` faux) et sans `porte_cell_id`. Une route qui porte une porte va vers le voisin (#259) : elle ne compte pas ici, et une même route ne sert donc jamais aux deux usages.

**Vers quel lieu.**
- L'extrémité qui sort du bourg est celui des deux bouts (premier ou dernier point) qui est le plus loin de l'origine du plan, c'est-à-dire du centre du bourg. En cas d'égalité, c'est le dernier point.
- Sa direction est `θ = atan2(y, x)`, dans le repère du plan : x vers l'est, y vers le nord.
- Chaque lieu de rang ≥ 1 a sa direction `φ = atan2(y_k − y_0, x_k − x_0)`, calculée depuis les places de #393 (`places_de_cellule`, EPSG:3035, mêmes axes).
- L'écart vaut `|atan2(sin(θ − φ), cos(θ − φ))|`. Le lieu retenu est celui de plus petit écart, à condition que cet écart ne dépasse pas `ANGLE_ROUTE_INTERIEURE_DEGRES = 30`. À écart égal, c'est le plus petit rang qui l'emporte.
- Sinon, aucun lieu n'est retenu, et la raison est déclarée : « aucun lieu à moins de 30° (le plus proche, rang k, à X°) », « route sans direction » (extrémité à l'origine), « un seul lieu », ou « ancres des bourgs absentes ».
- La longueur de la route ne compte pas (niveau 3).

**Ce que la route change.** Chaque lieu atteint par au moins une route compte voit la capacité de son chemin vers le bourg multipliée par `FACTEUR_ROUTE_INTERIEURE = 4` (la terre battue contre la piste) : `c × 4` au lieu de `c = capacite_chemins_interieurs_kg(1, facteur_transport)`. L'effet ne se cumule pas : deux routes vers le même lieu font ×4. La même capacité par rang sert aux deux usages du chemin :
- la consommation : l'étoile de `_apply_consumption` (demande, envois par rang croissant, service) ;
- le commerce : le dictionnaire `chemins[cid][rang]` que `_surplus` initialise et que `_sortir_par_bourg` consomme.

Les facteurs se calculent une fois par tick, après Chantiers (comme la porte, une route achevée ce jour sert dès ce tick), et seulement pour les cellules qui ont une route qui compte. Sans une telle route, aucune place n'est calculée et tout reste identique au bit près. Le chemin « sans lieux » (`_nourriture_accessible_au_rang0_kg`) ne change pas.

**Le tick ne lit pas le maître** (« Les maisons du monde » : « Le tick ne lit ni les maîtres ni le registre »). Or la place du bourg dépend du siège de son maître. `World.charger` garde donc, après l'attribution des maîtres, `ancres_des_bourgs` : un dictionnaire `cell_id → (siège du maître du bourg ou None, ville placée ou None)`, c'est-à-dire exactement les deux arguments que `places_du_monde` passe aujourd'hui à `places_de_cellule`. Cet attribut est posé comme `populations_bourg_amorcage` : il reste hors de `to_dict` et de l'empreinte. Un `World(...)` construit à la main le porte à `None`, et sa route est déclarée « ancres des bourgs absentes », sans effet. Le tick appelle `places_de_cellule(cid, carte[cid], surfaces, *ancres[cid])` pour les seules cellules routées : il ne lit ni `EtatDeLieu.maitre`, ni le registre, ni `attribution_villes`. Un changement de maître reste de niveau 3 ; le lot qui l'introduira recalculera ces ancres.

**L'IA** passe par le même geste : ses routes `(0, y)→(40, y)` partent vers l'est et nourriront un champ s'il y en a un à 30° de là. Le monde `--ia` change donc ; le monde sans IA, sans geste, ne change pas.

## Périmètre
jeu/sim/constants.py
jeu/sim/routes_interieures.py
jeu/sim/places.py
jeu/sim/world.py
jeu/sim/engine.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_distribution_interieure.py

## Conditions de succès
Les commandes se lancent depuis `jeu/`. Les cas neufs vont dans `sim/tests/test_distribution_interieure.py`, qui porte l'invariant de la distribution intérieure.

**SC1 — le lieu de la route** : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -k route_vers_lieu`.
- `sim/routes_interieures.py` expose une fonction pure `lieu_de_la_route(rue, places)` qui rend `(rang ou None, raison)`. Sur les places réelles d'une cellule de `World.charger(0)` qui a au moins deux lieux :
  - une route pointée exactement vers le lieu k rend k ;
  - tournée de 29°, elle rend encore k (si aucun autre lieu n'est plus proche en angle) ;
  - tournée de 31°, alors qu'aucun lieu n'est à 30°, elle rend None, avec une raison qui contient « 30 » ;
  - une route dont l'extrémité est l'origine rend None, « sans direction ».
- Sur des places synthétiques, deux lieux à écart égal donnent le plus petit rang, et l'extrémité la plus lointaine est bien celle qui décide (une route tracée de l'extérieur vers le centre vise le même lieu qu'à l'endroit).
- `routes_vers_les_lieux(monde, cell_id)` ignore une route en chantier et une route à porte.
- Contre-épreuve : comparer à l'extrémité la plus proche du centre, ou mesurer l'écart sans le ramener dans [−π, π] (une route à +179° contre un lieu à −179°), fait échouer un des cas.

**SC2 — la capacité exacte d'une route dans l'étoile** : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -k route_capacite`.
- Montage : `_cellule_par_lieu([20, 1, 1], [0, 6, 200])`, en plaine, avec `CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK = 5`.
- Sans route : pénurie 31 kg, paniers finaux `[0, 0, 193]`.
- Avec route vers le rang 2 (`facteurs={2: 4}` passé à `_apply_consumption`) : pénurie 16 kg, paniers `[0, 0, 178]`. La dette monte d'autant, la somme reste exacte en `Fraction` (`_controle_par_lieu`).
- Avec route vers le rang 1 (champ presque vide) : pénurie 31 kg, comme sans route.
- Contre-épreuve : la même cellule avec un facteur appliqué à tous les rangs ne donne pas 16.

**SC3 — le commerce emprunte la même route** : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -k route_commerce`.
- Dans la cellule de SC4, le dictionnaire `chemins` passé à `engine._apply_commerce` est initialisé à `4 × c` pour le rang routé et à `c` pour les autres.
- Contre-épreuve : sans route, tous les rangs valent `c`.

**SC4 — l'épreuve : la route vers le champ nourrit le bourg plus vite** (direction, pas valeur) : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -k route_nourrit_le_bourg`.
- Montage : `World.charger(0)`, graine 0, 30 ticks avec `numero_tick`.
- La cellule est dérivée des données, jamais nommée : c'est la première par `cell_id` où, sans route, le bourg a une pénurie strictement positive à un tick où un champ garde de la nourriture. Le champ visé est celui de plus grand panier à ce tick.
- On pose au tick 0, dans `World.plans`, une rue achevée de 4 m de large, de `(0, 0)` vers ce champ.
- Exigé : le nombre de ticks de faim du bourg et la somme de ses pénuries sur 30 ticks sont strictement plus bas qu'avec le même monde sans route.
- Mesure du chef (prototype sur la consommation seule) : cellule 1385, champ de rang 1 à −127°, 6 ticks de faim et 10 698 kg de pénurie sans route, 0 et 0 avec. Le test imprime ses valeurs, et le MODELE cite la mesure finale.
- Contre-épreuve : avec `FACTEUR_ROUTE_INTERIEURE = 1`, l'assertion de direction échoue (`pytest.raises(AssertionError)`).

**SC5 — la route vers le désert ne change rien, et le dit** : même fichier, `-k route_vers_le_desert`.
- Même cellule, route tournée de 180° depuis le champ (aucun lieu à 30°).
- Après 30 ticks, `to_dict()` sans la clé `plans` est égal à celui du monde sans route.
- `routes_vers_les_lieux` rend None et sa raison dit qu'aucun lieu n'est à moins de 30°.
- Contre-épreuve : la route de SC4 fait différer ce même `to_dict()`.

**SC6 — sans route, rien ne bouge et rien ne se calcule** : même fichier, `-k sans_route`.
- `World.charger(0)` joue 30 ticks avec `places.places_de_cellule` remplacée par une fonction qui échoue : aucun appel.
- Une route en chantier ou une route à porte ne déclenche pas non plus de calcul de places.
- Les empreintes figées existantes restent vertes, sans retouche : `test_forge_ia_sans`, `test_service_reponse_figee_*`, `test_determinisme.py`.
- Contre-épreuve : avec une route achevée vers un champ, la fonction qui échoue est appelée.

**SC7 — le tick routé ne lit pas le maître** : même fichier, `-k route_sans_maitre`.
- Le monde de SC4 avec sa route joue un tick sous la garde de `test_maitre_tick` (`EtatDeLieu.maitre` qui lève, `attribuer_maitres` qui lève). Il passe, et le facteur s'applique.
- `World.charger(0).ancres_des_bourgs` redonne, pour chaque cellule, exactement `places_du_monde(monde)` par `places_de_cellule(cid, carte[cid], surfaces, *ancres[cid])`. Ce dictionnaire est absent de `to_dict()`, et vaut `None` pour un `World(...)` construit à la main.
- Contre-épreuve : un tick qui calcule les places par `places_du_monde(world)` lève sous la garde.

**SC8 — les constantes et le texte** : `python3 -m pytest sim/tests/test_write_coverage.py sim/tests/test_no_hardcoded.py -q` et `-k route_documentee`.
- Les deux constantes sont dans `constants.py`, avec leur niveau. Elles sont lues par `_constantes.X` dans `sim/routes_interieures.py`, jamais par leur nom dans `sim/engine.py` : le monde d'épreuve n'a ni carte ni plan, et une constante lue par le moteur y serait inerte.
- Aucun littéral hors {0, 1, −1} dans une fonction : utiliser `math.radians`, `math.atan2`, `math.pi`.
- La section « La distribution à l'intérieur de la cellule » contient `FACTEUR_ROUTE_INTERIEURE`, `ANGLE_ROUTE_INTERIEURE_DEGRES`, `porte_cell_id`, `ancres_des_bourgs` et « niveau 2 », et garde tous les mots de `test_distribution_par_lieu_documentee`.
- « Le plan du bourg » ne dit plus que les effets locaux des rues achevées sont de niveau 3 sans nommer la route vers un lieu.
- `sim/README.md` cite `sim/routes_interieures.py`.
- Contre-épreuve : le texte sans `FACTEUR_ROUTE_INTERIEURE` fait échouer le test.

**SC9 — le budget du tick** : `python3 -m pytest sim/tests/test_monde.py -q -k budget`. Il reste vert sans retouche. Le MODELE donne la durée d'un tick avec dix cellules routées, mesurée sur le VPS.

## Hors périmètre
- **Le jour gagné par les convois de prélèvement.** L'issue veut qu'une route raccourcisse d'un jour la route des convois de ce lieu, sans descendre sous un jour. Mais les convois n'existent pas sur la base : ils arrivent avec #396 (jalon 3), dont la question est encore ouverte le 11/10. Ce qui n'est pas sur la base n'existe pas. Cette règle est à ajouter à #396, ou au lot qui la suivra ; le MODELE de ce lot ne la mentionne pas comme faite.
- Montrer la direction et la raison dans `/plan`, dans la photographie ou dans Unity (#419) ; le contrat `/plan` et ses octets ne changent pas.
- La longueur de la route, son usure, son effet sur le rendement ou sur la migration ; plusieurs routes qui se cumulent ; une route d'un champ à un autre champ.
- Un cache des places entre deux ticks, et toute réécriture de `places_du_monde` dans le service ou la photographie au-delà de l'extraction des ancres.
- Le changement de maître et le recalcul des ancres (niveau 3).
- La décision de l'IA de viser ses champs : son tracé `(0, y)→(40, y)` ne change pas.
