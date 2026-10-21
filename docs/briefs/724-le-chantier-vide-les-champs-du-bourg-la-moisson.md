# Lot #724 — Le chantier vide les champs du bourg, la moisson ceux de chaque lieu : les preuves
Jalon : J4 · Machine : vps · Taille prévue : 230 lignes

## But
Prouver par des cas ajoutés à `test_foyers.py` que la récolte de chaque lieu suit ses propres bras et la saison, et que les ouvriers et les artisans du chantier ne vident que les champs du bourg. Quand tous les lieux ont assez de bras, la récolte doit rester identique à l'octet près à celle de l'ancien partage.

## Le joueur
Le joueur paiera ses chantiers en récolte perdue, mais seulement là où le chantier prend des bras et seulement quand la saison en demande : en juillet, son bourg vidé par le chantier ne moissonne plus, alors que ses hameaux récoltent comme avant ; en janvier, les mêmes bras suffisent. Il prépare la décision du jalon 4 : « des bras au chantier, c'est moins de bras aux champs ; à la moisson, de la récolte perdue ». Lot de fond : il verrouille la règle livrée par #723. Le panneau #419 rendra ce coût visible, et la preuve complète #508 le montrera dans la capitale jouée.

Dépend de : #723, fusionné sur la base `c126e40`, ses tests de récolte sont verts. Rien n'attend le jalon 3. Lot issu de #719 : le second sous-lot, les preuves seules.

## Règle du monde
Sans changement : ce lot prouve la règle de #723 sans la modifier. Elle vient de « Les foyers par métier » et de « Le chantier et ses bras », dans `jeu/sim/MODELE.md` (niveau 2, plausible).

- Besoin d'un lieu = `km² cultivés du lieu × BRAS_AUX_CHAMPS_PAR_KM2 × facteur de saison de la production`. Les km² cultivés du lieu valent sa surface multipliée par les facteurs de relief, d'eau et de part agricole de sa cellule.
- Paysans d'un hameau = sa population. Paysans du bourg = `max(0, population du bourg − non-paysans de la cellule)`.
- Part d'un lieu = `récolte × surface / area_km2 × min(1, paysans / besoin)`. Si aucun lieu ne manque de bras, l'ancien partage s'applique tel quel.

## Périmètre
jeu/sim/tests/test_foyers.py

## Conditions de succès
Les commandes se lancent depuis la racine. On n'ajoute que des fonctions de test, sans modifier aucune ligne existante de `test_foyers.py`, et on ne touche ni au moteur ni à `MODELE.md`. On réutilise `_km2_cultives_reference` et les aides déjà présentes.

Les références se calculent dans le test, à partir des surfaces (`lieux.surfaces_des_lieux`), des populations, des constantes et du climat de la carte. Elles n'appellent jamais `foyers.facteur_bras`.

Chaque contre-épreuve remplace une fonction le temps d'un `monkeypatch.context()`. Elle doit faire échouer le même vérificateur que le cas nominal (`pytest.raises(AssertionError)`). Une précondition non tenue fait échouer le test ; elle ne le saute jamais.

Le jour 0 est le 1er janvier, et le solstice d'été le jour 172. On prend le jour 14 pour janvier et le jour 195 pour juillet.

SC1 — **Juillet manque de bras, janvier non.** Commande : `python3 -m pytest jeu/sim/tests/test_foyers.py -q -k juillet`.

Prendre une cellule de `World.charger(0)` qui a exactement deux lieux, dans l'hémisphère nord, avec des km² cultivés non nuls. Repère : la cellule 1274, saison 0,803 en janvier et 1,199 en juillet, besoin d'environ 149,7 bras par lieu sans saison. Les totaux sont cohérents : population de la cellule = somme des populations des lieux, et tous les habitants sont paysans.

Le premier lieu manque de bras en juillet seulement. Son rapport `paysans / (km² cultivés du lieu × constante)` est strictement entre 1 et le facteur de juillet ; l'asserter (repère : 164 paysans, rapport 1,096). L'autre lieu a assez de bras aux deux dates.

Appeler `engine._apply_production` aux jours 14 et 195, avec un relevé et des stocks antérieurs non nuls. À chaque date, comparer chaque part du relevé et chaque stock local à la formule (`rel=1e-12`), et le total cellulaire à leur somme. Calculer les kilos perdus comme part pleine moins part relevée. Exiger exactement 0 kg perdu partout en janvier, et plus de 0 kg perdu au premier lieu en juillet (repère : environ 3 751 kg). Ne pas comparer la récolte brute de juillet à celle de janvier : juillet produit plus même sans la règle.

