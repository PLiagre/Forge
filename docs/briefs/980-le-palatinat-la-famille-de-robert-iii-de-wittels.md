# Lot #980 — Le Palatinat : la famille de Robert III de Wittelsbach
Jalon : J6 · Machine : vps · Taille prévue : 520 lignes

## But
Au départ, le monde portera la famille de Robert III de Wittelsbach (`grande-29`) au 1er janvier 1400 : son épouse, ses huit enfants vivants, son fils mort et les unions futures exclus avec leurs sources. Ce lot achève les états familiaux des grandes maisons : vingt-huit des trente en ont un, et les deux autres (`grande-21`, `grande-24`) restent sans état, pour leur motif déjà décidé.

## Le joueur
C'est un lot de fond. Il prépare deux gestes du jalon J6 : choisir un mariage (#438) et suivre l'héritier que désigne la loi (#435 à #437). L'arbre de la dynastie (#446) le rendra visible, et le joueur qui prend le Palatinat (#1037) en héritera.

Après ce lot, le monde sait ceci de la maison de Heidelberg :
- Robert III, quarante-sept ans, électeur palatin, est marié depuis le 27 juin 1374 à Élisabeth de Nuremberg, quarante et un ans ;
- huit de leurs neuf enfants vivent. L'aîné, Robert Pipan, est mort en 1397 : le monde ne le ressuscite pas ;
- le fils aîné vivant est Frédéric, vingt-deux ans environ ; Louis, vingt et un ans, vient ensuite. Aucun héritier n'est désigné ;
- Marguerite est mariée au duc de Lorraine depuis 1393. Agnès épouse Adolphe de Clèves « peu avant mars 1400 » ou « peu avant 1400 » : les pages divergent et le monde ne tranche pas ;
- Louis, Élisabeth, Jean, Étienne et Otton n'ont pas de conjoint au départ. Leurs mariages viennent tous après 1400, dont celui de Louis avec Blanche d'Angleterre (1402) : une alliance est encore possible. Otton n'a que neuf ans.

Le joueur sent une grande maison d'Empire, riche de fils à marier, qui va prendre la couronne des Romains en août 1400. Le Palatinat reste joué par l'IA : aucun héritier n'est désigné, aucun événement futur n'est programmé.

## Règle du monde
Dépend de : #979, sur la base (`59a51446`). Le catalogue fermé, les présences, les états, les exclusions, les liens familiaux, les contrôles chronologiques et la copie profonde existent déjà. Le lot découle de « Les personnes » et de « Les maisons du monde » dans `jeu/sim/MODELE.md`. Il étend les données de départ et leurs preuves. Il ne change ni `jeu/sim/personnages.py`, ni aucune règle du moteur.

Niveau 1, au 1er janvier 1400. Sources publiques relues le 13 novembre 2026 :
- ROBERT = https://en.wikipedia.org/wiki/Rupert,_King_of_the_Romans#Family_and_children (la page `Rupert_of_Germany` de la fiche de chef y redirige ; la fiche de chef garde son URL) ;
- ELISABETH_N = https://en.wikipedia.org/wiki/Elisabeth_of_Nuremberg ;
- MARGUERITE_P = https://en.wikipedia.org/wiki/Margaret_of_the_Palatinate ; CHARLES_L = https://en.wikipedia.org/wiki/Charles_II_of_Lorraine ;
- LOUIS_P = https://en.wikipedia.org/wiki/Louis_III,_Elector_Palatine ; ADOLPHE_C = https://en.wikipedia.org/wiki/Adolph_I,_Duke_of_Cleves ;
- JEAN_N = https://en.wikipedia.org/wiki/John,_Count_Palatine_of_Neumarkt ; CATHERINE_P = https://en.wikipedia.org/wiki/Catherine_of_Pomerania,_Countess_Palatine_of_Neumarkt ;
- ETIENNE_S = https://en.wikipedia.org/wiki/Stephen,_Count_Palatine_of_Simmern-Zweibrücken ; ANNA_V = https://en.wikipedia.org/wiki/Anna_of_Veldenz,_Countess_Palatine_of_Simmern-Zweibrücken ;
- OTTON_M = https://en.wikipedia.org/wiki/Otto_I,_Count_Palatine_of_Mosbach ;
- FREDERIC_A = https://en.wikipedia.org/wiki/Frederick_IV_of_Austria ; MATHILDE_S = https://en.wikipedia.org/wiki/Matilda_of_Savoy.

La fiche de chef de `grande-29` (identité, naissance `1352-05-05`, précision `jour`, sources `Rupert_of_Germany`) ne change pas. Chaque présence, exclusion et lacune nomme la personne et porte une URL. Les tests tirent leurs attentes de constantes nommées d'après ces pages, sans les relire dans le catalogue ni dans le constructeur.

**Le chef (`grande-29`).** Le lot ajoute un complément `personne-grande-29` dans `liens` :
- `presence=vivante`, source ROBERT : électeur jusqu'à sa mort, le 18 mai 1410 au château de Landskron, à Oppenheim ; élu roi des Romains le 21 août 1400, après le départ ; aucune mort ni élection programmée ;
- `pere=null`, lacune de périmètre : Robert II, électeur palatin, son père ; aucune fiche, aucune absence attestée ;
- `mere=null`, lacune de périmètre qui nomme Béatrice de Sicile (« Beatrice of Aragon » dans le texte de la même page, divergence conservée) ;
- `conjoints=['personne-elisabeth-nuremberg']`, source ROBERT : mariage à Amberg le 27 juin 1374.

**L'épouse.** Une fiche nouvelle, de maison `grande-29` : `personne-elisabeth-nuremberg`, « Élisabeth de Nuremberg », née le 13 décembre 1358 (`jour`, ELISABETH_N ; le fait garde la divergence : l'infobox de la même page ne donne que 1358). Vivante (morte le 26 juillet 1411, ELISABETH_N), conjointe réciproque de Robert (sources ROBERT et ELISABETH_N, 27 juin 1374, Amberg). Ses parents, Frédéric V de Nuremberg et Élisabeth de Misnie, sont des lacunes de périmètre. Elle est de la maison de Hohenzollern : aucun lien vers une autre fiche.

