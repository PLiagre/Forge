# Brief 053 — Le monde porte sa date

## But

Faire porter au monde le nombre de ticks réellement terminés, en dériver
une date depuis 1400 et la rendre lisible par la ligne de commande, sans
changer les règles physiques ni le régime saisonnier des appels existants.

État de départ à mesurer :

```bash
rg -n 'numero_tick|jour_de_tick|ticks_ecoules|date_simulation' sim/world.py sim/engine.py sim/__main__.py sim/constants.py
python3 -m sim --ticks 0 --seed 0 --json
python3 -m sim --ticks 20 --seed 0 --json
```

Aujourd'hui le lanceur compte ses appels et donne le rang du tick au
moteur ; `World` ne garde pas ce temps. Si le monde porte déjà un compteur
mis à jour par `tick` et une date consultable dans le résumé, ce lot est
caduc. Une étiquette `tick` fournie séparément à l'export ne suffit pas.

## Règle du monde

Ce lot découle de `sim/MODELE.md` § « La base de temps », en particulier
« L'année calendaire et le rang du jour », et de l'absence déclarée
« dater le monde ». Il conserve les conventions de § « Les trois régimes
de production » : nominal sans carte, saison moyenne sans numéro fourni,
saison du jour avec un numéro explicite.

**Fidélité niveau 2 pour le calendrier simplifié.** L'année de départ 1400
est le cadre déjà donné au produit ; le calendrier conserve l'année fixe
de `CALENDAR_DAYS_PER_YEAR`, sans mois ni années bissextiles. Il ne prétend
pas restituer un calendrier civil historique. Un jour de simulation reste
dérivé de `TICK_DURATION_DAYS` ; aucun second rythme annuel n'est introduit.

### Un seul état temporel, des consultations dérivées

`World` initialise `ticks_ecoules` à zéro. C'est un entier non négatif,
le nombre de ticks terminés depuis l'amorçage, jamais le rang du tick en
cours. Ni l'année ni le jour ne sont stockés sur le monde ou ses cellules.

`sim/constants.py` déclare `ANNEE_INITIALE = 1400` et une consultation
`date_de_tick(ticks_ecoules)` qui relit les constantes à chaque appel :

```
jours_ecoules = ticks_ecoules × TICK_DURATION_DAYS
annees_ecoulees, rang_jour = divmod(jours_ecoules, CALENDAR_DAYS_PER_YEAR)
date = {
    "annee": ANNEE_INITIALE + annees_ecoulees,
    "jour_de_l_annee": rang_jour + 1,
}
```

`jour_de_l_annee` est lisible par un humain, de 1 à la durée de l'année.
`jour_de_tick`, conservé tel quel pour la saison, reste un rang depuis
zéro ; la relation entre les deux est donc explicite. `World.date_simulation`
est une propriété calculée par `date_de_tick`, jamais un dictionnaire
conservé et remis à jour à côté du compteur. Une consultation retourne une
nouvelle valeur : la modifier ne modifie pas le monde.

La date de l'état initial est le premier jour de l'année initiale. Un tick
numéroté zéro joue ce premier jour ; après son retour, le monde est au
début du jour suivant. L'année avance dès que les jours écoulés atteignent
la durée de l'année. Le compteur ne se remet pas à zéro en janvier.

### Le tick tient le compteur, le lanceur le consulte

Pour un `World` portant `ticks_ecoules`, `tick()` incrémente ce compteur
**une fois à la fin**, après tous les maillons réussis. Aucun sous-maillon,
aucune vue, aucun export ne l'incrémente. Une exception ne doit pas annoncer
un tick achevé. Ce lot n'ajoute pas de transaction sur les autres champs :
si un maillon échoue après une mutation, il ne promet pas de restaurer tout
le monde ; cette limite reste explicite.

Lorsqu'un numéro est fourni, il doit être un entier non booléen,
non négatif et égal au compteur avant le tick. Un numéro incohérent est
refusé par `ValueError` **avant** toute mutation, consommation d'aléa ou
extraction, avec le numéro reçu et le numéro attendu dans le message.
Le même refus s'applique si le compteur du monde a été rendu invalide.

Lorsque le numéro est omis, le compteur avance aussi, mais la production
garde le régime saisonnier moyen existant. La date mesure le temps écoulé ;
elle ne transforme pas implicitement une expérience en saison moyenne en
une expérience saisonnière. Pour jouer la saison du jour sans entretenir
de compteur parallèle, l'appelant passe `world.ticks_ecoules` à `tick`.

