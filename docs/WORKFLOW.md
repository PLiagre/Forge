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
 issue « lot »  ──►  CHEF (claude opus, par cursor · secours claude code) ─── brief dans la branche lot/<n>-<slug>, PR brouillon
 (jalon courant, ou le    │ trop gros : découpe en sous-lots · hors de son jalon : bloque
  suivant en avance)      │
                          ▼
                    CODEUR (codex sol · secours cursor grok)   — lot « pc » : le même sur le PC (claude en dernier secours)
                          │ le pilote commit, pousse, capture
                          ▼
                    CI : tests + gitleaks ── rouge ──► CODEUR corrige (2 fois au plus)
                          │ vert
                          ▼
                    RELECTEUR (claude opus, puis par cursor ; codex, puis grok, si un Claude a écrit)
                     ├─ ACCEPTE  ──► fusion automatique (squash) ──► issue « livre »
                     └─ CORRIGER ──► CODEUR corrige (2 fois au plus) ──► puis « bloque »
```

Le **mécanicien** (cursor composer) répare master quand sa CI est rouge et
résout les conflits d'une branche de lot. Le **chroniqueur** (cursor grok, en
lecture seule) écrit le journal chaque matin ; la **boussole** (claude opus,
secours cursor claude-opus) compare chaque lundi les lots livrés à CAP.md.

Le relecteur n'est jamais de la **famille de modèle** qui a écrit le lot :
Claude Code ne porte que des Claude, Codex que des GPT, et Cursor porte tout
(sa famille se lit dans le nom du modèle). Du code écrit par
`cursor/claude-opus-5-5-high` est donc relu par codex, pas par
`claude/claude-opus-5-5`.

**Claude juge, les autres écrivent.** Le plafond de Claude Code a été atteint
le 29 septembre 2026 : il se garde pour la relecture. Le chef reste Claude
Opus, porté d'abord par Cursor ; le code s'écrit avec codex sol, sur le VPS
comme sur le PC, et Claude n'y vient qu'en dernier secours. La ligne du
relecteur laisse toujours au moins deux agents à un lot, quelle que soit la
famille qui l'a écrit : un quota ne le laisse plus sans relecture.

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
| `reserve` | à ranger dans la Réserve ; le pilote l'y range et retire l'étiquette | qui veut, même depuis le téléphone |

## Les jalons suivent CAP.md

Chaque section « ## Jalon n — Titre » de [CAP.md](../CAP.md) est un
milestone « Jn — Titre ». À chaque tour, le pilote crée celui qui manque et
renomme celui dont le titre a changé ; il ne supprime ni ne ferme rien (un
jalon se ferme quand ses lots sont livrés). Changer l'échelle, c'est donc
changer CAP.md en mode direct : les milestones suivent seuls au tour d'après.

La **Réserve** (la section « ## La réserve » de CAP.md) est le milestone des
lots qui ne servent aucun jalon pour l'instant. Son titre ne commence pas par
« J » : le pilote ne la prend jamais pour le jalon courant, et il n'en fait
sortir aucun lot. Un lot y entre par le formulaire (jalon « Réserve »), par
l'étiquette `reserve`, ou à la main ; un jalon qui en a besoin l'en tire.

### La fenêtre de deux jalons

Le pilote prend d'abord dans le jalon courant. Une machine libre qui n'y a
plus rien à prendre (tout est en cours, livré, ou attend une dépendance)
prend dans le **jalon suivant**, jamais plus loin. Le 29 septembre 2026, J1
n'avait plus que des lots `pc` : le VPS attendait sans rien faire que le PC
finisse, alors que J2 ne demande que `sim/`.

Le chef d'un lot pris en avance le sait : son lot ne s'appuie sur rien que le
jalon courant doit encore livrer (ce qui n'est pas sur master n'existe pas) ;
s'il en a besoin, il refuse, et le lot est bloqué avec sa raison. Le journal
annonce ces lots à part, sous « EN AVANCE ». Un lot marqué `reserve` ne se
prend jamais : il sort de son jalon.

### Un jalon qui commence se fait découper

Quand le jalon courant n'a encore aucun lot prêt, en cours ou livré, le
pilote ouvre un lot « Découper le jalon Jn — Titre » (`pret`). Le jalon
suivant se découpe de même, en avance, quand la fenêtre s'ouvre : le courant
a déjà sa découpe ou ses lots, et une machine libre n'y a plus rien à
prendre. Le chef le prend comme un autre, et le découpe d'après la section du jalon dans
CAP.md et d'après [VISION.md](VISION.md) : les lots qu'il faut, dans l'ordre,
le dernier portant la preuve du jalon. Les lots déjà ouverts dans le jalon
passent d'abord (la découpe « dépend » d'eux), et la découpe ne se refait
jamais : son lot porte une marque que le pilote relit. Un jalon qu'on a
lancé à la main, avec un lot `pret`, n'est pas redécoupé.

### Découper un lot trop gros

Le chef découpe en sous-lots (`pret`, même jalon), écrits « Découpé du lot
#N », et ferme le lot d'origine. Un sous-lot garde la machine du lot
découpé, sauf si le chef finit sa ligne par « :: pc » ou « :: vps ». Les
sous-lots se suivent dans l'ordre du chef : chacun dépend du précédent. Un
lot qui « dépend de #N » attend tous les sous-lots de #N (et les leurs, si
un sous-lot est découpé à son tour), pas seulement sa fermeture.

Un lot **en cours** dont une dépendance est encore ouverte redevient `pret`
et rend sa machine ; la reprise le relance quand elle est livrée, essais
remis à zéro.

### Reprendre un lot bloqué

Corriger la cause (en mode direct si elle est dans la chaîne), puis retirer
`bloque` et remettre `pret`. Le pilote décide selon ce qui existe :

- **la PR du lot est ouverte** : le lot est **repris** où il en est. Le pilote
  écrit une marque `reprise` sur la PR et le remet `en-cours`, sans relancer
  le chef ; le travail déjà poussé reste, et les essais du codeur, du chef et
  du relecteur repartent de zéro (ils se comptent depuis la dernière
  reprise) ;
- **pas de PR** (le chef avait échoué ou refusé) : le chef reprend le lot, ses
  essais comptés depuis le dernier blocage.

Pour repartir de zéro avec un nouveau brief : fermer la PR, supprimer sa
branche, puis remettre `pret`.

Remettre `en-cours` à la main ne suffit pas : sans marque de reprise, le
pilote recompte les échecs et rebloque.

## Ce que le pilote retient, et où

Rien en local. Ce que la chaîne a fait vit dans les commentaires de la PR, sous
une marque invisible que le pilote écrit et relit :

```
<!-- atelier {"role": "relecteur", "sha": "…", "verdict": "ACCEPTE", "agent": "claude/claude-opus-5-5"} -->
```

Un tour interrompu ne perd rien : le suivant relit GitHub. Le journal local
(`~/.atelier/journal.jsonl`) ne sert qu'à dire pourquoi la chaîne a attendu.

## Quotas et sessions

Un agent qui répond « quota épuisé » ou « session expirée », ou dont l'outil
ne démarre pas (binaire introuvable : une panne d'installation, pas un échec
du codeur), passe la main à son secours (la suite de sa ligne dans
`atelier.toml`). Si personne ne répond, le lot **attend** : ce n'est pas un
échec, aucun essai n'est compté, le tour suivant réessaie, et une ligne le dit
dans le journal avec la raison de chaque agent. Les clés d'API sont retirées
de l'environnement de chaque agent ; le jeton longue durée de Claude Code se
lit dans `~/.atelier/claude.token` (mode 600).

## Les lots « pc »

Le pilote lance `.github/workflows/lot-pc.yml` par `workflow_dispatch` (jamais
`pull_request` : une fourche ne lance rien sur le PC). Le runner `pc-forge`
travaille dans des worktrees de `D:\Forge` : `.atelier\pilote-pc` (le code de
la chaîne), `.atelier\chantiers\pc` (le lot, avec sa `Library` Unity et une
jonction vers les packs de l'Asset Store). Unity compile la révision poussée
et photographie la scène en Play ; ce qu'il a vu entre dans le compte rendu du
codeur, que lit le relecteur (qui n'a pas Unity), et les images s'y affichent.

**La partie PC n'avance que quand le PC est allumé.** Un PC éteint ou en
veille garde le travail en file chez GitHub ; il part au réveil. Le PC répond
toujours sur la PR : un compte rendu, ou une **attente** (aucun de ses agents
n'a pu répondre, ou le passage a cassé avant) qui ne compte pas comme un essai
et que le pilote renvoie au bout d'une heure. Sans réponse du tout en 24 h, il
renvoie le même travail. Sous Windows, les agents livrés en `.cmd`
(cursor-agent, codex par npm) sont lancés par leur `node.exe`, jamais par
`cmd.exe` : le prompt y serait coupé et interprété. Prouver les agents du PC
là où ils tournent : `gh workflow run sonde-pc.yml -R PLiagre/Forge`.

## Les captures et le journal

Un lot qui touche `jeu/` est photographié par `python3 -m forge` (la carte du
monde) ; un lot `pc`, par Unity. Les images vivent sur la branche orpheline
`journal` et s'affichent par leur adresse `raw.githubusercontent.com`, sur
téléphone comme ailleurs. Chaque matin à 07:15, le journal paraît dans sa
propre issue, épinglée, « Journal du JJ/MM/AAAA » ; celle de la veille se
désépingle et se ferme (la boussole du lundi fait de même). Le pilote relève les faits
(`atelier/journal.py`) : pour chaque lot livré, ce qu'en dit le compte rendu
du codeur, son nombre de passages, le verdict du relecteur et ses captures ;
à part, les changements de la machine (mode direct) ; ce que la chaîne a
vécu, lot par lot, d'après le journal du pilote (attentes et leur raison,
secours, découpes, reprises) ; les lots bloqués et en cours ; le jalon et son
pourcentage (lots fermés / lots du jalon) ; et **ce que le propriétaire doit
faire** (une session à rouvrir, sur le VPS ou le PC, avec sa commande ; le
plafond Claude ; une ligne de veille en échec ; un lot bloqué). Le
chroniqueur écrit trois parties : un bandeau (avancé, bloqué, à faire), ce
qui a changé dans le jeu avec une capture par lot livré (celle de la
révision fusionnée), et aujourd'hui. Le pilote ajoute lui-même l'avancement
du jalon, lot par lot, et les détails de la chaîne, repliés. Un texte qui
sort du gabarit, ou cite une image ou un numéro absent des faits, est
écarté : le pilote écrit alors le journal seul, dans le même gabarit.

## La cadence (VPS, heure de Paris)

| quand | quoi |
|---|---|
| toutes les 2 min | un tour du pilote (au plus un agent ; un tour qui tourne encore fait passer le suivant) |
| 06:45 | la veille : outils, jetons, accès GitHub |
| 07:15 | le journal |
| lundi 07:45 | la boussole |
| 02:30 (PC) | le build Windows de la nuit, dans `D:\Forge\builds\dernier` ; PC en veille, il part au réveil |

Armer : `atelier/crons/atelier-boucle jour`. Arrêter : `atelier-boucle arret`.
Regarder : `atelier-boucle etat`. Installer : [atelier/crons/README.md](../atelier/crons/README.md).

## Quand ça casse

| symptôme | ce que ça veut dire | le geste |
|---|---|---|
| issue `bloque` | trois passages du codeur n'ont pas suffi, un conflit ne s'est pas résolu, ou le chef a refusé | lire la raison en commentaire ; corriger en mode direct, ou reformuler l'issue ; puis remettre `pret` (reprise, ci-dessus) |
| « attente » répétée au journal | quotas épuisés, session expirée, ou outil qui ne démarre pas (la raison de chaque agent est écrite) | `python3 -m atelier veille`, puis `claude setup-token` si c'est la session Claude |
| un lot `pc` n'avance pas | le PC est éteint ou en veille, ou ses agents attendent (marque d'attente sur la PR) | allumer le PC ; `gh workflow run sonde-pc.yml` |
| rien ne bouge | profil `arret`, copie principale hors de master, ou un jalon courant que CAP.md ne décrit pas (le pilote ne découpe que ce que CAP.md décrit) | `atelier-boucle etat` ; ajouter la section du jalon à CAP.md, ou des lots |
| master rouge | le mécanicien ouvre une PR `meca/…` ; s'il ne peut pas, le journal le dit | mode direct |
