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

## Reste, dans l'ordre (arrêt sur quota, 7/11 au soir)

État : PR 1 fusionnée (#1022) ; PR 2 (#1023) et PR 6 (#1024, la chaîne pour
Claude seul) en fusion automatique. Branches de travail poussées sans PR :

1. **PR 3** `direct/modificateurs` (worktree `.atelier/direct/refonte-modificateurs`) :
   après la fusion de #1023, `git rebase --onto origin/master be630e69
   direct/modificateurs`, suite entière (Windows puis WSL : `bash
   /mnt/d/Forge/.atelier/wsl_autres.sh`), PR. 24 épreuves vertes ; sans pose,
   monde et photographie à 365 jours = PR 2 (`96f0ad5d…`, `b2befd1b…`).
2. **PR 4** `direct/pays-et-jauges` (`refonte-pays`), partie de `7c412e00` :
   `git rebase --onto direct/modificateurs 7c412e00 direct/pays-et-jauges` ;
   puis neutraliser les jauges (`sim.jauges.mettre_a_jour` → rien) dans
   l'épreuve d'identité de `test_modificateurs.py` et dans les calibrages de
   `test_prelevement.py` (`_habitants_apres_un_an_calibres`, `_course_departs`) ;
   16 épreuves de `test_pays_et_jauges.py` vertes ; MODELE « Le pays et ses jauges » écrit.
3. **PR 5** `direct/batiments-de-province` (`refonte-batiments`) : `data/batiments.toml`
   et `sim/batiments.py` écrits ; le branchement (`scratchpad/brancher_batiments.py`)
   n'est passé que pour `world.py` : le refaire après le rebase sur la PR 4
   (tick après `_affecter_artisans`, intention `batir_dans_une_province`, IA, `/pays`),
   puis les épreuves (refus avec raison, +10 % en vrais kilos, même graine même monde, IA).
4. **PR 7** : CAP.md réécrit (J4 clos, décision 40 ; #849 #850 → J6 ; #860 → J5 ;
   #851 #419 #508 #962 #960 → Réserve avec leur ligne ; lots de la refonte et
   leurs issues « Demander un lot »), #434 récrit (compétences déjà là).
5. **Réarmer la chaîne** seulement après la PR 7 : `gh variable delete PC_ACTIF
   -R PLiagre/Forge`, puis `ssh hermes-boost 'cd ~/Forge && atelier/crons/atelier-boucle jour'`.
6. Question du monde laissée au propriétaire : recalibrer la part coutumière
   (3 %) sur un monde qui a sa soudure.

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
