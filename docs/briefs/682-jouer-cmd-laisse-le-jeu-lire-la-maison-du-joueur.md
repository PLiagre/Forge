# Lot #682 — Jouer.cmd laisse le jeu lire la maison du joueur
Jalon : J4 · Machine : vps · Taille prévue : 220 lignes

## But
Lancé sans `--cellule`, `pc\Jouer.cmd` ne choisit plus de cellule à la place du jeu : il démarre le service puis le jeu sans `-forgeCell`, et c'est le jeu qui lit la maison du joueur pour ouvrir sa capitale ou la carte de 1400.

## Le joueur
Quatrième sous-lot de #409 « Le jeu ouvre la capitale du joueur ». C'est le geste du J4 de `CAP.md` : le joueur **entre dans sa capitale**, et **passe de la carte à sa ville**. Jusqu'ici, `Jouer.cmd` imposait au jeu la cellule la plus ensoleillée de la carte : le joueur tombait dans un ksar qui n'était pas le sien, quoi qu'il ait choisi. Après ce lot, `Jouer.cmd` laisse le jeu décider, par la règle de #687 appliquée par #688 (sur la base depuis `25a1190`). Le joueur arrive sur la carte de 1400 tant qu'il n'a pas de terre, et dans Biskra quand le service lui sert le Zab. Il sent que le jeu part de sa maison, et non d'un choix du lanceur.

Limite à dire : chaque `Jouer.cmd` démarre un service neuf, donc sans choix. Le lancement ouvre donc toujours la carte, où le joueur choisit sa terre. L'entrée dans la capitale depuis la carte, d'un geste, vient avec #681 et #410. `--cellule` reste pour les épreuves qui le disent.

## Règle du monde
Sans objet : c'est un lot d'outil. Le monde, `jeu/sim/MODELE.md` et le service ne changent pas. La destination se lit au service : `/monde` (`maison_du_joueur`), puis `/maison` (« Les maisons servies, vue dérivée »). C'est le jeu qui la lit (`AiguillageDeCapitale`, #679), pas le lanceur. `cell_id` reste la seule clé spatiale.

## Périmètre
pc/jouer.py
pc/Jouer.cmd
jeu/ville/tests/test_lanceur_jouer.py
jeu/ville/README.md

Tout autre chemin est interdit. En particulier, `jeu/ville/cellule_du_desert.py`, ses tests, `pc/epreuve_*.py`, les scènes et tout le C# restent tels quels. La branche part de `origin/master` à `25a1190` (#688) ou plus récent.

Budget : environ 15 lignes dans `jouer.py`, 5 dans `Jouer.cmd`, 15 dans le README, 75 dans les tests, le reste pour ce brief.

### `pc/jouer.py`
- Sans `--cellule` :
  - `main` n'appelle plus `_regle()` ni `_verifier_lieu` ;
  - la commande du jeu ne reçoit pas `-forgeCell` (`--carte` ajoute toujours `-forgeCarte`) ;
  - au lieu de `cellule <n>`, le lanceur écrit une constante de module, `AUCUNE_CELLULE = "aucune cellule imposée : le jeu lit la maison du joueur"`.
- Avec `--cellule C`, rien ne change : `cellule C`, `_verifier_lieu(port, C, …)` (un 404 refuse toujours le lancement), puis `-forgeCell C`.
- `REGLE`, `_regle`, `_cellule`, `_repond`, `_lire_flux`, `_attendre_pret` et `_verifier_lieu` restent, sans changement de signature. `pc/epreuve_jalon1.py` et `pc/epreuve_carte.py` appellent `JOUER._regle()` pour leur cellule par défaut. `test_un_unity_introuvable_sort_a_2_en_le_nommant` (dans `test_epreuve_jalon1.py`) la parcourt.
- La docstring dit la nouvelle règle : sans `--cellule`, aucune cellule ; le jeu ouvre la capitale du joueur, la carte, ou dit l'absence (#688).

### `pc/Jouer.cmd`
Les commentaires disent la même règle. La ligne `set "REGLE=…"` part, car le lanceur Windows ne nomme plus la règle. `py pc\verifier_lanceurs.py` vérifie une cible de moins, sans autre écart.

### `jeu/ville/README.md`
La section « La cellule par défaut du lanceur » change. `Jouer.cmd` ne passe `-forgeCell` qu'avec `--cellule`. Sans lui, c'est le jeu qui décide : la capitale du joueur si sa terre a un kit, sinon la carte de 1400. `cellule_du_desert.py` reste la cellule par défaut des épreuves (`epreuve_jalon1.py`, `epreuve_carte.py`). La règle de l'insolation et ses refus sont gardés mot pour mot. Le titre peut devenir « La cellule par défaut des épreuves ».

### `jeu/ville/tests/test_lanceur_jouer.py`
L'issue #409 ordonne ce changement d'invariant, et #682 le reprend : `test_chemin_nominal` figeait `-forgeCell = cellule_du_desert`. Rien d'autre ne s'assouplit.
- **Le faux jeu** lit `-forgeCell` s'il le reçoit, et lit alors `/lieu?cell=<c>` comme aujourd'hui. Sans lui, il lit `/monde`, comme l'aiguillage du vrai jeu. Il ajoute au JSON :
  - `"lu"` : `"/lieu"` ou `"/monde"` ;
  - `"maison_du_joueur"` : la valeur lue, ou `null`.
  - `"forgeCell"` vaut `null` s'il n'a rien reçu.
  - Les autres clés sont gardées : `statut`, `cell_id`, `ticks`, `refuse_pendant`, `forgeCarte`.
