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
 issue « lot »  ──►  CHEF (Claude Code, opus, high · secours Codex, gpt-6-astra, puis gpt-6-sol, high) ─── brief dans la branche lot/<n>-<slug>, PR brouillon
 (jalon courant, ou le    │ trop gros : découpe en sous-lots · hors de son jalon : bloque
  suivant en avance)      │
                          ▼
                    CODEUR (Codex, gpt-6-sol, high · secours Cursor, grok-high)   — lot « pc » : Claude Code, opus, high sur le PC (secours Cursor, grok-high)
                          │ le pilote commit, pousse, capture
                          ▼
                    CI : tests + gitleaks ── rouge ──► CODEUR corrige (2 fois au plus ; la 2e : RENFORT)
                          │ vert
                          ▼
                    RELECTEUR (Claude Code, opus, high ; puis Codex astra, Codex sol, Cursor grok-high : jamais la famille qui a écrit)
                     ├─ ACCEPTE  ──► fusion automatique (squash) ──► issue « livre »
                     └─ CORRIGER ──► CODEUR corrige (2 fois au plus ; la 2e : RENFORT) ──► puis « bloque »
```

Le **renfort** (Codex, gpt-6-astra, high ; puis les agents du codeur) fait
le dernier passage du codeur d'un lot du VPS avant blocage : la 2e correction,
avec `corrections_max = 2`. Deux passages n'ont pas suffi, un modèle plus fort
reprend, avec la revue ou l'erreur de CI sous les yeux. Il ne sert qu'à ces
lots-là, donc peu du quota Plus d'Astra ; épuisé, Sol reprend la main. Sa
marque reste celle du codeur : le passage compte, et la famille GPT ne relit
pas le lot. Les lots du PC n'ont pas de renfort (Codex n'y écrit pas, Claude
Opus y code déjà).

Le **mécanicien** (Codex, gpt-6-sol, medium ; secours Cursor, composer-2.5) répare master quand sa CI est rouge
et résout les conflits d'une branche de lot. Le **chroniqueur** (Cursor,
grok-4.7-high, en lecture seule) écrit le journal chaque matin ; la
**boussole** (Claude Code, opus, xhigh ; secours Codex, gpt-6-astra, puis gpt-6-sol, high) compare
chaque lundi les lots livrés à CAP.md.

**Chaque agent dit son harnais, son modèle et son effort** :
`harnais/modèle@effort` dans [`atelier.toml`](../atelier.toml), et
`python3 -m atelier agents` en fait la table. L'effort passe à chaque harnais
par son chemin : `--effort` pour Claude Code (low, medium, high, xhigh, max),
`model_reasoning_effort` pour Codex (minimal, low, medium, high, xhigh) ;
Cursor n'a pas d'option, l'effort est dans le nom du modèle
(`grok-4.7-high` s'écrit `@high`, et `@defaut` dit qu'un modèle Cursor n'en
propose pas). Un effort qu'un harnais ne connaît pas, ou qui ne correspond pas
au nom d'un modèle Cursor, se refuse au chargement : Claude Code, lui,
l'ignorerait sans rien dire (mesuré le 29 septembre 2026). Chaque commentaire
de la chaîne nomme l'agent avec son effort (`codex/gpt-6-sol@high`).

**Claude ne passe que par Claude Code**, jamais par Cursor ni un autre
harnais : c'est le choix du propriétaire, et le chargement de `atelier.toml`
refuse la ligne qui en mettrait un.

Le relecteur n'est jamais de la **famille de modèle** qui a écrit le lot
(Claude, GPT, Grok, Composer ; elle se lit dans le nom du modèle) : il relit
avec l'agent suivant de sa ligne.

**Claude juge, les autres écrivent, sauf sur le PC.** Le plafond de Claude
Code a été atteint le 29 septembre 2026 : il se garde pour le chef, la
relecture et les lots du PC. Le code du VPS s'écrit avec Codex GPT-6 Sol, le
meilleur score par dollar mesuré ; GPT-5.6 Sol le suit partout où GPT-6 sert,
car un Codex trop ancien refuse GPT-6, et ce refus passe la main sans brûler
d'essai. Les lots du PC, peu nombreux et chers quand
ils ratent, ont Claude Opus en tête et Cursor grok-high en secours (le bac à
sable de Codex n'y démarre pas) : choix du propriétaire, 29 septembre 2026.
GPT-6 Astra ne passe qu'en secours (chef, relecteur, boussole) : l'abonnement
ChatGPT Plus ne lui donne que quelques dizaines de messages toutes les cinq
heures ; il relit le code de Claude, et GPT-6 Sol prend la suite quand son
quota est épuisé, au relecteur comme au chef et à la boussole. La ligne du relecteur laisse toujours au moins deux agents à
un lot, quelle que soit la famille qui l'a écrit : un quota ne le laisse plus
sans relecture.

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
découpé, sauf si le chef finit sa ligne par « :: pc » ou « :: vps ». Chaque
ligne dit aussi ce qu'elle attend : « :: après 1, 3 » (les rangs, dans la
liste, des sous-lots dont elle a besoin), « :: après rien » (elle part tout
de suite) ; sans « après », elle attend la précédente. Les sous-lots qui ne
s'attendent pas avancent en même temps. Le dernier d'une découpe de jalon
porte la preuve : il attend tous les autres. Une ligne qui attend un
sous-lot placé après elle rend la découpe illisible, et rien n'est créé. Un
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

## Plusieurs lots en même temps

Le cron lance un tour toutes les deux minutes, même si d'autres tournent
encore ; chaque tour n'invoque qu'un agent, et un tour dont l'agent code
pendant quarante minutes n'empêche plus les autres lots d'avancer. Ce qui
ne doit se faire qu'une fois se tient par des verrous de fichier
([`atelier/verrous.py`](../atelier/verrous.py), dans `~/.atelier/verrous`),
que le système rend seul quand un tour meurt :

| verrou | ce qu'il garde |
|---|---|
| `lot-<n>` | un lot n'avance que dans un tour à la fois |
| `decider` | relire GitHub, ranger, reprendre, livrer, choisir le lot suivant : un tour après l'autre, en quelques secondes |
| `git` | un geste git à la fois sur le dépôt partagé (les worktrees partagent ses références) |
| `captures` | une publication à la fois sur la branche `journal` (le journal du matin compris) |
| `meca` | un mécanicien de master à la fois |
| `outil-<outil>-<i>` | les places d'un outil, jusqu'à son plafond |
| `tour-<i>` | les places des tours : si GitHub ne répond plus, ils ne s'empilent pas |

Les réglages sont dans [`atelier.toml`](../atelier.toml) :

- `[machines]` : combien de lots chaque machine fait avancer en même temps
  (le VPS en tient plusieurs, chacun dans son worktree ; le PC n'a qu'un
  runner). Un lot dont un autre tour écrit le brief compte déjà.
- `[outils]` : combien d'agents de chaque outil tournent ensemble. Un outil
  plein passe la main au secours de sa ligne, comme un quota : le troisième
  lot du VPS code avec cursor grok pendant que codex en tient deux. Si
  personne n'est libre, le lot attend, sans compter d'essai.

Deux lots qui touchent les mêmes fichiers finissent en conflit : le
mécanicien le résout. Le chef les fait s'attendre quand il le voit.
`atelier-boucle etat` montre les verrous en vol.

## Ce que le pilote retient, et où

Rien en local. Ce que la chaîne a fait vit dans les commentaires de la PR, sous
une marque invisible que le pilote écrit et relit :

```
<!-- atelier {"role": "relecteur", "sha": "…", "verdict": "ACCEPTE", "agent": "claude/claude-opus-5-5"} -->
```

Un tour interrompu ne perd rien : le suivant relit GitHub. Le journal local
(`~/.atelier/journal.jsonl`) ne sert qu'à dire pourquoi la chaîne a attendu.

## Quotas et sessions

Un agent qui répond « quota épuisé » ou « session expirée », dont l'outil
ne démarre pas (binaire introuvable : une panne d'installation, pas un échec
du codeur), ou dont le harnais refuse l'appel (une option ou une valeur de
réglage qu'il ne connaît pas : sa version ou sa ligne est en cause, le journal
le dit), passe la main à son secours (la suite de sa ligne dans
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
| toutes les 2 min | un tour du pilote (au plus un agent), même si d'autres tournent encore : un par lot en cours, voir « Plusieurs lots en même temps » |
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
