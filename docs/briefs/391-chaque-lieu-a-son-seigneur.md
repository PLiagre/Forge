# Lot #391 — Chaque lieu a son seigneur
Jalon : J3 · Machine : vps · Taille prévue : 295 lignes

## But
Le monde saura qui tient chaque lieu, afin que le joueur reconnaisse son domaine, ses voisins et le suzerain auquel il devra une part de ses récoltes.

## Le joueur
Le joueur voit, lieu par lieu, qui tient sa cellule : ses quatre lieux autour de son siège, ceux des seigneurs voisins, et au-dessus de lui son suzerain. C'est la première fois que le monde sait que la terre appartient à quelqu'un. Ce lot de fond rend cette tenure lisible dans `/lieu` et la photographie ; #401 la montrera dans la carte de la forge, #403 dans Unity. Il prépare le geste de J3 : fixer une part pour tout son domaine (#395), puis voir le grain monter vers son grenier (#396) et celui de son suzerain (#397), avec l'arbitrage entre prendre davantage et garder ses gens.

## Règle du monde
Dépend de : #390, registre et pyramide des maisons livrés. Appliquer la décision A du pilote : attribution, publication et adaptations de toutes les preuves strictes restent ensemble dans #391.

S'appuyer sur « Les maisons du monde » et « Ce que porte un lieu » de `jeu/sim/MODELE.md`. Ajouter `maitre` à `EtatDeLieu` : l'identifiant d'une maison de `World.maisons`, jamais un identifiant spatial. Un état construit à la main peut déclarer `maitre = None`, donnée absente ; tout lieu d'un monde chargé reçoit un maître. Préserver les constructeurs existants et leur déclaration explicite des données manquantes ; un `World(...)` d'épreuve ne charge toujours aucune table et n'invente aucun lieu.

Après l'amorçage des lieux et le chargement du registre, une attribution unique, sans tirage, parcourt cellules et rangs dans l'ordre. La placer dans `sim/maitres.py`, appelée par `World.charger`, avec une validation réutilisable sur un monde altéré. Réutiliser les sièges du registre et la couverture de `puissances_depuis_monde` ; ne pas déduire la puissance du seul siège d'une maison. Relire les deux constantes par `sim.constants` à chaque attribution.

1. Chaque seigneurie de départ tient les `LIEUX_DE_LA_SEIGNEURIE = 4` premiers rangs de la cellule de son siège, bourg compris ; si elle a moins de lieux, elle les tient tous.
2. Chaque grande maison tient les autres lieux encore libres de la cellule de sa capitale ; chaque institution tient ceux encore libres de la cellule de son siège. Les sièges hors carte restent déclarés tels quels, sans déplacement ni lieu inventé.
3. Dans une cellule couverte par une puissance, les rangs encore libres forment des groupes consécutifs de `LIEUX_PAR_SEIGNEUR_PLAUSIBLE = 3`, le dernier éventuellement plus petit. Chaque groupe appartient à une maison `plausible-<cell_id>-<premier rang>`, de sorte `plausible`, siégeant au premier lieu du groupe et relevant de `grande-<id maison>` ou `institution-<id puissance>` de cette puissance.
4. Dans une cellule non couverte, le même découpage crée des maisons plausibles sans suzerain. Chaque maison plausible entre dans le tuple gelé du registre, trié par `id` ; son siège garde seulement `cell_id` et `rang`, et `hors_carte = None`. Ses textes de nom et de siège peuvent reprendre son identifiant stable ; leur génération plausible appartient à #392.

Le lecteur des trois tables reste pur et conserve exactement ses fiches historiques ; l'attribution complète le registre détenu par le monde. Valider références des maîtres, unicité des maisons, sièges des plausibles et pyramide finale. Une référence absente ou inconnue doit faire échouer le contrôle en nommant le couple (`cell_id`, `rang`) ; aucun échantillon vide ne constitue une preuve.

