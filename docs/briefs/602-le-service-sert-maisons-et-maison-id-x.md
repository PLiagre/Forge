# Lot #602 — Le service sert /maisons et /maison?id=X
Jalon : J3 · Machine : vps · Taille prévue : 290 lignes

## But
Le service dit, pour chaque maison du monde, qui elle est, où elle siège,
quels lieux elle tient, quelle part elle prend, ce que contient son grenier
et ce qui a circulé pour elle sur trente jours : `GET /maisons` donne la
liste légère, `GET /maison?id=X` la fiche entière, et un identifiant inconnu
reçoit un 404.

## Le joueur
Lot de fond. Il prépare l'écran du jalon 3 : « la cellule découpée en
lieux, chacun avec son seigneur (réel quand on le sait, plausible sinon) et
son nom ; les flèches de ce qui monte vers le siège du joueur et vers celui
de son suzerain ; les lieux qui se vident quand il prend trop ; son panneau,
sa part et son grenier ». Il prépare aussi la décision du jalon, « prendre
plus aujourd'hui ou garder ses gens » : pour la sentir, il faut lire côte à
côte sa part, son grenier, ce qui est monté de ses lieux, ce qui est parti
chez son suzerain, ce que les charretiers ont mangé, et combien de gens ont
quitté ses lieux. Après ce lot, une seule requête au service le dit, pour
lui comme pour chaque voisin. Le joueur ne le voit pas encore : #401 en
dessine les flèches dans la forge, #403 et #405 dans Unity ; le sous-lot 3
de #400 complète `/lieu` et le sous-lot 4 met la fiche dans la photographie.