**Les enfants vivants.** Huit fiches nouvelles, de maison `grande-29`. Chacune a pour père `personne-grande-29` et pour mère `personne-elisabeth-nuremberg`, avec les sources ROBERT et ELISABETH_N (liste des enfants de Robert et d'Élisabeth) :
- `personne-marguerite-palatinat`, « Marguerite du Palatinat », naissance `{"valeur": "1376", "precision": "annee"}` (ROBERT, MARGUERITE_P), vivante. Le fait de présence garde la divergence : morte le 27 août 1434 à Nancy (ROBERT, ELISABETH_N) ou le 26 août 1434 à Einville-au-Jard (MARGUERITE_P). `conjoints=[]`, lacune : Charles II de Lorraine, épousé le 6 février 1393 (ROBERT, MARGUERITE_P ; CHARLES_L dit 1393). Conjoint d'enfant hors périmètre, aucune absence attestée ;
- `personne-frederic-palatinat`, « Frédéric du Palatinat », naissance `{"valeur": "vers 1377", "precision": "vers"}` (ROBERT : « c. 1377 », Amberg), vivant (mort le 7 mars 1401 à Amberg, après le départ ; aucune mort programmée). Fils aîné vivant au départ. `conjoints=[]`, lacune : aucune épouse nommée par ROBERT ni ELISABETH_N ; ni célibat ni veuvage ;
- `personne-louis-palatinat`, « Louis III du Palatinat », né le 23 janvier 1378 (`jour`, ROBERT, LOUIS_P), vivant (mort le 30 décembre 1436). LOUIS_P le dit « troisième fils ». `conjoints=[]`, lacune : ses mariages avec Blanche d'Angleterre (6 juillet 1402) et Mathilde de Savoie (30 novembre 1417) sont futurs (LOUIS_P). Ni célibat ni veuvage ;
- `personne-agnes-palatinat`, « Agnès du Palatinat », naissance `{"valeur": "1379", "precision": "annee"}` (ROBERT), vivante (morte en 1401 à Heidelberg, sans enfant, ADOLPHE_C). `conjoints=[]`, lacune qui garde la divergence : mariée à Heidelberg à Adolphe Ier de Clèves « peu avant mars 1400 » (ROBERT, ELISABETH_N) ou « peu avant l'année 1400 » (ADOLPHE_C). Le monde ne sait pas si l'union est active au 1er janvier 1400 : ni fiche, ni exclusion, aucune absence attestée ;
- `personne-elisabeth-palatinat`, « Élisabeth du Palatinat », née le 27 octobre 1381 (`jour`, ROBERT), vivante (morte le 31 décembre 1408 à Innsbruck, ROBERT ; FREDERIC_A la dit morte peu après la naissance de sa fille, le 27 décembre 1408). `conjoints=[]`, lacune : son mariage avec Frédéric IV d'Autriche, le 24 décembre 1407 à Innsbruck, est futur (ROBERT, FREDERIC_A). Frédéric IV n'est pas Albert IV : aucun lien vers `personne-grande-30` ;
- `personne-jean-neumarkt`, « Jean de Neumarkt », naissance `{"valeur": "1383", "precision": "annee"}` (ROBERT, JEAN_N ; Neunburg vorm Wald), vivant. Le fait de présence garde la divergence : mort les 13–14 mars 1443 (ROBERT) ou le 14 mars 1443 (JEAN_N). `conjoints=[]`, lacune : son mariage avec Catherine de Poméranie (1407, JEAN_N ; 15 août 1407 à Ribe, CATHERINE_P) est futur. Ni célibat ni veuvage ;
- `personne-etienne-simmern`, « Étienne de Simmern-Deux-Ponts », né le 23 juin 1385 (`jour`, ROBERT, ETIENNE_S), vivant (mort le 14 février 1459). `conjoints=[]`, lacune : son mariage avec Anna de Veldenz est futur, en juin 1410 (ETIENNE_S) ou en 1409 (ANNA_V), divergence conservée ;
- `personne-otton-mosbach`, « Otton de Mosbach », né le 24 août 1390 (`jour`, ROBERT, OTTON_M), « fils cadet » (OTTON_M), vivant (mort le 5 juillet 1461). `conjoints=[]`, lacune : son mariage avec Jeanne de Bavière-Landshut, en janvier 1430, est futur (OTTON_M).

Les petits-enfants (dont Isabelle de Lorraine, née en 1400) sont hors périmètre : ni fiche, ni exclusion. Aucun nom nouveau n'est déjà porté par une fiche du catalogue.

**Blanche d'Angleterre.** `personne-blanche-angleterre` reste la seule fiche de ce nom, de maison `grande-1`, fille de Henri IV. Sa fiche ne change pas, mot pour mot, lacune de conjoint comprise : elle ne reçoit aucun conjoint. Comme Philippa d'Angleterre dans l'état de Kalmar, elle est nommée par une exclusion de `grande-29`.

**L'état `grande-29`.** `conjoints=union` (source ROBERT, 27 juin 1374) et `enfants=documentes` (source ROBERT : neuf enfants, dont huit vivants au départ ; ELISABETH_N donne la même liste). Sept exclusions sourcées :
- Robert Pipan (20 février 1375 – 25 janvier 1397, Amberg) : fils aîné mort avant 1400 (ROBERT, ELISABETH_N) ;
- Blanche d'Angleterre : épouse future de Louis, le 6 juillet 1402 (LOUIS_P) ; elle garde sa seule fiche anglaise et ses parents, sans conjoint actif au départ ;
- Mathilde de Savoie : seconde épouse future de Louis, le 30 novembre 1417 (LOUIS_P, MATHILDE_S) ;
- Frédéric IV d'Autriche : époux futur d'Élisabeth, le 24 décembre 1407 (ROBERT, FREDERIC_A) ;
- Catherine de Poméranie : épouse future de Jean, le 15 août 1407 (CATHERINE_P, JEAN_N) ;
- Anna de Veldenz : épouse future d'Étienne, en juin 1410 ou en 1409 (ETIENNE_S, ANNA_V) ;
- Jeanne de Bavière-Landshut : née en 1413, épouse future d'Otton en janvier 1430 (OTTON_M).

Robert III n'a pas d'union future : il meurt en 1410, Élisabeth lui survivant.

**Les trente grandes maisons.** Avec cet état, vingt-huit grandes maisons ont leur état familial. La Horde d'Or (`grande-21`, chef inconnu) et Tlemcen (`grande-24`, décision A du 10 novembre sur #977 : la maison reste sans famille) n'en ont pas, et leurs preuves existantes restent mot pour mot.

**Totaux.** Quatre-vingt-quinze fiches (neuf nouvelles), vingt-huit compléments, vingt-huit états, triés par maison. Le registre passe de 2 372 à 2 381 personnes. Le lot complète `fidelite` dans le catalogue. Dans « Les personnes » de MODELE.md, il met à jour les compteurs, ajoute une phrase Palatinat (`grande-29`) et dit que la couverture des grandes maisons est achevée, avec ses deux exceptions motivées. Il n'ajoute aucun champ de premier niveau ni aucun emplacement : `cell_id` reste la seule clé spatiale.

**Niveau 2.** Huit filiations donnent vingt-quatre contrôles chronologiques (mesuré sur une copie en mémoire avec `valider_liens_familiaux`) :
- vingt et un vérifiés : sept antériorités de Robert (5 mai 1352), sept antériorités et sept âges maternels d'Élisabeth (13 décembre 1358), de 17 ans (Marguerite) à 31 ans (Otton), pour tous les enfants sauf Frédéric ;
- trois indéterminés, pour Frédéric (« vers 1377 », sans bornes) : l'antériorité paternelle, l'antériorité maternelle et l'âge maternel, avec le motif « Naissance absente ou sans bornes exploitables. ».

Le bilan exact passe de 56/115 à 77 vérifiés et 118 indéterminés.

**Niveau 3.** Génération, évolution familiale, succession, élection royale et partage restent non simulés. Les décès, mariages et naissances postérieurs servent seulement à établir la photographie de départ.

## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_modificateurs.py (seulement son empreinte `EMPREINTES_365` et son commentaire)
jeu/sim/MODELE.md
docs/briefs/980-le-palatinat-la-famille-de-robert-iii-de-wittels.md

## Conditions de succès
SC1 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k familles_historiques`. Sur le catalogue d'avant le lot, la commande échoue d'abord sur les cas neufs, faute de fiches, de complément et d'état. Elle passe ensuite, et le constat du rouge est transmis au pilote. Contre-épreuve : une sélection vide, un test ignoré ou une seule erreur de collecte ne valent pas un rouge.

Comme dans #823 à #826 et #977 à #979 (décision A de #431 et #800), les attentes exhaustives sont enrichies, jamais assouplies :
- dans `_familles_historiques`, le décompte des fiches passe à 95, avec l'ensemble exact de leurs identifiants, et `len(liens) == 28`, avec l'ensemble exact des compléments (`'29'` ajouté) ;
- dans `_etats_historiques`, `len(etats) == 28`, avec l'ensemble exact des maisons (`'29'` ajouté) ;
- dans `test_familles_historiques_maghreb`, `test_familles_historiques_mamelouks_chypre_autriche` et `test_familles_historiques_bourgogne`, l'inventaire passe à 95/28/28 : leurs autres assertions restent mot pour mot ;
- les neuf fiches nouvelles et `personne-grande-29` rejoignent l'ensemble que la boucle générique saute.

Aucune autre attente existante n'est remplacée.

SC2 — La même commande compare le catalogue ET le monde à des constantes dédiées, sur le gabarit de `_bourgogne` : `PALATINAT = 'grande-29'`, `FICHES_PALATINAT`, `ENFANTS_PALATINAT`, `LIEN_PALATINAT`, `ETAT_PALATINAT`, `PALATINAT_EXCLUSIONS` et `PALATINAT_DIVERGENCES`. Une fonction `_palatinat(fiches=None, etat=None)` est appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle :
- pour le chef et chaque fiche nouvelle : le nom, la maison, la naissance et sa précision, le père, la mère, les conjoints, la présence, les URL des sources et les repères des faits et des lacunes ;
- que seuls les huit enfants ont `personne-grande-29` pour père et `personne-elisabeth-nuremberg` pour mère ;
- que `personne-blanche-angleterre` est la seule « Blanche d'Angleterre » du catalogue, de maison `grande-1`, avec `conjoints == []` et sa lacune de conjoint inchangée ;
- qu'aucune fiche ne relie un enfant de Robert à `personne-grande-30`, à `personne-blanche-angleterre` ni à une autre maison ;
- que les maisons qui ont un état sont exactement `grande-1` à `grande-30` sauf `grande-21` et `grande-24`.

Un test neuf, `test_familles_historiques_palatinat`, sur le gabarit de `test_familles_historiques_bourgogne`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler une fiche, le complément ou l'état ;
- altérer chacune de leurs feuilles ;
- donner à Blanche d'Angleterre `conjoints=['personne-louis-palatinat']` et à Louis `conjoints=['personne-blanche-angleterre']` (réciproques, liens résolus, `_controler_famille` passe) ;
- relier Élisabeth du Palatinat à `personne-grande-30` comme conjointe réciproque ;
- ajouter une seconde « Blanche d'Angleterre » de maison `grande-29`, conjointe réciproque de Louis ;
- remplacer un repère : « 27 juin 1374 », « Amberg », « 18 mai 1410 », « 21 août 1400 », « Robert II », « Béatrice de Sicile », « Beatrice of Aragon », « 13 décembre 1358 », « 26 juillet 1411 », « 6 février 1393 », « Charles II de Lorraine », « 27 août 1434 », « 26 août 1434 », « vers 1377 », « 7 mars 1401 », « fils aîné vivant », « troisième fils », « 6 juillet 1402 », « 30 novembre 1417 », « peu avant mars 1400 », « peu avant l'année 1400 », « 24 décembre 1407 », « 15 août 1407 », « 13–14 mars 1443 », « juin 1410 », « 1409 », « janvier 1430 », « 1413 », « neuf enfants », « 25 janvier 1397 », « ni célibat ni veuvage », « aucune absence attestée » ;
- passer `conjoints` à `lacune` ou `veuvage`, `enfants` à `lacune` ou `absence_attestee`, ou une lacune d'enfant à une absence attestée ;
- supprimer une exclusion, ou altérer son motif, ses sources ou ses dates ;
- donner à Frédéric la naissance `1377` (précision `annee`), à Élisabeth de Nuremberg la naissance `1358` (précision `annee`), ou à Agnès un conjoint actif ;
- ajouter un état `grande-21`, ou retirer l'état `grande-29`.

SC3 — La même commande éprouve des copies non vides, avec des liens résolus (`_controler_famille` passe à chaque fois) :
- Robert Pipan construit comme enfant de Robert et d'Élisabeth, avec `presence=decedee` ;
- les six conjoints futurs (Blanche d'Angleterre comprise, comme fiche nouvelle de `grande-29`) et un « Héritier inventé » construits comme enfants de Robert, puis comme conjoints réciproques de Robert, vivants.

Dans chaque cas, `_palatinat` doit échouer, et la preuve d'ensemble aussi. Le codeur vérifie que les contre-épreuves existantes qui copient une fiche (voisins, Constantinople, Ottomans, Balkans, Maghreb, Mamelouks-Chypre-Autriche, Horde, Bourgogne) échouent toujours pour leur motif.

SC4 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k 'personnages_sources or personnages_attestes or personnes_catalogue or personnes_chefs or familles_etats or familles_liens or familles_integration'` passe sur le lecteur réel, la construction et la validation publique. Les inventaires passent à 95 fiches, 28 compléments et 28 états. Dans `test_familles_integration`, le bilan exact est de 77 vérifiés et 118 indéterminés : Frédéric rejoint les listes des indéterminés paternels et maternels, et la formule reste exacte (`86 + 14 + 2 × 9 == 118`). Les vingt et un contrôles vérifiés de la Règle du monde rejoignent l'ensemble exact `verifies` ; les trois de Frédéric rejoignent les indéterminés, avec leur motif.

Contre-épreuves conservées, toutes doivent échouer : une référence inconnue, un auto-lien, un cycle, un conjoint dupliqué ou non réciproque, un enfant antérieur ou contemporain, une mère de 14 ou de 46 ans. Une mère de 15 ou de 45 ans est acceptée. Contre-épreuves neuves, refusées (`ValueError`) :
- la naissance d'Élisabeth de Nuremberg placée au `1378-01-23` (antériorité impossible vers Louis) ;
- la naissance d'Élisabeth de Nuremberg placée au `1340-01-01` (mère de 50 ans à la naissance d'Otton).

