# Lot #731 — Le jeu s'ouvre sur la carte à sa vitesse
Jalon : J4 · Machine : vps · Taille prévue : 200 lignes

## But
`pc/jouer.py` démarre le monde à la vitesse de la vue sur laquelle le jeu s'ouvre. Il prend cette vitesse dans le fichier de réglages des vues, et non plus à 1 jour par seconde : 6 sur la carte, 0,1 quand `--cellule` impose une ville.

## Le joueur
Lot de fond, sous-lot 4 de #410 « Le joueur passe de la carte à sa capitale, et l'horloge suit la vue ». Il prépare le geste du J4 de `CAP.md` : le joueur **passe de la carte à sa ville d'un geste**. Il lance `pc\Jouer.cmd` et la carte s'ouvre. Le monde y avance tout de suite à la vitesse de la carte : une année dure environ une minute, et il voit ses lieux se remplir ou se vider. Il n'attend plus six minutes par an, et ce n'est plus une vitesse que le jeu aurait dû corriger. S'il impose une ville par `--cellule`, elle s'ouvre à la vitesse de la ville : une année dure environ une heure, le temps de regarder ses chantiers. Le passage dans le noir (#728) garde donc, dès le premier geste, une vitesse qui suit la vue. Les sous-lots 5 et 6 de #410 (session et verdict de l'épreuve) le montreront sur le PC.

Dépend de : rien qui manque. `3d/unity/Assets/ForgeLocal3D/Pont/Resources/ReglagesDesVues.json` vaut `{"VITESSE_VILLE": 0.1, "VITESSE_CARTE": 6}` sur la base (#728, 05307bf). `python -m sim.service --jours-par-seconde` existe.

## Règle du monde
Sans objet : c'est un lot d'outil. La vitesse dit combien de ticks le service joue par seconde réelle, pas ce que dure un tick. « La base de temps » de `jeu/sim/MODELE.md` (un tick = un jour) reste intacte. Aucune constante du monde ne change, et le service garde son défaut de 1 j/s (`DEFAULT_JOURS_PAR_SECONDE`).

Règle de vue retenue au découpage de #410 : la vitesse est celle de la vue d'ouverture. Sans `--cellule`, le monde neuf n'a aucune maison confirmée (`maison_du_joueur` nul au tick 0, déjà vérifié par `test_chemin_nominal`), et le jeu s'ouvre sur la carte. Avec `--carte`, il s'ouvre aussi sur la carte : `-forgeCarte` passe avant `-forgeCell` dans `OuvertureDeLaCapitale.Decider`. Seul `--cellule` sans `--carte` ouvre une ville. Le lanceur n'écrit aucune vitesse en chiffres : il lit les deux valeurs dans le même fichier qu'Unity.

## Périmètre
pc/jouer.py
jeu/ville/tests/test_lanceur_jouer.py
docs/briefs/731-le-jeu-s-ouvre-sur-la-carte-a-sa-vitesse.md

Tout autre chemin est interdit, en particulier `ReglagesDesVues.json`, `jeu/sim/service.py`, `pc/Jouer.cmd` et les `pc/epreuve_*.py`. Budget : environ 30 lignes de lanceur, 85 de tests, le reste pour ce brief.

Ce que le lanceur fait :
- `REGLAGES = RACINE / "3d/unity/Assets/ForgeLocal3D/Pont/Resources/ReglagesDesVues.json"` est une constante du module, que les tests remplacent.
- Une fonction `_vitesse(carte: bool, cellule: int | None) -> tuple[str, float]` rend `("ville", VITESSE_VILLE)` si `cellule` n'est pas `None` et `carte` est faux, et `("carte", VITESSE_CARTE)` sinon. Elle lève `RuntimeError` dans ces cas : fichier absent, JSON illisible, clé absente, valeur qui n'est pas un nombre (`bool` et texte compris), NaN, infini, ou valeur ≤ 0. Le message nomme le fichier et la clé fautive. Une vitesse nulle mettrait le monde en pause : elle est refusée, comme dans `ReglagesDesVues.Lire`. Aucune valeur de repli.
- `main` appelle `_vitesse` avant de démarrer le service. En cas de refus, il écrit sur stderr « le jeu n'est pas lancé : <cause> » et rend 1. Ni le service ni le jeu ne sont démarrés.
- Sinon, il écrit la ligne `vitesse de la <vue> : <v> jours par seconde`. Il ajoute `--jours-par-seconde`, `repr(v)` à la commande du service, et rien d'autre ne change.
- Les noms que les épreuves reprennent (`JEU_PY`, `_lire_flux`, `_attendre_pret`, `_cellule`, `_regle`, `_repond`, `LIGNES_STDERR_GARDEES`, `DELAI_ARRET_S`) restent tels quels. La docstring dit la vitesse. Le cell_id du ksar n'est jamais écrit en chiffres (`test_le_numero_n_est_pas_ecrit`).

Dans les tests, le faux jeu ajoute à son document la clé `jours_par_seconde`, lue dans la dernière réponse `/horloge`. C'est la seule ligne existante qui change. Aucune assertion existante n'est touchée.

## Conditions de succès
Commande unique, depuis `jeu/` : `python -m pytest ville/tests/ -q`, sortie 0. Écrire les cas neufs et les voir rouges sur `pc/jouer.py` d'avant, puis écrire le lanceur.

**SC1 — la carte s'ouvre à la vitesse de la carte.**
- Par `_jouer` (le vrai lanceur, en sous-processus), sans option, puis avec `--carte` : le faux jeu lit un `jours_par_seconde` égal à `VITESSE_CARTE`, lu dans `REGLAGES` par le test lui-même. On exige aussi `ticks[1] > ticks[0]`, et dans la sortie la ligne `vitesse de la carte : …`. Le service est arrêté à la fin (`port_refuse`).
- Le test exige aussi que 365 / `VITESSE_CARTE` tombe entre 50 et 70 s : c'est la phrase du joueur.
- Contre-épreuves : un lanceur qui ne passe pas `--jours-par-seconde` rend 1,0 et rougit. Un lanceur qui écrit 6 en dur rougit sur le cas suivant.
- Par `jouer.main` en processus, avec `REGLAGES` remplacé par un fichier temporaire `{"VITESSE_VILLE": 0.25, "VITESSE_CARTE": 4}` : le faux jeu lit 4.

**SC2 — une ville imposée s'ouvre à la vitesse de la ville.**
- `--cellule 1175` (`CELLULE_DU_PANNEAU`) donne `VITESSE_VILLE` au faux jeu.
- `--cellule 1175 --carte` donne `VITESSE_CARTE` : la carte l'emporte, comme dans le jeu.
- Avec le fichier temporaire de SC1, `--cellule` donne 0,25.
- Contre-épreuve : des vues inversées rougissent les deux valeurs.

**SC3 — un réglage faux ne lance rien.**
Par `jouer.main` en processus, avec `capsys`. `REGLAGES` est remplacé tour à tour par :
- un fichier absent ;
- un JSON tronqué ;
- un fichier sans `VITESSE_CARTE` ;
- `VITESSE_CARTE` valant `"6"`, `true`, `0`, `-1`, `NaN`, puis `Infinity`.

Pour chacun on exige : `main` rend 1 ; stderr contient « le jeu n'est pas lancé » et nomme la clé (ou le fichier, s'il est absent ou illisible) ; « service prêt » et « service arrêté » sont absents de la sortie, donc aucun service n'a démarré ; le fichier de sortie du faux jeu n'existe pas ; `port_refuse(port)` est vrai. Le même refus vaut pour `VITESSE_VILLE` à 0 sous `--cellule`.
Contre-épreuve : un lanceur qui retombe sur 1 j/s rend 0 et rougit.

