# Lot #1085 — Branković, Evrenos et le Zab, et l'achèvement des états
Jalon : J6 · Machine : vps · Taille prévue : 650 lignes

## But
Au départ, le monde portera ce qu'on sait de la famille des trois dernières seigneuries : Đurađ Branković (`seigneurie-4`), Gazi Evrenos (`seigneurie-5`) et le chef du Zab (`seigneurie-6`). Chacune des trente-quatre maisons qui ont un chef historique résolu aura alors son état familial, et la preuve d'ensemble l'exigera exactement.

## Le joueur
C'est un lot de fond. Il prépare deux gestes du jalon J6 : choisir un mariage (#438) et suivre l'héritier que désigne la loi (#435 à #437). L'arbre de la dynastie (#446) le rendra visible. Les six seigneuries de départ sont jouables depuis #1037 : après ce lot, chacune sait ce que le monde connaît de sa famille.

Après ce lot, le monde sait ceci :
- **Branković.** Đurađ, vingt-deux ans, tient les terres de son père Vuk, mort en 1397. Sa mère, Mara, fille du prince Lazar, vit encore, mais le monde ne la porte pas. Il n'a aucune épouse connue au départ : il épousera Irène Cantacuzène en 1414, et ses enfants naîtront après. C'est un parti à marier ;
- **Evrenos.** Le vieux chef de marche de Yenice-i Vardar a sept fils et plusieurs filles, mais aucune page ne donne leur naissance ni le nom de son épouse. Le monde ne les invente pas : il ne sait pas qui, de ses fils, est vivant au 1er janvier 1400 ;
- **Le Zab.** Son chef porte un nom plausible et déclaré (#1052). Le monde déclare que son épouse et ses enfants sont inconnus. Il n'en invente aucun.

Le joueur de Biskra connaît ainsi ses voisins balkaniques et ottomans, et il sait que sa propre famille reste inconnue. Ce n'est pas un oubli : le monde le dit.

Rien n'est programmé : ni le mariage de 1414, ni la mort d'Evrenos en 1417, ni la fin de l'émirat du Zab en 1402. Aucun héritier n'est désigné : c'est l'affaire de #435.

## Règle du monde
Dépend de : #1084, sur la base (`d76b4152`). Le catalogue fermé, les présences, les états, les exclusions, les liens familiaux, les contrôles chronologiques et la copie profonde existent déjà. `sim/personnages.py` accepte déjà un complément et un état pour toute maison dont le chef est résolu, et un état sans complément (Morée, #1084). Le lot découle de « Les personnes » et de « Les seigneuries de départ, vue dérivée » dans `jeu/sim/MODELE.md`. Il étend les données de départ et leurs preuves. Il ne change ni `jeu/sim/personnages.py`, ni aucune règle du moteur.

Niveau 1, au 1er janvier 1400. Sources publiques relues le 14 novembre 2026 :
- DJURADJ = https://en.wikipedia.org/wiki/%C4%90ura%C4%91_Brankovi%C4%87 (c'est déjà la source de la fiche de chef) ; VUK = https://en.wikipedia.org/wiki/Vuk_Brankovi%C4%87 ; IRENE = https://en.wikipedia.org/wiki/Irene_Kantakouzene ;
- EVRENOS_EN = https://en.wikipedia.org/wiki/Evrenos ; EVRENOS_TDV = https://islamansiklopedisi.org.tr/evrenosogullari (c'est déjà la source de la fiche de chef) ;
- ZAB = https://en.wikipedia.org/wiki/Zab_Emirate (c'est déjà la source de la fiche de chef).

La page `Eirene_Kantakouzene` est une redirection : la constante nomme la page d'arrivée. Les URL gardent l'encodage du catalogue (`%C4%90`). Les fiches de chef de `seigneurie-4` (naissance `1377-02-22`, précision `jour`), de `seigneurie-5` (naissance nulle) et de `seigneurie-6` (nom plausible et déclaré, naissance nulle) ne changent pas. Chaque présence, exclusion et lacune nomme la personne et porte une URL. Les tests tirent leurs attentes de constantes nommées d'après ces pages, sans les relire dans le catalogue ni dans le constructeur.

**Branković : le chef (`seigneurie-4`).** Le lot ajoute un complément `personne-seigneurie-4` dans `liens` :
- `presence=vivante`, source DJURADJ : despote de Serbie de 1427 à 1456, mort le 24 décembre 1456 ;
- `pere=null`, lacune de périmètre : Vuk Branković, mort le 6 octobre 1397 (`death_date` de VUK ; la page le classe aussi dans « 1398 deaths » : la divergence est conservée). Il n'a aucune fiche, et aucune absence n'est attestée ;
- `mere=null`, lacune de périmètre : Mara Lazarević, fille du prince Lazar (DJURADJ), mariée à Vuk en 1371 et morte le 12 avril 1426 (VUK). Elle vit au départ, mais n'a pas de fiche. Elle est la sœur de Stefan Lazarević (`personne-grande-17`) et d'Olivera Despina (`personne-olivera-despina`, `grande-16`), mais le monde n'a pas de lien de fratrie : aucun lien vers `grande-17` ni vers `grande-16` ;
- `conjoints=[]`, lacune : aucune épouse connue au départ. Irène Cantacuzène l'épouse le 26 décembre 1414 (IRENE ; `1414` dans l'infobox). « According to some historians », sa première épouse aurait été « Eleni of Trebizond (1395–1410) » (DJURADJ, marqué `{{cn}}`), sans date d'union. Ni célibat ni veuvage, aucune absence attestée.

**L'état `seigneurie-4`.** `conjoints=lacune` (même motif) et `enfants=lacune` : DJURADJ écrit « at least six children » (marqué `{{CN}}`) ; IRENE parle de « five children » et marque Todor d'un « (?) » ; le commentaire de DJURADJ dit que sa liste « conflicts with information on the Eirene Kantakouzene page ». Todor n'a pas de naissance : aucune absence attestée. Huit exclusions sourcées :
- Eleni de Trébizonde : épouse « disputed » (infobox de DJURADJ), née en 1395 ; union non datée, aucune union active au départ ;
- Irène Cantacuzène : née « c. 1400 », mariée le 26 décembre 1414 (IRENE) ; union future ;
- Todor Branković : « d. before 1429 », « probably died early », sans naissance (DJURADJ) ; présence indéterminée ;
- Grgur (« c. 1415 »), Stefan (« c. 1417 »), Katarina (« c. 1418 »), Mara (« c. 1420 ») et Lazar Branković (« c. 1421 ») : cinq enfants futurs (DJURADJ). Mara Branković reste distincte de Mara Lazarević, Stefan Branković de Stefan Lazarević, et Lazar Branković du prince Lazar.

**Evrenos : le chef (`seigneurie-5`).** Le lot ajoute un complément `personne-seigneurie-5` dans `liens` :
- `presence=vivante`, sources EVRENOS_EN (« died 1417 », à Yenice-i Vardar ; il sert Bayezid Ier, puis Süleyman Çelebi et Mehmed Ier) et EVRENOS_TDV (mort en novembre 1417, comme le dit déjà la fiche de chef) ;
- `pere=null`, lacune de périmètre : Îsâ « Prangi » Bey (EVRENOS_EN ; « Prangı lakabı ile anılan Îsâ Bey » pour EVRENOS_TDV). « According to some sources », il est le fils de Bozoklu Han. Il est mort en martyr à Prangi. Il n'a aucune fiche, et aucune absence n'est attestée ;
- `mere=null`, lacune : aucune des deux pages ne la nomme ;
- `conjoints=[]`, lacune : aucune épouse nommée (EVRENOS_EN, EVRENOS_TDV). Ni célibat ni veuvage, aucune absence attestée.

La fiche de chef garde sa lacune de naissance mot pour mot : l'âge de plus de cent ans évoqué par la TDV ne sert pas à calculer une naissance.

**L'état `seigneurie-5`.** `conjoints=lacune` et `enfants=lacune`. EVRENOS_EN nomme « seven sons » et « several daughters » sans aucune naissance ; EVRENOS_TDV dit qu'Ali et Îsâ servent « babalarından sonra ». Aucun enfant n'a de fiche, et aucune absence n'est attestée. Huit exclusions sourcées, sur le gabarit de Faraj (#978) :
- sept fils, sans naissance connue, de présence indéterminée au 1er janvier 1400 : Ali Bey, İsa Bey, Hızırşah Bey (« Khidr-shah » dans le texte), Yakub Bey, Beğce Bey (« Begdje »), Süleyman Bey et Barak Bey (infobox d'EVRENOS_EN). Ali reçoit de Bayezid Ier le sancak d'Ergiri (EVRENOS_TDV), sans date : le monde ne déduit ni sa naissance ni sa présence. Yakub Bey reste distinct de Yâkub Paşa, que nomme aussi EVRENOS_TDV. Süleyman Bey reste distinct de Süleyman Çelebi (`personne-suleyman-celebi`), dont la fiche ne change pas ;
- les filles de Gazi Evrenos : sans nom ni naissance. L'une épouse le grand vizir Çandarlı Halil Pasha le Jeune, et elle est la mère de Çandarlı İbrahim Pasha (EVRENOS_EN). Union non datée, aucune fiche.

**Le Zab : un état sans complément (`seigneurie-6`).** Le chef, « Abd al-Rahman ibn Mozni », est plausible et déclaré (#1052) : il est résolu, donc son état est permis, comme le dit MODELE.md (« un état appartient toujours à un chef résolu »). Il ne reçoit aucun complément : sa personne garde ses seules clés de chef, plus `etat_familial`, comme Théodore Ier. L'état porte :
- `conjoints=lacune` et `enfants=lacune`. ZAB atteste les Banu Muzni à Biskra « from mid 14th century to 1402 ». Elle ne nomme ni le titulaire, ni son épouse, ni ses enfants. L'identité individuelle n'est pas établie : aucune épouse ni aucun enfant n'est inventé. Ni célibat ni veuvage, aucune absence attestée ;
- aucune exclusion (`{}`).

**L'achèvement.** Trente et une maisons avaient leur état. Branković, Evrenos et le Zab s'y ajoutent : ce sont désormais trente-quatre états, pour trente-deux compléments. Ce sont toutes les grandes maisons et toutes les seigneuries, sauf deux : la Horde d'Or (`grande-21`), sans chef, et Tlemcen (`grande-24`), sans famille par la décision A de #977, bien que son chef soit nommé depuis #1052. Les dix institutions (les républiques et l'Église) n'ont pas de dynastie, donc pas d'état. Les maisons plausibles n'en ont pas non plus. Leurs preuves existantes restent mot pour mot.

**Totaux.** Cent quatre fiches (aucune nouvelle), trente-deux compléments, trente-quatre états, triés par maison. Le registre reste à 2 390 personnes. Le lot complète `fidelite` dans le catalogue. Dans « Les personnes » de MODELE.md, il met à jour les compteurs. Il ajoute une phrase Branković, une phrase Evrenos et une phrase Zab : le Zab est le second état sans complément. La dernière phrase de la Morée (« les seigneuries 4 à 6, la Horde d'Or et Tlemcen restent sans état ») devient celle de l'achèvement. Le paragraphe de la Horde ne change pas. Le lot n'ajoute aucun champ de premier niveau ni aucun emplacement : `cell_id` reste la seule clé spatiale.

**Niveau 2.** Aucune filiation n'est ajoutée : aucun contrôle chronologique nouveau. Le bilan reste à 83 vérifiés et 133 indéterminés. Le codeur le remesure avec `valider_liens_familiaux` avant d'écrire les attentes.

**Niveau 3.** Génération, évolution familiale, succession, partage, mariage de 1414, mort d'Evrenos en 1417 et conquête hafside du Zab en 1402 restent non simulés. Les décès, mariages et naissances postérieurs servent seulement à établir la photographie de départ.

## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_modificateurs.py (seulement son empreinte `EMPREINTES_365` et son commentaire)
jeu/sim/MODELE.md
docs/briefs/1085-brankovic-evrenos-et-le-zab-et-l-achevement-des.md

## Conditions de succès
SC1 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k familles_historiques`. Sur le catalogue d'avant le lot, la commande échoue d'abord sur les cas neufs, faute de compléments et d'états. Elle passe ensuite, et le constat du rouge est transmis au pilote. Contre-épreuve : une sélection vide, un test ignoré ou une seule erreur de collecte ne valent pas un rouge.

Comme dans #977 à #980, #1083 et #1084 (décision A de #431 et #800), les attentes exhaustives sont enrichies, jamais assouplies :
- dans `_familles_historiques`, le décompte des fiches reste 104, et `len(liens) == 32`, avec l'ensemble exact des compléments : `personne-seigneurie-4` et `personne-seigneurie-5` ajoutés, `personne-seigneurie-3` et `personne-seigneurie-6` absents. Les deux compléments rejoignent l'ensemble que la boucle générique saute ;
- dans `_etats_historiques` et dans `test_familles_integration`, `len(etats) == 34`, avec l'ensemble exact des maisons, et trois branches `_brankovic(etat=e)`, `_evrenos(etat=e)` et `_zab(etat=e)` ;
- `MAISONS_AVEC_ETAT` reçoit `seigneurie-4`, `seigneurie-5` et `seigneurie-6` ;
- dans les tests du Maghreb, des Mamelouks-Chypre-Autriche, de la Bourgogne, du Palatinat, de Bar, de Wurtemberg et de la Morée, l'inventaire passe à 104 fiches, 32 compléments et 34 états. Le registre reste à 2 390 personnes. Leurs autres assertions restent mot pour mot ;
- dans `_bar_controle`, l'ensemble exact des identifiants `personne-seigneurie-*` passe à `{CHEF_BAR, 'personne-seigneurie-2', 'personne-seigneurie-4', 'personne-seigneurie-5'}`. Les fiches de famille (hors chefs) des seigneuries restent exactement celles de `{BAR, 'seigneurie-2'}`, dans la lecture du catalogue comme dans celle du monde. Dans `test_familles_historiques_bar`, l'ensemble exact des états de seigneurie devient les six seigneuries ;
- deux contre-épreuves existantes visaient `seigneurie-4`, qui reçoit maintenant un complément et un état : elles changent de cible pour garder leur sens. La contre-épreuve « un état de plus » de `test_familles_historiques_bar` vise `grande-24` : Tlemcen a un chef résolu, le chargeur accepte cet état, et la preuve doit le refuser. Dans `test_familles_historiques_moree`, les deux modifications de `personne-seigneurie-4` (un état seul copié de la Morée, et `conjoints=[]` isolé) visent `personne-grande-24`.

Aucune autre attente existante n'est remplacée. `_constantinople`, `_balkans` (Stefan Lazarević), `_ottomans` (Olivera Despina, Süleyman Çelebi), `_maghreb` et le test du Zab dans `test_pays_et_jauges.py` restent mot pour mot.

SC2 — La même commande compare le catalogue ET le monde à des constantes dédiées, sur le gabarit de `_wurtemberg` : `BRANKOVIC = 'seigneurie-4'`, `LIEN_BRANKOVIC`, `ETAT_BRANKOVIC`, `BRANKOVIC_EXCLUSIONS` et `BRANKOVIC_DIVERGENCES`. Une fonction `_brankovic(fiches=None, etat=None)` est appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle :
- pour le complément : le père, la mère et les conjoints nuls ou vides, la présence, les URL des sources, et les repères des faits et des lacunes ;
- qu'aucune fiche n'a `personne-seigneurie-4` pour père, mère ou conjoint, et que le complément n'a aucun lien vers `personne-grande-17` ni vers `personne-olivera-despina` ;
- qu'aucune fiche ne porte les noms « Mara Lazarević », « Vuk Branković », « Irène Cantacuzène », « Eleni de Trébizonde », ni l'un des six noms d'enfants ;
- que les fiches de chef de `seigneurie-4`, `seigneurie-5` et `seigneurie-6` restent égales à des constantes (nom, naissance, précision, URL, lacunes).

Un test neuf, `test_familles_historiques_brankovic`, sur le gabarit de `test_familles_historiques_wurtemberg`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler le complément ou l'état ; altérer chacune de leurs feuilles ;
- remplacer un repère : « 24 décembre 1456 », « 1427 », « Vuk Branković », « 6 octobre 1397 », « 1398 deaths », « Mara Lazarević », « prince Lazar », « 1371 », « 12 avril 1426 », « Irène Cantacuzène », « 26 décembre 1414 », « According to some historians », « Eleni of Trebizond (1395–1410) », « disputed », « at least six children », « five children », « conflicts with information on the Eirene Kantakouzene page », « d. before 1429 », « probably died early », « c. 1400 », « c. 1415 », « c. 1417 », « c. 1418 », « c. 1420 », « c. 1421 », « ni célibat ni veuvage », « aucune absence attestée » ;
- passer `conjoints` à `union` ou `veuvage`, `enfants` à `documentes` ou `absence_attestee`, ou une lacune de complément à une absence attestée ;
- supprimer une exclusion, ou altérer son motif ou ses sources ;
- donner au complément `conjoints=['personne-olivera-despina']` réciproque, ou `mere='personne-olivera-despina'` (liens résolus, `_controler_famille` passe).

SC3 — La même commande éprouve Evrenos par des constantes dédiées : `EVRENOS = 'seigneurie-5'`, `LIEN_EVRENOS`, `ETAT_EVRENOS`, `EVRENOS_EXCLUSIONS` et `EVRENOS_DIVERGENCES`. Une fonction `_evrenos(fiches=None, etat=None)` est appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle le complément et l'état comme SC2. Elle vérifie aussi qu'aucune fiche n'a `personne-seigneurie-5` pour parent ou conjoint, qu'aucune fiche ne porte l'un des sept noms de fils, et que `personne-suleyman-celebi` reste égale à `FICHE_SULEYMAN`.

Un test neuf, `test_familles_historiques_evrenos`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler le complément ou l'état ; altérer chacune de leurs feuilles ;
- remplacer un repère : « died 1417 », « Yenice-i Vardar », « Süleyman Çelebi », « Mehmed Ier », « Îsâ « Prangi » Bey », « Prangı lakabı ile anılan Îsâ Bey », « According to some sources », « Bozoklu Han », « Prangi », « seven sons », « several daughters », « babalarından sonra », « Khidr-shah », « Begdje », « Ergiri », « Yâkub Paşa », « Çandarlı Halil Pasha », « Çandarlı İbrahim Pasha », « présence indéterminée », « ni célibat ni veuvage », « aucune absence attestée » ;
- passer `conjoints` à `union` ou `veuvage`, ou `enfants` à `documentes` ou `absence_attestee` ;
- supprimer l'une des huit exclusions, ou altérer son motif ou ses sources ;
- donner à la fiche de chef une naissance (`1300`, précision `annee`).

SC4 — La même commande éprouve le Zab par `ZAB = 'seigneurie-6'`, `ETAT_ZAB` et une fonction `_zab(fiches=None, etat=None)`, appelée par `_familles_historiques` et par `_etats_historiques`. Elle contrôle l'état (`lacune`, `lacune`, sources nulles, repères des deux lacunes, `exclusions == {}`), l'absence de tout complément `personne-seigneurie-6` et de toute fiche de maison `seigneurie-6`, et qu'aucune fiche n'a `personne-seigneurie-6` pour parent ou conjoint.

`_complements_du_monde` exige maintenant que les chefs qui portent `etat_familial` sans complément soient exactement `{'personne-seigneurie-3', 'personne-seigneurie-6'}`, avec les clés de `CLES_CHEF_SANS_COMPLEMENT` et des sources et lacunes limitées à `identite` et `naissance` ; sa docstring le dit. Un test neuf, `test_familles_historiques_zab`, fait les contre-épreuves. Chacune doit échouer :
- retirer ou dédoubler l'état ; altérer chacune de ses feuilles ; remplacer un repère : « Abd al-Rahman ibn Mozni », « plausible et déclaré », « Banu Muzni », « from mid 14th century to 1402 », « Biskra », « ni célibat ni veuvage », « aucune absence attestée » ;
- passer `conjoints` à `union` ou `veuvage`, ou `enfants` à `documentes` ou `absence_attestee` ; ajouter une exclusion ;
- ajouter un complément neutre `personne-seigneurie-6` (`pere=null`, `mere=null`, `conjoints=[]`, `presence=vivante`, sources et lacunes complètes : le lecteur l'accepte) ;
- sur des copies de `monde.personnages`, pour chacune des sept preuves du monde : `personne-seigneurie-6` reçoit `conjoints=[]` ou `presence='vivante'`, ou perd son `etat_familial`.

SC5 — Un test neuf, `test_familles_historiques_achevement`, prouve l'achèvement depuis le catalogue ET le monde, sans recopier la liste :
- les maisons des états sont exactement les maisons des chefs du catalogue qui ne sont pas des institutions, moins `grande-21` et `grande-24`. Elles sont aussi exactement `{m.id for m in monde.maisons if m.sorte in ('grande maison', 'seigneurie')} - {'grande-21', 'grande-24'}`, et égales à `MAISONS_AVEC_ETAT` (34 maisons) ;
- dans le monde, les personnes qui portent `etat_familial` sont exactement les chefs `personne-<maison>` de ces 34 maisons. Aucune n'est un chef d'institution ou de maison plausible, ni une fiche de famille.

Contre-épreuves, chacune doit échouer :
- retirer l'état de `seigneurie-4`, de `seigneurie-5`, de `seigneurie-6`, ou d'une maison plus ancienne (`grande-3`) ;
- ajouter une copie d'état pour `grande-24` ou pour `institution-13` (Venise : le chef est résolu, le chargeur l'accepte, la preuve le refuse) ;
- ajouter un état pour `grande-21` : le chargeur le refuse (`ValueError`), comme aujourd'hui.

SC6 — La même commande éprouve des copies non vides, avec des liens résolus (`_controler_famille` passe à chaque fois). Dans chaque cas, `_brankovic`, `_evrenos` ou `_zab` doit échouer, et la preuve d'ensemble aussi :
- Irène Cantacuzène, puis Eleni de Trébizonde, construites comme fiches de `seigneurie-4`, vivantes et conjointes réciproques de Đurađ ;
- Todor Branković, construit comme enfant de Đurađ, vivant puis décédé ; Grgur Branković, enfant vivant ;
- Ali Bey, construit comme enfant d'Evrenos, vivant puis décédé ; une « Fille d'Evrenos », enfant vivante ;
- une « Épouse inventée », conjointe réciproque du chef du Zab, et un « Héritier inventé », son enfant vivant.

Le codeur vérifie que les contre-épreuves existantes qui copient une fiche (voisins, Constantinople, Ottomans, Balkans, Maghreb, Mamelouks-Chypre-Autriche, Horde, Bourgogne, Palatinat, Bar, Wurtemberg, Morée) échouent toujours pour leur motif.

SC7 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py -q -k 'personnages_sources or personnages_attestes or personnes_catalogue or personnes_chefs or familles_etats or familles_liens or familles_integration or personnes_serialisation'` passe. Les inventaires passent à 104 fiches, 32 compléments et 34 états. Dans `test_familles_integration`, le bilan exact reste de 83 vérifiés et 133 indéterminés, et les listes d'indéterminés ne changent pas. Dans `test_personnes_serialisation`, la liste de `alterer_iles` reçoit `seigneurie-4`, `seigneurie-5` et `seigneurie-6`, avec leurs compléments, leurs états, leurs sources, leurs lacunes et leurs exclusions. Les graines 0 et 42 et les permutations des tables donnent les mêmes personnes. Contre-épreuves : une mutation d'une copie publiée reste sans effet sur le monde ; une mutation du monde se retrouve exactement dans sa copie ; un objet imbriqué partagé, une lecture du catalogue ou une reconstruction à la sérialisation font échouer le test.

SC8 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_maisons.py sim/tests/test_determinisme.py sim/tests/test_pays_et_jauges.py -q` passe. `test_personnes_neutres` reste intact : habitants, économie, retours et état aléatoire restent égaux au témoin sans personnes, pour les graines 0 et 42. Les points du pays ne viennent que des chefs : ceux de Branković, d'Evrenos et du Zab ne changent pas (`test_les_chefs_du_maghreb_gagnent_leurs_points` reste mot pour mot). Le départ du joueur sur une seigneurie reste vert. Contre-épreuve : une lecture ou une reconstruction au tick, une mutation familiale ou une consommation d'aléa créent un écart détecté. Aucun test n'est supprimé, ignoré ou rendu moins exigeant.

SC9 — Depuis `jeu/`, `python3 -m pytest sim/tests/test_modificateurs.py -q` passe. Deux compléments et trois états entrent dans le registre : l'empreinte du monde au 365e jour (`EMPREINTES_365["linux"][0]`) change. Le codeur la recapture sous Linux. Avant de le faire, il mesure, sur la base et sur le lot, deux choses :
- seule la clé `personnages` de `World.to_dict()` diffère : aucune fiche nouvelle, trois personnes changées, `personne-seigneurie-4` et `personne-seigneurie-5` (complément et état) et `personne-seigneurie-6` (état seul) ;
- l'empreinte de la photographie (`EMPREINTES_365["linux"][1]`) est identique.

Le commentaire au-dessus de la constante le dit, daté du lot (le registre reste à 2 390 personnes). Contre-épreuve : l'ancienne empreinte du monde échoue sur le lot. Une différence hors de `personnages`, ou une photographie qui change, est un défaut du lot : il faut la corriger, pas la recapturer. Les autres hachages figés ne bougent pas : `python3 -m pytest sim/tests/test_ville1400.py -q` et `python3 -m pytest sim/tests/test_monde.py -q -k service_reponse_figee` passent sans retouche.

SC10 — `git diff --check` passe. Après l'enregistrement du brief par le pilote, `git diff --numstat origin/master | awk '{n += $1 + $2} END {print n; exit (n >= 1000)}'` passe. Tant que le brief n'est pas suivi par git, ajouter ses lignes une seule fois. Le budget est de 650 lignes environ, ajouts et suppressions compris. Contre-épreuve : un espacement fautif, ou un total de 1 000 lignes, font échouer la commande. Un dépassement impose une découpe, jamais le retrait d'une lacune, d'une exclusion ou d'une preuve.

Pour le relecteur :
- vérifie que chaque `fait` dit ce que la page dit vraiment. Relis les pages des constantes : `curl -A "ForgeBrief/1.0" "https://en.wikipedia.org/w/index.php?title=<page>&action=raw"` ; `action=raw` ne suit pas les redirections, et une « Wikimedia Error » se règle en réessayant. La page de la TDV se lit en HTML ;
- vérifie qu'aucune épouse, aucun enfant et aucune date ne sont inventés ; que Đurađ, Evrenos et le chef du Zab n'ont aucun conjoint actif ; que les fils d'Evrenos ne sont ni vivants ni datés ; et qu'aucune lacune n'est devenue une absence attestée ;
- vérifie que `personne-seigneurie-6` n'a aucun complément, que Tlemcen, la Horde et les institutions n'ont aucun état, et que les fiches de `personne-grande-17`, `personne-olivera-despina` et `personne-suleyman-celebi` sont inchangées ;
- vérifie que les deux contre-épreuves reciblées sur `grande-24` échouent bien, et pour leur motif ;
- vérifie que le diff ne touche que les cinq fichiers du périmètre, que `test_modificateurs.py` ne change que son empreinte et son commentaire, et que `personnages.py` n'a pas bougé.

## Hors périmètre
- Toute fiche nouvelle : Vuk Branković, Mara Lazarević, Irène Cantacuzène, Eleni de Trébizonde, les enfants de Đurađ, ses frères Grgur et Lazar Vuković, Îsâ « Prangi » Bey, l'épouse, les fils et les filles d'Evrenos, Çandarlı Halil Pasha, et toute personne de la maison du Zab ; toute personne hypothétique qui comblerait une lacune.
- Tout lien de fratrie ou d'oncle (Stefan Lazarević, Olivera Despina) ; le nom réel du chef du Zab ; la famille de Tlemcen (`grande-24`, décision A de #977) et de la Horde d'Or (`grande-21`) ; tout état pour une institution ou une maison plausible.
- Le mariage de 1414, la mort d'Evrenos en 1417, la conquête hafside du Zab en 1402, la succession de Branković : #435 et #436 traiteront l'héritier et le partage.
- Toute attente nouvelle sur la Serbie (`grande-17`), les Ottomans (`grande-16`), Constantinople (`grande-15`) ou le Maghreb (`grande-23`, `grande-25`).
- Aucun changement du schéma, de `jeu/sim/personnages.py`, de `data/seigneuries-1400.json`, des briefs précédents, de `test_determinisme.py` ou de `test_pays_et_jauges.py`.
- Aucune naissance, mort, union ou succession future programmée ; aucune loi, partage, proposition de mariage, dot, alliance, éducation, trait ou ambition.
- Aucun changement des habitants, de l'économie, des terres ou du tick ; aucun service, aucune vue, ni Unity ni Blender.
- Tout autre chemin est interdit en écriture.
