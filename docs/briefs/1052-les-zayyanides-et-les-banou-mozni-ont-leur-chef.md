# Lot #1052 — Les Zayyanides et les Banou Mozni ont leur chef
Jalon : J5 · Machine : vps · Taille prévue : 90 lignes

## But
Le sultan de Tlemcen (`grande-24`) et l'émir du Zab (`seigneurie-6`) ont un chef au 1er janvier 1400 : leurs maisons gagnent chaque mois de la Plume, du Sceau et de l'Épée, comme les autres maisons de la carte.

## Le joueur
Le joueur voit ces deux voisins du Maghreb gagner chaque mois de la Plume, du Sceau et de l'Épée comme les autres : ils ont de quoi agir, et lui des raisons de s'en méfier. Le panneau du pays (#1045) et la barre (#1032) affichent leurs réserves et le nom de leur chef, au lieu d'« aucun point ». Le lot prépare un geste du jalon J5 : regarder toutes les maisons gouverner seules, et choisir un pays après l'avoir vu vivre. Il sert le lot #1027, dont c'est le premier des trois sous-lots. Le sous-lot 3, l'IA qui dépense un geste de points par mois, rendra visible ce que ces deux maisons font de leurs réserves.

## Règle du monde
Elle découle de `jeu/sim/MODELE.md`, section « Le pays et ses jauges », point « Les compétences ». Le chef de la maison (`World.chefs`) a une compétence par domaine, tirée de `personne-<maison>`. Chaque mois, chaque réserve reçoit la compétence de son domaine fois `par_point_de_competence_par_mois` (0,5, dans `jeu/data/jauges.toml`). Une maison dont le chef n'est pas connu n'a pas de compétence, et le dit (`absents.competences`). La règle ne change pas : le lot remplit deux fiches. La section de MODELE.md ne change pas non plus.

Fidélité (principe 7, « réel quand on sait, plausible sinon ») :
- **Tlemcen, `grande-24` : réel, niveau de vraisemblance 1.** La page `https://en.wikipedia.org/wiki/Zayyanid_dynasty` donne Abu Muhammad Ier (1397–1400), puis Abu Abdallah Ier (1400–1411), sans dater la succession dans l'année 1400. Le titulaire au 1er janvier 1400 est donc celui dont le règne court déjà à cette date (Abu Muhammad Ier, sous le nom exact que donne la page). Le codeur relit la page avant d'écrire. Le champ `fait` dit le règne que donne la page, et la divergence : la succession n'est pas datée, et le choix du 1er janvier en découle.
- **Zab, `seigneurie-6` : réel s'il existe une page publique qui nomme l'émir des Banou Mozni à Biskra au 1er janvier 1400**, ou le dernier émir attesté avant cette date. Le codeur s'accorde deux lectures de pages au plus : `Zab_Emirate`, puis une page sur les Banou Mozni ou sur Biskra. Le champ `fait` dit alors ce que nomme la page, et l'écart de dates s'il y en a un. **Plausible et déclaré sinon**, comme le demande l'issue : un nom d'émir de la lignée, formé sur ceux que la page cite (« … ibn Mozni »). Sa source `identite` est la page qui atteste les Banou Mozni émirs à Biskra. Son `fait` le déclare en toutes lettres, par exemple : « La page atteste les Banou Mozni émirs du Zab à Biskra en 1400 sans nommer le titulaire ; ce nom est plausible et déclaré (principe 7), aucun fait ne le confirme. » Le niveau de vraisemblance est 1 si une page nomme l'émir, 3 s'il est plausible. La PR dit lequel des deux cas s'applique.
- Les naissances restent `null`, avec leur `lacune`, sauf si la même page en donne une.

Le chargement (`valider_catalogue`, `jeu/sim/personnages.py:28-72`) ne change pas : il refuse tout nom qui n'a pas de source `{url, fait}`. La contre-épreuve SC4 en dépend.

## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_pays_et_jauges.py

## Conditions de succès
- **SC1. Les deux fiches sont remplies.** Dans `personnages-1400.json`, les entrées `chefs` de `grande-24` et de `seigneurie-6` ont un `nom`, une source `identite` `{url, fait}` dont le `fait` n'est pas vide, et une `lacunes.identite` à `null`. Dans `test_maisons.py`, `_personnages_attestes` les sort de la liste des chefs sans nom (ligne 1475, où `grande-21` reste) et les fait entrer dans des assertions de chefs nommés : `nom` non nul, nom de la page dans `url`, `fait` non vide. La ligne 1477 garde `seigneurie-6` tant que sa naissance reste `null`. `test_personnages_attestes` ajoute une altération qui remet `nom` à `None` sur chacune des deux fiches, et l'assertion doit alors tomber.
  Commande : `cd jeu && python -m pytest sim/tests/test_maisons.py -k "personnages_attestes" -q`.
  Contre-épreuve : sur master, les fiches à `nom: null` font rougir les nouvelles assertions.
- **SC2. Les tests qui prenaient ces maisons pour exemples de maisons sans chef passent sur `grande-21`, aussi stricts.** Dans `test_maisons.py`, `seigneurie-6` devient `grande-21` aux lignes 1497, 1559, 1606 et 1620, ainsi que dans la mutation `('maison', 'seigneurie-6')` de la ligne 2109 (`test_familles_etats` : un état posé sur une maison sans chef reste refusé). Aucune assertion n'est retirée, et aucun `pytest.raises` n'est élargi.
  Commande : `cd jeu && python -m pytest sim/tests/test_maisons.py -k "personnages or personnes or familles_etats" -q`.
  Contre-épreuve : laisser `seigneurie-6` à la ligne 2109 fait accepter la mutation, puisque la maison a maintenant un chef, et le test rougit.
- **SC3. La preuve : deux mois de points.** Un test neuf de `test_pays_et_jauges.py`, `test_les_chefs_du_maghreb_gagnent_leurs_points`, suit le modèle de `test_les_points_naissent_chaque_mois_des_competences` (ligne 155). On joue `2 * c.FENETRE_FLUX_TICKS + 1` ticks. Puis, pour `grande-24` et `seigneurie-6`, `J.competences` n'est pas `None`, et chaque réserve (Plume, Sceau, Épée) vaut `pytest.approx(2 * comp[domaine] * par_point_de_competence_par_mois)`. `J.document_des_jauges(monde, maison, regles)["absents"] == {}`. La somme des six réserves est strictement positive : une compétence peut valoir 0, mais toutes à la fois, la preuve serait vide.
  Commande : `cd jeu && python -m pytest sim/tests/test_pays_et_jauges.py -k "chefs_du_maghreb" -q`.
  Contre-épreuve : sur master, `J.competences` renvoie `None` pour les deux maisons, et le test rougit.
- **SC4. Contre-épreuve du chargement : un chef nommé sans source est refusé.** Dans le même test, ou dans un test voisin de `test_maisons.py`, on copie le catalogue et on y écrit `sources.identite = None` sur la fiche de `seigneurie-6`, puis sur celle de `grande-24`, en gardant le `nom`. Le test écrit la copie dans `tmp_path`. `charger_catalogue(maisons, chemin)` lève alors `ValueError`.
  Commande : `cd jeu && python -m pytest sim/tests/test_pays_et_jauges.py -k "chefs_du_maghreb" -q`.
  Contre-épreuve : un `valider_catalogue` assoupli, qui accepte un nom sans source, laisse passer la copie, et le test rougit.
- **SC5. Contre-épreuve : `grande-21` garde « aucun point ».** Dans le même test, `J.competences(monde, "grande-21", regles) is None`, ses réserves restent à 0 après deux mois, et `J.document_des_jauges(...)["absents"]["competences"]` n'est pas vide.
  Commande : la même que pour SC3.
  Contre-épreuve : un chef ajouté par erreur à `grande-21` fait rougir le test.
- **SC6. Rien d'autre ne bouge.** Les tests qui se servent de `seigneurie-6` ou de `grande-24`, et ceux des jauges, restent verts :
  `cd jeu && python -m pytest sim/tests/test_pays_et_jauges.py sim/tests/test_epreuve_enceinte.py -q`,
  `cd jeu && python -m pytest sim/tests/test_intentions.py -k "seigneurie or part or jauge" -q`,
  `cd jeu && python -m pytest ville/tests/test_epreuve_moree.py -q`.
  Ne lance pas une suite entière : la CI le fait. Si l'un de ces tests rougit, ne l'assouplis pas. L'IA dépense déjà de la Plume quand la concorde tombe sous son neutre (`sim/ia.py:182`). Écris dans la PR ce qui a changé, et arrête-toi.
  Contre-épreuve : la CI complète de la PR.

Pour le relecteur : vérifie SC1 à SC5. Vérifie que le diff ne touche que les trois fichiers du périmètre, et que `personnages.py` n'a pas bougé. Vérifie qu'aucun test existant n'est affaibli : chaque `seigneurie-6` ou `grande-24` retiré d'un cas « sans chef » réapparaît soit en `grande-21`, soit dans une assertion de chef nommé. Vérifie enfin que le `fait` de chaque fiche dit la vérité sur ce que nomme la page, et que la fiche du Zab déclare s'il est plausible.

## Hors périmètre
- Le chargement : pas de voie « plausible » pour une maison du catalogue, aucun changement à `jeu/sim/personnages.py`.
- Les familles et les états familiaux de ces deux chefs (fiches `familles`, `liens`, `etats`) ; Tlemcen garde la décision de #977.
- Un chef pour `grande-21` ou pour les institutions sans chef.
- Le geste « améliorer une province » (sous-lot 2 de #1027) et l'IA qui dépense ses points chaque mois (sous-lot 3).
- Unity : le panneau et la barre lisent déjà `/pays`, et aucune photo n'est à prendre.
