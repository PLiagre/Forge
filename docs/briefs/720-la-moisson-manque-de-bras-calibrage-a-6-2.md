# Lot #720 — La moisson manque de bras : calibrage à 6,2
Jalon : J4 · Machine : vps · Taille prévue : 190 lignes

## But
Le lieu médian du monde a tout juste ses bras au pic de sa saison : en juillet, ses champs demandent tous ses paysans.

## Le joueur
Le joueur sent qu'en juillet ses champs demandent tous les bras, et qu'envoyer
des paysans au chantier coûte une partie de la récolte. C'est un lot de fond :
il donne son poids à la décision de J4 (« des bras au chantier, c'est moins de
bras aux champs — et à la moisson, de la récolte perdue ») et fait partie de
#415, « Les moissons demandent tous les bras ». Le panneau de #419 montrera ce
coût, et #508 en portera la preuve visible. La règle lieu par lieu avec la
saison est déjà sur la base (#723, #724). Ce lot n'attend rien d'autre.

## Règle du monde
Niveau 2, plausible, jamais sourcé. Découle de « Les foyers par métier »
(paragraphe des bras), du renvoi agricole de la production (« Le facteur de
bras local multiplie chaque part de surface… ») et de « Le chantier et ses
bras » dans `jeu/sim/MODELE.md`.

La formule ne change pas. Un lieu récolte
`min(1, paysans_du_lieu / (km²_cultivés_du_lieu × BRAS_AUX_CHAMPS_PAR_KM2 × facteur_de_saison))`.
Seule la constante change : `BRAS_AUX_CHAMPS_PAR_KM2` passe de 0,1 à 6,2.
Elle reste relue à chaque appel.

Calibrage, reproductible sur `World.charger(0)`. Pour chaque lieu cultivable,
on calcule le rapport `paysans du lieu / (km² cultivés du lieu × maximum annuel
du facteur de saison de sa cellule)`. Un lieu est cultivable si ses métiers
sont calculés et si ce dénominateur est strictement positif. Au bourg, les
paysans valent `population du bourg − non-paysans de la cellule`, plancher 0.
Ailleurs, ce sont tous les habitants du lieu. La médiane mesurée vaut
6,204260778 sur 6 619 lieux cultivables.

Mesures acquises, à reprendre sans les refaire :
- à 6,2, la moitié des lieux manquent de bras à la moisson, aucun en janvier,
  et 35 lieux sur le chemin à saison moyenne (sans numéro de jour) ;
- sur un an numéroté, sans chantier, par rapport à 0,1 : population finale
  −0,56 %, récolte annuelle −2,47 %. C'est sous les bornes de 1 % et 3 %
  autorisées par la réponse A du propriétaire sur #705. Ces bornes ne sont
  jamais relevées ;
- `_sortir_par_bourg` (`jeu/sim/engine.py:883`) ne demande plus rien aux
  champs d'une cellule sans chemin : le défaut de la cellule 8992 au tick 242
  est déjà réparé.

MODELE.md à mettre à jour :
- dans « Les foyers par métier » : la valeur 6,2, le calcul reproductible
  ci-dessus, la médiane et l'effectif mesurés (sans les figer dans un test),
  et le fait que l'ancienne valeur 0,1 a été relevée par ce lot ;
- le renvoi agricole : le facteur de bras suit la saison, la moisson manque
  de bras ;
- dans « Le chantier et ses bras » : réécrire le passage « La petite constante
  `BRAS_AUX_CHAMPS_PAR_KM2 = 0,1` demeure… » ;
- dans « Ce que le moteur ne fait pas encore », l'item « répartir le
  travail » dit que la moisson demande les bras de chaque lieu. La saison
  agricole ne fait plus partie de ce qui n'est pas simulé.

## Périmètre
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/tests/test_foyers.py
jeu/forge/tests/test_forge.py

## Conditions de succès
Les commandes se lancent depuis `jeu/`. Avant de changer la constante,
prouver sur la base le rouge des nouveaux contrôles (calibrage, empreinte
nouvelle) et le vert des témoins. Les contre-épreuves altèrent la constante
ou le moteur en mémoire (monkeypatch) et doivent faire échouer exactement
l'assertion qu'elles visent. Seules les trois réécritures autorisées par la
réponse A sur #705 sont permises : `test_bras_suffisent_un_an`, le passage
d'empreinte de `test_forge_ia_sans`, et l'ajout d'assertions à
`test_documentation_bras`. Toutes les autres assertions restent intactes.

Consigne de coût au codeur : un an joué sur le monde entier prend du temps.
Lance un seul test ciblé à la fois, au premier plan. Ne relance pas
`pytest jeu` avant la fin.

SC1 — `python3 -m pytest sim/tests/test_foyers.py -k calibrage_bras -q -s`.
Ajouter `test_calibrage_bras`. Sur `World.charger(0)`, dériver pour chaque
lieu sa surface cultivée (même ordre d'opérations que le moteur : surface du
lieu × relief × eau × part agricole), ses paysans (règle du bourg ci-dessus)
et le maximum annuel du facteur de saison de sa cellule (jours 0 à 364).
Garder les lieux cultivables. Affirmer que l'effectif n'est pas vide et que
`BRAS_AUX_CHAMPS_PAR_KM2` est à moins de 1 % de la médiane. Imprimer la
médiane et l'effectif, sans les figer.
Contre-épreuves : la constante remise à 0,1 fait échouer le contrôle ; un
relevé vide le fait échouer aussi (assertion explicite, pas une erreur de
`statistics`).

SC2 — `python3 -m pytest sim/tests/test_foyers.py -k bras_suffisent_un_an -q -s`.
Réécrire `test_bras_suffisent_un_an`, paramétré avec et sans numéro de jour.
- Témoin de l'avant-lot : 365 ticks sans chantier, même graine (`World.charger(0)`,
  `random.Random(0)`), avec la constante forcée à 0,1. C'est exactement la base
  avant ce lot. Un seul témoin par chemin.