- **`test_chemin_nominal`**, réécrit :
  - code 0, et le port est refusé après la sortie ;
  - `recu["forgeCell"] is None`, avec le message `-forgeCell reçu sans --cellule : <valeur>` ;
  - `lu == "/monde"`, `statut == 200`, `maison_du_joueur is None` (service neuf, aucun choix) ;
  - l'horloge avance ;
  - `refuse_pendant is False` ;
  - la sortie contient `AUCUNE_CELLULE` (lue dans le module chargé), `service prêt sur 127.0.0.1:<port>`, `jeu fermé (code 0)` et `service arrêté` ;
  - aucune ligne de la sortie ne correspond à `^cellule \d+$`.
- **`test_carte_ouvre_le_jeu_sur_la_carte`** garde ses assertions. Il ajoute `recu["forgeCell"] is None` dans ses deux cas.
- **Nouveau, `test_seule_la_cellule_demandee_est_verifiee`**, paramétré sur deux cas : sans option, et `--cellule 1175`.
  - Le test se fait en processus : `jouer = _charger("jouer", LANCEUR)`. `monkeypatch` remplace `jouer._regle` par un compteur qui lève si on l'appelle, et enveloppe `jouer._verifier_lieu` d'un relevé des cellules, qui appelle ensuite l'original.
  - Il lance `jouer.main(["--port", p, *options, "--", *faux_jeu])`.
  - Sans option : code 0, `_regle` jamais appelé, `_verifier_lieu` jamais appelé, `forgeCell` nul.
  - Avec `--cellule 1175` : code 0, `_regle` jamais appelé, `_verifier_lieu` appelé une seule fois pour 1175, `forgeCell == "1175"`.
  - Dans les deux cas, le port est refusé à la fin.
- `test_cellule_choisie`, `test_cellule_absente_de_la_carte`, `test_cellule_invalide_refusee`, `test_le_jeu_plante`, `test_pas_de_build`, `test_port_deja_pris`, `test_le_meme_port_partout` et les cinq tests des délais restent tels quels. Ils tournent avec le nouveau faux jeu. La constante `REGLE` du test part si plus rien ne la lit.

## Conditions de succès
Toutes depuis la racine du dépôt, sur le VPS.

**SC1 — sans `--cellule`, le jeu ne reçoit aucune cellule.** `python3 -m pytest jeu/ville/tests/test_lanceur_jouer.py -q` passe en entier : 17 cas, les 15 d'avant et les 2 du nouveau test.
Contre-épreuve : remettre le lanceur de master, puis rejouer.
```
cp pc/jouer.py /tmp/jouer-682.py
git show origin/master:pc/jouer.py > pc/jouer.py
python3 -m pytest jeu/ville/tests/test_lanceur_jouer.py -q
cp /tmp/jouer-682.py pc/jouer.py
```
Trois cas doivent rougir :
- `test_chemin_nominal`, avec `-forgeCell reçu sans --cellule : '<cellule du désert>'` ;
- `test_carte_ouvre_le_jeu_sur_la_carte` ;
- le cas « sans option » du nouveau test (`_regle` appelé).

Le cas `--cellule 1175` reste vert : seule la règle sans cellule change. Le codeur colle le résumé des deux passes.

**SC2 — `--cellule` sert encore les épreuves.** `test_cellule_choisie`, `test_cellule_absente_de_la_carte` (404 nommé, jeu jamais lancé) et le cas `--cellule 1175` du nouveau test sont verts dans SC1. Contre-épreuve : un `main` qui saute aussi `_verifier_lieu` avec `--cellule` fait rougir `test_cellule_absente_de_la_carte` (le faux jeu tourne et écrit `recu.json`) et le cas `--cellule 1175`. Le codeur le constate sur une copie jetable, puis la retire.

**SC3 — les épreuves gardent leur cellule par défaut.** `python3 -m pytest jeu/ville -q` passe. Contre-épreuve : retirer `_regle` de `pc/jouer.py` fait rougir `test_un_unity_introuvable_sort_a_2_en_le_nommant` (`AttributeError`). `python3 -m pytest jeu -q` passe aussi, avec le même nombre de cas qu'avant, plus 2.

**SC4 — le lanceur Windows reste juste.** `python3 pc/verifier_lanceurs.py` liste pour `Jouer.cmd` `JEU`, `LANCEUR` et `SERVICE`, et plus `REGLE`. Les autres lignes ne changent pas par rapport à master. Sur le VPS, le code de sortie reste 1, à cause des trois cibles Windows manquantes, comme avant le lot.
- `grep -n "forgeCell" pc/jouer.py` ne trouve que la branche `--cellule`.
- `grep -c "charger_et_choisir" pc/jouer.py` vaut 0. La règle se charge, mais ne s'appelle plus dans le lanceur.
- `git diff --name-only origin/master` ne liste que le périmètre et ce brief.

## Hors périmètre
- Tout le C# : l'aiguillage (#679), la décision (#687), son application (#688), la carte qui ouvre la capitale (#681), le passage carte → ville d'un geste (#410).
- Le relief de Biskra (sous-lot 5 de #409) et l'épreuve Zab/Bar (sous-lot 6).
- Un service qui garderait le choix du joueur d'un lancement à l'autre ; une vérification de `/monde` ou de `/maison` par le lanceur.
- `cellule_du_desert.py`, sa règle et ses tests ; les épreuves de `pc/` et leurs options.