**SC4 — rien d'autre ne bouge.**
- Tous les cas existants de `test_lanceur_jouer.py`, `test_cellule_du_desert.py`, `test_epreuve_carte.py`, `test_epreuve_moree.py`, `test_epreuve_capitale.py` et `test_epreuve_jalon4.py` restent verts, sans retouche.
- `git diff origin/master -- jeu/ville/tests/test_lanceur_jouer.py` ne retire aucune ligne `assert`.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le périmètre.
- Contre-épreuve : le JSON des réglages, le service, `Jouer.cmd` ou une épreuve touchés refusent la livraison.

## Hors périmètre
- Changer les valeurs du fichier de réglages, ou le défaut du service (1 j/s, qu'utilisent les autres appelants).
- Poser la vitesse en jeu : le double-clic sur le siège (sous-lot 2 de #410), la touche C et la pause en ville (sous-lot 3). La session et le verdict de l'épreuve (sous-lots 5 et 6).
- Les épreuves et captures : elles démarrent leur propre service en pause (`--jours-par-seconde 0`) et restent ce qu'elles sont.
- Une option du lanceur pour choisir une autre vitesse.

## Vérification du codeur

La vitesse d'ouverture est lue et contrôlée avant de lancer le service, puis
transmise par `--jours-par-seconde`. Les réglages partagés et le défaut du
service restent intacts. Aucune assertion existante n'a été retirée.

Depuis la racine, les commandes suivantes ont réussi :

```bash
python3 -m pytest jeu/ville/tests/test_lanceur_jouer.py -k vitesse -q
# 17 réussis ; les mêmes 17 cas échouaient avant la modification du lanceur.
python3 -m pytest jeu/ville/tests/test_lanceur_jouer.py -k 'chemin_nominal or cellule or carte_ouvre or jeu_plante or pas_de_build or port_deja_pris or le_meme_port' -q
# 12 réussis.
python3 -m pytest jeu/ville/tests/test_cellule_du_desert.py jeu/ville/tests/test_epreuve_carte.py jeu/ville/tests/test_epreuve_moree.py jeu/ville/tests/test_epreuve_capitale.py jeu/ville/tests/test_epreuve_jalon4.py -k 'le_numero_n_est_pas_ecrit or introuvable or orchestre or un_refus_http or est_egale or sont_egaux' -q
# 16 réussis.
python3 -m pytest jeu/sim/tests/test_no_hardcoded.py jeu/sim/tests/test_write_coverage.py -q
# 8 réussis.
```

La suite entière `ville/tests/` n'a pas été lancée, conformément à la consigne
du lot donnée au codeur. `git diff --check` est propre ; le diff contre
`origin/master` ne contient que les trois fichiers du périmètre, sans fichier
non suivi.
