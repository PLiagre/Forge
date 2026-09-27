# La chaîne — comment un lot avance sans personne

> Les règles font foi dans [AGENTS.md](../AGENTS.md) ; l'ordre des jalons dans
> [CAP.md](../CAP.md) ; la table des rôles dans [atelier.toml](../atelier.toml)
> (`python3 -m atelier agents`). Ce fichier explique la mécanique.

## En une phrase

Une issue devient une branche et une PR ; le chef l'explique, le codeur la
code, la CI la teste, un relecteur qui ne l'a pas écrite la juge, et `ACCEPTE`
la fusionne toute seule.

## Le schéma

```
 issue « lot »  ──►  CHEF (claude opus) ─── brief dans la branche lot/<n>-<slug>, PR brouillon
 (jalon courant)          │ trop gros : découpe en sous-lots · hors du jalon : bloque
                          ▼
                    CODEUR (codex sol · secours cursor grok)   — lot « pc » : claude sur le PC
                          │ le pilote commit, pousse, capture
                          ▼
                    CI : tests + gitleaks ── rouge ──► CODEUR corrige (2 fois au plus)
                          │ vert
                          ▼
                    RELECTEUR (claude opus ; codex si claude a écrit)
                     ├─ ACCEPTE  ──► fusion automatique (squash) ──► issue « livre »
                     └─ CORRIGER ──► CODEUR corrige (2 fois au plus) ──► puis « bloque »
```

Le **mécanicien** (cursor composer) répare master quand sa CI est rouge et
résout les conflits d'une branche de lot. Le **chroniqueur** (cursor grok, en
lecture seule) écrit le journal chaque matin ; la **boussole** (claude opus)
compare chaque lundi les lots livrés à CAP.md.

## Qui fait quoi

| acteur | fait | ne fait jamais |
|---|---|---|
| le propriétaire | ouvre des issues, lit le journal, travaille en mode direct | valider une PR de lot |
| le pilote (`atelier/pilote.py`) | lit GitHub, décide en fonction pure (`atelier/lots.py`), fait **tous** les gestes : commit, poussée, PR, commentaires, étiquettes, fusion | écrire du code du jeu |
| un agent | édite des fichiers dans le worktree du lot, ou rend un texte | `git commit`, `git push`, `gh` |
| la CI | joue `tests` (jeu + atelier) et `gitleaks` | décider d'entrer |

## Les états d'un lot (étiquettes de l'issue)

| étiquette | veut dire | qui la pose |
|---|---|---|
| `idee` | recensé ; la chaîne le prend après les `pret` de son jalon | le formulaire |
| `pret` | à prendre en premier | le propriétaire, ou le chef en découpant |
| `en-cours` | branche et PR ouvertes | le pilote |
| `bloque` | une décision attend ; la raison est en commentaire | le pilote |
| `livre` | fusionné | le pilote |
| `pc` | demande Unity ou Blender : le travail part sur le PC | le formulaire |

Reprendre un lot bloqué : retirer `bloque`, remettre `pret`.

## Ce que le pilote retient, et où

Rien en local. Ce que la chaîne a fait vit dans les commentaires de la PR, sous
une marque invisible que le pilote écrit et relit :

```
<!-- atelier {"role": "relecteur", "sha": "…", "verdict": "ACCEPTE", "agent": "claude/claude-opus-5-5"} -->
```

Un tour interrompu ne perd rien : le suivant relit GitHub. Le journal local
(`~/.atelier/journal.jsonl`) ne sert qu'à dire pourquoi la chaîne a attendu.

## Quotas et sessions

Un agent qui répond « quota épuisé » ou « session expirée » passe la main à
son secours (la suite de sa ligne dans `atelier.toml`). Si personne ne répond,
le lot **attend** : ce n'est pas un échec, le tour suivant réessaie, et une
ligne le dit dans le journal. Les clés d'API sont retirées de l'environnement
de chaque agent ; le jeton longue durée de Claude Code se lit dans
`~/.atelier/claude.token` (mode 600).

## Les lots « pc »

Le pilote lance `.github/workflows/lot-pc.yml` par `workflow_dispatch` (jamais
`pull_request` : une fourche ne lance rien sur le PC). Le runner `pc-forge`
travaille dans des worktrees de `D:\Forge` : `.atelier\pilote-pc` (le code de
la chaîne), `.atelier\chantiers\pc` (le lot, avec sa `Library` Unity et une
jonction vers les packs de l'Asset Store). Unity compile, photographie la
scène en Play, et les images partent en commentaire de la PR.

## Les captures et le journal

Un lot qui touche `jeu/` est photographié par `python3 -m forge` (la carte du
monde) ; un lot `pc`, par Unity. Les images vivent sur la branche orpheline
`journal` et s'affichent par leur adresse `raw.githubusercontent.com`, sur
téléphone comme ailleurs. Chaque matin à 07:15, le journal est commenté dans
l'issue épinglée « Journal de Forge » : livré hier (avec captures), bloqué et
pourquoi, prévu aujourd'hui, jalon en cours et son pourcentage (lots fermés /
lots du jalon).

## La cadence (VPS, heure de Paris)

| quand | quoi |
|---|---|
| toutes les 10 min | un tour du pilote (au plus un agent) |
| 06:45 | la veille : outils, jetons, accès GitHub |
| 07:15 | le journal |
| lundi 07:45 | la boussole |
| 02:30 (PC) | le build Windows de la nuit, dans `D:\Forge\builds\dernier` |

Armer : `atelier/crons/atelier-boucle jour`. Arrêter : `atelier-boucle arret`.
Regarder : `atelier-boucle etat`. Installer : [atelier/crons/README.md](../atelier/crons/README.md).

## Quand ça casse

| symptôme | ce que ça veut dire | le geste |
|---|---|---|
| issue `bloque` | trois passages du codeur n'ont pas suffi, un conflit ne s'est pas résolu, ou le chef a refusé | lire la raison en commentaire ; corriger en mode direct, ou reformuler l'issue et remettre `pret` |
| « attente » répétée au journal | quotas épuisés ou session expirée | `python3 -m atelier veille`, puis `claude setup-token` si c'est la session Claude |
| rien ne bouge | profil `arret`, copie principale hors de master, ou aucun lot dans le jalon courant | `atelier-boucle etat` |
| master rouge | le mécanicien ouvre une PR `meca/…` ; s'il ne peut pas, le journal le dit | mode direct |
