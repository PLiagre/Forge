# AGENTS.md — les règles, en une page

Forge est un jeu de grande stratégie sur l'Europe de 1400 : une carte à la
manière d'Europa Universalis, une ville bâtie à la main à la manière de Manor
Lords, et plus tard la bataille à la manière de Total War, dans **une seule
simulation** ([docs/VISION.md](docs/VISION.md)). On avance par **paliers
jouables d'une semaine** ([CAP.md](CAP.md)). Tout s'écrit en **français
clair**.

## 1. La chaîne — elle fait le travail de la semaine

Cinq rôles, répartis par niveau de jugement. Celui qui conçoit un lot le
construit. Le détail : [docs/WORKFLOW.md](docs/WORKFLOW.md).

| rôle | modèle | il fait | il ne fait jamais |
|---|---|---|---|
| **le CTO** | Fable | le samedi, tire les lots du palier de ce que le propriétaire a dit ; en semaine, tranche les questions, débloque ou redécoupe un lot, relit ce qui touche le cœur du moteur, répond de la démo du vendredi. Appelé à ces moments, il ne surveille pas. | coder |
| **le chef de lot** | Opus | conçoit, écrit le plan dans la PR, code le difficile, confie le reste, tient la PR jusqu'à la fusion ; mène aussi les lots de la ville 3D | relire son propre lot |
| **le développeur** | Sonnet | les tâches bornées que le chef lui confie, dans la session du chef ; mène seul les lots simples (données, écran courant) | décider d'une règle du monde |
| **le relecteur** | Opus, autre session, lecture seule | lit la fiche et le diff, rejoue des tests, rend un verdict | écrire |
| **le lecteur** | Haiku | résume un journal de CI, écrit le journal du matin | juger : ni verdict, ni tri d'un blocage |

- **Un lot = une issue = une session = une PR.** La session du chef est
  reprise à chaque étape et à chaque correction, jamais relancée à froid.
- **Les agents éditent des fichiers ou rendent un texte.** Commit, poussée,
  PR, commentaire, étiquette et fusion appartiennent au pilote
  (`python3 -m atelier tour`, sur le VPS).
- **Un lot ne touche jamais** `atelier/`, `.github/`, `atelier.toml`,
  `AGENTS.md`, `CLAUDE.md`, `CAP.md` : le pilote retire ces changements.
- **Aucune question n'attend le propriétaire pendant la semaine.** Le CTO
  prend le choix réversible, le note dans « à revoir samedi », et le lot
  continue. Seuls l'irréversible, l'argent et les droits lui arrivent tout de
  suite.
- **Ce que le propriétaire écrit sur une issue suit le lot** : le chef et le
  relecteur le reçoivent comme une consigne, avec ses raisons.
- Les rôles, leurs modèles et leurs délais : `python3 -m atelier agents`.
  Changer un rôle de modèle, c'est changer une ligne de
  [`atelier.toml`](atelier.toml).

## 2. Le mode direct — la refonte, puis les réparations

Quand le propriétaire ouvre un agent dans `D:\Forge` (PC) ou `~/Forge` (VPS)
pour refondre ou réparer, l'agent modifie directement :

1. une branche `direct/<sujet>` partie de `origin/master`, dans un worktree
   (`git worktree add .atelier/direct/<sujet> -b direct/<sujet> origin/master`) :
   la copie principale reste sur master, c'est de là que tourne le pilote ;
2. une PR, puis `gh pr merge --auto --squash` : elle entre seule sur CI verte ;
3. avant de commencer, il regarde les lots en cours
   (`gh pr list --search "head:lot/"`) et prévient si l'un touche les mêmes
   fichiers.

Le travail du jeu passe par la chaîne. Seul le mode direct touche `atelier/`,
`.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md` et `CAP.md`.

## 3. Les principes du jeu, non négociables

Leur raison est dans [docs/VISION.md](docs/VISION.md), dans le même ordre.

