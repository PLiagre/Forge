# Forge

**Un moteur de simulation historique de l'Europe, de 1400 à 1900 — et le jeu de
grande stratégie qu'on bâtit dessus.**

On commence seigneur d'un domaine : on trace, on bâtit, on nourrit des gens qui
portent le bois sur leur dos. Si l'on réussit, on devient prince, puis
royaume, et le jeu change de registre sans changer de monde : la fiscalité, les
lois, la diplomatie et la guerre prennent le pas sur la charrette. Manor Lords
au départ, Europa Universalis puis Victoria à l'arrivée. **L'ascension est le
jeu**, et il n'y a qu'**une seule simulation**.

| pour savoir | lire |
|---|---|
| où on va, dans quel ordre (les 7 jalons) | [CAP.md](CAP.md) |
| où on en est aujourd'hui | l'issue épinglée **« Journal du … »** du jour |
| ce que le jeu doit devenir | [docs/OBJECTIF.md](docs/OBJECTIF.md) · [docs/VISION.md](docs/VISION.md) |
| comment le monde fonctionne | [jeu/sim/MODELE.md](jeu/sim/MODELE.md) |
| les règles (mode direct en tête) | [AGENTS.md](AGENTS.md) |
| comment la chaîne d'agents avance seule | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| toutes les commandes | [docs/NOTICE.md](docs/NOTICE.md) |

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
| `docs/` | notice, workflow, vision, objectif, briefs des lots, mesures |
| `CAP.md` · `AGENTS.md` · `CLAUDE.md` · `atelier.toml` | le cap, les règles, le branchement de la chaîne |

```
            jeu/data/world-1400.json (la carte, figée)
                           │
                           ▼
                    ┌─────────────┐
                    │  jeu/sim/   │   le moteur : fabrication, extraction, production,
                    │  (Python)   │   commerce, consommation, faim, mort, naissances, migration
                    └──────┬──────┘
                           │  photographie, et bientôt service local (CAP.md, jalon 1)
          ┌────────────────┼────────────────┬────────────────┐
          ▼                ▼                ▼                ▼
    jeu/vues/tableau  jeu/vues/chronique  jeu/vues/relief   3d/unity
    tableau de bord   suite d'instants    carte (forge3d)   le lieu en 3D
```

**Aucune vue ne décide rien.** Elles lisent ; le moteur tourne sans elles.

## Comment le travail avance

Deux façons, et seulement deux.

- **La chaîne**, quand personne n'est là : un lot est une issue du jalon
  courant ; le pilote (VPS, toutes les dix minutes) la fait passer par le chef,
  le codeur, la CI et un relecteur qui ne l'a pas écrite ; `ACCEPTE` fusionne
  tout seul. La table des rôles et de leurs modèles :
  `python3 -m atelier agents`. Détail : [docs/WORKFLOW.md](docs/WORKFLOW.md).
- **Le mode direct**, quand le propriétaire ouvre un agent dans `D:\Forge` ou
  `~/Forge` : une branche `direct/<sujet>`, une PR, fusion automatique sur CI
  verte. Voir [AGENTS.md](AGENTS.md).

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