Les petits mondes d'épreuve qui ne sont pas des `World` et ne portent pas
ce compteur gardent leur contrat actuel : `tick` ne leur greffe aucun
attribut temporel. Il n'y a pas de compteur de repli dans une variable de
module et pas de seconde horloge cachée. Leur état n'a pas de date à
prétendre exporter.

`sim/__main__.py::_simulate` passe `world.ticks_ecoules` au moteur pour
chaque pas demandé. Son résumé garde les anciennes clés et valeurs, et
ajoute `date_simulation`, lue sur le monde final. Le rendu texte affiche
l'année et le jour dans l'année. `--ticks` continue de désigner le nombre
de pas à exécuter depuis un monde neuf ; ce n'est pas une date de reprise.

`World.to_dict()` ajoute `ticks_ecoules` à la racine pour que l'empreinte
distingue deux états temporels. La date, redérivable, n'y est pas recopiée.
La forme des cellules et le panier maritime ne changent pas. Toute
comparaison de parité avec la base retire uniquement cette nouvelle clé,
et compare les cellules ainsi que le bassin ; aucune ancienne empreinte
n'est recopiée comme valeur attendue.

### Le contrat du snapshot est un autre sujet

`build_snapshot_document(world, seed, tick)` accepte aujourd'hui une
étiquette de tick indépendante, y compris sur un monde non avancé ; des
tests existants exercent exactement cette convention. Ce lot n'ajoute donc
pas la date au snapshot, n'en change pas la signature ou la validation et
ne prétend pas corriger cette limite en silence. Le résumé de simulation
et le snapshot restent deux contrats distincts, explicitement nommés.

Il ouvre une extension ultérieure : photographier puis afficher la date
portée par le monde. Cette extension devra refuser l'absence de compteur
et trancher le contrat de l'étiquette de tick avant de modifier les vues.
Elle n'est pas nécessaire à la livraison de ce lot et n'a pas de numéro
inventé ici. Les lots 051 et 052 peuvent livrer le bourg sans cette date.

## Périmètre

En écriture : `sim/constants.py`, pour l'année initiale et la consultation
de date ; `sim/world.py`, pour le compteur, la propriété dérivée et sa
sérialisation ; `sim/engine.py`, uniquement pour valider puis avancer le
compteur autour des maillons existants ; `sim/__main__.py`, pour lire le
compteur, enrichir le résumé et afficher la date ; `sim/tests/test_monde.py`
et `sim/tests/test_determinisme.py`, uniquement pour ajouter les cas qui
protègent le temps du monde, sa visibilité et le déterminisme.

Tout autre chemin est interdit, nommément : `sim/model.py`,
`sim/aggregation.py`, `sim/snapshot_export.py`, `sim/MODELE.md`,
`sim/tests/test_write_coverage.py`, `sim/tests/test_survie.py`,
`sim/tests/test_commerce.py`, `sim/tests/test_province.py`,
`sim/tests/test_no_hardcoded.py`, `data/`, `viewer/`, `visualisateur/`,
`outils/`, `.github/`, `VISION.md`, `AGENTS.md`, `atelier.toml` et les
autres briefs. La fiche 053 relève de l'outillage du registre ; aucune
autre fiche ni prose de la feuille ne change. Aucun test existant n'est
modifié, renommé, supprimé ou relâché.

## Conditions de succès

Chaque commande ciblée ci-dessous doit collecter les nouveaux cas nommés ;
zéro test sélectionné est un échec, jamais une preuve. Les paramètres de
monde viennent des constantes et le dénominateur des données réellement
jouées. La base est le dernier `master` au démarrage du lot.

### SC1 — Le monde neuf porte le début de l'année

Commande : `python3 -m pytest sim/tests/test_monde.py -k date_initiale -q`.
Ajouter un cas qui charge le monde réel, exige des cellules, puis vérifie
le compteur nul et la date calculée à partir d'`ANNEE_INITIALE`. L'année
et le jour n'apparaissent pas dans les attributs stockés du monde ou des
cellules. Modifier le dictionnaire obtenu par consultation ne change pas
la consultation suivante. Rouge d'abord : le compteur manque sur la base.

### SC2 — Le compteur suit les ticks réussis dans les trois régimes

