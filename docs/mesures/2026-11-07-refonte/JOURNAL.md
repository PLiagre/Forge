# Journal de la refonte du 7 novembre 2026

> Le journal de travail de la session de refonte (mode direct). Si le contexte
> se résume, on repart d'ici. Les mesures et leurs commandes :
> [RAPPORT.md](RAPPORT.md).

## La consigne, en bref

1. Mesurer depuis `origin/master` : le monde sans joueur (graine 0, IA) à 90,
   365 et 3 650 jours ; le tick avec et sans IA, et son profil ; la chaîne
   (gh, et le journal du pilote sur le VPS, en lecture seule). Tout dans
   `RAPPORT.md`, avec un plan classé.
2. Demander au propriétaire, en une fois (quatre questions au plus) : les
   jauges, l'arrêt de la chaîne, J4, les événements à choix. **Rien d'écrit
   avant sa réponse.**
3. Réécrire, une PR `direct/<sujet>` par étape : la vision ; la soudure et le
   tick ; le registre des modificateurs ; le pays et ses jauges ; les
   bâtiments de province ; la chaîne pour Claude seul ; le cap et ses issues.

## Où l'on travaille

- Worktree `D:\Forge\.atelier\direct\refonte-mesures`, branche
  `direct/refonte-rapport`, partie d'`origin/master` = `17557033`
  (Lot #952, 7 novembre).
- La session du 6 novembre avait commencé ici (branche `direct/refonte-mesures`,
  base `b6e15ae6`, jamais poussée) : ses mesures et ses scripts sont dans
  [`../2026-11-06-refonte/`](../2026-11-06-refonte/JOURNAL.md). On les refait
  sur le master du jour et on compare.

## Fait

- 07/11 : lecture d'AGENTS.md, CAP.md, VISION.md, WORKFLOW.md, atelier.toml,
  du journal #1021. Scripts du 6 novembre recopiés dans `scripts/`.
- Lancés : `mesure_tick.py` puis `mesure_monde.py` (3 650 jours, IA) ; deux
  sous-agents : la chaîne par `gh` (`brut/chaine-github.md`) et le journal du
  pilote sur le VPS (`brut/vps-pilote.md`).

- Mesures faites (RAPPORT.md, sections 1 à 4) : monde témoin à 90 et 365
  jours (Paris 0 % à un an, comme le 6/11) ; soudure : 212 jours de ration
  passent de justesse (pire Gand 47 %), 90 jours et « moins la perte »
  échouent, partage par surface = par habitants ; tick 43 / 230 ms, profil :
  `maisons_de_l_ia` 170 ms ; calculée une fois par la boucle, même monde
  (empreinte égale au 120e tick) ; chaîne GitHub et VPS (sous-agents, fichiers
  `brut/chaine-github.md`, `brut/vps-pilote.md`).
- Questions posées au propriétaire : les quatre recommandations retenues
  (RAPPORT.md, section 5 ; VISION.md, décisions 39 à 41).
- **Chaîne arrêtée** le 7/11 : `ssh hermes-boost 'cd ~/Forge &&
  atelier/crons/atelier-boucle arret'` (profil `arret`, rien en vol) ;
  `gh variable set PC_ACTIF --body non` — la variable **n'existait pas**
  avant : à la fin, `gh variable delete PC_ACTIF -R PLiagre/Forge` puis
  `atelier-boucle jour`.
- Monde à dix ans et tick au calme mesurés : 213 ms → 67 ms avec la liste des
  maisons de l'IA calculée une fois (RAPPORT.md, section 2).
- PR 1, la vision : branche `direct/vision-modificateurs` (VISION.md,
  AGENTS.md §3, README, COHERENCE PH-01 à 03, deux phrases du CAP, consigne
  du relecteur dans `atelier/prompts.py`, et ce dossier de mesures).

- PR 1 fusionnée (#1022, 7/11 13:21 UTC).
- PR 2, `direct/soudure-et-tick` (worktree `.atelier/direct/refonte-soudure`) :
  `JOUR_DE_LA_MOISSON = 212`, `jours_de_soudure`, soudure portée **par lieu à
  proportion de ses habitants** (`_porter_la_soudure_dans_chaque_lieu`) — par
  surface, le bourg dense partait vers ses champs dès le premier mois (vu par
  `test_metiers_lus_a_l_amorcage`) ; `toutes_les_maisons_de_l_ia` +
  `jouer_ia(monde, releve, maisons)` dans les trois boucles. Tests :
  `test_soudure.py`, `test_maisons_de_l_ia_une_fois.py` ; 28 rouges traités :
  empreintes de déterminisme recapturées (même code de mesure), contre-épreuve
  du commerce à la résolution de la photographie, faux `jouer_ia` à trois
  arguments, et **`sim/tests/amorcage_d_avant.py`** (l'amorçage d'avant, à
  l'octet près) pour les réponses figées du pont (tests C# pinnés), les
  calibrages documentés (part coutumière, départs) et les épreuves d'une
  famine précoce (programme de l'IA, distribution intérieure).
- Linux : WSL `Ubuntu-24.04`, venv `~/forge-venv` (pytest, xdist, numpy,
  pillow) ; `/tmp` s'efface entre deux sessions WSL : écrire les journaux dans `~`.
  Rouges propres à WSL (git de worktree) : `test_texte_master_*`,
  `test_une_seule_definition_part_miniere`.
- PR 3 commencée, `direct/modificateurs` (worktree
  `.atelier/direct/refonte-modificateurs`, parti de la PR 2) : `sim/modificateurs.py`,
  `data/modificateurs.toml`, branché sur récolte, prélèvement, natalité,
  mortalité, départs, coût et durée des chantiers (IA comprise), commerce ;
  `/modificateurs` au service, `modificateurs` à la photographie ;
  `test_modificateurs.py` (21 cas, verts sous Windows). Sans pose : monde et
  photographie à 365 jours identiques à la PR 2 (`96f0ad5d…`, `b2befd1b…`).

- 08/11 : PR 3 fusionnée (#1025). PR 4, le pays et ses jauges : la suite
  Linux trouvait le tick qui lisait le registre, les chefs et les maîtres
  (`test_registre_tick`, `test_maitre_tick`) par la mise à jour mensuelle des
  jauges ; elle sort du tick (`jauges.avant_le_tick`, jouée par les trois
  boucles avant l'IA, défaite avec les intentions si l'IA échoue) ; les deux
  épreuves de master qu'on avait neutralisées (`test_modificateurs.py`,
  `test_prelevement.py`) redeviennent celles de master. PR 5, les bâtiments
  de province : le chantier ne relit plus le maître du bourg au tick (vérifié
  au dépôt), avec son épreuve sous la garde de `test_maitre_tick`.
- **Un écart à la consigne, à dire au propriétaire** : le 7/11 au soir, la
  branche de sauvegarde `direct/modificateurs` (sans PR) a été poussée une
  fois avec `--force-with-lease`. Depuis, les branches réécrites sont
  poussées sous un nouveau nom (`direct/pays-et-ses-jauges`,
  `direct/batiments-des-provinces`), jamais de force.
- PR 4 : #1039, fusionnée. PR 5 : #1040 ; la suite Linux y trouvait l'IA qui
  proposait un moulin deux fois, ou le jour d'une route : un chantier à la
  fois, et `test_ia_raisons_egalent_le_monde` contrôle les raisons du moulin
  et du geste de jauge. #1039 fusionnée en un commit, #1040 en conflit :
  master fusionné dans la branche (`-s ours`, l'arbre de master étant celui
  de la pointe de #1039, contenue), sans force. PR 7 (ce CAP) : la PR de ce journal.
- Lots déplacés (`gh issue edit --milestone`, chacun avec sa ligne en
  commentaire, aucun fermé) : #849, #850 → J6 ; #860 → J5 ; #851, #419, #508,
  #962, #960, #953, #954, #955, #956 → Réserve ; #434 commenté (compétences
  déjà là) ; « Dépend de » ajoutés pour que le pilote suive l'ordre du CAP
  (il prend le plus petit numéro prêt) : #427 attend #1027, #324 attend #1026
  à #1030. Milestone J4 fermé.
- Mesures de fin, graine 0, IA, sous Windows au calme (scripts de
  `scripts/`) : tick avec IA 51,8 ms de médiane (65 au plus ; 213 ms au début de la refonte) ; Paris à un an 52,6 % (0 % au début, 50,6 % avec la soudure seule) ; Europe à un an
  107,2 % (93,8 % à dix ans, 88,3 % avec la soudure seule).
- Chaîne : réarmée à la fusion de cette PR, `gh variable delete PC_ACTIF -R PLiagre/Forge` puis `ssh hermes-boost 'cd ~/Forge && atelier/crons/atelier-boucle jour'` ; le pilote prendra #1026 et #1027 au VPS, #1031 au PC (simulé avec `atelier/lots.py`).

## Reste

1. Question du monde laissée au propriétaire : recalibrer la part coutumière
   (3 %) sur un monde qui a sa soudure (RAPPORT.md, section 6).
2. Les villes tombent après la première année (Paris 26 % à dix ans) : le
   commerce ne les nourrit pas — le lot #1026 (J5) le prend.
3. L'IA se tait à moitié après la première année (18 maisons sur 36 jouent
   encore à cinq ans, 17 à dix) : le lot #1027 (J5).
4. #860 (le jeu s'ouvre en pause) attend la réponse du propriétaire à la
   question du chef du 6/11 (la surbrillance des terres de départ, ou les
   gestes d'aujourd'hui) ; #1030, l'observateur, l'attend.
5. Les branches `direct/pays-et-jauges` et `direct/batiments-de-province`
   restent sur GitHub, sauvegardes d'avant les rebases, sans PR : à supprimer
   quand le propriétaire le dit.

## Décisions techniques prises seul (et pourquoi)

- Soudure = 212 jours de ration des habitants (jusqu'au 1er août), sans
  retrait de perte : le moteur ne fait pas pourrir le grain des foyers
  (niveau 3) ; partagée entre lieux par habitants (le total d'un an est le
  même qu'au partage par surface, le chemin non).
- Les épreuves dont le décor est l'amorçage d'avant (contrats figés du pont,
  calibrages cités au chiffre près, famine précoce) le gardent par
  `amorcage_d_avant.py` plutôt que de réécrire des chiffres C# sans Unity ou
  des calibrages sans décision : recalibrer la part coutumière sur la soudure
  est une question du monde, laissée au propriétaire.
- Tick : la boucle (service, forge, `python -m sim`) calcule une fois la
  liste des maisons de l'IA et la passe à `jouer_ia`. Pas de cache dans le
  monde ni dans un module : les tests exigent `monde.__dict__` inchangé
  après `decider_intentions`, et `world.py` ne nomme pas les capitales.
  `verifier_base` reste sans cache (ses contre-épreuves le remplacent par une
  fonction de même signature).
