# Forge

**Un moteur de simulation historique de l'Europe, de 1400 à 1900 — et le jeu de
grande stratégie qu'on bâtit dessus.**

On commence seigneur d'un domaine : on trace, on bâtit, on nourrit des gens qui
portent le bois sur leur dos. Si l'on réussit — héritage, mariage, conquête —
on devient prince, puis royaume, et le jeu change de registre sans changer de
monde : la fiscalité, les lois, la diplomatie et la guerre prennent le pas sur
la charrette. Manor Lords au départ, Europa Universalis puis Victoria à
l'arrivée. **L'ascension est le jeu.**

| pour savoir | lire |
|---|---|
| ce que le jeu doit devenir | [OBJECTIF.md](OBJECTIF.md) |
| ce que le moteur promet | [VISION.md](VISION.md) |
| comment le monde fonctionne | [sim/MODELE.md](sim/MODELE.md) |
| où on en est, et dans quel ordre on avance | [ROADMAP.md](ROADMAP.md) |
| comment s'en servir | [docs/NOTICE.md](docs/NOTICE.md) |
| comment le travail avance tout seul | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| les règles, pour tous | [AGENTS.md](AGENTS.md) |

---

## Essayer en une minute

```bash
python3 -m forge --ticks 365 --seed 0 --sortie sortie
```

Une année simulée, en une vingtaine de secondes, et cinq fichiers :

```
sortie/monde.json      la photographie — la seule source des trois vues
sortie/carte.png       la statistique en plan, coloriée par une grandeur
sortie/tableau.svg     le tableau de bord, en preuve dessinée
sortie/planche.html    la chronique : la suite des instants
sortie/resume.json     ce que la commande a mesuré
```

Le moteur seul ne dépend de rien — bibliothèque standard uniquement. La carte
demande `numpy` et `pillow` ; le rendu 3D demande `forge3d` et un GPU, et refuse
proprement quand il n'y en a pas.

---

## Comment c'est fait

```
                       data/world-1400.json
                       (la carte, figée)
                                │
                                ▼
                         ┌─────────────┐
                         │    sim/     │  le moteur — un tick = un jour
                         │  (Python)   │  fabrication, extraction, production,
                         └──────┬──────┘  commerce, consommation, faim,
                                │         mortalité, natalité, migration
                                ▼
                          snapshot JSON        ← la photographie du monde
                                │
              ┌─────────────────┼─────────────────┬──────────────┐
              ▼                 ▼                 ▼              ▼
        vues/tableau/    vues/chronique/    vues/relief/      unity/
        tableau de bord  planche + bobine   carte de          la ville
        2D web           (suite d'instants) statistique       jouable
                                            (forge3d)
```

**Aucune vue ne décide rien.** Elles lisent une photographie et l'affichent. Le
moteur tourne sans elles : `python3 -m sim` n'a besoin d'aucune vue, et aucune
vue ne parle au moteur.

| dossier | ce qu'il fait |
|---|---|
| `sim/` | le moteur. Un tick = un jour. Ne dépend de rien. |
| `data/` | la carte figée et les centres de provinces |
| `vues/tableau/` | tableau de bord 2D web, sur `GET /dashboard.json` |
| `vues/chronique/` | la suite des instants : planche HTML et bobine `.webm` |
| `vues/relief/` | la carte de statistique, et le rendu 3D par forge3d |
| `forge/` | la commande qui relie tout : simuler, photographier, afficher |
| `outils/` | l'intégration qui **décide** — et n'écrit jamais sur GitHub |
| `.github/scripts/` | l'intégration qui **fait** le geste |
| `atelier/` | l'invocation des agents : cartes, verrous, worktrees |
| `briefs/` | les briefs, seule source d'instruction d'un lot |
| `ville/` | le contrat de la vue ville : schéma JSON, exemples, autorité |
| `unity/` | les paquets Unity de la vue ville (URP 6000.0.43f1) |
| `fabrique/` | l'Asset Factory : Blender **hors** Unity, recettes déterministes |

---

## Le monde, en chiffres mesurés

| | |
|---|---|
| étendue | Irlande → Anatolie, Norvège → Alexandrie |
| projection | EPSG:3035 (lon/lat WGS84 conservés en référence) |
| surface | 6 667 147 km² |
| cellules | 596, dont 11 186 km² en moyenne |
| arêtes d'adjacence | 1 364 |
| provinces nommées | 50 |
| relief | 322 plaines · 162 collines · 77 montagnes · 20 marais · 15 hautes montagnes |
| gisements | 27 |
| population à t0 | 36 969 739 |
| coût d'une année simulée | ~21 s |