Le tick ne lit ni les maîtres ni le registre. Ils persistent sans réattribution : hors ces nouveaux champs et fiches, tous les états, flottants, retours et tirages suivent exactement l'évolution précédente. `to_dict()` porte les maîtres et les maisons plausibles : l'empreinte change avec cette extension du monde, sans effet économique. Assurer une véritable écriture et lecture de `maitre` dans `model.py` pour les contrôles de couverture, sans modifier leur dénominateur ni ajouter une lecture au tick.

Étendre `lieux_en_photographie` : chaque entrée de lieu porte son `maitre`, dans la photographie et dans `/lieu`, toujours issue de `EtatPublie` au même tick. Conserver tous les anciens champs et leur précision, ainsi que le contrat léger de `/monde`. Régénérer depuis le service les deux réponses figées du pont et adapter les attentes de `LecteurJsonTests.cs`, en ajoutant la lecture du maître. Cette édition de texte ne demande ni Unity ni Blender : machine vps.

Niveau 1 : sièges, capitales et identités historiques déjà sourcés, conservés. Niveau 2, plausible, jamais sourcé : quatre lieux par départ, groupes de trois, maisons plausibles et leurs rattachements. Mettre à jour les deux sections du modèle et leurs mentions devenues fausses sur la propriété, la publication et le registre initial. Budget du diff, brief compris : attribution et raccordements 65 lignes, cas ajoutés 105, adaptations strictes 40, modèle 15, fichiers figés 4, brief 66 ; total prévu 295, rester sous 300.

## Périmètre
jeu/sim/model.py
jeu/sim/constants.py
jeu/sim/world.py
jeu/sim/maitres.py
jeu/sim/snapshot_export.py
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/test_monde.py
jeu/forge/tests/test_forge.py
jeu/sim/MODELE.md
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs

## Conditions de succès
Commandes depuis la racine, sauf mention contraire. Ajouter les cas dans le fichier portant l'invariant, noms contenant `maitre`, et constater leur rouge avant l'implémentation. Références et compteurs dérivés des lieux, tables et constantes ; vérifier des échantillons non vides pour chaque branche. Tout autre chemin que ceux du périmètre est interdit.

Inventaire des preuves à adapter selon A : dans `test_lieux.py`, `test_amorcage_conserve_habitants_et_panier` et `test_photographie_et_empreinte_portent_les_lieux` gardent leurs ensembles exacts, augmentés de `maitre` ; dans `test_monde.py`, `_CLES_D_UN_LIEU` est augmenté de même. Dans `test_maisons.py`, `test_registre_world` conserve la comparaison exacte des fiches issues des tables et ajoute la complétude exacte des plausibles ; les preuves du lecteur pur restent intactes. Dans `test_determinisme.py`, `test_registre_bit_pres` compare tous les anciens champs et vérifie séparément les nouveaux. Dans `test_monde.py`, les deux tests de réponses figées et `test_service_ia_sans`, et dans `test_forge.py`, `test_forge_ia_sans`, conservent leurs égalités exactes avec références régénérées après preuve de conservation. Les attentes du lecteur C# gardent les anciennes valeurs et ajoutent `maitre`. Aucun arrondi, tolérance, exclusion d'ancien champ ou suppression de contre-épreuve.

SC1 — `python3 -m pytest jeu/sim/tests/test_lieux.py -q -k maitre` contrôle tous les lieux du monde chargé : un maître non vide chacun, présent dans un registre sans doublons ; la somme des effectifs par maître égale exactement le nombre dérivé de lieux. Contre-épreuves : mettre un maître à `None`, à un identifiant inconnu, retirer sa fiche, dupliquer une fiche ou vider l'échantillon fait échouer le même contrôle.

