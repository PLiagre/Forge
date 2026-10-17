# Lot #705 — Les champs de chaque lieu demandent leurs bras, à la moisson surtout
Jalon : J4 · Machine : vps · Taille prévue : 280 lignes

## But
Chaque lieu récolte selon les paysans restés sur ses champs et les bras que demande la saison, surtout à la moisson.

## Le joueur
Le joueur sent que la moisson manque de bras : envoyer ses paysans au chantier
peut laisser une partie de ses champs sans récolte. Ce lot de fond prépare
l'arbitrage de J4 entre bâtir sa capitale et la nourrir ; le panneau du lot
#419 montrera ce que coûte le chantier, et #508 en portera la preuve visible.
Les lieux, leurs populations, les métiers et les chantiers payés existent
sur la base : ce lot n'attend aucune livraison restante de J3.

## Règle du monde
Niveau 2, plausible, jamais sourcé. Découle de « Les foyers par métier »,
« Les lieux d'une cellule, vue dérivée » et « Le chantier et ses bras » dans
`jeu/sim/MODELE.md`.

La récolte brute garde sa formule, son unique tirage de rendement par cellule
et sa saison. Chaque lieu en reçoit sa part de surface, puis applique :
`min(1, paysans_du_lieu / (km²_cultivés_du_lieu × BRAS_AUX_CHAMPS_PAR_KM2 × facteur_de_saison))`.
Les km² cultivés sont sa surface dérivée multipliée, dans le même ordre
qu'aujourd'hui, par relief, eau et part agricole ; sans carte, sa surface.
Le facteur de saison est exactement celui appliqué à la production : celui
du jour numéroté, la moyenne annuelle sur le chemin historique sans numéro,
et 1 pour une production sans saison. La saison intervient dans la récolte
potentielle et dans son besoin de bras ; elle n'est pas appliquée deux fois
au rendement. Le plafond de survie reste celui d'une récolte à bras suffisants.

Au rang supérieur à 0, tous les habitants du lieu comptent comme paysans.
Au bourg, les paysans valent `max(0, population_du_bourg − non_paysans_de_la_cellule)` :
mineurs, artisans, ouvriers et tout autre métier non paysan sont soustraits.
Les ouvriers du jour réduisent donc les bras du seul bourg. Sans lieux,
garder le calcul cellulaire avec les paysans déclarés ; avec un seul lieu,
appliquer la règle du bourg. Métiers non calculés (`-1`) ou besoin nul :
facteur 1. Aucune réaffectation de population ni aucun métier stocké par lieu.

Recalibrer `BRAS_AUX_CHAMPS_PAR_KM2` à environ 6,2, relue à chaque appel :
sur `World.charger(0)`, la médiane des rapports paysans / (surface cultivée
du lieu × maximum annuel de sa saison) vaut 6,204260778 sur 6 619 lieux
cultivables, mesurés sur cette base. Le lieu médian a ainsi tout juste ses
bras au pic ; hors saison, les bras restent disponibles. Documenter le
calcul reproductible et sa population mesurée, sans figer ces compteurs.

Les paniers locaux, le total cellulaire et `recoltes[cell_id][rang]` portent
la récolte réellement produite ; le prélèvement reçoit donc ces kilos.
Corriger le résidu numérique au bourg, sans redistribuer les champs.
Si tous les facteurs valent 1, conserver exactement l'ordre des opérations
et les octets de l'ancien partage, sans reconstruire le total par une somme
de parts arrondies. Garder les chemins avec et sans relevé `recoltes`.

Réparer aussi `_sortir_par_bourg` : un résidu d'envoi peut demander des
champs alors que `chemins[cell_id]` n'a pas été ouvert (cellule 8992,
tick 242 signalé). Sans chemin ouvert, aucun apport des champs ; conserver
le débit effectif et la correction au bourg. Ne créer ni capacité ni grain.

La réponse A du propriétaire autorise les trois réécritures nommées dans
l'issue : sur une année sans chantier, l'écart absolu relatif à l'avant-lot
reste au plus de 1 % pour la population finale et de 3 % pour la récolte
cumulée. Elle ne permet pas de relever ces bornes. Mettre à jour le paragraphe
des bras de « Les foyers par métier », le renvoi agricole et le passage
obsolète à 0,1 de « Le chantier et ses bras » ; la saison agricole quitte
la liste du non-simulé. Les autres règles restent en vigueur.

## Périmètre
jeu/sim/engine.py
jeu/sim/constants.py
jeu/sim/foyers.py
jeu/sim/MODELE.md
jeu/sim/tests/test_foyers.py
jeu/sim/tests/test_chantiers.py
jeu/sim/tests/test_commerce.py

## Conditions de succès
Commandes depuis `jeu/`, sauf indication contraire. Prouver d'abord le rouge
des nouveaux contrôles sur la base ; les contre-épreuves altèrent le moteur
en mémoire et doivent faire échouer les mêmes assertions. Garder tous les
paramètres et contre-épreuves existants. Hors des trois tests explicitement
autorisés, ajouter des cas sans retirer ni assouplir les contrôles existants.