1. **Une seule simulation** : `jeu/sim/`. Les vues (carte, ville, tableau)
   lisent ; elles ne décident jamais un nombre. La bataille se calcule dans
   `sim/` avec les hommes et le terrain du monde, et lui rend ses pertes.
2. **Des modificateurs partout, sur un monde physique.** Un modificateur a
   un nom, une source, une cible, une grandeur du moteur, une valeur, une
   durée ; il change un taux, ne remplace pas la cause qu'il nomme et ne crée
   jamais un kilo ni une pièce. Ses chiffres vivent dans `jeu/data/`.
3. **L'économie est physique.** Tout kilo et toute pièce ont une origine, un
   transport, un stockage, une destination.
4. **L'IA a les outils du joueur.** Tout geste est une intention déposée dans
   `sim/` ; l'IA passe par le même chemin, sans bonus. Un geste de jeu qui
   n'existe qu'en 3D n'existe pas.
5. **Les rails posent un fait, jamais une issue.**
6. **Chaque décision pèse.** Les gestes demandés au joueur par année de jeu
   ne grandissent pas avec son royaume ; ce qui se répète se délègue.
7. **Réel quand on sait, plausible sinon.** Niveau 1 : juste dans les grandes
   lignes, obligatoire. Niveau 2 : plausible, jamais sourcé. Niveau 3 : pas
   simulé. Toute fiche de lot qui touche le monde dit son niveau.
8. **Une capacité n'existe que si sa preuve peut échouer.** Prouver le rouge
   d'abord ; un échantillon vide échoue. **Un changement du monde met à jour
   les tests qu'il touche, dans la même PR, en disant pourquoi** : un test
   juge le monde livré, jamais un « monde d'avant » gardé pour lui. Les
   longues preuves (un an, dix ans) tournent la nuit et ne bloquent pas une
   fusion.

`cell_id` est la seule clé spatiale ; ce qui s'en dérive (province, bourg,
lieu) ne se stocke pas comme une seconde clé ([jeu/sim/MODELE.md](jeu/sim/MODELE.md)).

## 4. Les règles payées par un vrai défaut

- `py` sur Windows, `python3` sur Linux, jamais `python` nu.
- Un contrôle **dérive** sa référence des données ; `-1` veut dire « non
  calculé », `0` est une mesure. Une absence de donnée se **déclare**.
- **Jouer les tests de ce qu'on touche avant de rendre la main**, jamais la
  suite entière ni une simulation longue sur le VPS (deux processeurs).
- **Regarder les captures et jouer le build soi-même** : des suites vertes
  ont laissé passer des défauts visibles à l'œil.
- **Un commentaire dit ce que le code fait et la contrainte qu'il respecte**,
  jamais une date, un numéro de lot, une décision ou un auteur.
- Sous `bash -e` (la CI), un code de retour se lit par `cmd || code=$?`.
- **Jamais un pack de l'Asset Store dans git** (le dépôt est public) :
  `**/Assets/Vendor/` est ignoré.
- Jamais de force-push sur master ; jamais de secret affiché ni committé.

## 5. Où vit quoi

| chemin | quoi | ses règles |
|---|---|---|
| `jeu/` | le jeu en Python : `sim/` (le moteur), `data/` (la carte figée et les chiffres), `vues/`, `forge/` (la commande de bout en bout), `ville/` (le contrat avec Unity) | [jeu/sim/CLAUDE.md](jeu/sim/CLAUDE.md) |
| `3d/` | `unity/` (le projet unique : la carte, l'interface, la ville du désert), `local3d/` (Blender), `archives/` (les prototypes qui dorment) | [3d/unity/CLAUDE.md](3d/unity/CLAUDE.md) |
| `atelier/` | la chaîne : le pilote, les rôles, le journal ; `crons/` pour le VPS | [atelier/CLAUDE.md](atelier/CLAUDE.md) |
| `pc/` | les lanceurs Windows | |
| `docs/` | la vision, le workflow, l'architecture, la direction artistique | |

Les commandes pour tester et lancer le jeu : [CLAUDE.md](CLAUDE.md).