SC2 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k maitre` vérifie chaque départ, son bourg et ses premiers rangs, chaque capitale et siège institutionnel placés, et la priorité des départs sur les lieux déjà pris. Ajouter une cellule à moins de quatre lieux et une cellule synthétique où départ et grande maison partagent le siège : le départ garde ses rangs, la grande maison reçoit seulement le reste. Contre-épreuves : attribuer le bourg d'un départ à une autre maison, ou un lieu libre de capitale à un plausible, fait échouer les assertions correspondantes.

SC3 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k maitre` contrôle exactement les groupes, identifiants, premiers rangs, sièges, sortes et suzerains des plausibles, depuis les rangs libres et la couverture. Éprouver puissance avec grande maison, puissance avec institution, cellule non couverte et dernier groupe incomplet ; remplacer séparément chaque constante en mémoire change l'attribution attendue. Aucun plausible ne tient un lieu hors de sa cellule. Contre-épreuves : déplacer un lieu vers un plausible d'une autre cellule, fusionner deux groupes, retirer une fiche ou donner une mauvaise racine connue échoue ; référence suzeraine inconnue et cycle restent refusés par la validation du registre.

SC4 — `python3 -m pytest jeu/sim/tests/test_determinisme.py -q -k 'registre_bit_pres or maitre'` compare 366 points, amorçage puis 365 ticks, pour les quatre couples de graines déjà éprouvés. Construire le témoin en désactivant explicitement l'attribution neuve et le registre comme auparavant ; comparer sans arrondi tous les anciens champs des lieux et cellules, plans, mer, carte, graphe, retours et état du générateur. Comparer séparément, à chaque point, maîtres et registre complet à leurs valeurs initiales ; les permutations de cellules et du registre ne changent pas l'attribution. Contre-épreuves : altérer d'une unité le dernier bit d'un ancien stock échoue toujours, changer un maître ou une fiche échoue au contrôle de stabilité, ajouter une lecture des maîtres au tick déclenche une garde dédiée ; la comparaison vide échoue.

SC5 — `python3 -m pytest jeu/sim/tests/test_lieux.py jeu/sim/tests/test_monde.py -q -k 'maitre or photographie_et_empreinte or service_lieu_porte_les_lieux or reponse_figee_du_pont or service_ia_sans'` vérifie la lecture exacte des maîtres de chaque lieu dans la photographie et `/lieu` au même tick, sans nouvelle clé spatiale. Les fichiers figés aux ticks 3 et 4 sont exactement les octets du service ; leurs valeurs anciennes restent identiques après retrait du seul champ ajouté. Les attentes C# reprennent ces données et gardent les vérifications des paniers, métiers, totaux et JSON refusés. Contre-épreuves : retirer ou falsifier un maître dans une copie de sortie échoue ; une copie figée modifiée échoue à l'égalité ; modifier seulement un maître valide modifie les empreintes du monde et de sa photographie.

SC6 — `python3 -m pytest jeu/forge/tests/test_forge.py -q -k 'ia_sans or maitre'` conserve les empreintes strictes de Forge aux ticks 0 et 30, régénérées avec les maîtres. Ajouter une comparaison exacte des anciens champs aux références antérieures en retirant uniquement `maitre` des lieux de la photographie ; faire de même pour les empreintes du service dans SC5, sans changer `/monde`. Contre-épreuves : altérer un ancien nombre ou ajouter une sortie IA sans option fait encore échouer ces comparaisons ; retirer le nouveau champ échoue à la preuve de publication.

SC7 — `python3 -m pytest jeu -q` passe, y compris couverture des champs et constantes, nombres magiques, conservation des lieux, registre, choix du joueur, sélection IA et preuves historiques. Contre-épreuves : conserver leurs mutations déjà présentes ; une omission de `maitre` dans l'écriture ou la lecture du modèle doit faire échouer `python3 -m pytest jeu/sim/tests/test_write_coverage.py -q`. Relire `MODELE.md` contre SC1 à SC6 : il décrit l'attribution réelle et distingue l'absence déclarée des mondes manuels d'un monde chargé complet.

## Hors périmètre
Noms plausibles de #392, géométrie interne des lieux, greniers, prélèvements, convois, dû matériel au suzerain, départs sous pression fiscale et redistribution. Aucun changement de maître en cours de partie, intention nouvelle ou décision d'IA ; aucune nouvelle maison dans la sélection IA existante. Aucun changement aux tables historiques, sièges sourcés, polygones, anciennes tenures dérivées, calculs économiques ou effectifs. Aucun écran, lancement Unity, Blender ou modification du lecteur JSON de production ; seuls les textes de preuve du pont sont actualisés.
