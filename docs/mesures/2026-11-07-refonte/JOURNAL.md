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

## Reste, dans l'ordre

1. PR 2 : la soudure (212 jours) et le tick (liste des maisons de l'IA par
   la boucle).
2. PR 3 : le registre des modificateurs.
3. PR 4 : le pays et ses jauges (compétences des chefs de 1400, niveau 2).
4. PR 5 : les bâtiments de province.
5. PR 6 : la chaîne pour Claude seul.
6. PR 7 : le cap, ses issues, J4 clos (décision 40), Réserve.
7. Réarmer la chaîne (`gh variable delete PC_ACTIF`, `atelier-boucle jour`).

## Décisions techniques prises seul (et pourquoi)

- Soudure = 212 jours de ration des habitants de la cellule (jusqu'au
  1er août), sans retrait de perte : le moteur ne fait pas pourrir le grain
  des foyers (niveau 3) ; partage entre lieux inchangé (par surface), la
  mesure ne voit aucune différence.
- Tick : la boucle (service, forge, `python -m sim`) calcule une fois la
  liste des maisons de l'IA et la passe à `jouer_ia`. Pas de cache dans le
  monde ni dans un module : les tests exigent `monde.__dict__` inchangé
  après `decider_intentions`, et `world.py` ne nomme pas les capitales.
  `verifier_base` reste sans cache (ses contre-épreuves le remplacent par une
  fonction de même signature).
