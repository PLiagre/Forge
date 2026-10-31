# Lot #825 — Les Ottomans : la famille de Bayezid Ier
Jalon : J6 · Machine : vps · Taille prévue : 290 lignes

## But
Au départ, le monde portera les compagnes et les enfants connus de Bayezid Ier, chef de `grande-16`, en distinguant chaque maternité établie d'une maternité inconnue.
## Le joueur
« Le joueur gagne les familles connues de ces voisins » (#802, dont ce lot est découpé après #824). Ce lot de fond prépare le choix d'un mariage (#438) et la transmission selon la loi (#435 à #437) ; l'arbre de #446 le rendra visible. Le joueur de Morée verra autour de Bayezid quatre compagnes, six fils attestés après 1400 et quatre filles attestées, sans qu'une mère soit inventée pour compléter l'arbre. Il sentira une maison nombreuse dont les liens sûrs ouvrent des alliances et dont les lacunes rendent la succession incertaine. Les Ottomans restent joués par l'IA : aucun héritier n'est choisi ici et aucun événement futur n'est programmé.
## Règle du monde
Dépend de : #824, livré sur la base (`f75ec82`). Le catalogue fermé, les présences, les états, les exclusions, les liens familiaux et leur copie profonde existent. Aucun apport futur de J4 ou J5 n'est requis. Le lot découle de « Les personnes » et « Les maisons du monde » de `jeu/sim/MODELE.md`. Il étend seulement les données initiales et leurs preuves, sans changer `sim/personnages.py` ni une règle du moteur.

Niveau 1 : on étudie `grande-16` au 1er janvier 1400. Les sources publiques, consultées le 28 octobre 2026, sont :
- BAYEZID = https://islamansiklopedisi.org.tr/bayezid-i ;
- MEHMED = https://islamansiklopedisi.org.tr/mehmed-i ;
- FETRET = https://islamansiklopedisi.org.tr/fetret-devri ;
- TTK = https://ttk.gov.tr/osmanli-padisahlari/ ;
- ULUCAY = https://turuz.com/storage/Turkologi/2017/2278-Padishahlarin_Qadinlari_Ve_Qizlari-M.Chaghatay_Uluchay-1992-313s.pdf, p. 23-26 ;
- UZUNCARSILI = https://dergipark.org.tr/tr/download/article-file/3043592, p. 185-188 ;
- DEVLETSAH = https://en.wikipedia.org/wiki/Devlet%C5%9Fah_Hatun ;
- HAFSA = https://en.wikipedia.org/wiki/Hafsa_Hatun ;
- OLIVERA = https://en.wikipedia.org/wiki/Olivera_Despina.

Chaque identité, présence, naissance, union, filiation et exclusion porte une URL et un fait lisible qui nomme les personnes. Les attentes des tests viennent de constantes nommées depuis ces pages, indépendamment du catalogue et du constructeur.

Réutiliser `personne-grande-16` et lui ajouter un complément dans `liens`. Ses quatre compagnes réciproques, toutes vivantes au départ, sont :
- `personne-devletsah-hatun`, « Devletşah Hatun », née `c. 1365`, précision `vers`, morte en 1414 ; union en 1378/vers 1381 selon ULUCAY/BAYEZID ;
- `personne-devlet-hatun`, « Devlet Hatun », naissance inconnue, morte en janvier 1414 ; UZUNCARSILI établit qu'elle est une convertie distincte de Devletşah et la mère de Mehmed ;
- `personne-olivera-despina`, « Olivera Despina », née `c. 1372`, précision `vers`, vivante après 1444 ; union en 1390 ;
- `personne-hafsa-hatun`, « Hafsa Hatun », naissance inconnue, fille d'İsa Bey d'Aydın ; union en 1390 et présence après 1403.

Ajouter les six fils que BAYEZID, MEHMED, FETRET et TTK établissent vivants après le départ : `personne-suleyman-celebi`, `personne-isa-celebi`, `personne-musa-celebi`, `personne-mehmed-ier`, `personne-kasim-celebi` et `personne-mustafa-celebi`. Tous ont Bayezid pour père. Îsâ (`1380`, précision `annee`) et Mûsâ (naissance inconnue) ont Devletşah pour mère. Mehmed (`1386 ou 1387`, précision `intervalle`) a Devlet Hatun pour mère. Süleyman, Kasım et Mustafa gardent `mere=null`, source nulle et une lacune qui dit que les pages examinées n'établissent pas leur mère.

Ajouter quatre filles attestées vivantes au départ : `personne-hundi-hatun`, `personne-oruz-hatun`, `personne-pasa-melek-hatun` et `personne-fatma-hatun`, naissances inconnues. Toutes ont Bayezid pour père. OLIVERA et ULUCAY établissent Olivera comme mère d'Oruz et de Paşa Melek. La mère de Hundi et celle de Fatma restent inconnues. Le mariage de Hundi après Nicopolis (1396), la capture d'Oruz et Paşa Melek avec Olivera (1402), et l'envoi de Fatma et Kasım à Constantinople (1403) prouvent leur présence initiale ; leurs conjoints et descendants restent des lacunes de périmètre.

L'état `grande-16` vaut `union` et enfants `documentes`. Il nomme les quatre compagnes et les dix enfants intégrés. Il conserve comme exclusions motivées :
- Ertuğrul Çelebi, mort en 1400 sans jour établi : présence indéterminée au 1er janvier, jamais vivant ni `decedee` par déduction ;
- Erhondu Hatun : fille et mère attestée par ULUCAY, mais aucune date ne permet d'établir sa présence au départ ;
- Yusuf, Hasan, Ömer, Korkud et İbrahim Çelebi : listes tardives divergentes, absents des six fils survivants de BAYEZID et du relevé TTK ; existence ou présence non promue en fait certain ;
- la fille non nommée proposée à Ladislas : projet déjà conservé dans l'exclusion de `grande-11`, jamais fusionnée avec Hundi, Oruz, Paşa Melek, Fatma ou Erhondu ;
- les compagnes supplémentaires Fülane, la fille non nommée de Jean V, Maria Fadrique, Angelina et Maria : ULUCAY déclare ne trouver aucune trace dans les sources et signale une confusion probable avec Olivera ; aucune personne ni union active n'est inventée.

Conserver intégralement les cinquante-huit fiches, seize compléments et seize états existants. Les ajouts portent les totaux à soixante-douze fiches, dix-sept compléments et dix-sept états. Mettre à jour `fidelite` et « Les personnes ». Aucun champ de premier niveau ni emplacement n'est ajouté ; `cell_id` reste la seule clé spatiale.

Niveau 2 inchangé : un enfant est strictement postérieur à ses parents, et la mère a entre 15 et 45 ans révolus inclus. Les dix filiations paternelles et les dix contrôles maternels des cinq maternités établies sont indéterminés faute de bornes exploitables ; aucune approximation ne devient une borne. Le bilan chronologique passe de 36 vérifiés / 86 indéterminés à **36 / 106**.

Niveau 3 : génération, évolution familiale, succession et polygamie comme règle de jeu restent non simulées. Les décès et événements postérieurs servent seulement à établir la photographie initiale.
## Périmètre
jeu/data/personnages-1400.json
jeu/sim/tests/test_maisons.py
jeu/sim/MODELE.md
docs/briefs/825-les-ottomans-la-famille-de-bayezid-ier.md
## Conditions de succès
SC1 — Depuis la racine, lancer `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k familles_historiques`. On constate d'abord le rouge des cas ottomans indépendants, causé par les fiches, le complément, l'état et les exclusions absents ; puis la commande passe. Le constat est transmis au pilote. Contre-épreuves : une sélection vide, un test ignoré ou une erreur de collecte ne valent pas rouge. Les attentes exhaustives de #824 sont enrichies, jamais remplacées ni assouplies.

SC2 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k familles_historiques` compare le catalogue ET le monde aux ensembles exacts enrichis : 72 fiches, 17 liens, 17 états, identités, maisons, naissances et précisions, présences, parents, conjoints, sources, lacunes et exclusions. Une fonction ottomane dédiée est appelée par `_familles_historiques` et `_etats_historiques`. Contre-épreuves, chacune doit échouer : retirer ou dédoubler une des quatorze fiches, le complément ou l'état ; fusionner Devlet Hatun avec Devletşah ; attribuer une mère inconnue ; retirer une maternité établie ; changer un nom, une présence, une naissance, une source ou un motif.

SC3 — La même commande éprouve des copies non vides. Pour chaque exclusion, construire l'intrus comme enfant ou compagne de Bayezid avec des liens résolus : la preuve échoue, comme avec un « Héritier inventé ». Elle échoue aussi si Ertuğrul ou Erhondu devient vivant ou `decedee`, si l'une des cinq maternités établies change, si une maternité inconnue est remplie, si la fille proposée à Ladislas est fusionnée, si une compagne douteuse devient active, si `documentes` devient `absence_attestee` ou `lacune`, ou si un fait, un repère, une divergence ou une exclusion disparaît.

SC4 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k 'personnages_sources or personnes_catalogue or personnes_chefs or familles_etats or familles_liens or familles_integration'` passe sur le lecteur réel, la construction et la validation publique. Les inventaires passent à 72/17/17 ; la sentinelle `grande-16` éprouve père, mère et plusieurs conjoints ; le bilan exact passe à 36/106, dérivé des dix liens paternels et des cinq maternités. Contre-épreuves conservées : référence inconnue, auto-lien, cycle, conjoint dupliqué ou non réciproque, enfant antérieur ou contemporain, mère de 14 ou 46 ans. Les âges de 15 et 45 ans restent acceptés.

SC5 — `python3 -m pytest jeu/sim/tests/test_maisons.py -q -k personnes_serialisation` étend les mutations profondes à `grande-16`, aux quatorze fiches, au complément, à l'état, aux sources, lacunes et exclusions. Les graines 0 et 42 et les permutations des tables donnent les mêmes personnes. Contre-épreuves : une mutation d'une copie publiée reste sans effet sur le monde ; une mutation du monde se retrouve exactement dans sa copie ; un objet imbriqué partagé, une lecture du catalogue ou une reconstruction à la sérialisation font échouer le test.

SC6 — `python3 -m pytest jeu/sim/tests/test_maisons.py jeu/sim/tests/test_determinisme.py -q` passe. `test_personnes_neutres` reste intact : habitants, économie, retours et état aléatoire sont égaux au témoin sans personnes, graines 0 et 42. Contre-épreuves : une lecture ou reconstruction au tick, une mutation familiale ou une consommation d'aléa crée un écart détecté. Aucun test n'est supprimé, ignoré ou rendu moins exigeant.

SC7 — `git diff --check` passe. Après l'enregistrement du brief par le pilote, `git diff --numstat origin/master | awk '{n += $1 + $2} END {print n; exit (n >= 300)}'` passe ; tant que le brief n'est pas suivi, ajouter ses lignes une seule fois. Budget total, ajouts et suppressions compris : 290 lignes au plus. Contre-épreuves : un espacement fautif ou un total de 300 font échouer la commande. Un dépassement impose une découpe, jamais le retrait d'une personne, d'une lacune, d'une exclusion ou d'une preuve.
## Hors périmètre
Autres familles de #802, ancêtres de Bayezid, fratrie, conjoints et descendants des enfants, et personnes hypothétiques pour combler les lacunes. Aucun changement du schéma, de `personnages.py`, des briefs précédents ou de `test_determinisme.py`. Aucune naissance, mort ou union future programmée ; aucune succession, loi, partage, proposition de mariage, dot, alliance, éducation, trait ou ambition. Aucun changement des habitants, de l'économie, des terres ou du tick. Aucun service, aucune vue, ni Unity ni Blender. Tout autre chemin est interdit en écriture.
