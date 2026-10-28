# Lot #824 — Constantinople : la famille de Manuel II
Jalon : J6 · Machine : vps · Taille prévue : 265 lignes

## But
Au départ, le monde portera la famille connue de Manuel II Paléologue, chef de `grande-15` : son épouse, ses enfants attestés vivants, et des exclusions motivées pour les enfants morts jeunes, futurs ou de présence incertaine.
## Le joueur
« Le joueur gagne les familles connues de ces voisins » (#802, dont ce lot est découpé après #823). Ce lot de fond prépare deux décisions du jalon : le choix d'un mariage (#438) et la transmission (#435 à #437). L'arbre familial de #446 rendra cette famille visible. Le joueur de Morée, voisin de Constantinople, verra l'épouse de l'empereur et ses deux fils attestés vivants au départ, Jean VIII et Théodore II, sans les confondre avec les enfants futurs ni avec ceux dont la présence exacte reste incertaine. Il saura donc ce qui est sûr avant de jauger une alliance avec la maison impériale. Cette maison reste jouée par l'IA ; aucun héritier n'est désigné ici et aucune naissance, mort ou union future n'est programmée.
## Règle du monde
Dépend de : #823, livré sur la base (`98df94d`). Le catalogue fermé, les présences `vivante`/`decedee`/`indeterminee`, les états, les exclusions, la construction dans `World.personnages`, `valider_liens_familiaux` et la copie profonde existent. Aucun apport futur de J4 ou J5 n'est requis. Le lot découle de « Les personnes » et « Les maisons du monde » de `jeu/sim/MODELE.md`. Il prolonge ces sections sans changer les règles du moteur ni `personnages.py`.

Niveau 1 : on étudie exactement `grande-15` au 1er janvier 1400. Les notices ont été consultées le 28 octobre 2026 :
- MANUEL = https://en.wikipedia.org/wiki/Manuel_II_Palaiologos#Family ;
- HELENE = https://en.wikipedia.org/wiki/Helena_Draga%C5%A1#Marriage_and_issue ;
- JEAN = https://en.wikipedia.org/wiki/John_VIII_Palaiologos ;
- THEODORE = https://en.wikipedia.org/wiki/Theodore_II_Palaiologos ;
- ANDRONIC = https://en.wikipedia.org/wiki/Andronikos_Palaiologos_(son_of_Manuel_II) ;
- CONSTANTIN_XI = https://en.wikipedia.org/wiki/Constantine_XI_Palaiologos ;
- DEMETRIOS = https://en.wikipedia.org/wiki/Demetrios_Palaiologos ;
- THOMAS = https://en.wikipedia.org/wiki/Thomas_Palaiologos ;
- CELIK = https://doi.org/10.1017/9781108874038.021 ;
- GANCHOU = https://www.persee.fr/doc/rebyz_0766-5598_2008_num_66_1_3033.

Chaque identité, naissance, présence, lien et état attesté porte une URL et un fait lisible qui nomme les personnes. Chaque exclusion garde son motif et ses sources. Les attentes des tests viennent de ces sources, indépendamment du catalogue produit et du constructeur.

Union : réutiliser `personne-grande-15` (ajouter un complément dans `liens`). Ajouter `personne-helena-dragas` (« Hélène Dragaš », maison `grande-15`), née `c. 1372`, précision `vers`, vivante (morte le 1450-03-23). Les conjoints sont réciproques et l'état est `union` : HELENE donne le mariage du 10 février 1392 et le couronnement du lendemain, MANUEL donne le mariage-couronnement de 1392. Le père d'Hélène, Constantin Dragaš, et sa mère non nommée restent des lacunes de périmètre.

Enfants vivants, état `documentes`, source HELENE (ordre de Sphrantzes) :
- `personne-jean-viii` (« Jean VIII Paléologue ») : naissance `1392-12-18`, précision `jour` (JEAN), mort le 1448-10-31 ;
- `personne-theodore-ii` (« Théodore II Paléologue ») : naissance `c. 1396`, précision `vers` (THEODORE), mort le 1448-06-21. C'est une identité distincte de Théodore Ier, chef de `seigneurie-3`.

Le père et la mère de ces deux enfants sont Manuel et Hélène. Le fait de filiation nomme les deux parents.

Les parents de Manuel (Jean V, Hélène Cantacuzène) restent des lacunes de périmètre. La lacune dit aussi que la fratrie n'est pas intégrée : Théodore Ier (`seigneurie-3`) ne reçoit aucun lien et ne perd aucun lien. Ce n'est jamais une absence attestée.

Exclusions de l'état `grande-15`, une par personne, existence conservée, divergences gardées :
- **Présences incertaines** (repère « indéterminée », jamais vivant ni `decedee`) :
  - « Constantin Paléologue (aîné) » : né vers 1393/1398, mort à Monemvasia entre 1400 et 1402 (CELIK), en tout cas avant 1405 (MANUEL, PLP 21490), et « died young » (HELENE). Sa présence exacte au 1er janvier 1400 n'est pas établie.
  - « Andronic Paléologue » : né en 1400 sans jour (ANDRONIC), mort le 1429-03-04. Sa présence au 1er janvier n'est pas établie. L'ordre des naissances diverge entre MANUEL et HELENE.
  - « Fille aînée non nommée » et « Seconde fille non nommée » (MANUEL, HELENE) : CELIK situe leur mort entre 1400 et 1402, sans établir leur présence au jour de départ ; ni nom ni date n'est inventé.
- **Filiation réfutée** : la prétendue « Zampia Paléologue, fille de Manuel » reste exclue (HELENE, GANCHOU). Ganchou montre que l'épouse d'Ilario Doria était une fille naturelle non nommée de Jean V, donc la demi-sœur de Manuel ; « Zampia » désignerait plutôt leur fille. Aucune sœur ni nièce n'est créée.
- **Enfants futurs** (repère « future », aucun événement programmé) :
  - « Constantin XI » : 8 février 1404 selon CONSTANTIN_XI, 1405 selon HELENE ;
  - « Michel Paléologue » : né en 1406/1407, mort en 1409/1410 (MANUEL) ;
  - « Démétrios Paléologue » : vers 1407 (HELENE, DEMETRIOS) ;
  - « Thomas Paléologue » : vers 1409 (HELENE, THOMAS).
- **Enfants déjà morts au départ** : aucun n'est établi. Les morts de Constantin l'aîné et des deux filles sont seulement bornées entre 1400 et 1402 ; ne déclarer aucune présence `decedee` par déduction.

Conserver intégralement `chefs`, les cinquante-cinq fiches, les quinze compléments et les quinze états existants, faits, lacunes et contre-épreuves compris. Les ajouts portent le total à cinquante-huit fiches, seize compléments et seize états. Mettre à jour `fidelite` et « Les personnes ». Aucun champ de premier niveau ni emplacement n'est ajouté, et `cell_id` reste la seule clé spatiale.

Niveau 2 inchangé : un enfant est strictement postérieur à ses parents, et la mère a entre 15 et 45 ans révolus inclus. Une approximation ne fournit pas de borne. Le bilan chronologique passe de 35 vérifiés / 81 indéterminés à **36 / 86**. Le contrôle vérifié ajouté est l'antériorité Manuel (1350-06-27) → Jean VIII (1392-12-18). Les cinq indéterminés ajoutés sont : Manuel → Théodore II, puis antériorité et âge maternel d'Hélène vers Jean VIII et vers Théodore II.

Niveau 3 : la génération, l'évolution familiale et la succession restent non simulées. Les décès cités documentent seulement la sélection initiale.
## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/MODELE.md
docs/briefs/824-constantinople-la-famille-de-manuel-ii.md
## Conditions de succès
SC1 — Depuis la racine, lancer `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k familles_historiques`. On constate d'abord le rouge des nouveaux cas indépendants, causé par les fiches, le complément, l'état et les exclusions absents ; puis la commande passe. Le constat est transmis au pilote. Contre-épreuves : une sélection vide, des cas ignorés ou une simple erreur de collecte ne valent pas rouge. Ce lot applique la décision A retenue dans #431/#800 et prolongée par #813 à #823 : les attentes exhaustives et leurs copies sont enrichies, et tous les faits et refus antérieurs sont conservés.

SC2 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k familles_historiques` compare le catalogue ET le monde aux ensembles exacts enrichis : 58 fiches, 16 liens, 16 états, identités, maisons, naissances et précisions, parents, conjoints, présences, sources, lacunes, états et exclusions. Les attentes de `grande-15` vivent dans des constantes nommées depuis les URL ci-dessus, sur le modèle de `VOISINS_*`, et dans une fonction dédiée appelée par `_familles_historiques` et `_etats_historiques`. Contre-épreuves, chacune doit échouer :
- retirer Hélène, Jean VIII, Théodore II, le complément ou l'état ;
- ajouter ou dédoubler une personne, même avec des liens résolus ;
- changer un nom, une naissance (Jean en `1392-12`, Théodore en `1396`, précision `annee`), un parent ou un conjoint ;
- effacer une source, un repère de date ou un motif.

`FAMILLE_1400`, Sophie, `ILES_1400`, `IBERIE_1400`, `FIN_1400`, `VOISINS_*` et leurs mutations sont conservés. Aucune inclusion ni sélection ne cache les ajouts.

SC3 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k familles_historiques` éprouve `grande-15` sur des copies non vides. Pour chacune des neuf exclusions, avec le gabarit d'intrus de #823 : construire la personne comme fiche vivante de `grande-15`, avec des liens résolus, en enfant puis en conjointe. La preuve échoue, de même qu'avec un « Héritier inventé ». Les cas suivants sont aussi détectés :
- passer Constantin l'aîné ou Andronic en vivant ou en `decedee` ;
- fusionner les deux Constantin, Théodore II avec Théodore Ier, ou Hélène Dragaš avec Hélène Cantacuzène ;
- relier Théodore Ier à Manuel comme fils ou comme frère ;
- faire de la prétendue Zampia une fille de Manuel ou effacer la correction de Ganchou ;
- passer l'état enfants en `absence_attestee` ou `lacune`, ou l'état conjoints en `veuvage` ;
- effacer la divergence 1404/1405 de Constantin XI ;
- retirer une exclusion, son motif, une de ses sources ou un de ses repères (« indéterminée », « future », dates, 1400–1402, Monemvasia, Ganchou).

SC4 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k 'personnages_sources or personnes_catalogue or personnes_chefs or familles_etats or familles_liens or familles_integration'` passe sur le lecteur réel, un JSON temporaire, la construction et la validation publique. Inventaire des attentes déplacées, toutes étendues et jamais relâchées :
- 55 fiches → 58 dans `_familles_historiques` ;
- 15 liens → 16, et 15 états → 16 dans `_etats_historiques` ;
- dans `test_familles_historiques_etats`, la sentinelle `grande-15` garde ses trois rôles père/mère/conjoint, et la même sentinelle s'ajoute sur `grande-16` ;
- le bilan exact de `test_familles_integration` passe de 35/81 à 36/86. Les ensembles `verifies` et `controles` sont dérivés des couples Manuel/Hélène → Jean VIII et Théodore II.

Contre-épreuves conservées, toutes refusées : référence inconnue, auto-lien, cycle sans dates, conjoint dupliqué ou non réciproque, enfant antérieur ou contemporain, mère de 14 ou 46 ans. Les âges de 15 et 45 ans restent acceptés. Ajout : Jean VIII né le 1350-06-27 ou avant est refusé. Un schéma ouvert, une source invalide, une lacune vide ou un état incohérent restent refusés.

SC5 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k personnes_serialisation` étend les mutations profondes à `grande-15` (ajout dans `alterer_iles`), aux trois fiches, au complément, à l'état, aux sources, aux lacunes et aux exclusions. Les graines 0 et 42 et les permutations des tables donnent les mêmes personnes. Contre-épreuves :
- une mutation d'une copie publiée reste sans effet sur le monde ;
- une mutation du monde se retrouve exactement dans sa copie ;
- un état perdu, un objet imbriqué partagé, une lecture du catalogue ou une reconstruction à la sérialisation font échouer le test.

SC6 — `python3 -m pytest jeu/sim/tests/test_maisons.py jeu/sim/tests/test_determinisme.py -q` passe. `test_personnes_neutres` reste intact : habitants, économie, retours et état aléatoire sont égaux au témoin sans personnes, graines 0 et 42. Contre-épreuves : une lecture ou une reconstruction des personnes au tick déclenche les gardes ; une mutation familiale ou une consommation d'aléa crée un écart détecté. Aucun test n'est supprimé, ignoré ou rendu moins exigeant.

SC7 — `git diff --check` passe. Après l'enregistrement du brief par le pilote, `git diff --numstat origin/master | awk '{n += $1 + $2} END {print n; exit (n >= 300)}'` passe ; tant que le brief n'est pas suivi, ajouter ses lignes une seule fois. Budget, ajouts et suppressions compris : brief 96, données 18, preuves 143, modèle 8, total 265. Contre-épreuves : un espacement fautif ou un total de 300 font échouer la commande. Un dépassement impose une découpe, jamais le retrait d'une exclusion, d'un fait établi ou d'une preuve pour tenir.
## Hors périmètre
Autres familles de #802 (Bayezid, Serbie, Bosnie, Valachie, Moldavie et au-delà). Généalogie des ancêtres, fratrie de Manuel — dont Théodore Ier et sa demi-sœur non nommée —, nièces, conjoints et descendance des enfants, et personnes hypothétiques pour combler les lacunes. Aucun changement du schéma, de `personnages.py`, des briefs précédents ou de `test_determinisme.py`. Aucune génération plausible, évolution familiale, succession, partage, proposition de mariage, dot, alliance, éducation, trait ou ambition. Aucun changement des habitants, de l'économie, des terres ou du tick. Aucun service, aucune vue, ni Unity ni Blender. Tout autre chemin est interdit en écriture.