La carte est **figée** : un seul fichier, jamais régénéré. Sa fidélité est
déclarée — niveau 1 (« juste dans les grandes lignes ») pour le trait de côte,
le relief et les gisements ; **niveau 2, plausible et jamais sourcé**, pour tout
ce que le jeu en déduit. La population initiale n'est pas une donnée
historique : c'est un proxy dérivé de ce que la terre produit, et le modèle le
dit lui-même.

---

## Ce que le monde sait faire

Le relief module le rendement d'une cellule et le débit d'une arête. Le climat
joue par la durée du jour, donc par la saison. Les gisements produisent des
kilos, et une part des habitants cesse de cultiver pour extraire — c'est le
premier métier. Le commerce transporte n'importe quelle marchandise, par terre
et par mer. La population naît, meurt de faim, et migre vers les voisines en
surplus.

Rien de tout cela n'est un script. Il n'existe nulle part de règle disant « si
famine alors +20 % de criminalité » : les gens ont faim, ils cherchent à
manger, et ce qui suit **émerge**.

Depuis, la matière première se **façonne** en objet, le monde porte sa **date**
depuis 1400, et le **bourg** est photographié puis affiché.

### Ce qu'il ne sait pas encore faire

- **Se subdiviser** — une cellule fait 11 186 km², c'est une région, pas un
  lieu. Tant qu'un lieu n'a pas d'identité stable, la ville ne se joue pas.
  C'est le lot pivot du projet.

---

## D'où vient ce dépôt

Trois dépôts et un outil orphelin y ont été réunis.

| origine | ce qu'elle a apporté |
|---|---|
| **ForgeHistory** | le moteur, la carte, les trois vues, la chaîne d'intégration, les briefs |
| **VictoriaCityLab** | les paquets Unity, le contrat de la vue ville, la fabrique d'assets, 40 lots |
| **forge3d** | rien — c'est un fork intact de [`milos-agathon/forge3d`](https://github.com/milos-agathon/forge3d), MIT/Apache-2.0, consommé comme **dépendance épinglée** et jamais recopié |
| **ForgeAtelier** | l'invocation des agents, qui n'était un dépôt nulle part : une branche détachée d'un côté, une copie vendorisée de l'autre |

La fusion a réparé un défaut que personne n'avait chiffré : le monde amorçait
**1,45 bouche pour chaque bouche que sa terre nourrit** et perdait 86 % de ses
habitants la première année simulée. La population d'une cellule est maintenant
dérivée de ce que cette cellule produit. Le détail est dans
[ROADMAP.md](ROADMAP.md).

---

## Comment le travail avance

Le propriétaire donne une direction. Le reste avance sans lui.

Une fiche entre au registre. Un **briefer** écrit le brief. Un **coder**
l'exécute. La **CI** joue les contrôles. Un **relecteur** — jamais l'auteur —
approuve sur la révision courante. L'**intégration** fusionne, une PR à la
fois, rejouée sur le dernier `master`.

Trois choses seulement restent au propriétaire : donner des directions,
reprendre ce qui est tombé, et fusionner ce qui n'est pas un lot. Le schéma
complet est dans [docs/WORKFLOW.md](docs/WORKFLOW.md).

Ce n'est plus une intention : trois lots ont traversé la chaîne entière sans
qu'une main intervienne — 054 le 17 septembre 2026, 049 le 19, 053 le 20. Dans
chaque cas le pilote a posé la carte à 07:00, le coder a ouvert sa PR à 07:30,
le relecteur a approuvé à 09:00 et l'intégration a fusionné dans la foulée.

---

## Les règles, en trois phrases

**Une capacité n'existe que si sa preuve peut échouer.** Un test qui ne peut pas
rougir ne prouve rien, et un échantillon vide échoue au lieu de passer en
silence.

**L'absence de données ne s'invente pas.** Elle se déclare, à l'endroit où elle
manque — c'est pourquoi une lecture sans donnée refuse au lieu de rendre zéro.

**Celui qui a écrit le code ne dit pas s'il est recevable.** C'est une règle
mécanique, pas une politesse : l'approbation doit venir d'une connexion qui n'a
écrit aucun des commits, sur la révision courante.

Le reste vit dans [AGENTS.md](AGENTS.md), et rien ne le paraphrase.
