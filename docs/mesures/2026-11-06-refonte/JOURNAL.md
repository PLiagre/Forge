# Journal de la refonte du 6 novembre 2026

> Le journal de travail de la session de refonte (mode direct). Si le contexte
> se résume, on repart d'ici. Mesures et commandes : [RAPPORT.md](RAPPORT.md).

## La consigne, en bref

1. Mesurer depuis `origin/master` (worktree `.atelier/direct/refonte-mesures`,
   branche `direct/refonte-mesures`, base `b6e15ae6`) : le monde sans joueur
   (graine 0, IA) à 90, 365 et 3 650 jours ; le tick avec et sans IA, et son
   profil ; la chaîne (gh, journal du pilote sur le VPS, en lecture seule).
   Tout dans `RAPPORT.md`, avec un plan classé.
2. Demander au propriétaire, en une fois (quatre questions au plus) : les
   jauges, l'arrêt de la chaîne, J4, les événements à choix. **Rien
   d'écrit avant sa réponse.**
3. Réécrire, une PR `direct/<sujet>` par étape : la vision ; la soudure et le
   tick ; le registre des modificateurs ; le pays et ses jauges ; les
   bâtiments de province ; la chaîne pour Claude seul ; le cap et ses issues.

## Fait

- 06/11 matin : lecture d'AGENTS.md, CAP.md, VISION.md, WORKFLOW.md,
  atelier.toml, du journal #1014. Worktree de mesure créé.
- Monde, graine 0, IA active (`scripts/mesure_monde.py`, `brut/monde-ia.json`) :
  au 90e jour Paris 1,1 %, Milan 1,1 %, Le Caire 5,6 % ; au 365e, Paris 0 %,
  Milan 0 %, Florence 5 %, Gand et Bruges 4 %, Le Caire 3,4 %, Constantinople
  97,6 %, Londres 103,4 %, Europe 101,8 % ; au 3 650e, toutes les grandes villes
  à 0 sauf Constantinople (95,9 %) et Londres (86,4 %), Europe 101,8 %, quatre
  échecs à la table du jalon 2, 44 cellules de la table mortes de faim à plus
  de moitié.
- Pourquoi (`scripts/diagnostic_villes.py`, `brut/diagnostic-villes.txt`) :
  Paris a 275 000 habitants pour 66 000 que sa cellule nourrit, il lui manque
  417 t par jour ; le commerce lui en apporte au mieux 41 t par jour (2e mois).
  Ses 5 jours de réserve et son mois de manque tombent en février.
- Expériences (`scripts/experience_monde.py`, sans IA, 365 jours) : 213 jours
  de ration propre pour chaque cellule → aucune cellule de la table à plus de
  moitié de morts de faim (pire Gand 45 %), Paris 50 %, Milan 105 %, Le Caire
  108 % ; même chose avec un transport ×10 : Paris 40 %, Gand 27 %.
- Tick, premier essai (`brut/tick-1.json`, faussé : le monde de 3 650 jours
  tournait en même temps) : sans IA 81 ms, avec IA 375 ms dont `jouer_ia`
  283 ms. Profil : `maisons_de_l_ia` 265 ms par tick, dont
  `cellule_de_capitale` (point dans polygone, `villes._dans_anneau`) et
  `charger_positions` qui relit un JSON à chaque tick.
- Deux sous-agents mesurent la chaîne (gh) et le VPS (pilote.log).

## En cours

- Les mesures (étape 1) : refaire le tick au calme ; attendre les sous-agents.

## Reste, dans l'ordre

1. RAPPORT.md (monde, tick, profil, chaîne, VPS) et plan classé.
2. La question au propriétaire.
3. Les sept PR de l'étape 3.