## Règle du monde
Sans objet : c'est une vue. Elle lit le registre des maisons (« Les maisons
du monde »), leurs greniers (« Le grenier d'une maison »), leurs parts
(« Le prélèvement »), les noms (« Les lieux d'une cellule, vue dérivée »)
et le registre des flux (« Les flux sur trente jours ») ; elle ne décide
aucun nombre, aucun tick ne la lit et aucune empreinte ne bouge.
`MODELE.md` gagne une section `## Les maisons servies, vue dérivée`, juste
après `## La carte et les terres servies, vue dérivée`. Les noms des
seigneurs plausibles restent de **niveau 2** (plausibles, jamais sourcés) ;
les autres sont ceux du registre (**niveau 1**).

**Le module `jeu/sim/maisons_servies.py`.** Pur : il ne lit que le monde et ce
qu'on lui passe, n'écrit rien, n'importe que la bibliothèque standard et
`sim.*`, et aucun littéral autre que 0, 1, −1 dans ses fonctions
(`test_no_hardcoded.py`). Il contient :

- `MatiereMaisons`, une dataclass gelée : `tick`, `date`, `registre` (le tuple
  `monde.maisons`), `noms` (le bloc de `noms_depuis_monde`), `places` (celles
  de `places_du_monde`), `tenus` (identifiant → tuple trié de couples
  `(cell_id, rang)` dont le lieu a ce `maitre`), `parts` (copie de
  `monde.parts`), `greniers` (copie de chaque panier de `monde.greniers`),
  `flux` (identifiant → les cinq kilos) et `personnes` (identifiant →
  `(partis, arrives)`).
- `matiere_des_maisons(monde, noms, places) -> MatiereMaisons`. Les cinq
  kilos d'une maison se somment sur les jours rendus par
  `sim.flux._jours_de_fenetre(monde)`, dans leur ordre, en partant de 0,
  comme `flux_de_maison` : **égalité exacte exigée**, pas d'arrondi. Une
  maison absente des noms des routes a cinq zéros, qui sont une mesure
  (#601). `partis` et `arrives` somment, sur les mêmes jours,
  `jour.partis` et `jour.arrives` des lieux qu'elle tient : ce sont des
  **personnes**, ce que le monde compte (#601), et le nom du champ le dit.
  On ne passe pas par `flux_de_maison` maison par maison : il cherche
  l'indice par `noms.index` et coûte 181 ms pour les 2 291 maisons ; une
  passe unique sur les jours coûte 14 ms (mesures du chef, tick 35,
  srv1914711, 14/10/2026).
- `document_de_maison(matiere, identifiant) -> dict`, exactement ces clés :
  `id`, `nom`, `sorte`, `suzerain` (identifiant ou `null` pour une racine,
  ce qui est un fait, pas une absence), `siege` = `{cell_id, rang, nom,
  point}` (`nom` = le nom du lieu dans `noms[cell_id]["lieux"]`, `point` =
  `places[cell_id][rang].en_document()`), `lieux` = liste de `{cell_id,
  rang}` triée, `part`, `grenier` (le panier, marchandise → kg),
  `flux_30j` = `{preleve_kg, recu_kg, du_envoye_kg, mange_en_route_kg,
  rendu_kg, partis_personnes, arrives_personnes}`, `absents`, `tick`, `date`.
  Le `nom` d'une maison `plausible` est `noms[cell_id]["maisons"][id]["nom"]` ;
  celui des autres, le `nom` du registre. Un identifiant inconnu lève
  `MaisonInconnue` (sous-classe de `KeyError`) en le nommant.
- **Un champ absent se déclare** dans `absents`, champ → raison, `{}` sinon :
  siège hors carte (`cell_id is None`) → `siege` = `{cell_id: null, rang:
  null, nom: <siege du registre>, point: null}` et `absents["siege"]` = la
  raison `hors_carte` du registre ; plausible absente du bloc de noms de sa
  cellule → `nom: null` et une raison qui nomme la cellule ; maison absente
  de `parts` ou de `greniers` → `null` et sa raison. Un grenier vide `{}` et
  une liste de lieux vide sont des mesures, pas des absences.
- `liste_des_maisons(matiere) -> dict` : `{tick, date, nombre, maisons}`,
  `maisons` triées par `id`, chacune `{id, nom, sorte, suzerain, siege,
  lieux}` avec `siege` = `{cell_id, rang}` ou `null` hors carte, et `lieux`
  le nombre de lieux tenus.

**Le service (`jeu/sim/service.py`).** `EtatPublie` gagne deux champs :
`maisons` (la `MatiereMaisons` du tick) et `octets_maisons` (un `dict`
vide à la publication). `_construire_etat` appelle `matiere_des_maisons`
avec `self._noms` et les places déjà calculées : c'est tout ce qu'il fait
de plus. **Aucune fiche n'est sérialisée à la publication** : 2 291 fiches
coûtent environ 50 ms, et le cycle tick + publication est déjà de 200 à
300 ms pour une cadence de 250 ms à 4 jours/s
(`test_horloge_pause_vitesse_et_budget`). Comme les plans (`octets_plan`),
une fiche, ou la liste, est sérialisée à sa première lecture, sous un verrou
propre `verrou_maisons` (jamais `verrou_tick` : une lecture n'attend pas un
tick), puis gardée dans `etat.octets_maisons`. Routes :

- `GET /maisons` → 200, la liste.
- `GET /maison?id=X` → 200, la fiche ; un `id` absent, vide ou répété → 400
  `{"erreur": "paramètre id invalide : reçu …, attendu un identifiant de maison"}` ;
  un identifiant inconnu → 404 `{"erreur": "maison inconnue : reçu 'X'"}`.

Les autres routes ne changent pas d'un octet. `jeu/sim/README.md` nomme les
deux routes dans son paragraphe du service et le module dans sa liste.

## Périmètre
jeu/sim/maisons_servies.py
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/README.md
jeu/sim/tests/test_maisons_servies.py

## Conditions de succès
Les cas neufs vivent dans `jeu/sim/tests/test_maisons_servies.py` (fichier
neuf, nommé dans `jeu/sim/tests/README.md`). Rouge d'abord : avant le lot,
chaque cas échoue (import de `sim.maisons_servies`, ou 404 « chemin
inconnu » sur `/maisons`). **Les tests lisent le service en processus** :
une fixture de module lance `ServeurMonde(("127.0.0.1", 0), 0, 0)` dans un
fil `serve_forever` (le motif `_service_local` de `test_carte_servie.py`),
pose `choisir_depart` pour `charger_seigneuries()[0]`, joue un tick, pose
`fixer_part` à 0,25 pour cette maison, puis `POST /tick?n=35`. L'horloge est
à l'arrêt : le monde ne bouge plus pendant les lectures. Chaque contrôle est
une fonction qui reçoit le document servi, pour que sa contre-épreuve lui
passe une copie altérée. Aucun nombre de maisons n'est écrit en dur : tout
se dérive de `serveur.world`.

- **SC1 — la liste est complète.** `GET /maisons` : 200 ; les `id` égalent
  `sorted(m.id for m in serveur.world.maisons)`, `nombre` égale leur
  nombre, qui est > 0 ; `sorte`, `suzerain` et `siege` suivent le registre ;
  `lieux` égale le nombre de lieux dont `maitre` est la maison.
  Contre-épreuve : la liste amputée d'une maison, ou une maison au
  `suzerain` changé, échoue.
- **SC2 — chaque fiche dit le monde, au flottant près.** Pour **chaque**
  maison de la liste, `GET /maison?id=…` : 200, exactement les clés
  nommées ; les cinq kilos de `flux_30j` **égalent** (`==`, sans
  `approx`) `flux_de_maison(serveur.world, id)` ; `partis_personnes` et
  `arrives_personnes` égalent les sommes de `flux_de_lieu` sur ses lieux ;
  `part` égale `world.parts[id]`, `grenier` égale `world.greniers[id]` ;
  `lieux` égale les couples dont le lieu a ce maître ; le `point` du siège
  égale celui que `/lieu?cell=<cell_id du siège>` sert pour ce rang ;
  `tick` égale celui de `/monde`. Échantillons non vides : au moins une
  maison a `preleve_kg > 0`, `du_envoye_kg > 0`, `mange_en_route_kg > 0`, et
  au moins une a `partis_personnes > 0`. La maison du joueur sert `part`
  0,25 et `du_envoye_kg > 0`, et la fiche de son suzerain répond 200.
  Contre-épreuves : une fiche dont `preleve_kg` porte 1e-9 kg de plus, ou
  dont `partis_personnes` compte un lieu d'une autre maison, échoue.
- **SC3 — les noms viennent du monde.** Chaque maison `plausible` qui tient
  un lieu porte `noms_depuis_monde(serveur.world)[cell_id]["maisons"][id]["nom"]`,
  jamais son identifiant ; les autres portent le `nom` du registre ; le
  `nom` du siège est celui que `/lieu` sert dans `noms["lieux"]` pour ce
  rang. Au moins une plausible et une maison historique sont contrôlées.
  Contre-épreuve : une fiche dont le `nom` est l'identifiant échoue.
- **SC4 — un champ absent se déclare.** Dans chaque fiche servie, toute
  valeur `null` parmi `nom`, `part`, `grenier` et `siege.point` a sa clé dans
  `absents`, et `absents` ne nomme que des champs nuls. Les maisons dont
  `cell_id is None` dans le registre (au moins une, dérivée du monde) servent
  `siege.point` nul et `absents["siege"]` égal à leur `hors_carte`. Sur
  `matiere_des_maisons` appelée directement, avec un bloc de noms privé
  d'une plausible et des parts privées d'une maison : `nom` et `part` nuls,
  leurs raisons présentes, celle du nom contient le `cell_id`.
  Contre-épreuve : une fiche à `nom` nul sans entrée dans `absents` échoue.
- **SC5 — 404 et 400.** `GET /maison?id=maison-inconnue` → 404,
  `{"erreur": "maison inconnue : reçu 'maison-inconnue'"}` ; `/maison`,
  `/maison?id=` et `/maison?id=a&id=b` → 400 ; `/monde` est identique à
  l'octet avant et après ces refus. Un service neuf, au tick 0, sert déjà
  `/maisons` et une fiche (200, `tick` 0). Contre-épreuve : l'identifiant
  d'une maison du registre, lui, répond 200.
- **SC6 — la fiche est celle du tick publié, et sérialisée à la demande.**
  Juste après un `POST /tick?n=1`, `serveur.etat_publie.octets_maisons`
  est vide. On note `flux_de_maison` et le grenier de la maison du joueur,
  puis on altère le monde vivant (grenier + 1 000 kg, part 0,9, 1 kg ajouté
  au `preleve` du dernier jour) : la première lecture de sa fiche sert les
  valeurs notées, une seconde lecture rend les mêmes octets, et
  `octets_maisons` ne contient que les entrées lues. Après un tick de plus,
  `tick` avance. Contre-épreuve : `sim.service.matiere_des_maisons`
  enveloppé pour remettre `greniers=monde.greniers` (le grenier vivant)
  fait échouer l'égalité.
- **SC7 — la publication ne déborde pas son temps.** Marque `chronometre` :
  un cas imprime la médiane de `matiere_des_maisons` sur le monde réel au
  tick 35 et la durée de `_construire_etat` ; `MODELE.md` donne ces
  médianes, avant et après le lot, mesurées sur srv1914711.
  `python3 -m pytest jeu/sim -q -m chronometre` reste vert, en particulier
  `test_horloge_pause_vitesse_et_budget` et
  `test_tick_sous_le_budget_du_service`, **sans toucher un seuil** : si la
  cadence rougit, on allège la matière (variables locales, une seule passe
  sur les jours, aucune sérialisation), et si l'on n'y arrive pas, on le dit
  sur la PR avec les mesures.
- **SC8 — la section du modèle.** `## Les maisons servies, vue dérivée`
  existe et contient `/maisons`, `/maison?id=`, `404`, `absents`,
  `EtatPublie`, `personnes` et `première lecture` ; le même contrôle sur le
  texte privé de `/maisons` échoue.

Commandes, depuis la racine :

- `python3 -m pytest jeu/sim/tests/test_maisons_servies.py -q -m "not chronometre"`
  — vert, au moins huit cas recueillis.
- `python3 -m pytest jeu/sim/tests/test_maisons_servies.py -q -m chronometre`
  puis `python3 -m pytest jeu/sim -q -m chronometre` — verts, joués seuls.
- `python3 -m pytest jeu/sim -q` — vert, en particulier `test_monde.py`
  (routes existantes, `test_service_depend_uniquement_de_la_bibliotheque_standard_et_de_sim`),
  `test_carte_servie.py`, `test_intentions.py`, `test_flux.py`,
  `test_no_hardcoded.py`, `test_determinisme.py`.

## Hors périmètre
- `/lieu` (nom, prélevé, partis et arrivés de chaque lieu) : sous-lot 3 de
  #400. La photographie et la preuve par rejeu : sous-lot 4
  (`snapshot_export.py` n'est pas touché ; il réutilisera
  `document_de_maison`).
- Les flèches de la forge et de Unity : #401, #403, #405.
- Des foyers au lieu de personnes pour les départs : le monde compte des
  personnes ; la fiche ne devine pas une taille de foyer.
- Toute règle du monde, toute écriture dans `sim/flux.py` ou le tick ; toute
  route existante ; tout test existant : aucun ne change.