Contre-épreuves, toutes rejetées par le vérificateur :
- le besoin sans saison : `foyers.facteur_bras` reçoit la surface divisée par la saison du jour testé. Juillet ne perd alors plus rien ;
- un facteur cellulaire commun : chaque appel de `foyers.facteur_bras` rend le facteur de son premier appel pour la cellule, celui de toute la cellule.

SC2 — **Le chantier ne vide que les champs du bourg.** Commande : `python3 -m pytest jeu/sim/tests/test_foyers.py -q -k non_paysans`.

Prendre une cellule à au moins trois lieux (repère : la cellule 10405, 34 lieux). Le bourg compte moins d'habitants que les non-paysans de la cellule (repère : 5 habitants pour 7 ouvriers et 5 artisans). Un hameau a moitié moins de paysans que son besoin. Les autres hameaux ont dix fois leur besoin. La population de la cellule est la somme des lieux, et les métiers en font le total.

Jouer le chemin journalier au jour 195 avec un relevé. Rejouer ensuite la même cellule avec les mêmes populations, mais avec tous les habitants paysans. Exiger :
- une récolte du bourg nulle et jamais négative, au relevé comme en stock (le stock du bourg ne descend jamais sous son stock antérieur) ;
- des parts de chaque hameau égales à l'octet près entre les deux métiers, et égales à leur formule.

Contre-épreuves, rejetées par le vérificateur :
- le plancher retiré : la fonction `max` vue par `sim.engine` rend son second argument quand le premier vaut 0. La part du bourg devient alors négative (repère : environ −1 694 kg) ;
- les ouvriers soustraits à chaque lieu : `foyers.facteur_bras` retire les non-paysans de la cellule quand ses métiers ne contiennent que des paysans, c'est-à-dire pour l'appel d'un hameau. Le hameau à court de bras perd plus qu'il ne devrait.

SC3 — **Tous pourvus, rien ne bouge.** Commande : `python3 -m pytest jeu/sim/tests/test_foyers.py -q -k ancien_partage`.

Sur `World.charger(0)`, vérifier d'abord, par le calcul du test, que tous les lieux ont assez de bras aux dates jouées. Vérifier aussi que des cellules à plusieurs lieux sont jouées.

Recopier dans le test l'ancien corps de `_apply_production` et de `_apply_production_saison_moyenne` d'avant #723 (`c126e40^`), sans le facteur de bras qui valait 1. Ce sont : le tirage, `production_du_tick_kg(..., jour=jour)` ou `_production_du_tick_kg_saison_moyenne`, l'écriture du stock cellulaire, puis `_produire_sur_les_lieux`, capturé avant tout remplacement.

Jouer toutes les cellules de deux copies du monde, chacune avec son propre `random.Random` à la même graine : l'une par le moteur, l'autre par cette référence. Couvrir :
- le chemin journalier aux jours 0 et 195, et le chemin moyen ;
- chacun avec et sans relevé.

Exiger l'identité à l'octet de :
- chaque stock cellulaire et local ;
- les relevés sérialisés ;
- `json.dumps(monde.to_dict(), sort_keys=True)` ;
- `rng.getstate()`.

Le prototype tient en moins d'une seconde par combinaison.

Contre-épreuve : un `_produire_sur_les_lieux` du moteur qui ajoute 1 kg à la part locale d'un hameau, côté moteur seulement, est rejeté.

SC4 — **Rien d'autre ne bouge.** Commandes : `python3 -m pytest jeu/sim/tests/test_foyers.py -q`, puis `python3 -m pytest jeu -q`.

Tous verts. `git diff --stat` ne montre que `test_foyers.py` et ce brief, et aucune ligne existante n'y est retirée.

## Hors périmètre
Ce lot ne change pas le moteur (`engine.py`, `foyers.py`, `constants.py`, `lieux.py`), ni `MODELE.md`, ni aucun autre test. Il ne modifie et n'assouplit aucun cas existant. Il ne crée pas de règle nouvelle et ne recalibre ni la constante de bras ni la saison. Il ne fait pas de panneau #419, ni Unity, ni capture, ni la preuve #508. Il ne touche pas aux salaires, au financement ou à l'affectation des chantiers. `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md` et `CAP.md` sont interdits.