Commande : `python3 -m pytest sim/tests/test_monde.py -k date_ticks -q`.
Jouer plusieurs ticks sur un monde sans carte, un monde avec carte en
saison moyenne et un monde avec carte en saison du jour. Après chaque
retour, le compteur égale le nombre d'appels terminés, la date se déduit
de ce nombre. Sur un monde d'épreuve sans compteur, aucun attribut n'est
ajouté. Un sous-maillon isolé ne fait pas passer le jour suivant.
Rouge d'abord sur la base, qui ne tient aucun compteur.

### SC3 — Le changement d'année et la durée du tick dérivent

Commande : `python3 -m pytest sim/tests/test_monde.py -k date_calendrier -q`.
Éprouver `date_de_tick` aux limites d'année, de part et d'autre, et sur
plusieurs années. Une seconde série remplace en mémoire la durée du tick,
la durée de l'année puis l'année initiale, avec restauration automatique ;
les résultats suivent `divmod` des valeurs effectivement lues. Aucun mois,
jour intercalaire ou second modulo annuel n'entre dans le moteur.
La consultation refuse un compteur négatif, booléen ou non entier.

### SC4 — Un numéro incohérent est refusé avant ses effets

Commande : `python3 -m pytest sim/tests/test_monde.py -k date_refus -q`.
Essayer un numéro passé, un numéro futur, un booléen et un non-entier,
puis un compteur du monde corrompu. Pour chacun : `ValueError`, message
qui nomme reçu et attendu, compteur et cellules inchangés, bassin inchangé,
carte inchangée et `rng.getstate()` inchangé. Les essais incluent un monde
à gisements pour détecter une garde posée après l'extraction.

Un autre cas provoque une exception dans un maillon : le compteur ne
progresse pas. Il ne prétend pas que les mutations précédentes sont
annulées. Rouge d'abord sur la base, puis preuve de sensibilité en
déplaçant temporairement la garde après l'extraction dans une copie privée.

### SC5 — Le résumé affiche la date du monde réellement joué

Commande : `python3 -m pytest sim/tests/test_monde.py -k date_cli -q`.
Ajouter les cas JSON et texte, à zéro tick et après une durée qui franchit
une année. La date du résumé égale celle du `World` retourné par
`_simulate`, et non une horloge système ou la graine. Les anciennes clés
du résumé sont identiques à celles de la base pour la même course, après
retrait de la seule clé `date_simulation`. Le refus de ticks négatifs reste
celui de la CLI existante. Rouge d'abord : aucune date dans le résumé.

### SC6 — Même temps, même monde ; temps distinct, empreinte distincte

Commande : `python3 -m pytest sim/tests/test_determinisme.py -k date -q`.
Ajouter une comparaison de deux courses identiques, à même graine et même
suite d'appels : compteurs, dates, `to_dict()` et bassin sont égaux. Sur
deux copies du même monde dont seul le compteur diffère, les cellules et
stocks sont égaux, mais les sérialisations et leurs empreintes diffèrent.
Les nombres de ticks comparés sont non nuls et dérivés de la course.

### SC7 — La date ne change pas la physique ni le snapshot

```bash
python3 -m pytest sim/tests/ viewer/tests/ -q
python3 -m sim --ticks 20 --seed 0 --json
git diff --exit-code origin/master -- sim/snapshot_export.py sim/model.py viewer/ data/
```

Comparer sur la base et après le lot une même course dans chacun des
trois régimes : les cellules, le bassin et les kilogrammes transportés
sont identiques, ainsi que l'état final du générateur aléatoire. Pour une
même graine, un même état et une même étiquette, les octets du snapshot
sont inchangés. Ces preuves sont rejouées après tout rebasage ; elles
n'utilisent aucune empreinte figée dans ce brief.

Les tests existants restent verts, y compris le schéma fermé du snapshot,
la sensibilité aux constantes et l'absence de littéraux numériques non
nommés. Les nouveaux cas sont uniquement ajoutés aux deux fichiers
autorisés. Aucun monde d'épreuve existant n'est élargi pour les faire passer.

## Hors périmètre

- changer le régime de saison moyenne de `tick(world, rng)` ou les
  formules de production, extraction, commerce, démographie et migration ;
- calendrier civil, mois, années bissextiles, horloge réelle, vitesse de
  jeu, pause, reprise de sauvegarde ou voyage dans le temps ;
- date dans le snapshot ou les vues, version du schéma et réconciliation
  de l'étiquette d'export avec le compteur réel ;
- nouveaux champs temporels sur les cellules ou une seconde date stockée ;
- atomicité transactionnelle de tous les maillons en cas d'exception ;
- documentation générale du modèle et toute réécriture de test existant.
