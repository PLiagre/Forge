# Lot #977 — Le Maghreb : Hafsides, Zayyanides et Mérinides, familles connues et lacunes
Jalon : J6 · Machine : vps · Taille prévue : 220 lignes

## But
Au départ, le monde portera ce qu'on sait des familles d'Abu Faris Abd al-Aziz II (`grande-23`, suzerain de Biskra) et d'Abu Said Uthman III (`grande-25`) : leurs présences, leurs lacunes motivées et leurs exclusions sourcées. Tlemcen (`grande-24`) restera sans famille, sans lien et sans état, avec la raison déjà écrite.

## Le joueur
« Le joueur de Biskra gagne la famille de son suzerain et de ses voisins » (#977, découpé de #803). C'est un lot de fond. Il prépare deux gestes du jalon J6 : choisir un mariage (#438) et suivre la transmission selon la loi (#435 à #437). L'arbre de la dynastie (#446) le rendra visible.

L'émir du Zab saura ceci de ses voisins :
- son suzerain hafside, à Tunis, n'a aucune épouse connue. Son fils et héritier al-Mansur est cité, mais on ne sait pas s'il est déjà né en 1400 ;
- le sultan mérinide de Fès, âgé de seize ou dix-sept ans, n'a ni épouse ni enfant connus. Son seul fils nommé ne naîtra qu'en 1419 ;
- à Tlemcen, on ne sait pas qui règne au 1er janvier 1400. Le monde le dit, et ne lui invente aucune famille.

Le joueur sent où une alliance est possible et où l'ignorance rend la succession incertaine. Ces maisons restent jouées par l'IA : aucun héritier n'est choisi, aucun événement futur n'est programmé.

## Règle du monde
Dépend de : #826, sur la base (`6cc4f2fa`). Le catalogue fermé, les présences, les états, les exclusions, les liens familiaux, les contrôles chronologiques et la copie profonde existent déjà. Le lot découle de « Les personnes » et de « Les maisons du monde » dans `jeu/sim/MODELE.md`. Il étend les données de départ et leurs preuves. Il ne change ni `jeu/sim/personnages.py`, ni aucune règle du moteur : un état reste porté par un chef résolu (décision A du propriétaire, 10 novembre 2026).

Niveau 1, au 1er janvier 1400. Sources publiques relues le 11 novembre 2026 :
- FARIS = https://en.wikipedia.org/wiki/Abu_Faris_Abd_al-Aziz_II ; AHMAD = https://en.wikipedia.org/wiki/Abu_al-Abbas_Ahmad_II ; MUNTASIR = https://en.wikipedia.org/wiki/Abu_Abd-Allah_Muhammad_al-Muntasir ; UTHMAN_H = https://en.wikipedia.org/wiki/Abu_%27Amr_%27Uthman ;
- UTHMAN = https://en.wikipedia.org/wiki/Abu_Said_Uthman_III ; ABDALHAQQ = https://en.wikipedia.org/wiki/Abd_al-Haqq_II ;
- ZAYYAN = https://en.wikipedia.org/wiki/Zayyanid_dynasty (déjà cité dans la lacune du chef de Tlemcen).

Chaque présence, exclusion et lacune nomme la personne et porte une URL. Les tests tirent leurs attentes de constantes nommées d'après ces pages, sans les relire dans le catalogue ni dans le constructeur.

**Hafsides (`grande-23`).** Le lot réutilise `personne-grande-23` (nom et naissance 1361 inchangés) et lui ajoute un complément dans `liens` :
- `presence=vivante`, source FARIS (« souverain hafside de juin 1394 à juillet 1434 ; en fonction et vivant au 1er janvier 1400, aucune mort programmée ») ;
- `pere=null`, avec une lacune de périmètre qui dit ce que donne AHMAD : Abu al-Abbas Ahmad II, mort le 3 juin 1394. Aucune fiche n'est créée, aucune absence n'est attestée ;
- `mere=null`, lacune « hors périmètre » ;
- `conjoints=[]`, avec une lacune : aucune épouse n'est nommée par FARIS ; ce n'est ni un célibat ni un veuvage.

L'état est `conjoints=lacune`, `enfants=lacune`, sources nulles.
- Le motif des enfants cite MUNTASIR : al-Mansur, fils et héritier d'Abu Faris, mort en 1430. MUNTASIR évoque aussi « un autre de ses fils » et des oncles en lutte pour sa succession en 1434, dont al-Mu'tamid, sans dates ni filiation écrite : aucun n'est inventé, et aucune absence n'est attestée.
- Une seule exclusion, Abu Abdallah Muhammad al-Mansur. Ses sources sont MUNTASIR et UTHMAN_H : fils et héritier d'Abu Faris, mort en 1430 avant son père, naissance inconnue. Sa présence au 1er janvier 1400 est donc indéterminée.

Rīm, la concubine valencienne d'al-Mansur, et les petits-fils al-Muntasir et Abu 'Amr 'Uthman (né en février 1419) sont hors périmètre : ils ne sont ni conjoints ni enfants du chef.

**Mérinides (`grande-25`).** Le lot réutilise `personne-grande-25` (naissance 1383 inchangée) et lui ajoute un complément :
- `presence=vivante`, source UTHMAN : « sultan du 19 mars 1398 au 21 octobre 1420 ». Le fait garde la divergence : la notice le dit monté sur le trône « à seize ans » (Ibn Khaldūn), alors que la naissance de 1383 lui donne quinze ans en mars 1398 ;
- `pere=null`, lacune : le nom complet « ibn Abi l-Abbas » ne donne pas une personne, et l'infobox laisse le père vide. Les parents et la fratrie sont hors périmètre : le frère et prédécesseur Abu Amir Abdallah, et le frère Abu Said, envoyé à Gibraltar en 1410 ;
- `mere=null`, lacune « hors périmètre » ;
- `conjoints=[]`, avec une lacune : l'infobox laisse l'épouse vide, et aucune épouse n'est nommée ; ni célibat ni veuvage.

L'état est `conjoints=lacune`, `enfants=lacune`, sources nulles. Le motif des enfants dit que seul Abd al-Haqq II est nommé, et qu'il naît en 1419. Que la notice écrive qu'en 1420 le sultan ne laisse « qu'un enfant d'un an » ne prouve rien pour 1400 : aucune absence n'est attestée. Une seule exclusion, Abd al-Haqq II : fils futur, né en 1419, sources ABDALHAQQ et UTHMAN.

**Tlemcen (`grande-24`).** Rien n'est ajouté. La fiche de chef garde son nom nul et sa lacune d'identité, qui cite ZAYYAN : Abu Muhammad Ier puis Abu Abdallah Ier, succession non datée dans l'année 1400. La preuve vérifie qu'il n'y a aucune fiche familiale de la maison `grande-24`, aucun complément `personne-grande-24`, aucun état `grande-24`, et qu'aucune personne de cette maison ne porte `pere`, `mere`, `conjoints`, `presence` ou `etat_familial`.

**Totaux.** Soixante-dix-sept fiches (aucune nouvelle), vingt-trois compléments, vingt-trois états, triés par maison. Le lot met à jour `fidelite` dans le catalogue, et dans « Les personnes » de MODELE.md : les compteurs, plus une phrase par maison du Maghreb, Tlemcen comprise. Il n'ajoute aucun champ de premier niveau ni aucun emplacement : `cell_id` reste la seule clé spatiale.

**Niveau 2, inchangé.** Aucune filiation nouvelle n'est créée : le bilan chronologique reste exactement de 36 vérifiés et 111 indéterminés.

**Niveau 3.** Génération, évolution familiale, succession et partage restent non simulés. Les décès et les événements postérieurs servent seulement à établir la photographie de départ.

## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/MODELE.md
docs/briefs/977-le-maghreb-hafsides-zayyanides-et-merinides-fami.md

## Conditions de succès
SC1 — Depuis la racine, `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k familles_historiques`. Sur le catalogue d'avant le lot, cette commande échoue d'abord sur les cas du Maghreb, faute de compléments et d'états. Elle passe ensuite, et le constat du rouge est transmis au pilote. Contre-épreuve : une sélection vide, un test ignoré ou une seule erreur de collecte ne valent pas un rouge.

Comme dans #823 à #826 (décision A de #431 et #800), les attentes exhaustives sont enrichies, jamais remplacées ni assouplies :
- dans `_familles_historiques`, `len(liens) == 23`, avec l'ensemble exact des identifiants des compléments ;
- dans `_etats_historiques`, `len(etats) == 23`, avec l'ensemble exact des maisons ;
- `grande-23` et `grande-25` sont ajoutées à l'ensemble que la boucle générique saute.

SC2 — La même commande compare le catalogue ET le monde à des constantes dédiées : `MAGHREB_MAISONS`, `LIENS_M` et `ETATS_M`, sur le gabarit de `LIENS_B` et `ETATS_B`, contrôlées par `_lacunes_b`. Une fonction `_maghreb(fiches=None, etat=None)`, sur le gabarit de `_balkans`, est appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle :
- pour chaque chef, le père, la mère, les conjoints, la présence, les sources et les repères des lacunes ;
- qu'aucune fiche ne désigne `personne-grande-23` ou `personne-grande-25` comme père, mère ou conjoint ;
- pour Tlemcen, ce que dit la Règle du monde : ni fiche, ni complément, ni état.

Un test neuf, `test_familles_historiques_maghreb`, sur le gabarit de `test_familles_historiques_balkans`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler un complément ou un état ;
- altérer chacune de leurs feuilles ;
- remplacer un repère (« 3 juin 1394 », « à seize ans », « 1419 », « un autre de ses fils », « al-Mu'tamid », « ni célibat ni veuvage », « aucune absence attestée ») ;
- passer une lacune à `absence_attestee`, `union` ou `veuvage` ;
- supprimer une exclusion.

SC3 — La même commande éprouve des copies non vides :
- pour al-Mansur, puis pour Abd al-Haqq II, construire l'intrus comme enfant (`pere`) puis comme conjoint réciproque du chef concerné, avec des liens résolus (`_controler_famille` passe). `_maghreb` doit alors échouer, et la preuve d'ensemble aussi ;
- pour Tlemcen, ajouter tour à tour une fiche familiale de maison `grande-24` (copiée de `personne-marie-bourgogne`), un complément `personne-grande-24` (copié de celui de `grande-25`), puis un état `grande-24` (copié de celui de `grande-25`) : `_maghreb` doit échouer ;
- l'état `grande-24`, écrit dans `tmp_path`, doit aussi être refusé par `charger_catalogue` (`ValueError`), car un état appartient à un chef résolu ;
- dans le monde construit, donner `etat_familial` ou `presence` à une copie d'une personne de `grande-24` fait échouer la preuve. Sur la base, aucune personne de cette maison n'a de champ familial.

SC4 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k 'personnages_sources or personnages_attestes or personnes_catalogue or personnes_chefs or familles_etats or familles_liens or familles_integration'` passe sur le lecteur réel, la construction et la validation publique. Les inventaires passent à 77 fiches, 23 compléments et 23 états. Le bilan exact reste à 36/111, dérivé comme aujourd'hui : aucun lien paternel ni maternel nouveau.

Contre-épreuves conservées, toutes doivent échouer : une référence inconnue, un auto-lien, un cycle, un conjoint dupliqué ou non réciproque, un enfant antérieur ou contemporain, une mère de 14 ou de 46 ans. Une mère de 15 ou de 45 ans est acceptée. Les assertions existantes sur le chef de `grande-24` (nom nul, lacune d'identité) restent intactes.

SC5 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k personnes_serialisation` étend les mutations profondes à `grande-23` et `grande-25`, avec leurs compléments, états, sources, lacunes et exclusions (liste de `alterer_iles`). Les graines 0 et 42 et les permutations des tables donnent les mêmes personnes. Contre-épreuves :
- une mutation d'une copie publiée reste sans effet sur le monde ;
- une mutation du monde se retrouve exactement dans sa copie ;
- un objet imbriqué partagé, une lecture du catalogue ou une reconstruction à la sérialisation font échouer le test.

SC6 — `python3 -m pytest jeu/sim/tests/test_maisons.py jeu/sim/tests/test_determinisme.py -q` passe. `test_personnes_neutres` reste intact : habitants, économie, retours et état aléatoire restent égaux au témoin sans personnes, pour les graines 0 et 42. Contre-épreuve : une lecture ou une reconstruction au tick, une mutation familiale ou une consommation d'aléa créent un écart détecté. Aucun test n'est supprimé, ignoré ou rendu moins exigeant.

SC7 — `git diff --check` passe. Après l'enregistrement du brief par le pilote, `git diff --numstat origin/master | awk '{n += $1 + $2} END {print n; exit (n >= 400)}'` passe. Tant que le brief n'est pas suivi par git, ajouter ses lignes une seule fois. Le budget est de 220 lignes environ, ajouts et suppressions compris. Contre-épreuve : un espacement fautif, ou un total de 400 lignes, font échouer la commande. Un dépassement impose une découpe, jamais le retrait d'une lacune, d'une exclusion ou d'une preuve.

Pour le relecteur :
- vérifie que chaque `fait` dit ce que la page dit vraiment. Relis FARIS, MUNTASIR, UTHMAN et ABDALHAQQ (`curl "https://en.wikipedia.org/w/index.php?title=<page>&action=raw"`) ;
- vérifie qu'aucune épouse, aucun enfant et aucune date ne sont inventés, et qu'aucune lacune n'est devenue une absence attestée ;
- vérifie que le diff ne touche que les quatre fichiers du périmètre, et que `personnages.py` n'a pas bougé.

## Hors périmètre
- Le chef de Tlemcen et celui du Zab : ils appartiennent à #1052 (sous-lot de #1027), en vol sur sa branche. #1052 nomme Abu Muhammad Ier, touche les mêmes fichiers de données et de tests, et ne pose aucune famille. Si #1052 est fusionné avant ce lot, le codeur repart de la base : il ne retouche aucune assertion de #1052. Il garde intégralement la preuve de Tlemcen sur la famille (ni fiche, ni complément, ni état, aucun champ familial sur `personne-grande-24`), et le dit dans la PR.
- Le Zab (`seigneurie-6`), `grande-21`, `grande-22`, et les maisons `grande-26` à `grande-30` (autres sous-lots de #803).
- Les parents et la fratrie des chefs (Abu al-Abbas Ahmad II, Abu Amir Abdallah, Abu Said), les conjoints des enfants (Rīm), les petits-fils (al-Muntasir, Abu 'Amr 'Uthman), et toute personne hypothétique qui comblerait une lacune.
- Aucun changement du schéma, de `jeu/sim/personnages.py`, des briefs précédents ou de `test_determinisme.py`.
- Aucune naissance, mort ou union future programmée ; aucune succession, loi, partage, proposition de mariage, dot, alliance, éducation, trait ou ambition.
- Aucun changement des habitants, de l'économie, des terres ou du tick ; aucun service, aucune vue, ni Unity ni Blender.
- Tout autre chemin est interdit en écriture.
