# Lot #1083 — Bar : la famille de Robert Ier
Jalon : J6 · Machine : vps · Taille prévue : 500 lignes

## But
Au départ, le monde portera la famille de Robert Ier, duc de Bar (`seigneurie-1`), au 1er janvier 1400 : son épouse Marie de Valois, ses six enfants dont la vie au départ est établie, et les autres, morts ou de présence indéterminée, exclus avec leurs sources ainsi que l'union de 1400 non tranchée. C'est la première seigneurie de départ à recevoir son état familial.

## Le joueur
C'est un lot de fond. Il prépare deux gestes du jalon J6 : choisir un mariage (#438) et suivre l'héritier que désigne la loi (#435 à #437). L'arbre de la dynastie (#446) le rendra visible. Le joueur qui prend Bar, l'une des six seigneuries de départ et jouable par #1037, en héritera.

Après ce lot, le monde sait ceci de la maison de Bar :
- Robert Ier, cinquante-cinq ans, duc de Bar, est marié depuis le 5 octobre 1364 à Marie de Valois, fille de Jean II le Bon, cinquante-cinq ans. Elle n'est plus confondue avec Marie de France, la fille de Charles VI née en 1393 ;
- six de leurs onze enfants sont vivants au départ. Henri et Charles sont morts avant 1400. Pour Philippe, Marie (comtesse de Namur) et Bonne (comtesse de Saint-Pol), les pages ne permettent pas de dire s'ils vivent au 1er janvier 1400 : le monde ne les ressuscite pas, et ne les déclare pas morts non plus ;
- Louis, l'aîné des fils vivants, est cardinal. Édouard, vingt-deux ans, marquis de Pont-à-Mousson, est l'aîné des fils laïcs, et Jean a dix-neuf ans environ. Aucun des deux n'a d'épouse : ce sont deux fils à marier ;
- Yolande, reine douairière d'Aragon, est veuve depuis 1396. Yolande la Jeune épouse Adolphe de Juliers « en 1400 » sans jour connu : le monde ne lui donne aucun conjoint actif. Jeanne est marquise de Montferrat depuis 1393, avec un époux que le monde ne porte pas.

Le joueur sent une petite maison d'Empire, liée au sang royal de France, riche de fils et de filles à marier. Son héritier n'est pas encore fixé : Robert ne cédera le duché à Édouard qu'en 1401. Bar reste jouée par l'IA tant que le joueur ne la prend pas. Aucun héritier n'est désigné, aucun événement futur n'est programmé.

## Règle du monde
Dépend de : #980, sur la base (`c6c83451`). Le catalogue fermé, les présences, les états, les exclusions, les liens familiaux, les contrôles chronologiques et la copie profonde existent déjà. `sim/personnages.py` accepte déjà un complément et un état pour toute maison qui a un chef historique : `seigneurie-1` en a un. Le lot découle de « Les personnes » et de « Les seigneuries de départ, vue dérivée » dans `jeu/sim/MODELE.md`. Il étend les données de départ et leurs preuves. Il ne change ni `jeu/sim/personnages.py`, ni aucune règle du moteur.

Niveau 1, au 1er janvier 1400. Sources publiques relues le 14 novembre 2026 :
- ROBERT_FR = https://fr.wikipedia.org/wiki/Robert_Ier_de_Bar#Mariage_et_enfants (c'est la source de la fiche de chef) ; ROBERT_EN = https://en.wikipedia.org/wiki/Robert,_Duke_of_Bar#Marriage_and_issue ;
- MARIE_EN = https://en.wikipedia.org/wiki/Marie_of_France,_Duchess_of_Bar ; MARIE_FR = https://fr.wikipedia.org/wiki/Marie_de_France_(1344-1404) ;
- VIOLANT = https://en.wikipedia.org/wiki/Violant_of_Bar ; JEAN_A = https://en.wikipedia.org/wiki/John_I_of_Aragon ;
- HENRI = https://en.wikipedia.org/wiki/Henry_of_Bar ; LOUIS = https://en.wikipedia.org/wiki/Louis_I,_Duke_of_Bar ; EDOUARD = https://en.wikipedia.org/wiki/Edward_III_of_Bar ; JEAN_B = https://en.wikipedia.org/wiki/John_of_Bar ;
- GUILLAUME_EN = https://en.wikipedia.org/wiki/William_II_of_Namur ; GUILLAUME_FR = https://fr.wikipedia.org/wiki/Guillaume_II_de_Namur ;
- WALERAN_EN = https://en.wikipedia.org/wiki/Waleran_III_of_Ligny ; WALERAN_FR = https://fr.wikipedia.org/wiki/Waléran_III_de_Luxembourg-Ligny ;
- THEODORE_M = https://en.wikipedia.org/wiki/Theodore_II_of_Montferrat ; ADOLPHE_J = https://en.wikipedia.org/wiki/Adolf,_Duke_of_Jülich-Berg.

Plusieurs pages anglaises sont des redirections (`Yolande_of_Bar`, `Edward_III,_Duke_of_Bar`, `William_II,_Marquis_of_Namur`…) : les constantes nomment la page d'arrivée. La fiche de chef de `seigneurie-1` (identité, naissance `1344-11-08`, précision `jour`, sources ROBERT_FR) ne change pas. Chaque présence, exclusion et lacune nomme la personne et porte une URL. Les tests tirent leurs attentes de constantes nommées d'après ces pages, sans les relire dans le catalogue ni dans le constructeur.

**Le chef (`seigneurie-1`).** Le lot ajoute un complément `personne-seigneurie-1` dans `liens` :
- `presence=vivante`, sources ROBERT_FR et ROBERT_EN : duc jusqu'à sa mort, le 12 avril 1411. Il cède le duché à Édouard en 1401 en gardant l'usufruit, et écarte son petit-fils Robert, fils d'Henri : c'est après le départ, et rien n'est programmé ;
- `pere=null`, lacune de périmètre : Henri IV de Bar, aucune fiche, aucune absence attestée ;
- `mere=null`, lacune de périmètre qui nomme Yolande de Flandre (ROBERT_FR, « Yolande of Flanders » dans ROBERT_EN), dite aussi Yolande de Dampierre (lien de la même page) ; divergence de nom conservée ;
- `conjoints=['personne-marie-valois']`, sources ROBERT_FR (le 5 octobre 1364, après dispense du pape Urbain V) et ROBERT_EN (1364).

**L'épouse.** Une fiche nouvelle, de maison `seigneurie-1` : `personne-marie-valois`, « Marie de Valois ». Ses pages la titrent « Marie de France » (MARIE_FR) ou « Marie of France » (MARIE_EN) ; ROBERT_EN la nomme « Marie of Valois ». Le monde retient « Marie de Valois », pour la distinguer de `personne-marie`, « Marie de France », fille de Charles VI née le 22 août 1393, dont la fiche ne change pas. Elle est née le 18 septembre 1344 (`jour`), à Saint-Germain-en-Laye (MARIE_EN, MARIE_FR). Vivante : morte le 15 octobre 1404 (MARIE_EN, MARIE_FR). Elle est conjointe réciproque de Robert, avec les sources ROBERT_FR et MARIE_FR (mariage de 1364, dot de soixante mille livres). Son père, Jean II le Bon, est une lacune de périmètre. Sa mère est une lacune qui garde la divergence de nom : « Bonne de Luxembourg » (MARIE_FR, ROBERT_EN) ou « Bonne of Bohemia » (MARIE_EN). Elle est la sœur de Charles V et de Philippe le Hardi (`personne-grande-27`), mais le monde n'a pas de lien de fratrie : aucun lien vers `grande-3` ni vers `grande-27`.

**Les enfants vivants.** Six fiches nouvelles, de maison `seigneurie-1`. Chacune a pour père `personne-seigneurie-1` et pour mère `personne-marie-valois`, avec les sources ROBERT_EN et ROBERT_FR (les onze enfants de Robert et de Marie ; MARIE_EN et MARIE_FR donnent la même liste) :
- `personne-yolande-bar`, « Yolande de Bar », naissance `{"valeur": "vers 1365", "precision": "vers"}` (VIOLANT et JEAN_A : « c. 1365 » ; ROBERT_EN et ROBERT_FR donnent 1365, divergence conservée). « Huitième de onze enfants » (VIOLANT). Vivante : morte le 3 juillet 1431 à Barcelone (VIOLANT). `conjoints=[]`, lacune : veuve de Jean Ier d'Aragon. Elle l'a épousé le 2 février 1380 (JEAN_A ; 1380 pour ROBERT_EN, ROBERT_FR et VIOLANT ; 1384 pour MARIE_EN). Il est mort le 19 mai 1396 (JEAN_A ; 1395 pour MARIE_FR et pour une phrase de VIOLANT). Aucune union active au départ, aucun lien vers `grande-6` (Martin Ier, frère de Jean Ier), aucune absence attestée. Sa fille, Yolande d'Aragon, est hors périmètre ;
- `personne-louis-bar`, « Louis de Bar », naissance `{"valeur": "entre 1370 et 1375", "precision": "intervalle"}` (LOUIS, ROBERT_EN). « Cinquième fils » (LOUIS), cardinal depuis 1391, évêque de Langres depuis 1397 (LOUIS ; 1395 pour MARIE_FR). Vivant ; le fait de présence garde la divergence : mort le 23 juin 1430 (LOUIS), le 26 juin 1430 (ROBERT_EN) ou en 1431 (MARIE_EN, MARIE_FR). `conjoints=[]`, lacune : homme d'Église, aucune épouse nommée ; ni célibat ni veuvage attestés ;
- `personne-edouard-bar`, « Édouard de Bar », naissance `{"valeur": "1377-06", "precision": "mois"}` (EDOUARD : « late June 1377 » ; ROBERT_EN et ROBERT_FR donnent 1377). Marquis de Pont-à-Mousson depuis 1399, héritier du duché après la mort de ses frères aînés (EDOUARD). Vivant : tué à Azincourt le 25 octobre 1415 (EDOUARD). `conjoints=[]`, lacune : « never married » (EDOUARD) ; ses enfants illégitimes sont hors périmètre ; aucune absence attestée ;
- `personne-yolande-jeune-bar`, « Yolande la Jeune de Bar », naissance `{"valeur": "vers 1378", "precision": "vers"}` (ADOLPHE_J : « c. 1378 »). Elle porte le prénom de sa sœur aînée « pour des raisons incertaines » (MARIE_EN). Vivante : morte le 10 janvier 1421 (ADOLPHE_J ; 1421 pour ROBERT_EN et ROBERT_FR). `conjoints=[]`, lacune : elle épouse Adolphe de Juliers et de Berg en 1400, au château de Dun (ADOLPHE_J ; « in 1400 » pour ROBERT_EN, « en 1400 » pour ROBERT_FR), sans jour. Le monde ne sait pas si l'union est active au 1er janvier 1400 : aucun conjoint actif, aucune absence attestée ;
- `personne-jean-bar`, « Jean de Bar », naissance `{"valeur": "1380", "precision": "annee"}` (JEAN_B, ROBERT_EN, ROBERT_FR), seigneur de Puisaye. Vivant : tué à Azincourt le 25 octobre 1415 (JEAN_B). `conjoints=[]`, lacune : aucune épouse nommée ; ni célibat ni veuvage ;
- `personne-jeanne-bar`, « Jeanne de Bar », naissance `null`, lacune : aucune page ne la donne. Vivante : morte le 15 janvier 1402 (THEODORE_M, MARIE_EN ; 1402 pour ROBERT_EN, ROBERT_FR et MARIE_FR). `conjoints=[]`, lacune : mariée en 1393 à Théodore II Paléologue, marquis de Montferrat (THEODORE_M, ROBERT_EN, ROBERT_FR, MARIE_EN, MARIE_FR). L'union est active au départ, mais le conjoint est hors périmètre, sans fiche ; aucune absence attestée. Théodore de Montferrat reste distinct de `personne-theodore-ii` (Théodore II Paléologue, fils de Manuel II, `grande-15`), qui ne reçoit aucun lien.

Les petits-enfants, dont Robert de Marle (fils d'Henri, né en 1390), Yolande d'Aragon et les enfants de Jeanne, sont hors périmètre : ni fiche, ni exclusion. Aucun nom nouveau n'est déjà porté par une fiche du catalogue.

**L'état `seigneurie-1`.** `conjoints=union` (source ROBERT_FR, 5 octobre 1364) et `enfants=documentes` (source ROBERT_EN : onze enfants, dont six vivants au départ ; ROBERT_FR, MARIE_EN et MARIE_FR donnent les mêmes onze). Six exclusions sourcées :
- Henri de Bar (vers 1362 – octobre 1397, à Trévise) : fils aîné, mort de la peste au retour de Nicopolis (HENRI, MARIE_EN, ROBERT_EN, ROBERT_FR). La naissance de 1362, antérieure au mariage de 1364, est discutée par ROBERT_EN : le motif le dit ;
- Philippe de Bar : présence indéterminée. Il est tué à Nicopolis en 1396 pour ROBERT_EN et MARIE_FR, le 25 septembre 1396 pour MARIE_EN, « at or soon after » la bataille pour EDOUARD. Mais ROBERT_FR le dit mort en 1404 dans une prison turque, marié en 1384 à Yolande d'Enghien. Il est exclu des vivants, sans décès ni survie déduits ;
- Charles de Bar (1373 – 1392), seigneur de Nogent-le-Rotrou (ROBERT_EN, ROBERT_FR, MARIE_EN, MARIE_FR) ;
- Marie de Bar : présence indéterminée. Née en 1374, sans date de mort (« 1374 †? », ROBERT_EN ; ROBERT_FR), mariée en 1384 à Guillaume II de Namur (ROBERT_EN, ROBERT_FR, MARIE_EN, MARIE_FR). Guillaume II se remarie en 1393 avec Jeanne d'Harcourt (GUILLAUME_EN, GUILLAUME_FR). Elle est exclue des vivants sans décès inventé, et n'a ni fiche ni union active ;
- Bonne de Bar : présence indéterminée. Elle meurt en 1400 sans jour (MARIE_FR, WALERAN_EN, WALERAN_FR) ou en 1436 (ROBERT_EN) ; ROBERT_FR écrit « † 1400 ou 1436 ? ». Elle est mariée en 1393 à Waléran III de Luxembourg, comte de Ligny et de Saint-Pol (ROBERT_EN, ROBERT_FR, MARIE_EN, WALERAN_FR ; « c. 1392 » dans l'infobox de WALERAN_EN). Comme Ertuğrul Çelebi (`grande-16`), une mort en 1400 sans jour ne dit pas qui vit au 1er janvier : ni vivante ni décédée par déduction ;
- Adolphe de Juliers : époux de Yolande la Jeune. Le mariage de 1400, au château de Dun, n'a pas de jour (ADOLPHE_J, ROBERT_EN, ROBERT_FR) : l'union n'est pas établie au départ, il n'a ni fiche ni conjoint actif.

Robert et Marie n'ont pas d'union future ; Marie meurt en 1404, avant lui.

La demande nommait huit enfants vivants et l'union de Namur et de Saint-Pol en lacunes. Les pages ne le permettent pas : le remariage de Guillaume II en 1393 et la mort de Bonne en 1400 sans jour laissent leur présence indéterminée. Le lot suit la règle déjà appliquée dans le catalogue, en Écosse, en Navarre, à Constantinople et chez les Ottomans : une présence indéterminée est une exclusion des vivants, jamais une vie supposée. Philippe reste exclu, comme le voulait la demande, mais son motif garde la divergence de ROBERT_FR. Aucun test existant ne change de sens, et aucune règle du monde ne change : ce n'est pas une question au propriétaire.

**Les maisons qui ont un état.** Vingt-huit grandes maisons avaient leur état ; `seigneurie-1` est la première seigneurie de départ à en recevoir un. Ce sont désormais vingt-neuf états. La Horde d'Or (`grande-21`) et Tlemcen (`grande-24`) restent sans état. Les cinq autres seigneuries (`seigneurie-2` à `seigneurie-6`) aussi : leurs lots suivent (#804). Leurs preuves existantes restent mot pour mot, dont `'personne-seigneurie-3' not in fiches` pour Constantinople.

**Totaux.** Cent deux fiches (sept nouvelles), vingt-neuf compléments, vingt-neuf états, triés par maison. Le registre passe de 2 381 à 2 388 personnes. Le lot complète `fidelite` dans le catalogue. Dans « Les personnes » de MODELE.md, il met à jour les compteurs et ajoute une phrase Bar (`seigneurie-1`) : la couverture des seigneuries commence. Il n'ajoute aucun champ de premier niveau ni aucun emplacement : `cell_id` reste la seule clé spatiale.

**Niveau 2.** Six filiations donnent dix-huit contrôles chronologiques :
- six vérifiés, pour Édouard (juin 1377) et Jean (1380) : l'antériorité de Robert (8 novembre 1344), l'antériorité de Marie (18 septembre 1344) et son âge maternel, de 32 et de 35 ans ;
- douze indéterminés, pour Yolande (`vers`), Louis (`intervalle`), Yolande la Jeune (`vers`) et Jeanne (sans naissance) : pour chacun, l'antériorité paternelle, l'antériorité maternelle et l'âge maternel, avec le motif « Naissance absente ou sans bornes exploitables. ».

Le bilan exact passe de 77/118 à 83 vérifiés et 130 indéterminés. Le codeur mesure ces nombres avec `valider_liens_familiaux`, sur une copie en mémoire, avant d'écrire les attentes.

**Niveau 3.** Génération, évolution familiale, succession, cession du duché en 1401 et partage restent non simulés. Les décès, mariages et naissances postérieurs servent seulement à établir la photographie de départ.

## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_modificateurs.py (seulement son empreinte `EMPREINTES_365` et son commentaire)
jeu/sim/MODELE.md
docs/briefs/1083-bar-la-famille-de-robert-ier.md

## Conditions de succès
SC1 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k familles_historiques`. Sur le catalogue d'avant le lot, la commande échoue d'abord sur les cas neufs, faute de fiches, de complément et d'état. Elle passe ensuite, et le constat du rouge est transmis au pilote. Contre-épreuve : une sélection vide, un test ignoré ou une seule erreur de collecte ne valent pas un rouge.

Comme dans #977 à #980 (décision A de #431 et #800), les attentes exhaustives sont enrichies, jamais assouplies :
- dans `_familles_historiques`, le décompte des fiches passe à 102, avec l'ensemble exact de leurs identifiants, et `len(liens) == 29`, avec l'ensemble exact des compléments (`personne-seigneurie-1` ajouté) ;
- dans `_etats_historiques`, `len(etats) == 29`, avec l'ensemble exact des maisons (`seigneurie-1` ajouté) ;
- dans `test_familles_historiques_maghreb`, `test_familles_historiques_mamelouks_chypre_autriche`, `test_familles_historiques_bourgogne` et `test_familles_historiques_palatinat`, l'inventaire passe à 102/29/29, et le registre du Palatinat passe de 2 381 à 2 388 personnes. Leurs autres assertions restent mot pour mot ;
- les sept fiches nouvelles et `personne-seigneurie-1` rejoignent l'ensemble que la boucle générique saute.

Aucune autre attente existante n'est remplacée.

SC2 — La même commande compare le catalogue ET le monde à des constantes dédiées, sur le gabarit de `_palatinat` : `BAR = 'seigneurie-1'`, `FICHES_BAR`, `ENFANTS_BAR`, `LIEN_BAR`, `ETAT_BAR`, `BAR_EXCLUSIONS` et `BAR_DIVERGENCES`. Une fonction `_bar(fiches=None, etat=None)` est appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle :
- pour le chef et chaque fiche nouvelle : le nom, la maison, la naissance et sa précision, le père, la mère, les conjoints, la présence, les URL des sources et les repères des faits et des lacunes ;
- que seuls les six enfants ont `personne-seigneurie-1` pour père et `personne-marie-valois` pour mère ;
- que `personne-marie` reste la seule « Marie de France » du catalogue, de maison `grande-3`, née le `1393-08-22`, fille de `personne-grande-3` et de `personne-isabeau`, sa fiche inchangée mot pour mot, et qu'aucune autre fiche ne s'appelle « Marie de Valois » ;
- qu'aucune fiche de `seigneurie-1` n'a de lien vers une fiche de `grande-6`, vers `personne-theodore-ii`, vers `personne-grande-27` ni vers une autre maison ;
- que les maisons qui ont un état sont exactement `grande-1` à `grande-30` sauf `grande-21` et `grande-24`, plus `seigneurie-1` ; aucune autre seigneurie n'a d'état ni de complément.

Un test neuf, `test_familles_historiques_bar`, sur le gabarit de `test_familles_historiques_palatinat`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler une fiche, le complément ou l'état ;
- altérer chacune de leurs feuilles ;
- renommer `personne-marie-valois` en « Marie de France » ; ou ajouter une seconde « Marie de France », de maison `seigneurie-1`, conjointe réciproque de Robert (liens résolus, `_controler_famille` passe) ;
- donner à Jeanne `conjoints=['personne-theodore-ii']` et à Théodore II Paléologue `conjoints=['personne-jeanne-bar']` (réciproques, vivants, `_controler_famille` passe) ;
- relier Yolande de Bar à `personne-grande-6` comme conjointe réciproque ;
- remplacer un repère : « 5 octobre 1364 », « Urbain V », « 12 avril 1411 », « 1401 », « Henri IV de Bar », « Yolande de Flandre », « Yolande of Flanders », « Yolande de Dampierre », « 18 septembre 1344 », « Saint-Germain-en-Laye », « 15 octobre 1404 », « Jean II le Bon », « Bonne de Luxembourg », « Bonne of Bohemia », « Marie of Valois », « 22 août 1393 », « c. 1365 », « huitième de onze enfants », « 3 juillet 1431 », « 2 février 1380 », « 1384 », « 19 mai 1396 », « 1395 », « entre 1370 et 1375 », « cinquième fils », « 23 juin 1430 », « 26 juin 1430 », « 1431 », « late June 1377 », « 1399 », « never married », « 25 octobre 1415 », « c. 1378 », « 10 janvier 1421 », « château de Dun », « Puisaye », « 15 janvier 1402 », « 1393 », « Montferrat », « onze enfants », « octobre 1397 », « Trévise », « 25 septembre 1396 », « 1404 », « Yolande d'Enghien », « Nogent-le-Rotrou », « Guillaume II de Namur », « Jeanne d'Harcourt », « 1436 », « Saint-Pol », « présence indéterminée », « ni célibat ni veuvage », « aucune absence attestée » ;
- passer `conjoints` à `lacune` ou `veuvage`, `enfants` à `lacune` ou `absence_attestee`, ou une lacune d'enfant à une absence attestée ;
- supprimer une exclusion, ou altérer son motif, ses sources ou ses dates ;
- donner à Yolande la naissance `1365` (précision `annee`), à Louis la naissance `1370` (précision `annee`), à Édouard la naissance `1377` (précision `annee`), ou à Yolande la Jeune un conjoint actif ;
- ajouter un état `seigneurie-2`, ou retirer l'état `seigneurie-1`.

SC3 — La même commande éprouve des copies non vides, avec des liens résolus (`_controler_famille` passe à chaque fois) :
- Henri et Charles construits comme enfants de Robert et de Marie, avec `presence=decedee` ;
- Philippe, Marie de Bar et Bonne construits comme enfants de Robert et de Marie, chacun avec `presence=vivante` puis `presence=decedee` ;
- Adolphe de Juliers construit comme fiche de `seigneurie-1`, vivant et conjoint réciproque de Yolande la Jeune ;
- un « Héritier inventé » construit comme enfant de Robert et de Marie, vivant.

Dans chaque cas, `_bar` doit échouer, et la preuve d'ensemble aussi. Le codeur vérifie que les contre-épreuves existantes qui copient une fiche (voisins, Constantinople, Ottomans, Balkans, Maghreb, Mamelouks-Chypre-Autriche, Horde, Bourgogne, Palatinat) échouent toujours pour leur motif.

SC4 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k 'personnages_sources or personnages_attestes or personnes_catalogue or personnes_chefs or familles_etats or familles_liens or familles_integration'` passe sur le lecteur réel, la construction et la validation publique. Les inventaires passent à 102 fiches, 29 compléments et 29 états. Dans `test_familles_integration`, le bilan exact est de 83 vérifiés et 130 indéterminés. Les quatre enfants sans bornes (Yolande, Louis, Yolande la Jeune, Jeanne) rejoignent les listes des indéterminés paternels (18) et maternels (13), et la formule reste exacte (`86 + 18 + 2 × 13 == 130`). Les six contrôles vérifiés de la Règle du monde rejoignent l'ensemble exact `verifies` ; les douze autres rejoignent les indéterminés, avec leur motif.

Contre-épreuves conservées, toutes doivent échouer : une référence inconnue, un auto-lien, un cycle, un conjoint dupliqué ou non réciproque, un enfant antérieur ou contemporain, une mère de 14 ou de 46 ans. Une mère de 15 ou de 45 ans est acceptée. Contre-épreuves neuves, refusées (`ValueError`) :
- la naissance de Marie de Valois placée au `1377-07-01` (antériorité impossible vers Édouard, né en juin 1377) ;
- la naissance de Marie de Valois placée au `1334-01-01` (mère de 46 ans à la naissance de Jean, en 1380).

SC5 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k personnes_serialisation` étend les mutations profondes à `seigneurie-1` (liste de `alterer_iles`), avec ses fiches, son complément, son état, ses sources, ses lacunes et ses exclusions. Les graines 0 et 42 et les permutations des tables donnent les mêmes personnes. Contre-épreuves :
- une mutation d'une copie publiée reste sans effet sur le monde ;
- une mutation du monde se retrouve exactement dans sa copie ;
- un objet imbriqué partagé, une lecture du catalogue ou une reconstruction à la sérialisation font échouer le test.

SC6 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py sim/tests/test_determinisme.py sim/tests/test_pays_et_jauges.py -q` passe. `test_personnes_neutres` reste intact : habitants, économie, retours et état aléatoire restent égaux au témoin sans personnes, pour les graines 0 et 42. Les points du pays ne viennent que des chefs : ceux de Bar ne changent pas. Le départ du joueur sur Bar (`choisir_depart`, preuve de `_preuve_departs_ia`) reste vert. Contre-épreuve : une lecture ou une reconstruction au tick, une mutation familiale ou une consommation d'aléa créent un écart détecté. Aucun test n'est supprimé, ignoré ou rendu moins exigeant.

SC7 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_modificateurs.py -q` passe. Sept fiches et un complément entrent dans le registre : l'empreinte du monde au 365e jour (`EMPREINTES_365["linux"][0]`) change. Le codeur la recapture sous Linux. Avant de le faire, il mesure, sur la base et sur le lot, deux choses :
- seule la clé `personnages` de `World.to_dict()` diffère (sept fiches nouvelles, une changée : `personne-seigneurie-1`) ;
- l'empreinte de la photographie (`EMPREINTES_365["linux"][1]`) est identique.

Le commentaire au-dessus de la constante le dit, daté du lot (de 2 381 à 2 388 personnes). Contre-épreuve : l'ancienne empreinte du monde échoue sur le lot. Une différence hors de `personnages`, ou une photographie qui change, est un défaut du lot : il faut la corriger, pas la recapturer. Les autres hachages figés ne bougent pas : `python3 -m pytest sim/tests/test_ville1400.py -q` et `python3 -m pytest sim/tests/test_monde.py -q -k service_reponse_figee` passent sans retouche.

SC8 — `git diff --check` passe. Après l'enregistrement du brief par le pilote, `git diff --numstat origin/master | awk '{n += $1 + $2} END {print n; exit (n >= 800)}'` passe. Tant que le brief n'est pas suivi par git, ajouter ses lignes une seule fois. Le budget est de 500 lignes environ, ajouts et suppressions compris. Contre-épreuve : un espacement fautif, ou un total de 800 lignes, font échouer la commande. Un dépassement impose une découpe, jamais le retrait d'une lacune, d'une exclusion ou d'une preuve.

Pour le relecteur :
- vérifie que chaque `fait` dit ce que la page dit vraiment. Relis les pages des constantes (`curl -A "ForgeBrief/1.0" "https://en.wikipedia.org/w/index.php?title=<page>&action=raw"`, et `fr.wikipedia.org` pour les pages françaises ; `action=raw` ne suit pas les redirections) ;
- vérifie qu'aucune épouse, aucun enfant et aucune date ne sont inventés ; que Yolande la Jeune n'a pas de conjoint actif ; que Philippe, Marie de Bar et Bonne ne sont ni vivants ni décédés par déduction ; et qu'aucune lacune n'est devenue une absence attestée ;
- vérifie que la fiche de `personne-marie` (Marie de France) et celle de `personne-theodore-ii` n'ont pas bougé, et que la Horde, Tlemcen et les seigneuries 2 à 6 restent sans état ;
- vérifie que le diff ne touche que les cinq fichiers du périmètre, que `test_modificateurs.py` ne change que son empreinte et son commentaire, et que `personnages.py` n'a pas bougé.

## Hors périmètre
- Tout autre chef et toute autre maison : les seigneuries 2 à 6 (Wurtemberg, Morée, Branković, Evrenos, Zab, lots suivants de #804), la Horde d'Or (`grande-21`) et Tlemcen (`grande-24`), qui restent sans famille ni état.
- Les parents et la fratrie de Robert Ier et de Marie de Valois (Henri IV de Bar, Yolande de Flandre, Jean II le Bon, Bonne de Luxembourg, Charles V, Philippe le Hardi comme frère) ; les conjoints des enfants (Jean Ier d'Aragon, Théodore II de Montferrat, Guillaume II de Namur, Waléran III, Yolande d'Enghien, Marie de Coucy) ; les petits-enfants, dont Robert de Marle, Yolande d'Aragon et les enfants de Jeanne ; les enfants illégitimes d'Édouard ; toute personne hypothétique qui comblerait une lacune.
- La place de Robert de Marle dans la succession de Bar, et la cession du duché à Édouard en 1401 : #435 et #436 les traiteront.
- Toute attente nouvelle sur Marie de France, Charles VI, l'Aragon (`grande-6`), la Bourgogne (`grande-27`) ou Constantinople (`grande-15`).
- Aucun changement du schéma, de `jeu/sim/personnages.py`, de `data/seigneuries-1400.json`, des briefs précédents, de `test_determinisme.py` ou de `test_pays_et_jauges.py`.
- Aucune naissance, mort, union ou cession future programmée ; aucune succession, loi, partage, proposition de mariage, dot, alliance, éducation, trait ou ambition.
- Aucun changement des habitants, de l'économie, des terres ou du tick ; aucun service, aucune vue, ni Unity ni Blender.
- Tout autre chemin est interdit en écriture.