SC5 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k personnes_serialisation` étend les mutations profondes à `grande-29` (liste de `alterer_iles`), avec ses fiches, son complément, son état, ses sources, ses lacunes et ses exclusions. Les graines 0 et 42 et les permutations des tables donnent les mêmes personnes. Contre-épreuves :
- une mutation d'une copie publiée reste sans effet sur le monde ;
- une mutation du monde se retrouve exactement dans sa copie ;
- un objet imbriqué partagé, une lecture du catalogue ou une reconstruction à la sérialisation font échouer le test.

SC6 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py sim/tests/test_determinisme.py sim/tests/test_pays_et_jauges.py -q` passe. `test_personnes_neutres` reste intact : habitants, économie, retours et état aléatoire restent égaux au témoin sans personnes, pour les graines 0 et 42. Les points du pays ne viennent que des chefs : ils ne changent pas. Contre-épreuve : une lecture ou une reconstruction au tick, une mutation familiale ou une consommation d'aléa créent un écart détecté. Aucun test n'est supprimé, ignoré ou rendu moins exigeant.

SC7 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_modificateurs.py -q` passe. Comme neuf fiches et un complément entrent dans le registre, l'empreinte du monde au 365e jour (`EMPREINTES_365["linux"][0]`) change. Le codeur la recapture sous Linux. Avant de le faire, il mesure, sur la base et sur le lot, que seule la clé `personnages` de `World.to_dict()` diffère (neuf fiches nouvelles, une changée : `personne-grande-29`), et que l'empreinte de la photographie (`EMPREINTES_365["linux"][1]`) est identique. Le commentaire au-dessus de la constante le dit, daté du lot (de 2 372 à 2 381 personnes). Contre-épreuve : l'ancienne empreinte du monde échoue sur le lot. Une différence hors de `personnages`, ou une photographie qui change, est un défaut du lot : il faut la corriger, pas la recapturer.

SC8 — `git diff --check` passe. Après l'enregistrement du brief par le pilote, `git diff --numstat origin/master | awk '{n += $1 + $2} END {print n; exit (n >= 800)}'` passe. Tant que le brief n'est pas suivi par git, ajouter ses lignes une seule fois. Le budget est de 520 lignes environ, ajouts et suppressions compris. Contre-épreuve : un espacement fautif, ou un total de 800 lignes, font échouer la commande. Un dépassement impose une découpe, jamais le retrait d'une lacune, d'une exclusion ou d'une preuve.

Pour le relecteur :
- vérifie que chaque `fait` dit ce que la page dit vraiment. Relis les pages des constantes (`curl -A "ForgeBrief/1.0" "https://en.wikipedia.org/w/index.php?title=<page>&action=raw"`) ;
- vérifie qu'aucune épouse, aucun enfant et aucune date ne sont inventés, qu'Agnès n'a pas de conjoint actif, et qu'aucune lacune n'est devenue une absence attestée ;
- vérifie que la fiche de Blanche d'Angleterre n'a pas bougé, et que Tlemcen et la Horde restent sans état ;
- vérifie que le diff ne touche que les cinq fichiers du périmètre, que `test_modificateurs.py` ne change que son empreinte et son commentaire, et que `personnages.py` n'a pas bougé.

## Hors périmètre
- Tout autre chef et toute autre maison, dont la Horde d'Or (`grande-21`) et Tlemcen (`grande-24`), qui restent sans famille ni état.
- Les parents et la fratrie de Robert III et d'Élisabeth (Robert II, Béatrice de Sicile, Frédéric V de Nuremberg, Élisabeth de Misnie), les conjoints des enfants (Charles II de Lorraine, Adolphe Ier de Clèves, et les conjoints futurs exclus), les petits-enfants, dont Isabelle de Lorraine, et toute personne hypothétique qui comblerait une lacune.
- Toute attente sur Blanche d'Angleterre, Henri IV, l'état `grande-1` ou l'Autriche (`grande-30`).
- Aucun changement du schéma, de `jeu/sim/personnages.py`, des briefs précédents, de `test_determinisme.py` ou de `test_pays_et_jauges.py`.
- Aucune naissance, mort, union ou élection future programmée ; aucune succession, loi, partage, proposition de mariage, dot, alliance, éducation, trait ou ambition.
- Aucun changement des habitants, de l'économie, des terres ou du tick ; aucun service, aucune vue, ni Unity ni Blender.
- Tout autre chemin est interdit en écriture.
