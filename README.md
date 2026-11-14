# Forge

**Un jeu de grande stratégie sur l'Europe réelle, de 1400 à 1900, bâti sur une
seule simulation.**

On joue comme dans Europa Universalis IV : le monde de 1400 tourne seul, et on
prend la tête d'un pays réel — du royaume au petit seigneur — qu'on fait
évoluer depuis la carte, le temps filant ou en pause. La terre se gagne et se
perd par la guerre, l'héritage, le mariage, l'argent et la révolte, contre des
dynasties que joue une IA qui a exactement les mêmes outils. Sa capitale peut
s'ouvrir en 3D, pour la voir vivre et la bâtir à la main. On perd quand le
pays n'a plus de terre. Ce qui n'existe nulle part ailleurs, c'est un Europa
Universalis dont le monde est simulé : des modificateurs partout, comme dans
EU4, et des jauges du pays à nos noms, mais sous eux des gens, des kilos et
des causes — un moulin à +10 % récolte vraiment 10 % de grain en plus, qui se
transporte et se mange —, dans **un seul monde**.

| pour savoir | lire |
|---|---|
| où on va, dans quel ordre (les paliers d'une semaine) | [CAP.md](CAP.md) |
| où on en est aujourd'hui | l'issue épinglée **« Journal du … »** du jour |
| ce que le jeu doit devenir | [docs/VISION.md](docs/VISION.md) |
| comment le monde fonctionne | [jeu/sim/MODELE.md](jeu/sim/MODELE.md) |
| les règles, en une page | [AGENTS.md](AGENTS.md) |
| la semaine, les rôles, le chemin d'un lot | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| tester et lancer le jeu | [CLAUDE.md](CLAUDE.md) |

## Essayer en une minute

```bash
cd jeu
python3 -m forge --ticks 365 --seed 0 --sortie sortie
```

Une année simulée et cinq fichiers : `monde.json` (la photographie, seule
source des vues), `carte.png`, `tableau.svg`, `planche.html`, `resume.json`.
Le moteur ne dépend de rien (bibliothèque standard) ; la carte demande `numpy`
et `pillow`.

Sur le PC Windows : `pc\Ouvrir_Unity.cmd` ouvre le projet Unity sur le ksar du
désert, `pc\Jouer.cmd` lance le dernier build de la nuit, `pc\Tests.cmd` joue
les tests du jeu et vérifie les lanceurs.

## Le dépôt

| dossier | ce qu'il contient |
|---|---|
| `jeu/` | le jeu en Python : `sim/` (le moteur, un tick = un jour), `vues/` (tableau, chronique, relief), `forge/` (la commande de bout en bout), `ville/` (le contrat avec Unity), `data/` (la carte figée de 596 cellules) |
| `3d/` | `unity/` (le projet Unity unique, kit du désert), `local3d/` (le pilotage de Blender), `archives/` (les prototypes qui dorment, intacts) |
| `atelier/` | la chaîne d'agents : le pilote, les rôles, le journal ; `crons/` pour le VPS |
| `pc/` | les lanceurs Windows |
| `docs/` | la vision, le workflow, la direction artistique |
| `CAP.md` · `AGENTS.md` · `CLAUDE.md` · `atelier.toml` | le cap, les règles, le branchement de la chaîne |

```
            jeu/data/world-1400.json (la carte, figée)
                           │
                           ▼
                    ┌─────────────┐
                    │  jeu/sim/   │   le moteur : fabrication, extraction, production,
                    │  (Python)   │   commerce, consommation, faim, mort, naissances, migration
                    └──────┬──────┘
                           │  photographie, et service local
          ┌────────────────┼────────────────┬────────────────┐
          ▼                ▼                ▼                ▼
    jeu/vues/tableau  jeu/vues/chronique  jeu/vues/relief   3d/unity
    tableau de bord   suite d'instants    carte (forge3d)   le lieu en 3D
```

**Aucune vue ne décide rien.** Elles lisent ; le moteur tourne sans elles.

## Comment le travail avance

- **La chaîne** fait le travail de la semaine : le samedi, le propriétaire
  joue la démo et dit ce qu'il veut ; le CTO en tire les lots du palier, un
  par piste au moins ; un chef de lot conçoit et construit chacun, dans une
  seule session, avec un développeur pour les tâches bornées ; un relecteur
  qui ne l'a pas écrit rend son verdict, et `ACCEPTE` fusionne tout seul. La
  table des rôles et de leurs modèles : `python3 -m atelier agents`. Détail :
  [docs/WORKFLOW.md](docs/WORKFLOW.md).
- **Le mode direct** ne sert qu'à refondre et à réparer, quand le
  propriétaire ouvre un agent dans `D:\Forge` ou `~/Forge` : une branche
  `direct/<sujet>`, une PR, fusion automatique sur CI verte. Voir
  [AGENTS.md](AGENTS.md).

## Le monde, en chiffres

| | |
|---|---|
| étendue | Irlande → Anatolie, Norvège → Alexandrie (EPSG:3035) |
| cellules | 596, 11 186 km² en moyenne ; 1 364 arêtes ; 50 provinces |
| relief | 322 plaines · 162 collines · 77 montagnes · 20 marais · 15 hautes montagnes |
| gisements | 27 |
| un tick du monde entier | 42 ms (PC, 27 septembre 2026) ; une année en 15 s |

La carte est **figée** : un seul fichier, jamais régénéré. Fidélité déclarée :
niveau 1 (juste dans les grandes lignes) pour la côte, le relief et les
gisements ; niveau 2 (plausible, jamais sourcé) pour tout ce que le jeu en
déduit. La population initiale est un proxy dérivé de ce que la terre produit,
et le modèle le dit.
