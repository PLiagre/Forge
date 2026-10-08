# Lot #335 — Commerce et migration passent par le bourg
Jalon : J3 · Machine : vps · Taille prévue : 290 lignes

## But
Les marchandises entrent et sortent par le bourg, avec l'aide des chemins intérieurs, et seuls les lieux affamés perdent des habitants au profit du bourg qui les accueille.

## Le joueur
Ce lot de fond prépare le choix de J3 : prendre davantage sur ses lieux ou ouvrir son grenier pour garder ses gens. Le ravitaillement atteint un lieu précis ; un champ rassasié ne se vide plus parce que son bourg a faim. Le joueur en sentira la conséquence dans les lieux qui se vident chez un maître qui les affame (#399), puis sur la carte et dans les flux de la forge (#400, #401) ; #405 rendra ses réglages et l'ouverture du grenier jouables dans Unity. Ce lot ne crée pas ces gestes ni leur écran.

## Règle du monde
Dépend de : #334. Découle de `jeu/sim/MODELE.md`, sections « Le commerce entre cellules », « La migration de famine », « La distribution à l'intérieur de la cellule » et « Les lieux d'une cellule, vue dérivée ». Niveau 2 : passage par le bourg, chemins, départs et accueil plausibles, jamais sourcés. Niveau 1 inchangé : carte et amorçage de 1400. Niveau 3 : délais, pertes, bagages des migrants, métiers propres aux lieux et tracé des chemins non simulés.

La décision technique **A** du pilote est acquise : adapter la preuve annuelle des écritures extérieures dans son test actuel et régénérer les références figées du pont et du service, avec toutes leurs exigences. Aucune nouvelle question. Les seules adaptations de tests existants autorisées sont précisées en SC4 et SC6 ; tous les autres cas s'ajoutent aux fichiers qui portent l'invariant.

**Commerce.** Besoin et surplus restent calculés sur les stocks et populations de cellule, par l'instantané et les formules actuelles. L'offre exportable est en outre bornée par ce qui peut quitter le bourg : son surplus local, puis les surplus des champs acheminés par rang croissant. Un champ garde sa ration locale ; son apport est borné par `capacite_chemins_interieurs_kg(1, facteur_transport)`, relue depuis les constantes actuelles. Ne remonter que les quantités effectivement expédiées. Une capacité intérieure nulle bloque l'apport des champs ; un bourg déjà en surplus peut toujours exporter. Une cellule à un seul lieu ne calcule aucun chemin.

Le plafond de chaque chemin pour ce maillon est partagé entre ses destinataires et marchandises : plusieurs demandes ne multiplient pas son débit. L'allocation conserve l'ordre stable, les plafonds des arêtes et quais, l'écrêtage du besoin du receveur et l'atomicité actuels. Une quantité inaccessible reste chez sa source et n'entre pas dans le compteur transporté. Les arrivées terrestres et débarquements vont au panier du rang 0 ; les départs terrestres et expéditions le quittent. Le bassin maritime garde ses règles : ce qui vient d'y entrer ne peut pas être débarqué dans le même tick. La consommation conserve sa distribution intérieure ; elle ne transforme pas une importation au bourg en partage proportionnel préalable. Commerce ne change ni dette ni faim.

**Migration.** Après mortalité et natalité, seuls les lieux vivants dont `duree_faim_ticks > 0` fournissent des partants. Dans une cellule avec lieux, remplacer la population source de la formule actuelle par la somme de ces habitants affamés ; garder `FRACTION_MIGRANTE_PAR_TICK` et le report cellulaire `migration_remainder`, sans ajouter de report ni de champ. Les partants se prélèvent entre ces seuls lieux au prorata de leurs habitants, en entiers, plus forts restes et égalités par rang croissant ; aucun lieu ne perd plus que sa population. Sans lieu affamé, aucun départ ni consommation du report.

Les destinations et leurs poids restent ceux du moteur : reste alimentaire cellulaire post-consommation sur un instantané, sans recompter la ration, sans pondération par les habitants ; voisinage terrestre, ou repli maritime uniquement sans voisine terrestre. Tous les arrivants rejoignent le rang 0. Une receveuse n'envoie personne ce tick, y compris ses habitants anciens ; les départs annulés ne sont jamais retirés des lieux. Mettre à jour les lieux seulement après cette annulation. Les métiers suivent une seule fois le solde cellulaire par `_ajouter_par_les_foyers` ou `_retirer_par_les_foyers`, au prorata actuel. Aucun kilo, aucune dette, aucune faim ni aucun report de mortalité ou natalité ne voyage avec les gens.

**Écritures et conservation.** `repartir_sur_les_lieux` sert à reprendre les écritures faites sur la cellule hors du tick, avant le premier maillon qui lit les lieux ; supprimer son appel général de fin de tick. Garder ses règles : contenu actuel comme poids, surfaces si tous les contenus sont nuls, retrait des marchandises absentes, états déjà cohérents intacts. Chaque maillon du tick tient ensuite ses propres écritures locales et cellulaires. Fabrication et extraction doivent aussi refléter leurs variations de marchandises dans les lieux, en conservant leur attribution proportionnelle actuelle ; cette mise en accord ciblée ne redistribue ni nourriture importée ni habitants déplacés. Ne pas déplacer le partage général après le commerce ou après la migration sous un autre nom.

Après chaque tick, habitants, métiers et lieux ont les mêmes totaux ; les clés de marchandises et leurs sommes retrouvent le panier cellulaire en `==` et en `Fraction`, avec stocks non négatifs. La correction du résidu numérique au bourg ne doit pas repondérer les lieux. Les chemins de production avec jour explicite ou saison moyenne restent couverts. Une cellule construite sans lieux conserve son calcul actuel, sans lieux inventés. Utiliser les lecteurs et écrivains de `model.py`, jamais un accès direct à `.stocks`. Aucun nouvel aléa, aucune sérialisation de monde dans le tick, aucun état de module ni seconde clé spatiale.

Réécrire « Le commerce entre cellules », « La migration de famine » et « En une page ». Corriger leurs renvois devenus faux dans « Ce que porte un lieu », « La natalité » et « La distribution à l'intérieur de la cellule » : distinguer reprise des écritures extérieures, maillons locaux, report migratoire cellulaire et prorata des métiers. Garder les mentions documentaires existantes de `partager` et « à proportion », en les rattachant au mécanisme qui les emploie encore.

## Périmètre
jeu/sim/engine.py
jeu/sim/lieux.py
jeu/sim/MODELE.md
jeu/sim/tests/test_commerce.py
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_monde.py
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs
docs/briefs/335-commerce-et-migration-passent-par-le-bourg.md

## Conditions de succès
Commandes depuis `jeu/`, au premier plan. Ajouter les cas et observer leur rouge avant de corriger le moteur ; les contre-épreuves doivent échouer sur le même contrôle. Chaque sélection de tests et chaque échantillon de monde est non vide. Ne lancer ni `pytest jeu` ni `pytest sim` en entier. Aucune borne, tolérance, durée ou taille d'échantillon existante ne baisse.

SC1 — `python3 -m pytest sim/tests/test_commerce.py -q -s -k commerce_par_bourg`. Ajouter des cellules à plusieurs lieux avec paniers non proportionnels aux surfaces. Une importation augmente seulement le rang 0, avant consommation ; un export prend au bourg puis aux champs donneurs par rang, sans toucher leur ration. Comparer capacité intérieure nulle, finie et infinie, et plaine/montagne ; tester un lieu unique et le repli sans lieux. Besoin et surplus de cellule restent identiques entre ces variantes, mais le flux réalisé respecte l'accès intérieur. Vérifier conservation locale et mondiale, plafonds cumulés avec deux destinataires et deux marchandises demandées, compteur transporté et absence de débit consommé par un flux bloqué. Contre-épreuves : répartir l'arrivée selon le contenu, exporter directement des champs sans chemin ou réinitialiser le plafond à chaque destinataire font échouer les contrôles respectifs.

SC2 — `python3 -m pytest sim/tests/test_commerce.py -q -s -k bourg_maritime`. Ajouter débarquement et expédition sur des ports avec lieux ; vérifier arrivée au bourg, source inaccessible conservée, bassin et quotas exacts. Couvrir une demande alimentée par terre et par mer, sans dépasser son besoin ; vérifier qu'une expédition ne finance pas un débarquement du même tick. Contre-épreuves : un débit maritime contournant le bourg ou utilisant le bassin après expédition fait échouer ces mêmes contrôles.

SC3 — `python3 -m pytest sim/tests/test_commerce.py -q -s -k migration_par_bourg`. Ajouter une source avec bourg affamé et champ rassasié, puis le cas inverse ; vérifier le nombre calculé sur les seuls habitants affamés et les départs par plus forts restes entre deux lieux affamés. Vérifier des petits effectifs sur plusieurs ticks, l'absence de départ pour une dette sans faim, l'accueil exclusivement au rang 0, le prorata des métiers et la conservation exacte des habitants, paniers et états locaux non déplacés. Couvrir des destinations aux mêmes stocks et populations différentes, l'ordre inversé des cellules/arêtes, une receveuse affamée dont les départs sont annulés et le repli maritime. Contre-épreuves : retirer les gens dans tous les lieux au prorata, répartir les arrivants ou retirer des départs annulés échoue sur ces mêmes cas.

SC4 — `python3 -m pytest sim/tests/test_lieux.py -q -s -k tick_repartit_sur_une_annee_et_suit_les_ecritures`. Adapter ce test actuel suivant A, sans retirer son année calendaire complète, graine 0, contrôle de toutes les cellules après chaque tick, égalités `==` et `Fraction`, non-négativité, clés de paniers et compteurs non nuls. Garder les cas de marchandise ajoutée, retirée, population écrite à la main, contenus tous nuls et second appel inerte. Vérifier les proportions immédiatement après la reprise des écritures extérieures, avant production et démographie, plutôt que sur les populations finales du tick. La sonde ne peut être rendue inerte pour éviter la fabrication : contrôler aussi son évolution réelle et sa somme après le tick. Pour la contre-épreuve de reprise inerte, injecter d'abord une vraie écriture extérieure ; sans reprise, le même contrôle échoue. Ajouter une garde où un partage général après migration est interdit : un monde sans écriture extérieure demeure conservatif, sans redistribuer ses arrivants ni ses importations. Contre-épreuve : rétablir l'ancien partage final fait échouer cette garde.

SC5 — `python3 -m pytest sim/tests/test_commerce.py sim/tests/test_distribution_interieure.py sim/tests/test_survie.py sim/tests/test_foyers.py sim/tests/test_chantiers.py -q`, puis `python3 -m pytest sim/tests/test_determinisme.py -q -s -k "ticks_deterministes_meme_graine or tick_bit_pres_sur_une_annee"`. Les invariants existants restent verts sans retouche : consommation physique, atomicité, écrêtage, sentinelles, refus avant mutation, survie, démographie locale, métiers, chantiers et référence annuelle #331. Cette référence remplace les anciens chemins d'accès et de répartition, pas les nouvelles règles de commerce et migration ; ne pas la régénérer. Contre-épreuves existantes conservées : duplication de kilos, perte d'un habitant, fraction de panier altérée et fonction inerte restent détectées.

SC6 — `python3 -m pytest sim/tests/test_monde.py -q -k "reponse_figee_du_pont or service_ia_sans"`. Suivant A, régénérer les deux JSON depuis les octets du vrai service graine 0, `/lieu?cell=9922` aux ticks 3 et 4. Actualiser uniquement les valeurs correspondantes dans les deux fichiers C#, y compris `FoyersTick3`, chaînes de retrait/remplacement et valeurs altérées : chaque altération doit toujours changer réellement sa cible. Dans `test_service_ia_sans`, régénérer seulement les empreintes devenues fausses, mêmes trois endpoints et ticks 0/4, mêmes assertions et refus de `/ia`. Contre-épreuves : décalage d'un tick encore détecté, clé IA ajoutée encore rejetée. Les tests Python du pont restent intacts. Ce sont des références textuelles ; aucune exécution Unity ou Blender n'est requise ni revendiquée.

SC7 — `python3 -m pytest sim/tests/test_monde.py -q -s -k tick_sous_le_budget_du_service`. Le tick entier de `World.charger(0)`, sans IA, garde la médiane sous `BUDGET_TICK_MS = 100`, avec les cinq ticks de chauffe et vingt ticks mesurés existants. Recopier médiane et maximum observés, sans relever le budget ni sortir un maillon de la mesure. Contre-épreuve existante : commerce ralenti fait toujours échouer le contrôle. Ne calculer ni surfaces, ni partages, ni capacités intérieures quand le cas ne les exige.

SC8 — `python3 -m pytest sim/tests/test_commerce.py -q -k bourg_documentation`, puis `python3 -m pytest sim/tests/test_lieux.py sim/tests/test_distribution_interieure.py sim/tests/test_foyers.py sim/tests/test_province.py sim/tests/test_monde.py -q -k "documente or documentation or ordre_du_tick"`, puis `python3 -m pytest sim/tests/test_write_coverage.py sim/tests/test_no_hardcoded.py -q`. Ajouter un contrôle des trois sections principales : commerce au bourg avec chemins bornés, départs des lieux affamés, accueil au rang 0, reprise des seules écritures extérieures et niveaux de fidélité. Les gardes documentaires et l'ordre réel du tick restent verts. Contre-épreuves : retirer le chemin ou remettre le partage général après migration dans le texte échoue ; retirer une lecture ou introduire un accès direct au panier reste détecté par les gardes existantes.

## Diagnostic de la correction CI

L'échec de `forge/tests/test_forge.py::test_forge_ia_sans` à 30 ticks est
reproduit avec la graine 0. Le moteur de `origin/master` produit exactement
la référence attendue
`57f377d47076029c36994c12a902aef0f1ce82c6ed2c23dd36d5e8dd053f71d6` ;
celui du lot produit
`4775cd7c576c32b4b647b8bd9f82061ac1216b5c658969afd254fdcf081cf694`,
comme en CI. Les deux photographies ont les mêmes clés hors cellules ;
348 cellules changent de contenu local. En contre-épreuve, le moteur de
`origin/master` échoue sur les dix cas sélectionnés de chemins, rations et
migration des seuls lieux affamés. Restaurer ce moteur abandonnerait donc
les règles du lot.

La décision A couvre les références du pont et du service, pas la référence
Forge. `jeu/forge/tests/test_forge.py` reste hors périmètre : aucune assertion
ni empreinte de ce fichier n'a été modifiée. La référence Forge demande une
décision distincte avant toute régénération ; ce diagnostic n'élargit pas le
périmètre.

Contrôles exécutés pour ce diagnostic, avec les commandes SC1 à SC8 ci-dessus
depuis `jeu/` :

| Condition | Résultat |
|---|---|
| SC1 | 10 tests verts |
| SC2 | 4 tests verts |
| SC3 | 7 tests verts |
| SC4 | 1 test vert, 365 ticks, 594 cellules dont la population change, 51 marchandises apparues, 6 619 lieux modifiés |
| SC5 | 361 tests verts dans les cinq fichiers, puis 2 tests de déterminisme verts ; référence annuelle #331 inchangée |
| SC6 | 3 tests verts |
| SC7 | 1 test vert ; médiane 86,45 ms, maximum 107,51 ms, budget médian 100 ms ; contre-épreuve ralentie rejetée à 1 411,37 ms de médiane |
| SC8 | Sélections successives : 1, 17 et 7 tests verts |

Commandes complémentaires jouées :

- `python3 -m pytest sim/tests/test_lieux.py -q` : 91 tests verts.
- `python3 -m pytest vues/relief/tests/test_carte1400.py -q -k capitales_ia_sans` : 1 test vert, référence de la carte conservée.
- `python3 -m pytest forge/tests/test_forge.py -q -k forge_ia_sans` : 1 test vert au tick 0, 1 échec au tick 30 sur la seule empreinte figée ci-dessus.

## Hors périmètre
Maîtres des lieux, prélèvement, dû au suzerain, ouverture du grenier et départs pour mieux vivre (#399) ; nouvelle calibration, report migratoire local, réforme des métiers, de la récolte, des formules de fabrication/extraction ou des règles maritimes ; nouvelles clés de service ou de photographie, publication de faim/dette/reports, gestes ou scènes Unity. Les seuls changements de tests existants sont l'adaptation annuelle de SC4 et les références numériques régénérées de SC6. Aucun fichier de la chaîne, aucun commit, aucune poussée ni commande GitHub.