- Partie nominale : mêmes 365 ticks à la constante du lot.
- Mesurer la récolte annuelle comme la somme des ajouts de récolte avant
  consommation et prélèvement, pas comme une différence de stocks.
- Affirmer : population finale à 1 % du témoin, récolte annuelle à 3 %.
  Écrire ces bornes une seule fois, en constantes du test, à 0,01 et 0,03.
- Enregistrer les facteurs lieu par lieu avec leur effectif. Garder le
  contrôle `facteurs == [min(1, rapport)]` existant, avec le besoin
  saisonnier. Sur l'année numérotée, affirmer au moins un facteur < 1
  (un manque en saison). Le relevé ne doit pas être vide.
- Imprimer les écarts mesurés. Ne recopier dans le test aucun chiffre de
  ce brief comme valeur attendue.
Contre-épreuves :
- les besoins multipliés par 100 sur l'année font échouer les bornes. Jouer
  cette année altérée sur le seul chemin numéroté suffit ;
- un relevé vide fait échouer le contrôle des facteurs.

SC3 — `python3 -m pytest forge/tests/test_forge.py -k forge_ia_sans -q`.
Réponse A du propriétaire sur #705 : « garder l'empreinte `b2d3dc6d…` comme
témoin à facteurs de bras forcés à 1 et ajouter l'empreinte exacte du nouveau
monde à 30 ticks, sans toucher aux autres assertions ni au tick 0 ».
- Attention : à 30 ticks, ce test vérifie à la suite cinq empreintes issues de
  la même partie : `b2d3dc6d…`, `a878777d…`, `275ccb88…`, `afbe1a29…` (le
  paramètre) et `4775cd7c…` (`ancienne`). Toutes changent à 6,2, pas
  seulement la première.
- Pour 30 ticks, jouer toutes ces assertions, inchangées et dans le même
  ordre, sur une partie témoin où `foyers.facteur_bras` est forcé à 1.
  Vérifier d'abord sur la base que ce témoin les reproduit toutes. Sinon,
  forcer plutôt la constante à 0,1, qui est la base par construction, et le
  dire dans la PR.
- Sur la partie normale à 30 ticks, ajouter une seule assertion :
  l'empreinte exacte du fichier, en sha256. Remesure-la (la CI de #705 a
  relevé `19d5227a…`) au lieu de la recopier.
- Le cas `ticks=0` ne change pas du tout.
Contre-épreuve : l'empreinte nouvelle diffère de `b2d3dc6d…`, et un octet
altéré du fichier normal fait échouer la nouvelle assertion.

SC4 — `python3 -m pytest sim/tests/test_foyers.py -k documentation -q`.
Ajouter à `test_documentation_bras`, sans retirer d'assertion :
- la section « Les foyers par métier » contient « 6,2 », « médiane » et
  « maximum annuel » ;
- tout le fichier ne contient plus « `BRAS_AUX_CHAMPS_PAR_KM2 = 0,1` » ;
- l'item « répartir le travail » de « Ce que le moteur ne fait pas encore »
  contient « moisson ».
L'assertion existante sur « 0,1 » reste. La section le garde en historique
(« relevée de 0,1 à 6,2 »).
Contre-épreuves : réintroduire « `BRAS_AUX_CHAMPS_PAR_KM2 = 0,1` » dans
« Le chantier et ses bras », ou retirer « 6,2 » de la section, fait échouer
le contrôle.

SC5 — Depuis la racine, à la fin et une seule fois : `python3 -m pytest jeu -q`.
Tout passe : conservation, déterminisme, empreintes à 0, 1, 3, 4 et 20 ticks
(janvier, aucun manque attendu) et lecture effective des constantes. Si un
autre test rougit, ne l'assouplis pas et ne change aucune autre empreinte ni
tolérance : arrête-toi et dis-le dans la PR.

Au relecteur, à vérifier :
- aucune empreinte de `test_forge.py` n'a disparu ni changé de valeur ;
- les bornes de 1 % et 3 % ne sont pas relevées ;
- les contre-épreuves échouent bien : retour à 0,1 au calibrage, besoins
  ×100 sur l'année, relevé vide.

## Hors périmètre
- Aucun changement de la formule, de `engine.py`, `foyers.py`, des métiers,
  de l'amorçage, du prélèvement, du commerce ou des capacités pour compenser
  la nouvelle récolte.
- Ni ouvriers pris dans les autres lieux du maître, ni entraide entre lieux,
  ni preuve comparée d'un chantier en janvier et en juillet, ni récolte
  perdue publiée dans `/plan` : ce sont d'autres morceaux de #415.
- Aucun écran, aucun service, rien dans Unity.
- Âge, sexe, outils et bêtes de trait restent de niveau 3.
