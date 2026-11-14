# Lot #1084 — Wurtemberg et Morée : familles connues
Jalon : J6 · Machine : vps · Taille prévue : 550 lignes

## But
Au départ, le monde portera la famille d'Eberhard III de Wurtemberg (`seigneurie-2`) : son épouse Antonia Visconti, son seul fils survivant Eberhard le Jeune, et ses autres enfants, morts en bas âge ou à naître, exclus avec leurs sources. Il portera aussi l'état familial de Théodore Ier de Morée (`seigneurie-3`), veuf et sans enfant connu, sans lui ajouter aucun lien.

## Le joueur
C'est un lot de fond. Il prépare deux gestes du jalon J6 : suivre l'héritier que désigne la loi (#435 à #437) et choisir un mariage (#438). L'arbre de la dynastie (#446) le rendra visible. Le joueur qui prend Wurtemberg ou Morée, deux des six seigneuries de départ jouables par #1037, en héritera.

Après ce lot, le monde sait si le seigneur de ces deux maisons a un héritier :
- **Wurtemberg.** Eberhard III le Doux, la trentaine passée, est comte depuis 1392. Il est marié depuis 1380 à Antonia Visconti, fille de Bernabò Visconti de Milan, qui a la quarantaine environ. Ils ont un seul fils vivant : Eberhard le Jeune, onze ans environ, fiancé depuis le 13 novembre 1397 à Henriette, l'héritière de Montbéliard. Le mariage n'est pas encore célébré : le monde ne lui donne aucune épouse. Ulrich et Louis, les deux autres fils, sont morts en bas âge ;
- **Morée.** Théodore Ier Paléologue, despote à Mistra, la quarantaine passée, est veuf de Bartolomea Acciaioli, morte vers 1396. Le couple n'a pas eu d'enfant. On ne lui connaît aucun enfant légitime. Sa fille illégitime Théodora épousera Süleyman Çelebi en 1404 : le monde ne la porte pas et ne la relie pas à son père.

Le joueur sent la différence entre les deux maisons. Wurtemberg tient sa lignée par un seul fils, et une alliance qui lui apportera Montbéliard. La Morée n'a pas d'héritier dans la maison du despote. Rien n'est programmé : ni le mariage d'Eberhard le Jeune, ni le remariage d'Eberhard III en 1406, ni le passage de la Morée à son neveu Théodore II en 1407. Aucun héritier n'est désigné : c'est l'affaire de #435.

## Règle du monde
Dépend de : #1083, sur la base (`c52c8050`). Le catalogue fermé, les présences, les états, les exclusions, les liens familiaux, les contrôles chronologiques et la copie profonde existent déjà. `sim/personnages.py` accepte déjà un complément et un état pour toute maison qui a un chef historique. Il accepte aussi un état sans complément : `_etats` lit les conjoints du chef par `chef.get('conjoints', [])`, et `veuvage` exige qu'il n'en ait aucun. Le lot découle de « Les personnes » et de « Les seigneuries de départ, vue dérivée » dans `jeu/sim/MODELE.md`. Il étend les données de départ et leurs preuves. Il ne change ni `jeu/sim/personnages.py`, ni aucune règle du moteur.

Niveau 1, au 1er janvier 1400. Sources publiques relues le 14 novembre 2026 :
- EBERHARD_III_EN = https://en.wikipedia.org/wiki/Eberhard_III_of_W%C3%BCrttemberg#Marriages_and_children ; EBERHARD_III_DE = https://de.wikipedia.org/wiki/Eberhard_III._(W%C3%BCrttemberg,_Graf) ; EBERHARD_III_LEO = https://www.leo-bw.de/detail/-/Detail/details/PERSON/ubt_hauswuerttemberg/132122669/W%C3%BCrttemberg+Eberhard+III+Graf ; NDB = https://www.deutsche-biographie.de/sfz35480.html (c'est déjà la source de la fiche de chef) ;
- ANTONIA_EN = https://en.wikipedia.org/wiki/Antonia_Visconti ; ANTONIA_DE = https://de.wikipedia.org/wiki/Antonia_Visconti ; ANTONIA_LEO = https://www.leo-bw.de/en/detail/-/Detail/details/PERSON/ubt_hauswuerttemberg/131370790/W%C3%BCrttemberg+Antonia+Gr%C3%A4fin ;
- EBERHARD_IV_EN = https://en.wikipedia.org/wiki/Eberhard_IV_of_W%C3%BCrttemberg ; EBERHARD_IV_DE = https://de.wikipedia.org/wiki/Eberhard_IV._(W%C3%BCrttemberg) ; EBERHARD_IV_LEO = https://www.leo-bw.de/detail/-/Detail/details/PERSON/ubt_hauswuerttemberg/134143868/W%C3%BCrttemberg+Eberhard+IV+Graf ;
- THEODORE_I = https://en.wikipedia.org/wiki/Theodore_I_Palaiologos#Personal_life ; BARTOLOMEA = https://en.wikipedia.org/wiki/Bartolomea_Acciaioli ; SULEYMAN = https://en.wikipedia.org/wiki/S%C3%BCleyman_%C3%87elebi.

Les pages anglaises `Eberhard_III,_Count_of_Württemberg` et `Eberhard_IV,_Count_of_Württemberg` sont des redirections : les constantes nomment la page d'arrivée, et leurs URL sont encodées comme celles du catalogue (`%C3%BC`). Les fiches de chef de `seigneurie-2` (naissance `nach 1362`, précision `intervalle`, source NDB) et de `seigneurie-3` (naissance `c. 1355`, précision `vers`) ne changent pas. Chaque présence, exclusion et lacune nomme la personne et porte une URL. Les tests tirent leurs attentes de constantes nommées d'après ces pages, sans les relire dans le catalogue ni dans le constructeur.

**Wurtemberg : le chef (`seigneurie-2`).** Le lot ajoute un complément `personne-seigneurie-2` dans `liens` :
- `presence=vivante`, sources EBERHARD_III_EN et EBERHARD_III_LEO : comte jusqu'à sa mort, le 16 mai 1417 à Göppingen ;
- `pere=null`, lacune de périmètre : Ulrich de Wurtemberg, tué à Döffingen le 23 août 1388 (EBERHARD_III_LEO, EBERHARD_III_EN). Il n'a aucune fiche, et aucune absence n'est attestée ;
- `mere=null`, lacune de périmètre : Élisabeth de Bavière (1329–1402), fille de l'empereur Louis IV (EBERHARD_III_LEO, EBERHARD_III_DE) ;
- `conjoints=['personne-antonia-visconti']`, sources EBERHARD_III_LEO (« 27.10.(?)1380 ») et EBERHARD_III_EN (« In 1380 », à Urach, dot convenue à Milan le 1er juillet 1380, soixante-dix mille florins).

**L'épouse.** Une fiche nouvelle, de maison `seigneurie-2` : `personne-antonia-visconti`, « Antonia Visconti ».
- Naissance `{"valeur": "vers 1360", "precision": "vers"}`. ANTONIA_EN écrit « born after 1350, probably about 1360 », ANTONIA_DE et ANTONIA_LEO « nach 1350 » : la divergence est conservée.
- Vivante : morte en mars 1405 à Stuttgart. Le jour diverge : le 26 mars pour ANTONIA_DE, ANTONIA_LEO, EBERHARD_III_DE et le corps d'ANTONIA_EN, le 16 mars pour l'infobox et l'introduction d'ANTONIA_EN.
- Conjointe réciproque d'Eberhard III, avec les sources ANTONIA_LEO et ANTONIA_DE. Le mariage est célébré le 27 octobre 1380 à Urach ; la date est marquée « (?) » par ANTONIA_LEO, et la note d'ANTONIA_DE dit qu'elle n'est pas assurée. L'union est active au départ.
- Son père, Bernabò Visconti, et sa mère, Beatrice Regina della Scala (ANTONIA_EN, ANTONIA_LEO ; « Beatrice della Scala » dans ANTONIA_DE), sont des lacunes de périmètre. Elle est sœur de Caterina Visconti (`personne-caterina-visconti`, `grande-10`) et tante d'Isabeau de Bavière (`personne-isabeau`), mais le monde n'a pas de lien de fratrie : aucun lien vers `grande-10` ni vers `grande-3`.

**Le fils vivant.** Une fiche nouvelle, de maison `seigneurie-2` : `personne-eberhard-iv-wurtemberg`, « Eberhard IV de Wurtemberg », dit le Jeune (« der Jüngere »). Il a pour père `personne-seigneurie-2` et pour mère `personne-antonia-visconti`, avec les sources EBERHARD_IV_LEO et EBERHARD_IV_EN (« the only surviving child »).
- Naissance `{"valeur": "vers 1388", "precision": "vers"}`. C'est « um 1388 » pour EBERHARD_IV_LEO et « c. 1388 » pour EBERHARD_IV_EN. EBERHARD_IV_DE et ANTONIA_EN donnent le 23 août 1388, et NDB « 1388 ». Le monde suit les deux notices qui hésitent, et garde le jour en divergence : c'est aussi le jour de la mort de son grand-père à Döffingen (EBERHARD_III_LEO).
- Vivant : mort le 2 juillet 1419 à Waiblingen (EBERHARD_IV_EN, EBERHARD_IV_DE, EBERHARD_IV_LEO). Comte de Wurtemberg de 1417 à 1419.
- `conjoints=[]`, lacune : fiancé le 13 novembre 1397 à Henriette de Montbéliard (EBERHARD_IV_DE, EBERHARD_IV_LEO, EBERHARD_III_EN). Le mariage est célébré « in 1407 at the latest » (EBERHARD_IV_EN), « spätestens 1407 » (EBERHARD_IV_DE, EBERHARD_IV_LEO), sans date : aucune union active, ni célibat ni veuvage, aucune absence attestée. Ses enfants, légitimes ou non, sont hors périmètre.

Aucun nom nouveau n'est déjà porté par une fiche du catalogue.

**L'état `seigneurie-2`.** `conjoints=union` (source EBERHARD_III_LEO : Antonia, 27 octobre 1380) et `enfants=documentes` (source EBERHARD_III_LEO : « Kinder: 4 », Ulrich, Ludwig, Eberhard IV et Elisabeth ; « issue = 4, including Eberhard IV » dans l'infobox d'EBERHARD_III_EN). Cinq exclusions sourcées :
- Ulrich, fils d'Eberhard III, et Louis (Ludwig), fils d'Eberhard III : deux exclusions. Ils sont morts « in früher Kindheit », sans date (EBERHARD_III_LEO, ANTONIA_LEO). ANTONIA_EN écrit « died young », et seul Eberhard IV atteint l'âge adulte. Leurs noms « urkundlich nicht überliefert » viennent de chroniques plus tardives (EBERHARD_III_LEO). Ils sont exclus des vivants, sans date de mort déduite. Les clés des exclusions disent « fils d'Eberhard III », pour ne pas les confondre avec Ulrich, le père d'Eberhard III, ni avec les petits-fils Ulrich V et Louis Ier, nés en 1412 et 1413 et hors périmètre ;
- Henriette de Montbéliard : la fiancée d'Eberhard le Jeune. L'union n'est pas établie au départ ; elle n'a ni fiche ni conjoint actif (EBERHARD_IV_EN, EBERHARD_IV_DE, EBERHARD_IV_LEO) ;
- Élisabeth de Nuremberg, fille de Jean III : la seconde épouse, future. Le contrat de mariage date du 27 mars 1406 (EBERHARD_III_LEO, EBERHARD_III_DE ; le 27 mars dans l'infobox d'EBERHARD_III_EN, le 29 mars dans son texte), et le « Beilager » de 1412 (EBERHARD_III_DE ; « 1406/12 » pour NDB). Elle est née en 1391 ou 1392 (ANTONIA_DE, NDB). Elle reste distincte de `personne-elisabeth-nuremberg`, l'épouse de Robert III née en 1358 et fille de Frédéric V, dont la fiche ne change pas ;
- Élisabeth de Wurtemberg : la fille future, née en 1412 de la seconde union (EBERHARD_III_EN), et morte après le 26 avril 1460 (EBERHARD_III_LEO).

**Morée : un état sans complément (`seigneurie-3`).** Théodore Ier ne reçoit aucun complément dans `liens` : sa personne garde ses seuls champs de chef, plus `etat_familial`. La preuve de Constantinople (#824) l'exige mot pour mot : `'personne-seigneurie-3' not in fiches`, et aucune fiche ne l'a pour père, mère ou conjoint. MODELE.md le dit aussi : « Théodore Ier (`seigneurie-3`), qui ne reçoit aucun lien et n'en perd aucun ». L'état porte :
- `conjoints=veuvage`, source BARTOLOMEA. Bartolomea Acciaioli, fille aînée de Nerio Ier Acciaioli, épouse Théodore Ier en 1385, et meurt vers 1396 (« c. 1396 ») ; « Her husband outlived her ». THEODORE_I nomme le même mariage. Aucune union n'est active au départ, et le chef n'a aucun conjoint ;
- `enfants=lacune`, lacune : Théodore Ier « is not known to have children » et meurt « without known heirs » (THEODORE_I). Son mariage « produced no children », et Bartolomea « died childless » (BARTOLOMEA). Mais il a une fille illégitime. Ce n'est donc pas une absence attestée, et le monde ne porte aucun enfant de lui ;
- une exclusion, « Théodora », sources THEODORE_I et SULEYMAN. Elle est la fille illégitime de Théodore Ier. Sa mère est « unknown » (THEODORE_I), « his unnamed mistress » (SULEYMAN), et sa naissance n'est pas connue. Elle épouse Süleyman Çelebi en 1404 : ce mariage est futur. Elle n'a ni fiche, ni lien vers Théodore Ier ni vers `personne-suleyman-celebi`, dont la fiche ne change pas.

La fiche de chef de `seigneurie-3` ne change pas. Théodore II (`personne-theodore-ii`, `grande-15`), son neveu, lui succède en 1407 : ce n'est pas programmé, et aucun lien n'est ajouté.

**Les maisons qui ont un état.** Vingt-neuf maisons avaient leur état : vingt-huit grandes maisons et Bar. Wurtemberg et Morée s'y ajoutent : ce sont désormais trente et un états, pour trente compléments. La Morée est la première maison qui a un état sans complément. La Horde d'Or (`grande-21`), Tlemcen (`grande-24`) et les seigneuries 4 à 6 restent sans état : leur lot suit (#804). Leurs preuves existantes restent mot pour mot.

**Totaux.** Cent quatre fiches (deux nouvelles), trente compléments, trente et un états, triés par maison ; les familles restent triées par identifiant. Le registre passe de 2 388 à 2 390 personnes. Le lot complète `fidelite` dans le catalogue. Dans « Les personnes » de MODELE.md, il met à jour les compteurs. Il ajoute une phrase Wurtemberg (`seigneurie-2`) et une phrase Morée (`seigneurie-3`) : la Morée a un état sans complément, et un état appartient toujours à un chef résolu. Il n'ajoute aucun champ de premier niveau ni aucun emplacement : `cell_id` reste la seule clé spatiale.

**Niveau 2.** Une filiation donne trois contrôles chronologiques. Les trois sont indéterminés, avec le motif « Naissance absente ou sans bornes exploitables. » : l'antériorité d'Eberhard III (`intervalle`) vers Eberhard IV (`vers`), l'antériorité d'Antonia (`vers`) et son âge maternel. Le bilan exact passe de 83/130 à 83 vérifiés et 133 indéterminés. Il a été mesuré par le chef sur une copie en mémoire, avec `valider_liens_familiaux` ; le codeur le remesure avant d'écrire les attentes.

**Niveau 3.** Génération, évolution familiale, succession, partage, mariage d'Eberhard le Jeune et passage de la Morée restent non simulés. Les décès, mariages et naissances postérieurs servent seulement à établir la photographie de départ.

## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_modificateurs.py (seulement son empreinte `EMPREINTES_365` et son commentaire)
jeu/sim/MODELE.md
docs/briefs/1084-wurtemberg-et-moree-familles-connues.md

## Conditions de succès
SC1 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k familles_historiques`. Sur le catalogue d'avant le lot, la commande échoue d'abord sur les cas neufs, faute de fiches, de complément et d'états. Elle passe ensuite, et le constat du rouge est transmis au pilote. Contre-épreuve : une sélection vide, un test ignoré ou une seule erreur de collecte ne valent pas un rouge.

Comme dans #977 à #980 et #1083 (décision A de #431 et #800), les attentes exhaustives sont enrichies, jamais assouplies :
- dans `_familles_historiques`, le décompte des fiches passe à 104, avec l'ensemble exact de leurs identifiants, et `len(liens) == 30`, avec l'ensemble exact des compléments (`personne-seigneurie-2` ajouté, `personne-seigneurie-3` absent) ;
- dans `_etats_historiques`, `len(etats) == 31`, avec l'ensemble exact des maisons (`seigneurie-2` et `seigneurie-3` ajoutés), et leurs deux branches `_wurtemberg(etat=e)` et `_moree(etat=e)` ;
- `MAISONS_AVEC_ETAT` reçoit `seigneurie-2` et `seigneurie-3` ;
- dans `test_familles_historiques_maghreb`, `_mamelouks_chypre_autriche`, `_bourgogne`, `_palatinat` et `_bar`, l'inventaire passe à 104 fiches, 30 compléments et 31 états. Le registre du Palatinat et de Bar passe de 2 388 à 2 390 personnes. Leurs autres assertions restent mot pour mot ;
- dans `_bar_controle`, les deux ensembles exacts des seigneuries passent de `{CHEF_BAR}` à `{CHEF_BAR, 'personne-seigneurie-2'}`, et de `{BAR}` à `{BAR, 'seigneurie-2'}`. Dans `test_familles_historiques_bar`, l'interdiction d'un état d'une autre seigneurie devient l'ensemble exact `{BAR, 'seigneurie-2', 'seigneurie-3'}`. La contre-épreuve « un état de plus » vise `seigneurie-4` au lieu de `seigneurie-2` : elle garde son sens, car un doublon de `seigneurie-2` échouerait pour une autre raison ;
- les deux fiches nouvelles et `personne-seigneurie-2` rejoignent l'ensemble que la boucle générique saute.

Aucune autre attente existante n'est remplacée. `_constantinople` et `test_familles_historiques_constantinople` restent mot pour mot, y compris `'personne-seigneurie-3' not in fiches` et la contre-épreuve `lier(…, id='personne-seigneurie-3', …)`.

SC2 — La même commande compare le catalogue ET le monde à des constantes dédiées, sur le gabarit de `_bar` : `WURTEMBERG = 'seigneurie-2'`, `FICHES_WURTEMBERG`, `LIEN_WURTEMBERG`, `ETAT_WURTEMBERG`, `WURTEMBERG_EXCLUSIONS` et `WURTEMBERG_DIVERGENCES`. Une fonction `_wurtemberg(fiches=None, etat=None)` est appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle :
- pour le chef et les deux fiches nouvelles : le nom, la maison, la naissance et sa précision, le père, la mère, les conjoints, la présence, les URL des sources, et les repères des faits et des lacunes ;
- que seul Eberhard IV a `personne-seigneurie-2` pour père et `personne-antonia-visconti` pour mère, et qu'Eberhard III et Antonia sont les seuls conjoints l'un de l'autre ;
- qu'aucune fiche de `seigneurie-2` n'a de lien vers une autre maison, en particulier ni vers `grande-10`, `personne-caterina-visconti`, `personne-isabeau`, ni vers `personne-elisabeth-nuremberg`. Celle-ci reste la seule « Élisabeth de Nuremberg », de maison `grande-29`, née le `1358-12-13`, conjointe de `personne-grande-29` seulement ;
- que les fiches de chef de `seigneurie-2` et de `seigneurie-3` restent égales à des constantes (nom, naissance, précision, URL).

Un test neuf, `test_familles_historiques_wurtemberg`, sur le gabarit de `test_familles_historiques_bar`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler une fiche, le complément ou l'état ;
- altérer chacune de leurs feuilles ;
- remplacer un repère : « 16 mai 1417 », « Göppingen », « Ulrich de Wurtemberg », « 23 août 1388 », « Döffingen », « Élisabeth de Bavière », « Louis IV », « 27 octobre 1380 », « 27.10.(?)1380 », « In 1380 », « Urach », « 1er juillet 1380 », « soixante-dix mille », « born after 1350, probably about 1360 », « nach 1350 », « 26 mars 1405 », « 16 mars 1405 », « Stuttgart », « Bernabò Visconti », « Beatrice Regina della Scala », « Beatrice della Scala », « der Jüngere », « the only surviving child », « um 1388 », « c. 1388 », « 2 juillet 1419 », « Waiblingen », « 13 novembre 1397 », « Henriette de Montbéliard », « in 1407 at the latest », « spätestens 1407 », « Kinder: 4 », « 4, including Eberhard IV », « in früher Kindheit », « died young », « urkundlich nicht überliefert », « fils d'Eberhard III », « 27 mars 1406 », « 29 mars », « 1406/12 », « Jean III », « Frédéric V », « 1391 ou 1392 », « 1412 », « 26 avril 1460 », « ni célibat ni veuvage », « aucune absence attestée » ;
- passer `conjoints` à `lacune` ou `veuvage`, `enfants` à `lacune` ou `absence_attestee`, ou une lacune de conjoint à une absence attestée ;
- supprimer une exclusion, ou altérer son motif, ses sources ou ses dates ;
- donner à Eberhard IV la naissance `1388-08-23` (précision `jour`) ou `1388` (précision `annee`), ou à Antonia la naissance `1360` (précision `annee`) ;
- renommer Antonia « Caterina Visconti » ; donner à Eberhard III `personne-elisabeth-nuremberg` comme conjointe réciproque (liens résolus, `_controler_famille` passe) ; relier Antonia à `personne-grande-10` comme conjointe réciproque.

SC3 — La même commande éprouve la Morée par des constantes dédiées : `MOREE = 'seigneurie-3'`, `ETAT_MOREE`, `MOREE_EXCLUSIONS` et `MOREE_DIVERGENCES`. Une fonction `_moree(fiches=None, etat=None)` est appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle :
- l'état : `veuvage`, `lacune`, la source BARTOLOMEA, le texte de la lacune et l'exclusion « Théodora » avec ses deux sources ;
- l'absence de tout complément `personne-seigneurie-3` et de toute fiche de maison `seigneurie-3` ;
- qu'aucune fiche ne s'appelle « Théodora » ni « Bartolomea Acciaioli » ;
- que `personne-suleyman-celebi` garde `conjoints=[]` et sa lacune.

Dans le monde, `personne-seigneurie-3` porte exactement les clés d'un chef sans complément plus `etat_familial`. Ses sources et ses lacunes ne portent que `identite` et `naissance`.

Un test neuf, `test_familles_historiques_moree`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler l'état ; altérer chacune de ses feuilles ; remplacer un repère : « 1385 », « c. 1396 », « Nerio Ier Acciaioli », « Her husband outlived her », « is not known to have children », « without known heirs », « produced no children », « died childless », « illégitime », « unknown », « his unnamed mistress », « Süleyman Çelebi », « 1404 », « aucune absence attestée » ;
- passer `conjoints` à `union` ou `lacune`, ou `enfants` à `absence_attestee` ou `documentes` ;
- supprimer l'exclusion de Théodora, ou altérer son motif ou ses sources ;
- ajouter un complément neutre `personne-seigneurie-3` (`pere=null`, `mere=null`, `conjoints=[]`, `presence=vivante`, sources et lacunes complètes : le lecteur l'accepte) ;
- ajouter une fiche « Théodora », de maison `seigneurie-3`, fille de `personne-seigneurie-3`, vivante puis décédée ; ou une fiche « Théodora », de maison `grande-16`, conjointe réciproque de `personne-suleyman-celebi`.

SC4 — Les preuves qui lisent le monde (`test_familles_historiques` et les `_preuve_monde_*` du Maghreb, de la Horde, de la Bourgogne, du Palatinat et de Bar) repèrent aujourd'hui un complément par `{'pere', 'mere', 'conjoints', 'presence', 'etat_familial'} & f.keys()`. Avec un état sans complément, Théodore Ier y entrerait comme complément : l'inventaire et la sentinelle de Constantinople rougiraient à tort. Les six sélections deviennent un seul assistant, `_complements_du_monde(personnes)`. Il retient les chefs qui portent `pere`, `mere`, `conjoints` ou `presence`. Il exige en plus que les chefs qui portent `etat_familial` sans complément soient exactement `{'personne-seigneurie-3'}`, avec les clés de SC3. La preuve ne devient pas moins exigeante : un chef qui recevrait un état seul, ou un champ familial isolé, échoue toujours. `CHAMPS_FAMILIAUX` et les gardes de Tlemcen et de la Horde ne changent pas.

Contre-épreuves, sur des copies de `monde.personnages`. Chacune doit échouer :
- `personne-seigneurie-3` reçoit `conjoints=[]`, ou `presence='vivante'` : il redevient un complément, et la preuve de Constantinople le refuse ;
- `personne-seigneurie-4` reçoit une copie de l'`etat_familial` de la Morée sans complément ;
- `personne-seigneurie-3` perd son `etat_familial`.

SC5 — La même commande éprouve des copies non vides, avec des liens résolus (`_controler_famille` passe à chaque fois) :
- Ulrich, fils d'Eberhard III, et Louis, construits comme enfants d'Eberhard III et d'Antonia, chacun vivant puis décédé ;
- Élisabeth de Wurtemberg construite comme enfant d'Eberhard III, vivante ;
- Henriette de Montbéliard construite comme fiche de `seigneurie-2`, vivante et conjointe réciproque d'Eberhard IV ;
- Élisabeth de Nuremberg (fille de Jean III) construite comme fiche de `seigneurie-2`, vivante et conjointe réciproque d'Eberhard III ;
- un « Héritier inventé » construit comme enfant d'Eberhard III et d'Antonia, vivant.

Dans chaque cas, `_wurtemberg` doit échouer, et la preuve d'ensemble aussi. Le codeur vérifie que les contre-épreuves existantes qui copient une fiche (voisins, Constantinople, Ottomans, Balkans, Maghreb, Mamelouks-Chypre-Autriche, Horde, Bourgogne, Palatinat, Bar) échouent toujours pour leur motif.

SC6 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k 'personnages_sources or personnages_attestes or personnes_catalogue or personnes_chefs or familles_etats or familles_liens or familles_integration'` passe sur le lecteur réel, la construction et la validation publique. Les inventaires passent à 104 fiches, 30 compléments et 31 états. Dans `test_familles_integration`, le bilan exact est de 83 vérifiés et 133 indéterminés. Eberhard IV rejoint les listes des indéterminés paternels (19) et maternels (14), et la formule reste exacte (`86 + 19 + 2 × 14 == 133`). Ses trois contrôles rejoignent les indéterminés, avec leur motif ; l'ensemble exact `verifies` ne change pas. `personne-seigneurie-3`, sans `pere`, n'entre pas dans les fiches réelles du bilan.

Contre-épreuves conservées, toutes doivent échouer : une référence inconnue, un auto-lien, un cycle, un conjoint dupliqué ou non réciproque, un enfant antérieur ou contemporain, une mère de 14 ou de 46 ans. Une mère de 15 ou de 45 ans est acceptée. Contre-épreuve neuve, refusée (`ValueError`) : sur une copie, Eberhard IV né le `1388-08-23` (précision `jour`) et Antonia le `1389-01-01`. La filiation de Wurtemberg entre bien dans les contrôles dès que les bornes existent.

SC7 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k personnes_serialisation` étend les mutations profondes à `seigneurie-2` et `seigneurie-3` (liste de `alterer_iles`), avec leurs fiches, le complément, les deux états, leurs sources, leurs lacunes et leurs exclusions. Les graines 0 et 42 et les permutations des tables donnent les mêmes personnes. Contre-épreuves :
- une mutation d'une copie publiée reste sans effet sur le monde ;
- une mutation du monde se retrouve exactement dans sa copie ;
- un objet imbriqué partagé, une lecture du catalogue ou une reconstruction à la sérialisation font échouer le test.

SC8 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py sim/tests/test_determinisme.py sim/tests/test_pays_et_jauges.py -q` passe. `test_personnes_neutres` reste intact : habitants, économie, retours et état aléatoire restent égaux au témoin sans personnes, pour les graines 0 et 42. Les points du pays ne viennent que des chefs : ceux de Wurtemberg et de Morée ne changent pas. Le départ du joueur sur une seigneurie (`choisir_depart`, preuve de `_preuve_departs_ia`) reste vert. Contre-épreuve : une lecture ou une reconstruction au tick, une mutation familiale ou une consommation d'aléa créent un écart détecté. Aucun test n'est supprimé, ignoré ou rendu moins exigeant.

SC9 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_modificateurs.py -q` passe. Deux fiches, un complément et deux états entrent dans le registre : l'empreinte du monde au 365e jour (`EMPREINTES_365["linux"][0]`) change. Le codeur la recapture sous Linux. Avant de le faire, il mesure, sur la base et sur le lot, deux choses :
- seule la clé `personnages` de `World.to_dict()` diffère : deux fiches nouvelles, et deux changées, `personne-seigneurie-2` (complément et état) et `personne-seigneurie-3` (état seul). Le chef l'a constaté sur une copie en mémoire ;
- l'empreinte de la photographie (`EMPREINTES_365["linux"][1]`) est identique.

Le commentaire au-dessus de la constante le dit, daté du lot (de 2 388 à 2 390 personnes). Contre-épreuve : l'ancienne empreinte du monde échoue sur le lot. Une différence hors de `personnages`, ou une photographie qui change, est un défaut du lot : il faut la corriger, pas la recapturer. Les autres hachages figés ne bougent pas : `python3 -m pytest sim/tests/test_ville1400.py -q` et `python3 -m pytest sim/tests/test_monde.py -q -k service_reponse_figee` passent sans retouche.

SC10 — `git diff --check` passe. Après l'enregistrement du brief par le pilote, `git diff --numstat origin/master | awk '{n += $1 + $2} END {print n; exit (n >= 900)}'` passe. Tant que le brief n'est pas suivi par git, ajouter ses lignes une seule fois. Le budget est de 550 lignes environ, ajouts et suppressions compris. Contre-épreuve : un espacement fautif, ou un total de 900 lignes, font échouer la commande. Un dépassement impose une découpe, jamais le retrait d'une lacune, d'une exclusion ou d'une preuve.

Pour le relecteur :
- vérifie que chaque `fait` dit ce que la page dit vraiment. Relis les pages des constantes : `curl -A "ForgeBrief/1.0" "https://en.wikipedia.org/w/index.php?title=<page>&action=raw"`, et `de.wikipedia.org` pour les pages allemandes ; `action=raw` ne suit pas les redirections. Les fiches LEO-BW se lisent en HTML ;
- vérifie qu'aucune épouse, aucun enfant et aucune date ne sont inventés ; qu'Eberhard le Jeune n'a pas de conjoint actif ; qu'Ulrich et Louis ne sont ni vivants ni datés ; que Théodora n'a ni fiche ni lien ; et qu'aucune lacune n'est devenue une absence attestée ;
- vérifie que `personne-seigneurie-3` n'a aucun complément, que `_constantinople` n'a pas bougé, et que les fiches de `personne-elisabeth-nuremberg`, `personne-caterina-visconti`, `personne-suleyman-celebi` et `personne-theodore-ii` sont inchangées ;
- vérifie que `_complements_du_monde` est au moins aussi exigeant que les six sélections qu'il remplace ;
- vérifie que le diff ne touche que les cinq fichiers du périmètre, que `test_modificateurs.py` ne change que son empreinte et son commentaire, et que `personnages.py` n'a pas bougé.

## Hors périmètre
- Les seigneuries 4 à 6 (Branković, Evrenos, Zab : dernier lot de #804), la Horde d'Or (`grande-21`) et Tlemcen (`grande-24`), qui restent sans famille ni état.
- Toute fiche ou tout lien pour Théodore Ier : son complément, ses parents (Jean V, Hélène Cantacuzène), Bartolomea Acciaioli, Théodora, et Théodore II comme successeur.
- Les parents et la fratrie d'Eberhard III et d'Antonia (Ulrich de Wurtemberg, Élisabeth de Bavière, Bernabò Visconti, Beatrice Regina della Scala, Caterina et Taddea Visconti) ; Henriette de Montbéliard, Élisabeth de Nuremberg (fille de Jean III) et Élisabeth de Wurtemberg, qui ne sont que des exclusions ; les petits-enfants (Anna, Louis Ier, Ulrich V) et les enfants illégitimes d'Eberhard le Jeune ; toute personne hypothétique qui comblerait une lacune.
- Le passage de Montbéliard au Wurtemberg, le remariage de 1406, la vente de la Morée aux Hospitaliers (1399–1400, reprise en 1404), et la succession de 1407 : #435 et #436 traiteront l'héritier et le partage.
- Toute attente nouvelle sur Milan (`grande-10`), la France (`grande-3`), le Palatinat (`grande-29`), les Ottomans (`grande-16`) ou Constantinople (`grande-15`).
- Aucun changement du schéma, de `jeu/sim/personnages.py`, de `data/seigneuries-1400.json`, des briefs précédents, de `test_determinisme.py` ou de `test_pays_et_jauges.py`.
- Aucune naissance, mort, union ou succession future programmée ; aucune loi, partage, proposition de mariage, dot, alliance, éducation, trait ou ambition.
- Aucun changement des habitants, de l'économie, des terres ou du tick ; aucun service, aucune vue, ni Unity ni Blender.
- Tout autre chemin est interdit en écriture.