SC1 — `python3 -m pytest sim/tests/test_foyers.py -k bras_par_lieu_saison -q`.
Ajouter un cas à plusieurs lieux, à totaux cohérents : un lieu manque de bras
en juillet mais pas en janvier, un autre récolte pleinement aux deux dates.
Choisir le premier avec un rapport paysans / (km² cultivés × constante)
supérieur à 1 et inférieur au facteur de juillet. Comparer chaque récolte
au calcul indépendant de la formule, sur des quantités strictement positives.
Contre-épreuves : retirer la saison du seul besoin de bras laisse suffire
les bras aux deux dates ; appliquer un facteur cellulaire commun efface
la différence entre lieux. Chacune fait échouer le contrôle.

SC2 — `python3 -m pytest sim/tests/test_foyers.py -k 'recolte_bras or recolte_sans_metiers or paysans_du_bourg' -q`.
Réécrire `test_recolte_bras` lieu par lieu, sur sa cellule minière existante,
pour les chemins journalier et moyen : égalité stricte à pleine récolte,
perte proportionnelle sous le seuil et mineurs exclus des bras. Après toute
écriture de métiers, aligner explicitement les populations locales du montage.
Ajouter les cas du bourg avec ouvriers et artisans, dont non-paysans plus
nombreux que ses habitants : récolte nulle, jamais négative, autres lieux
inchangés. Conserver sentinelle, besoin nul et chemins sans carte/sans lieux.
Contre-épreuves : facteur toujours 1, mineurs comptés comme paysans,
plancher supprimé ou ouvriers soustraits à chaque lieu doivent être détectés.

SC3 — `python3 -m pytest sim/tests/test_foyers.py -k 'bras_suffisent_un_an or calibrage_bras' -q -s`.
Ajouter le contrôle du calibrage : dériver les surfaces, paysans, pics
saisonniers et effectif non vide ; constante à moins de 1 % de la médiane.
Réécrire `test_bras_suffisent_un_an`, avec et sans numéro : 365 ticks sans
chantier, même graine et aléas que le témoin avant-lot ; population finale
à 1 %, récolte annuelle à 3 %, en mesurant les ajouts avant consommation
et prélèvement. Un témoin aux facteurs forcés à 1 doit être validé contre
la base avant modification, pas supposé équivalent. Observer les facteurs
lieu par lieu avec effectif dérivé ; au moins un manque en saison sur
l'année numérotée. Ne pas publier de résultats annuels avant de les mesurer.
Contre-épreuves : revenir à 0,1 échoue au calibrage ; multiplier les besoins
par 100 fait échouer les bornes annuelles. Un relevé vide échoue aussi.

SC4 — `python3 -m pytest sim/tests/test_foyers.py -k bras_tous_suffisants_octets -q`.
Ajouter une comparaison aux opérations de l'avant-lot sur des lieux tous
pourvus : stocks cellulaires et locaux, relevés, monde sérialisé et état
du générateur identiques à l'octet, chemins journalier et moyen, avec et
sans relevé. Contre-épreuve : une perturbation d'un kilo sur une part locale
ou d'un octet du témoin fait échouer exactement la même comparaison.

SC5 — `python3 -m pytest sim/tests/test_chantiers.py -k 'recolte_diminue_avec_les_bras_envoyes or ateliers_tick' -q`.
Réécrire `test_recolte_diminue_avec_les_bras_envoyes` en observant la récolte
du bourg dans `recoltes` : conserver les 30 ticks, les quatre scénarios,
le chantier toujours actif et `témoin == petit > moyen > gros == 0` pour
le bourg, tandis que les autres lieux produisent encore. Dériver les seuils
des paysans du bourg et de la saison de chaque tick ; garder paiement,
ordre d'affectation et aléas. Contre-épreuve existante conservée : le facteur
forcé à 1 fait échouer la comparaison. Aucun transfert depuis les hameaux.

SC6 — `python3 -m pytest sim/tests/test_commerce.py -k 'sortir_par_bourg_sans_chemin or plafond_cumule' -q`.
Ajouter une régression à plusieurs lieux : `chemins = {}`, surplus au bourg,
envoi dépassant ce surplus d'un résidu positif représentable ; total cellulaire
déjà débité comme chez l'appelant. Aucun plantage ni apport des champs,
conservation des paniers et capacités existantes intactes. Contre-épreuve :
la lecture non gardée d'origine lève `KeyError` sur le même montage.

SC7 — `python3 -m pytest sim/tests/test_foyers.py -k documentation -q`.
Ajouter au contrôle existant la règle lieu par lieu, la saison, le plancher
du bourg et le calibrage mesuré ; supprimer les descriptions obsolètes sans
retirer les assertions antérieures. Contre-épreuve : remettre le paragraphe
sans saison ou la valeur 0,1 doit faire échouer ce contrôle.

SC8 — Depuis la racine, `python3 -m pytest jeu -q` : tous les invariants
restants passent, notamment conservation, déterminisme, empreintes et lecture
effective des constantes. Aucune empreinte ni tolérance existante n'est
actualisée pour masquer un écart. Contre-épreuves SC1 à SC7 incluses ;
l'année de SC3 franchit aussi le tick du défaut commercial signalé.

## Hors périmètre
Prendre des ouvriers dans les lieux du même maître, changer leur recrutement,
prouver le coût comparé d'un même chantier en janvier et juillet ou publier
la récolte perdue dans `/plan` : autres morceaux de #415. Aucun nouveau geste,
écran, changement du service, de Unity ou des vues. Ni entraide entre lieux,
ni âge, sexe, outils ou bêtes de trait (niveau 3). Aucun changement des métiers,
de l'amorçage, du prélèvement ou des capacités de transport pour compenser
la nouvelle récolte.
