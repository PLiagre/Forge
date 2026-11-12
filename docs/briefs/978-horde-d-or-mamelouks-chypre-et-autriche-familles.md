# Lot #978 — Horde d'Or, Mamelouks, Chypre et Autriche, familles connues et lacunes
Jalon : J6 · Machine : vps · Taille prévue : 380 lignes

## But
Au départ, le monde portera ce qu'on sait des familles de Faraj (`grande-22`), de Janus de Lusignan (`grande-26`) et d'Albert IV (`grande-30`) : présences, conjoints, enfants, lacunes motivées et exclusions sourcées. La Horde d'Or (`grande-21`) gardera son chef inconnu et son motif, sans aucune famille inventée.

## Le joueur
C'est un lot de fond. Il prépare deux gestes du jalon J6 : choisir un mariage (#438) et suivre l'héritier que désigne la loi (#435 à #437). L'arbre de la dynastie (#446) le rendra visible, et le joueur qui prend l'un de ces pays (#1037) en héritera.

Après ce lot, le monde sait ceci de quatre grandes maisons de l'Est et du Danube :
- à Vienne, Albert IV, vingt-deux ans, est marié à Jeanne-Sophie de Bavière. Ils ont une fille, Marguerite (1395), et un fils de deux ans, Albert, l'héritier ;
- à Nicosie, Janus de Lusignan n'a ni épouse ni enfant au 1er janvier 1400. Son mariage avec Anglesia Visconti vient plus tard dans l'année : une alliance est encore possible ;
- au Caire, le sultan Faraj a treize ans environ. Ses épouses et ses enfants sont nommés, mais aucun n'est daté : le monde ne les invente pas ;
- à Saraï, on ne sait pas quel khan règne au 1er janvier 1400. Le monde le dit, et ne lui donne aucune famille.

Le joueur sent où un mariage peut se faire, où l'héritier est déjà né, et où l'ignorance rend la succession incertaine. Ces maisons restent jouées par l'IA : aucun héritier n'est choisi, aucun événement futur n'est programmé.

## Règle du monde
Dépend de : #977, sur la base (`bb384fc0`, avec #1052). Le catalogue fermé, les présences, les états, les exclusions, les liens familiaux, les contrôles chronologiques et la copie profonde existent déjà. Le lot découle de « Les personnes » et de « Les maisons du monde » dans `jeu/sim/MODELE.md`. Il étend les données de départ et leurs preuves. Il ne change ni `jeu/sim/personnages.py`, ni aucune règle du moteur.

**La Horde d'Or n'a pas d'état dans `etats`.** L'issue demande « un état motivé ». Mais un état appartient à un chef résolu : c'est la décision A du propriétaire, du 10 novembre 2026, sur la même question posée par #977 pour Tlemcen. Deux tests existants la figent sur `grande-21`. Le chargeur refuse un état `grande-21` (`test_familles_historiques_maghreb`), et une mutation de la maison d'un état vers `grande-21` doit échouer (`test_familles_etats`). L'état motivé de la Horde est donc sa lacune d'identité, déjà portée par sa fiche de chef. Elle cite la page Shadi_Beg : succession de Timur Qutluq par Shadi Beg « fin 1399 ou début 1400 ». Cette lacune reste mot pour mot.

Niveau 1, au 1er janvier 1400. Sources publiques relues le 12 novembre 2026 :
- FARAJ = https://en.wikipedia.org/wiki/An-Nasir_Faraj ;
- JANUS = https://en.wikipedia.org/wiki/Janus,_King_of_Cyprus ; ANGLESIA = https://en.wikipedia.org/wiki/Anglesia_Visconti ;
- ALBERT = https://en.wikipedia.org/wiki/Albert_IV_of_Austria ; JOANNA = https://en.wikipedia.org/wiki/Joanna_Sophie_of_Bavaria ; ALBERTV = https://en.wikipedia.org/wiki/Albert_II_of_Germany ;
- SHADI = https://en.wikipedia.org/wiki/Shadi_Beg (déjà cité par la lacune du chef de la Horde).

La fiche de chef existante de `grande-26` cite `Janus_of_Cyprus`, une redirection vers JANUS : elle ne change pas. Chaque présence, exclusion et lacune nomme la personne et porte une URL. Les tests tirent leurs attentes de constantes nommées d'après ces pages, sans les relire dans le catalogue ni dans le constructeur.

**Mamelouks (`grande-22`).** Le lot réutilise `personne-grande-22` (naissance « c. 1386 », `vers`, inchangée) et lui ajoute un complément dans `liens` :
- `presence=vivante`, source FARAJ : sultan depuis juin 1399, premier règne jusqu'au 20 septembre 1405, tué le 23 mai 1412 ; aucune mort programmée ;
- `pere=null`, lacune de périmètre : Barquq, son père, mort subitement en juin 1399 (FARAJ) ; aucune fiche, aucune absence attestée ;
- `mere=null`, lacune « hors périmètre » qui nomme Khawand Shirin (infobox de FARAJ) ;
- `conjoints=[]`, lacune : Khawand Fatima, sœur d'Ibn Taghribirdi, est « l'une de ses épouses », sans date d'union ; ni célibat ni veuvage.

L'état est `conjoints=lacune`, `enfants=lacune`, sources nulles. Le motif des enfants dit que FARAJ nomme Ghars ad-Din Khalil, Khawand Asiya, Khawand Satita (morte en 1416) et Khawand Shakra (morte en 1482), sans aucune naissance. Faraj a treize ans environ : aucune absence attestée. Sept exclusions, toutes sourcées par FARAJ :
- Khawand Fatima : épouse, union non datée, remariée à Inal Nauruzi après 1412 ; épouse active au départ indéterminée ;
- Lâ Aflaha man Zalama, mère de Khalil, et Thuraiya, mère d'Asiya : concubines, union non datée. Le schéma n'a pas de concubinage : ni conjointes, ni mères référencées ;
- Ghars ad-Din Khalil, Khawand Asiya, Khawand Satita, Khawand Shakra : enfants sans naissance connue, présence indéterminée au 1er janvier 1400.

Le frère, al-Mansur Abd al-Aziz, est hors périmètre (fratrie).

**Chypre (`grande-26`).** Le lot réutilise `personne-grande-26` (naissance 1375 inchangée) et lui ajoute un complément :
- `presence=vivante`, source JANUS : couronné le 11 novembre 1398, roi jusqu'en 1432 ;
- `pere=null`, lacune de périmètre : Jacques Ier de Chypre, mort le 9 septembre 1398 (JANUS) ; aucune fiche ;
- `mere=null`, lacune « hors périmètre » qui nomme Helvis de Brunswick-Grubenhagen ;
- `conjoints=[]`, lacune : le mariage avec Anglesia Visconti a lieu « après janvier 1400 » (JANUS, ANGLESIA ; reine de 1401 à 1407 dans l'infobox). Aucun conjoint actif au départ, ni célibat ni veuvage.

L'état est `conjoints=lacune`, `enfants=lacune`, sources nulles. Le motif des enfants dit que JANUS compte neuf enfants. Six sont nés de Charlotte de Bourbon, épousée en 1411. Aloysius est né en 1408, Guy en 1410. Une fille hors mariage, sans nom ni naissance, se marie en 1427 : aucune absence attestée. Cinq exclusions :
- Anglesia Visconti : épouse future, mariée après janvier 1400, union annulée entre 1407 et 1409 sans enfant (JANUS, ANGLESIA) ;
- Charlotte de Bourbon : épouse future, 1411 (JANUS) ;
- Jean II : fils futur et héritier, né en 1414 (JANUS) ;
- Aloysius (1408) et Guy (1410) : fils hors mariage futurs (JANUS).

Les autres enfants de Charlotte sont couverts par le motif, sans fiche ni exclusion. Marie de Lusignan, sœur de Janus et déjà exclue dans `grande-11`, n'est ni touchée ni dédoublée.

**Autriche (`grande-30`).** Le lot réutilise `personne-grande-30` (né le 19 septembre 1377, `jour`, inchangé) et lui ajoute un complément :
- `presence=vivante`, source ALBERT : duc de 1395 à sa mort, le 14 septembre 1404 ;
- `pere=null`, lacune de périmètre : Albert III, son prédécesseur (ALBERT) ; aucune fiche ;
- `mere=null`, lacune « hors périmètre » qui nomme Beatrix de Nuremberg ;
- `conjoints=['personne-jeanne-sophie-baviere']`, source ALBERT et JOANNA. Le fait garde la divergence : mariage le 24 avril 1390 selon ALBERT, le 13 juin 1395 selon JOANNA, avant le départ dans les deux cas.

Trois fiches nouvelles, de maison `grande-30` :
- `personne-jeanne-sophie-baviere`, « Jeanne-Sophie de Bavière », naissance `{"valeur": "vers 1373", "precision": "vers"}` (JOANNA), vivante (morte le 15 novembre 1410), conjointe réciproque d'Albert IV. Ses parents (Albert Ier de Bavière, Marguerite de Brieg) sont des lacunes de périmètre. Elle reste distincte de Sophie de Bavière (`personne-sophie-baviere`, `grande-9`) et de sa sœur Jeanne de Bavière, exclue de `grande-9` : aucune fusion, aucun lien entre elles ;
- `personne-marguerite-autriche`, « Marguerite d'Autriche », née le 26 juin 1395 (`jour`, ALBERT et JOANNA), vivante (morte le 24 décembre 1447). Ses parents sont Albert IV et Jeanne-Sophie, avec `conjoints=[]` : lacune, mariage futur avec Henri XVI de Bavière le 25 novembre 1412 ;
- `personne-albert-v`, « Albert V d'Autriche », naissance `{"valeur": "1397-08", "precision": "mois"}`, vivant (mort le 27 octobre 1439). Ses parents sont Albert IV et Jeanne-Sophie, avec `conjoints=[]` : lacune, mariage futur avec Élisabeth de Luxembourg en 1422. Le fait de naissance garde la divergence : 16 août 1397 selon ALBERT et JOANNA, 10 août selon ALBERTV ; aucun jour n'est choisi.

L'état est `conjoints=union` (source ALBERT) et `enfants=documentes` (source ALBERT#Family_and_children, deux enfants), sans exclusion.

**Horde d'Or (`grande-21`).** Rien n'est ajouté. SHADI dit que Shadi Beg « eut plusieurs enfants », dont Ghiyath ad-Din. Comme le titulaire n'est pas établi au départ, aucun n'est intégré. La preuve vérifie qu'il n'y a ni fiche familiale de maison `grande-21`, ni complément `personne-grande-21`, ni état `grande-21`, et qu'aucune personne de la maison ne porte `pere`, `mere`, `conjoints`, `presence` ou `etat_familial`.

**Totaux.** Quatre-vingts fiches (trois nouvelles), vingt-six compléments, vingt-six états, triés par maison. Le lot met à jour `fidelite` dans le catalogue. Dans « Les personnes » de MODELE.md, il met à jour les compteurs et ajoute une phrase par maison : Mamelouks, Chypre, Autriche, Horde. Il corrige aussi la phrase de Tlemcen, que #1052 a rendue fausse : le chef est nommé (Abu Muhammad Ier), mais la maison reste sans famille ni état. Il n'ajoute aucun champ de premier niveau ni aucun emplacement : `cell_id` reste la seule clé spatiale.

**Niveau 2.** Deux filiations autrichiennes donnent six contrôles chronologiques. Les deux antériorités d'Albert IV (1377-09-19) vers Marguerite (1395-06-26) et vers Albert V (août 1397) sont vérifiées. Les deux antériorités et les deux âges maternels de Jeanne-Sophie (`vers`) restent indéterminés, faute de bornes exploitables. Le bilan exact passe de 36/111 à 38 vérifiés et 115 indéterminés.

**Niveau 3.** Génération, évolution familiale, succession et partage restent non simulés. Les décès, les mariages et les naissances postérieurs servent seulement à établir la photographie de départ.

## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_modificateurs.py (seulement son empreinte `EMPREINTES_365` et son commentaire)
jeu/sim/MODELE.md
docs/briefs/978-horde-d-or-mamelouks-chypre-et-autriche-familles.md

## Conditions de succès
SC1 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k familles_historiques`. Sur le catalogue d'avant le lot, la commande échoue d'abord sur les cas neufs, faute de fiches, de compléments et d'états. Elle passe ensuite, et le constat du rouge est transmis au pilote. Contre-épreuve : une sélection vide, un test ignoré ou une seule erreur de collecte ne valent pas un rouge.

Comme dans #823 à #826 et #977 (décision A de #431 et #800), les attentes exhaustives sont enrichies, jamais remplacées ni assouplies :
- dans `_familles_historiques`, le décompte des fiches passe à 80, avec l'ensemble exact de leurs identifiants, et `len(liens) == 26`, avec l'ensemble exact des compléments ;
- dans `_etats_historiques`, `len(etats) == 26`, avec l'ensemble exact des maisons ;
- dans `test_familles_historiques_maghreb`, l'inventaire passe à 80/26/26 : ses autres assertions restent mot pour mot ;
- les trois nouvelles fiches et les chefs `grande-22`, `grande-26` et `grande-30` rejoignent l'ensemble que la boucle générique saute.

SC2 — La même commande compare le catalogue ET le monde à des constantes dédiées, sur le gabarit des Balkans (`BALKANS`, `LIENS_B`, `ETATS_B`, contrôlées par `_lacunes_b`) : `MCA_MAISONS`, `HORDE = 'grande-21'`, `FICHES_MCA`, `LIENS_MCA`, `ETATS_MCA` et `MCA_DIVERGENCES`. Une fonction `_mca(fiches=None, etat=None)`, sur le gabarit de `_maghreb`, est appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle :
- pour chaque chef et chaque nouvelle fiche, le nom, la maison, la naissance et sa précision, le père, la mère, les conjoints, la présence, les sources et les repères des lacunes ;
- que seuls Albert V et Marguerite ont `personne-grande-30` pour père et Jeanne-Sophie pour mère ;
- qu'aucune fiche ne désigne `personne-grande-22` ou `personne-grande-26` comme père, mère ou conjoint ;
- pour la Horde, ce que dit la Règle du monde.

Un test neuf, `test_familles_historiques_mamelouks_chypre_autriche`, sur le gabarit de `test_familles_historiques_balkans` et `test_familles_historiques_maghreb`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler une fiche, un complément ou un état ;
- altérer chacune de leurs feuilles ;
- remplacer un repère : « juin 1399 », « Khawand Shirin », « 9 septembre 1398 », « après janvier 1400 », « neuf enfants », « 24 avril 1390 », « 13 juin 1395 », « 16 août », « 10 août », « treize ans », « ni célibat ni veuvage », « aucune absence attestée » ;
- passer une lacune à `absence_attestee`, `union` ou `veuvage`, ou `grande-30` à `lacune` ;
- supprimer une exclusion ;
- donner à Albert V le jour `1397-08-16` (précision `jour`) ;
- renommer Jeanne-Sophie « Sophie de Bavière » ou « Jeanne de Bavière ».

SC3 — La même commande éprouve des copies non vides :
- pour chacune des douze exclusions, construire l'intrus comme enfant (`pere`), puis comme conjoint réciproque du chef concerné, avec des liens résolus (`_controler_famille` passe). `_mca` doit alors échouer, et la preuve d'ensemble aussi ;
- pour la Horde, ajouter tour à tour une fiche familiale de maison `grande-21` (copiée de `personne-marie-bourgogne`), un complément `personne-grande-21` (copié de celui de `grande-26`), puis un état `grande-21` (copié de celui de `grande-26`) : `_mca` doit échouer. L'état `grande-21`, écrit dans `tmp_path`, est aussi refusé par `charger_catalogue` (`ValueError`) ;
- dans le monde construit, donner `etat_familial` ou `presence` à une copie d'une personne de `grande-21` fait échouer la preuve. Sur la base, `personne-grande-21` n'a aucun champ familial, et son nom et sa lacune d'identité sont inchangés.

SC4 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k 'personnages_sources or personnages_attestes or personnes_catalogue or personnes_chefs or familles_etats or familles_liens or familles_integration'` passe sur le lecteur réel, la construction et la validation publique. Les inventaires passent à 80 fiches, 26 compléments et 26 états. Dans `test_familles_integration`, le bilan exact est de 38 vérifiés et 115 indéterminés, avec les ensembles exacts de contrôles : les deux antériorités d'Albert IV rejoignent `verifies`, et les quatre contrôles de Jeanne-Sophie les indéterminés, avec le motif « Naissance absente ou sans bornes exploitables. ».

Contre-épreuves conservées, toutes doivent échouer : une référence inconnue, un auto-lien, un cycle, un conjoint dupliqué ou non réciproque, un enfant antérieur ou contemporain, une mère de 14 ou de 46 ans. Une mère de 15 ou de 45 ans est acceptée. Contre-épreuve neuve : la naissance de Marguerite placée au `1377-09-19` est refusée (`ValueError`, antériorité impossible). Les assertions existantes sur les chefs de `grande-21` et de `grande-24` restent intactes, dans `test_maisons.py` comme dans `test_pays_et_jauges.py`.

SC5 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k personnes_serialisation` étend les mutations profondes à `grande-22`, `grande-26` et `grande-30` (liste de `alterer_iles`), avec leurs fiches, compléments, états, sources, lacunes et exclusions. Les graines 0 et 42 et les permutations des tables donnent les mêmes personnes. Contre-épreuves :
- une mutation d'une copie publiée reste sans effet sur le monde ;
- une mutation du monde se retrouve exactement dans sa copie ;
- un objet imbriqué partagé, une lecture du catalogue ou une reconstruction à la sérialisation font échouer le test.

SC6 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py sim/tests/test_determinisme.py sim/tests/test_pays_et_jauges.py -q` passe. `test_personnes_neutres` reste intact : habitants, économie, retours et état aléatoire restent égaux au témoin sans personnes, pour les graines 0 et 42. Contre-épreuve : une lecture ou une reconstruction au tick, une mutation familiale ou une consommation d'aléa créent un écart détecté. Aucun test n'est supprimé, ignoré ou rendu moins exigeant.

SC7 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_modificateurs.py -q` passe. Comme les trois fiches et les trois compléments entrent dans le registre, l'empreinte du monde au 365e jour (`EMPREINTES_365["linux"][0]`) change. Le codeur la recapture sous Linux. Avant de le faire, il mesure, sur la base et sur le lot, que seule la clé `personnages` de `World.to_dict()` diffère, et que l'empreinte de la photographie (`EMPREINTES_365["linux"][1]`) est identique. Le commentaire au-dessus de la constante le dit, daté du lot. Contre-épreuve : l'ancienne empreinte du monde échoue sur le lot. Une différence hors de `personnages`, ou une photographie qui change, est un défaut du lot : il faut la corriger, pas la recapturer.

SC8 — `git diff --check` passe. Après l'enregistrement du brief par le pilote, `git diff --numstat origin/master | awk '{n += $1 + $2} END {print n; exit (n >= 600)}'` passe. Tant que le brief n'est pas suivi par git, ajouter ses lignes une seule fois. Le budget est de 380 lignes environ, ajouts et suppressions compris. Contre-épreuve : un espacement fautif, ou un total de 600 lignes, font échouer la commande. Un dépassement impose une découpe, jamais le retrait d'une lacune, d'une exclusion ou d'une preuve.

Pour le relecteur :
- vérifie que chaque `fait` dit ce que la page dit vraiment. Relis FARAJ, JANUS, ANGLESIA, ALBERT, JOANNA et ALBERTV (`curl "https://en.wikipedia.org/w/index.php?title=<page>&action=raw"`) ;
- vérifie qu'aucune épouse, aucun enfant et aucune date ne sont inventés, et qu'aucune lacune n'est devenue une absence attestée ;
- vérifie que le diff ne touche que les cinq fichiers du périmètre, que `test_modificateurs.py` ne change que son empreinte et son commentaire, et que `personnages.py` n'a pas bougé.

## Hors périmètre
- Un état `grande-21`, ou tout changement de la règle « un état appartient à un chef résolu » : décision A du propriétaire du 10 novembre 2026, figée par les tests existants.
- Le nom du khan de la Horde, ni Shadi Beg ni Timur Qutluq : la lacune d'identité reste telle quelle, et les tests de #1052 qui s'appuient sur `grande-21` sans chef restent intacts.
- Les maisons `grande-27` et `grande-29` (sous-lots suivants de #803), et tous les autres chefs.
- Les parents et la fratrie des chefs (Barquq, Khawand Shirin, al-Mansur Abd al-Aziz, Jacques Ier, Helvis, Albert III, Beatrix de Nuremberg, Marie de Lusignan), les parents de Jeanne-Sophie, les conjoints futurs des enfants (Henri XVI, Élisabeth de Luxembourg), les enfants de Charlotte autres que Jean II, et toute personne hypothétique qui comblerait une lacune.
- Aucun changement du schéma, de `jeu/sim/personnages.py`, des briefs précédents, de `test_determinisme.py` ou de `test_pays_et_jauges.py`.
- Aucune naissance, mort ou union future programmée ; aucune succession, loi, partage, proposition de mariage, dot, alliance, éducation, trait ou ambition.
- Aucun changement des habitants, de l'économie, des terres ou du tick ; aucun service, aucune vue, ni Unity ni Blender.
- Tout autre chemin est interdit en écriture.
