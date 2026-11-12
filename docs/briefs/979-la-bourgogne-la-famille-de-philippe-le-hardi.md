# Lot #979 — La Bourgogne : la famille de Philippe le Hardi
Jalon : J6 · Machine : vps · Taille prévue : 480 lignes

## But
Au départ, le monde portera la famille de Philippe le Hardi (`grande-27`) au 1er janvier 1400 : son épouse, ses six enfants vivants, ses enfants morts et les unions futures exclus avec leurs sources. Marie de Bourgogne gardera sa fiche unique de `grande-12` et recevra ses parents sourcés, sans doublon.

## Le joueur
C'est un lot de fond. Il prépare deux gestes du jalon J6 : choisir un mariage (#438) et suivre l'héritier que désigne la loi (#435 à #437). L'arbre de la dynastie (#446) le rendra visible, et le joueur qui prend la Bourgogne (#1037) en héritera.

Après ce lot, le monde sait ceci de la maison de Dijon :
- Philippe le Hardi, cinquante-sept ans, est marié depuis 1369 à Marguerite III de Flandre, quarante-neuf ans ;
- leur fils aîné, Jean, vingt-huit ans, est marié à Marguerite de Bavière depuis 1385 : l'héritier est un adulte ;
- trois filles sont déjà mariées hors de la maison : Marguerite en Hainaut-Bavière, Catherine en Autriche et Marie en Savoie. Marie est la même personne que l'épouse d'Amédée VIII, avec désormais son père et sa mère ;
- deux fils restent à marier : Antoine, quinze ans, et Philippe, dix ans. Leurs mariages viennent après 1400 : une alliance est encore possible ;
- Charles, Louis et Bonne sont morts avant 1400. Le monde ne les ressuscite pas.

Le joueur sent le réseau d'alliances que Philippe a tissé (Bavière, Autriche, Savoie), voit un héritier déjà fait et deux fils encore libres. La Bourgogne reste jouée par l'IA : aucun héritier n'est désigné, aucun événement futur n'est programmé.

## Règle du monde
Dépend de : #978, sur la base (`6fb7969d`). Le catalogue fermé, les présences, les états, les exclusions, les liens familiaux, les contrôles chronologiques et la copie profonde existent déjà. Le lot découle de « Les personnes » et de « Les maisons du monde » dans `jeu/sim/MODELE.md`. Il étend les données de départ et leurs preuves. Il ne change ni `jeu/sim/personnages.py`, ni aucune règle du moteur.

Niveau 1, au 1er janvier 1400. Sources publiques relues le 12 novembre 2026 :
- PHILIPPE = https://en.wikipedia.org/wiki/Philip_the_Bold#Marriage_and_issue ;
- MARGUERITE = https://en.wikipedia.org/wiki/Margaret_III_of_Flanders ;
- JEAN = https://en.wikipedia.org/wiki/John_the_Fearless ; MARGUERITE_BAV = https://en.wikipedia.org/wiki/Margaret_of_Bavaria ;
- MARGUERITE_B = https://en.wikipedia.org/wiki/Margaret_of_Burgundy,_Duchess_of_Bavaria ;
- CATHERINE = https://en.wikipedia.org/wiki/Catherine_of_Burgundy ; LEOPOLD = https://en.wikipedia.org/wiki/Leopold_IV,_Duke_of_Austria ;
- ANTOINE = https://en.wikipedia.org/wiki/Anthony_of_Brabant ; PHILIPPE_N = https://en.wikipedia.org/wiki/Philip_II_of_Nevers ;
- MARIE_SAVOIE (constante existante des tests) pour la fiche de Marie, inchangée.

La fiche de chef de `grande-27` (identité, naissance `1342-01`, précision `mois`, divergence 17/15 janvier) ne change pas. Chaque présence, exclusion et lacune nomme la personne et porte une URL. Les tests tirent leurs attentes de constantes nommées d'après ces pages, sans les relire dans le catalogue ni dans le constructeur.

**Le chef (`grande-27`).** Le lot ajoute un complément `personne-grande-27` dans `liens` :
- `presence=vivante`, source PHILIPPE : duc jusqu'à sa mort, le 27 avril 1404 ; aucune mort programmée ;
- `pere=null`, lacune de périmètre : Jean II de France, son père ; aucune fiche, aucune absence attestée ;
- `mere=null`, lacune de périmètre qui nomme Bonne de Luxembourg (« Bonne de Bohême » dans l'infobox de la même page, divergence conservée) ;
- `conjoints=['personne-marguerite-flandre']`, source PHILIPPE : mariage le 19 juin 1369.

**L'épouse.** Une fiche nouvelle, de maison `grande-27` : `personne-marguerite-flandre`, « Marguerite III de Flandre », née le 13 avril 1350 (`jour`, MARGUERITE), vivante (morte le 16 mars 1405, MARGUERITE), conjointe réciproque de Philippe (sources PHILIPPE et MARGUERITE, 1369). Son fait de conjoint dit aussi qu'elle était veuve de Philippe de Rouvres (mariage en 1355, mort en 1361, sans enfant) : cette union passée ne crée aucune fiche. Ses parents, Louis II de Flandre et Marguerite de Brabant, sont des lacunes de périmètre.

**Les enfants vivants.** Cinq fiches nouvelles, de maison `grande-27`. Chacune a pour père `personne-grande-27` et pour mère `personne-marguerite-flandre`, avec les sources PHILIPPE (liste des enfants de Philippe et Marguerite) :
- `personne-jean-sans-peur`, « Jean sans Peur », né le 28 mai 1371 (`jour`, JEAN), vivant (mort le 10 septembre 1419), fils aîné. `conjoints=[]`, lacune : Marguerite de Bavière (née en 1363), épousée le 12 avril 1385 à Cambrai (JEAN, MARGUERITE_BAV). Conjoint d'enfant hors périmètre, aucune absence attestée ;
- `personne-marguerite-bourgogne`, « Marguerite de Bourgogne », naissance `{"valeur": "1374-10", "precision": "mois"}` (MARGUERITE_B, PHILIPPE), vivante (morte le 8 mars 1441). `conjoints=[]`, lacune : Guillaume de Bavière, épousé le 12 avril 1385 (MARGUERITE_B) ; leur fille Jacqueline naît le 16 août 1401, après le départ ;
- `personne-catherine-bourgogne`, « Catherine de Bourgogne », naissance `{"valeur": "1378-04", "precision": "mois"}` (PHILIPPE et MARGUERITE ; CATHERINE ne donne que 1378), vivante. Le fait de présence garde la divergence : morte le 24 janvier 1425 à Gray (PHILIPPE, MARGUERITE) ou le 26 janvier 1425 à Dijon (CATHERINE). `conjoints=[]`, lacune : Léopold IV d'Autriche, épousé le 15 août 1393 (CATHERINE, LEOPOLD), union sans enfant. Léopold IV n'est pas Albert IV : aucun lien vers `personne-grande-30` ;
- `personne-antoine-bourgogne`, « Antoine de Bourgogne », naissance `{"valeur": "1384-08", "precision": "mois"}` (ANTOINE, PHILIPPE), vivant (mort le 25 octobre 1415 à Azincourt). `conjoints=[]`, lacune : aucun conjoint au départ ; ses mariages avec Jeanne de Saint-Pol (21 février 1402) et Élisabeth de Görlitz (16 juillet 1409) sont futurs (ANTOINE). Ni célibat ni veuvage ;
- `personne-philippe-nevers`, « Philippe de Bourgogne », naissance `{"valeur": "1389-10", "precision": "mois"}` (PHILIPPE_N), vivant (mort le 25 octobre 1415 à Azincourt). `conjoints=[]`, lacune : ses mariages avec Isabelle de Coucy (9 avril 1409) et Bonne d'Artois (20 juin 1413) sont futurs (PHILIPPE_N). Ni célibat ni veuvage.

Les petits-enfants (dont Philippe le Bon, né en 1396, et les filles de Jean) sont hors périmètre : ni fiche, ni exclusion.

**Marie de Bourgogne.** `personne-marie-bourgogne` reste la seule fiche de ce nom, de maison `grande-12`, conjointe d'Amédée VIII. Son nom, sa naissance (`1386`, `annee`), ses sources d'identité, de naissance, de conjoint et de présence, et leurs repères restent mot pour mot. Seuls ses deux liens changent :
- `pere='personne-grande-27'`, source PHILIPPE : Marie, née en septembre 1386 à Dijon, fille de Philippe et Marguerite, mariée à Amédée VIII ;
- `mere='personne-marguerite-flandre'`, source MARGUERITE. Le fait garde la divergence : la page de Marguerite III la dit née en septembre 1380. La fiche garde 1386, sans choisir de mois.

Leurs lacunes passent de « hors périmètre familial » à `null`. C'est la seule attente existante que le lot remplace. Dans `_voisins_historiques`, l'assertion `(None, None)` sur le père et la mère de Marie devient l'assertion exacte de ces deux références, et la vérification de leurs sources passe à `_bourgogne`. Elle n'est pas assouplie : elle devient plus exigeante, comme le veut la décision A de #431/#800 (enrichir les attentes, garder les faits). L'issue, listée par `CAP.md` parmi les découpes de #431, le demande. Toutes les autres attentes sur Marie, sur Amédée VIII et sur l'état `grande-12` (neuf enfants futurs exclus, réserve FMG) restent intactes.

**L'état `grande-27`.** `conjoints=union` (source PHILIPPE, 19 juin 1369) et `enfants=documentes` (source PHILIPPE : neuf enfants, dont six vivants au départ ; MARGUERITE_B dit aussi « neuf enfants »). Sept exclusions sourcées :
- Charles de Bourgogne (1372–1373) et Louis de Bourgogne (1377–1378) : enfants morts avant 1400 (PHILIPPE, MARGUERITE) ;
- Bonne de Bourgogne (1379–1399, Arras), fiancée à Jean de Bourbon : morte en 1399, avant le départ (PHILIPPE, MARGUERITE) ;
- Jeanne de Saint-Pol (1402) et Élisabeth de Görlitz (1409) : épouses futures d'Antoine (ANTOINE) ;
- Isabelle de Coucy (1409) et Bonne d'Artois (1413) : épouses futures de Philippe (PHILIPPE_N).

Philippe le Hardi n'a pas d'union future : il meurt en 1404 sans remariage.

**Totaux.** Quatre-vingt-six fiches (six nouvelles), vingt-sept compléments, vingt-sept états, triés par maison. Le lot complète `fidelite` dans le catalogue. Dans « Les personnes » de MODELE.md, il met à jour les compteurs, ajoute une phrase Bourgogne (`grande-27`) et complète la phrase Savoie : Marie est la fille de Philippe le Hardi et de Marguerite III. Il n'ajoute aucun champ de premier niveau ni aucun emplacement : `cell_id` reste la seule clé spatiale.

**Niveau 2.** Six filiations donnent dix-huit contrôles chronologiques, tous vérifiés (mesuré sur une copie en mémoire avec `valider_liens_familiaux`) :
- six antériorités de Philippe (janvier 1342) vers Jean, Marguerite, Catherine, Antoine, Marie et Philippe ;
- six antériorités et six âges maternels de Marguerite III (13 avril 1350), de 21 ans (Jean) à 39 ans (Philippe).

Le bilan exact passe de 38/115 à 56 vérifiés et 115 indéterminés.

**Niveau 3.** Génération, évolution familiale, succession et partage restent non simulés. Les décès, mariages et naissances postérieurs servent seulement à établir la photographie de départ.

## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_modificateurs.py (seulement son empreinte `EMPREINTES_365` et son commentaire)
jeu/sim/MODELE.md
docs/briefs/979-la-bourgogne-la-famille-de-philippe-le-hardi.md

## Conditions de succès
SC1 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k familles_historiques`. Sur le catalogue d'avant le lot, la commande échoue d'abord sur les cas neufs, faute de fiches, de complément et d'état. Elle passe ensuite, et le constat du rouge est transmis au pilote. Contre-épreuve : une sélection vide, un test ignoré ou une seule erreur de collecte ne valent pas un rouge.

Comme dans #823 à #826, #977 et #978 (décision A de #431 et #800), les attentes exhaustives sont enrichies, jamais assouplies :
- dans `_familles_historiques`, le décompte des fiches passe à 86, avec l'ensemble exact de leurs identifiants, et `len(liens) == 27`, avec l'ensemble exact des compléments ;
- dans `_etats_historiques`, `len(etats) == 27`, avec l'ensemble exact des maisons ;
- dans `test_familles_historiques_maghreb` et `test_familles_historiques_mamelouks_chypre_autriche`, l'inventaire passe à 86/27/27 : leurs autres assertions restent mot pour mot ;
- les six fiches nouvelles et `personne-grande-27` rejoignent l'ensemble que la boucle générique saute ;
- dans `_voisins_historiques`, seule l'assertion sur le père et la mère de Marie change, comme le dit la Règle du monde.

SC2 — La même commande compare le catalogue ET le monde à des constantes dédiées, sur le gabarit de `_mca` : `BOURGOGNE = 'grande-27'`, `FICHES_BOURGOGNE`, `LIEN_BOURGOGNE`, `ETAT_BOURGOGNE`, `BOURGOGNE_EXCLUSIONS` et `BOURGOGNE_DIVERGENCES`. Une fonction `_bourgogne(fiches=None, etat=None)` est appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle :
- pour le chef, chaque fiche nouvelle et Marie : le nom, la maison, la naissance et sa précision, le père, la mère, les conjoints, la présence, les URL des sources et les repères des faits et des lacunes ;
- que seuls les six enfants (Marie comprise) ont `personne-grande-27` pour père et `personne-marguerite-flandre` pour mère ;
- qu'une seule fiche de tout le catalogue s'appelle « Marie de Bourgogne », et que c'est `personne-marie-bourgogne`, de maison `grande-12` ;
- qu'aucune fiche ne relie un enfant de Philippe à `personne-grande-30` ni à une autre maison que par Marie et Amédée VIII.

Un test neuf, `test_familles_historiques_bourgogne`, sur le gabarit de `test_familles_historiques_mamelouks_chypre_autriche`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler une fiche, le complément ou l'état ;
- altérer chacune de leurs feuilles, et le père, la mère ou les sources de parenté de Marie ;
- remettre à Marie `pere=None` ou `mere=None` avec leurs anciennes lacunes ;
- ajouter une seconde « Marie de Bourgogne » de maison `grande-27`, enfant de Philippe et de Marguerite (liens résolus, `_controler_famille` passe) ;
- remplacer un repère : « 19 juin 1369 », « 27 avril 1404 », « Bonne de Luxembourg », « Bonne de Bohême », « 1355 », « 1361 », « fils aîné », « 12 avril 1385 », « Marguerite de Bavière », « Guillaume de Bavière », « 16 août 1401 », « 15 août 1393 », « Léopold IV », « 24 janvier », « 26 janvier », « 21 février 1402 », « 9 avril 1409 », « septembre 1380 », « neuf enfants », « ni célibat ni veuvage », « aucune absence attestée » ;
- passer `conjoints` à `lacune` ou `veuvage`, `enfants` à `lacune` ou `absence_attestee`, ou une lacune d'enfant à une absence attestée ;
- supprimer une exclusion, ou altérer son motif, ses sources ou ses dates ;
- donner à Catherine le jour `1378-04-01` (précision `jour`), ou à Marie la naissance `1380` ;
- relier Catherine à `personne-grande-30` comme conjointe réciproque.

SC3 — La même commande éprouve des copies non vides, avec des liens résolus (`_controler_famille` passe à chaque fois) :
- les trois enfants morts (Charles, Louis, Bonne) construits comme enfants de Philippe, avec `presence=decedee` ;
- les quatre épouses futures et un « Héritier inventé » construits comme enfants de Philippe, puis comme conjoints réciproques de Philippe, vivants.

Dans chaque cas, `_bourgogne` doit échouer, et la preuve d'ensemble aussi. Les copies sont faites, comme avant, depuis `personne-marie-bourgogne` : le codeur vérifie que les contre-épreuves existantes qui la copient (voisins, Constantinople, Ottomans, Balkans, Maghreb, Mamelouks-Chypre-Autriche, Horde) échouent toujours pour leur motif, malgré ses nouveaux liens.

SC4 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k 'personnages_sources or personnages_attestes or personnes_catalogue or personnes_chefs or familles_etats or familles_liens or familles_integration'` passe sur le lecteur réel, la construction et la validation publique. Les inventaires passent à 86 fiches, 27 compléments et 27 états. Dans `test_familles_integration`, le bilan exact est de 56 vérifiés et 115 indéterminés. Les dix-huit contrôles de la Règle du monde rejoignent l'ensemble exact `verifies` ; l'ensemble des indéterminés est inchangé.

Contre-épreuves conservées, toutes doivent échouer : une référence inconnue, un auto-lien, un cycle, un conjoint dupliqué ou non réciproque, un enfant antérieur ou contemporain, une mère de 14 ou de 46 ans. Une mère de 15 ou de 45 ans est acceptée. Contre-épreuves neuves, refusées (`ValueError`) :
- la naissance de Marguerite III placée au `1371-05-28` (antériorité impossible vers Jean) ;
- la naissance de Marguerite III placée au `1340-01-01` (mère de 49 ans à la naissance de Philippe).

SC5 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k personnes_serialisation` étend les mutations profondes à `grande-27` (liste de `alterer_iles`), avec ses fiches, son complément, son état, ses sources, ses lacunes et ses exclusions. Les graines 0 et 42 et les permutations des tables donnent les mêmes personnes. Contre-épreuves :
- une mutation d'une copie publiée reste sans effet sur le monde ;
- une mutation du monde se retrouve exactement dans sa copie ;
- un objet imbriqué partagé, une lecture du catalogue ou une reconstruction à la sérialisation font échouer le test.

SC6 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py sim/tests/test_determinisme.py sim/tests/test_pays_et_jauges.py -q` passe. `test_personnes_neutres` reste intact : habitants, économie, retours et état aléatoire restent égaux au témoin sans personnes, pour les graines 0 et 42. Contre-épreuve : une lecture ou une reconstruction au tick, une mutation familiale ou une consommation d'aléa créent un écart détecté. Aucun test n'est supprimé, ignoré ou rendu moins exigeant.

SC7 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_modificateurs.py -q` passe. Comme six fiches et un complément entrent dans le registre, et que Marie reçoit deux liens, l'empreinte du monde au 365e jour (`EMPREINTES_365["linux"][0]`) change. Le codeur la recapture sous Linux. Avant de le faire, il mesure, sur la base et sur le lot, que seule la clé `personnages` de `World.to_dict()` diffère, et que l'empreinte de la photographie (`EMPREINTES_365["linux"][1]`) est identique. Le commentaire au-dessus de la constante le dit, daté du lot. Contre-épreuve : l'ancienne empreinte du monde échoue sur le lot. Une différence hors de `personnages`, ou une photographie qui change, est un défaut du lot : il faut la corriger, pas la recapturer.

SC8 — `git diff --check` passe. Après l'enregistrement du brief par le pilote, `git diff --numstat origin/master | awk '{n += $1 + $2} END {print n; exit (n >= 750)}'` passe. Tant que le brief n'est pas suivi par git, ajouter ses lignes une seule fois. Le budget est de 480 lignes environ, ajouts et suppressions compris. Contre-épreuve : un espacement fautif, ou un total de 750 lignes, font échouer la commande. Un dépassement impose une découpe, jamais le retrait d'une lacune, d'une exclusion ou d'une preuve.

Pour le relecteur :
- vérifie que chaque `fait` dit ce que la page dit vraiment. Relis PHILIPPE, MARGUERITE, JEAN, MARGUERITE_BAV, MARGUERITE_B, CATHERINE, LEOPOLD, ANTOINE et PHILIPPE_N (`curl "https://en.wikipedia.org/w/index.php?title=<page>&action=raw"`) ;
- vérifie qu'aucune épouse, aucun enfant et aucune date ne sont inventés, et qu'aucune lacune n'est devenue une absence attestée ;
- vérifie que Marie n'a qu'une fiche, que seuls son père et sa mère ont changé, et que l'assertion remplacée dans `_voisins_historiques` est plus exigeante qu'avant ;
- vérifie que le diff ne touche que les cinq fichiers du périmètre, que `test_modificateurs.py` ne change que son empreinte et son commentaire, et que `personnages.py` n'a pas bougé.

## Hors périmètre
- La maison `grande-29` (sous-lot suivant de #803), et tous les autres chefs.
- Les parents et la fratrie de Philippe et de Marguerite III (Jean II, Bonne de Luxembourg, Louis II de Flandre, Marguerite de Brabant, Philippe de Rouvres), les conjoints des enfants (Marguerite de Bavière, Guillaume de Bavière, Léopold IV, Amédée VIII mis à part, déjà chef), les petits-enfants, dont Philippe le Bon, et toute personne hypothétique qui comblerait une lacune.
- Toute autre attente sur Marie de Bourgogne, Amédée VIII ou l'état `grande-12`.
- Aucun changement du schéma, de `jeu/sim/personnages.py`, des briefs précédents, de `test_determinisme.py` ou de `test_pays_et_jauges.py`.
- Aucune naissance, mort ou union future programmée ; aucune succession, loi, partage, proposition de mariage, dot, alliance, éducation, trait ou ambition.
- Aucun changement des habitants, de l'économie, des terres ou du tick ; aucun service, aucune vue, ni Unity ni Blender.
- Tout autre chemin est interdit en écriture.
