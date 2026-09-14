# crons/ — la machine qui fait tourner la chaîne

Le reste du dépôt décide. Ici, on réveille.

`outils/` dit **qui entre dans `master`**, `.github/scripts/` **pose le
geste**, `atelier/` dit **quel agent à quelle étape avec quel prompt**.
Aucun des trois n'a d'horloge. Ces scripts-là sont l'horloge : ils vivent
sur une machine allumée, ils réveillent un rôle, ils rangent sa carte, et
ils s'arrêtent.

C'est la seule pièce de la chaîne qui a besoin d'une machine à soi. C'est
donc elle qu'on installe sur le VPS — et c'est tout ce qu'on y installe.

---

## Tout installer, en une commande

Sur le serveur :

```bash
git clone https://github.com/PLiagre/Forge.git ~/Forge
~/Forge/atelier_meta/crons/installer.sh
```

C'est tout. L'installateur pose les arbres des rôles, la configuration,
le cron et la commande à taper, puis il démarre. Il se rejoue sans
risque : ce qui est déjà là est laissé en place.

La seule chose qu'il ne peut pas faire à ta place, c'est **connecter les
agents** — une session s'ouvre à la main, une fois. Il te le dit à la
fin, et seulement si ça manque.

Ensuite, quatre commandes, et tu n'en tapes jamais d'autre :

| commande | effet |
|---|---|
| `atelier-boucle etat` | où ça en est : profil, prochain réveil, ce qui tourne, et ce que la veille de ce matin a vu |
| `atelier-boucle arret` | tout arrêter. Attend le tour en cours au lieu de le couper |
| `atelier-boucle jour` | repartir : treize réveils, de 07:00 à 21:30 |
| `atelier-boucle atelier` | la boucle de banc : quatre rôles en quatre minutes, zéro quota |

Les journaux sont dans `~/.atelier/logs/`, un fichier par rôle.

### Pourquoi ça ne demande jamais `sudo`

Le cron est celui de ton compte, pas celui de root, et il ne porte
qu'une ligne : « appelle le répartiteur, chaque minute ». Tout le reste —
la cadence, l'arrêt, le redémarrage — est un fichier que tu écris.
**Ce qu'on ne peut pas désarmer seul, on ne l'arme pas.**

## Connecter Claude sur un serveur sans écran

C'est la seule étape qui ne s'automatise pas, et elle se fait une fois.

```bash
claude setup-token        # jeton longue durée, pour une machine sans écran
claude auth status --text # vérifier
```

`setup-token` affiche une adresse. Ouvre-la dans le navigateur de ton
PC — même en SSH, c'est un simple copier-coller — autorise, et rends le
code au terminal. Le jeton reste ; le cron n'a plus jamais à se
reconnecter.

**Ne pose jamais `ANTHROPIC_API_KEY`.** Une clé d'API bascule la facture
de l'abonnement vers la facturation à l'unité. `tour.sh` retire les trois
clés (`ANTHROPIC_API_KEY`, `CURSOR_API_KEY`, `OPENAI_API_KEY`) avant
chaque invocation, et un test le mesure — mais une clé posée ailleurs
dans ton shell te coûterait de l'argent sans que rien ne rougisse.

`veille.sh` dit qui est connecté, sans invoquer personne :

```bash
ATELIER_PROJET=~/Forge ~/Forge/atelier_meta/crons/veille.sh
```

Elle tourne toute seule à **06:45**, avant le pilote, et son rapport
reste dans `~/.atelier/veille.txt` : c'est lui que la ligne « veille »
d'`atelier-boucle etat` relit, avec son âge.

Elle démarre chaque binaire pour lire sa version, parce que **la
présence n'est pas la fonction**. Le 14 septembre 2026, le `claude` du
PATH était un talon qui refusait de démarrer — « native binary not
installed », l'installation npm avait sauté son postinstall. `command
-v` le voyait, `atelier pret` le disait PASS, et les postes de brief et
de relecture seraient tombés à chaque réveil sans que rien ne rougisse.
La réparation tient en une ligne, et la veille la donne :

```bash
node ~/.local/lib/node_modules/@anthropic-ai/claude-code/install.cjs
```

### Le jeton du relecteur

GitHub refuse qu'un compte approuve sa propre PR, et c'est la session
`gh` de cette machine qui ouvre les PR du coder. Le relecteur signe donc
sa revue avec un **second compte**, collaborateur du dépôt : un jeton
« repo » de ce compte, dans `~/.atelier/relire.token`, et rien d'autre.

```bash
umask 077; printf '%s\n' 'ghp_…' > ~/.atelier/relire.token
```

Sans lui, `atelier pret` rougit dès qu'on arme, et chaque tour de
relecture range sa carte en `echec/` : la revue est refusée, donc
absente, donc la porte reste fermée. Le coder et le briefer, eux,
signent leurs commits de l'adresse posée dans `~/.atelier/config`
(`ATELIER_GIT_EMAIL`) — celle d'un compte GitHub, sinon la relecture
refuse « aucun auteur connu ».

Le tour de relecture lit ensuite la revue sur la PR : approuvée, la
carte passe et l'intégration fusionne ; changements demandés ou aucune
revue, la carte tombe en `echec/` avec la cause `relecture`, et elle
attend une personne — le coder ne lit pas les revues, le brief est sa
seule source.

### La console du pilote

Hermes ne décide rien : la décision est calculée par `atelier piloter`
et écrite dans `~/.atelier/logs/pilote.log`. Il ne s'invoque que si le
profil pose `ATELIER_CONSOLE=1` ; par défaut, le pilote dépose et se
tait, et rien n'est dépensé.

### Installer sans toucher au binaire Claude

`installer.sh --sans-claude` ne lance aucune commande `claude`, pas même
`claude auth status`. C'est pour les machines où l'installation est faite
par une console qui porte la règle « je ne lance pas le binaire d'un
autre agent » : cette règle protège un quota et une séparation des rôles,
et elle vaut mieux qu'un contrôle d'installation.

L'installateur dit alors franchement ce qu'il n'a pas regardé, au lieu de
laisser croire que c'est vérifié. La connexion se fait à la main, ensuite.

### Pourquoi `-p` ne suffit pas

Un cron n'a personne pour répondre « oui » à une demande
d'autorisation. Sans mode de permission déclaré, `claude -p` s'arrête à
la première, et le réveil de 07:00 rend zéro sans rien livrer — la panne
la plus coûteuse, parce qu'elle ressemble à une file vide.

L'atelier déclare donc `--permission-mode` pour Claude. Ça ne rend pas
la main qui écrit au relecteur : `--disallowedTools` vient après, et
c'est lui qui retire Edit, Write et les commandes git qui poussent.

Pour voir la commande exacte, sans rien dépenser :

```bash
ATELIER_PROJET=~/Forge ~/Forge/atelier_meta/crons/tour.sh relire
```

### Cursor

L'atelier appelle `agent -p <prompt> --model <modèle>`. Les noms de
commande et d'option bougent d'une version à l'autre : vérifie contre
`agent --help` sur ta machine, et compare au mode à sec ci-dessus. Si la
syntaxe diffère, c'est `atelier/backends.py` qui la porte — un seul
endroit.

## Le drapeau

Rien n'invoque un agent sans `ATELIER_INVOQUER=1`. Sans lui, chaque
script imprime la ligne de commande exacte qu'il aurait lancée, dit la
branche du lot, et s'arrête : aucune carte ne bouge, aucun quota n'est
dépensé.

```bash
ATELIER_PROJET=~/Forge ~/Forge/atelier_meta/crons/tour.sh coder   # à sec
```

Le drapeau vit dans le profil, pas dans le crontab — pour la même raison
que la cadence.

## Roder avant d'armer

Le banc monte un produit pour de faux et des agents pour de faux. La
chaîne y tourne en entier, et elle ne peut pas atteindre un agent
payant : le `PATH` du banc commence par ses propres binaires.

```bash
~/Forge/atelier_meta/crons/banc.sh
atelier-boucle atelier      # regarder une carte traverser les quatre rôles
atelier-boucle jour         # revenir au vrai
```

## Ce que chaque script fait

| fichier | quoi |
|---|---|
| `repartiteur.sh` | lit le profil actif, demande qui se réveille, lance les tours. La seule ligne du crontab. |
| `atelier-boucle` | bascule de profil, arrêt, état. Aucun `sudo`. |
| `profils/jour.sh` | la cadence réelle et l'environnement du VPS. |
| `profils/atelier.sh` | la boucle de banc, isolée du produit. |
| `tour.sh` | **un** tour d'un rôle : une carte, un agent, la carte rangée. |
| `pilote.sh` | le tour du pilote : la feuille de route décide, la console rend compte. |
| `veille.sh` | ce qu'on regarde avant d'armer, et chaque matin à 06:45. Démarre les binaires, n'invoque aucun agent. |
| `reveil.sh` | la garde d'heure, pour la forme directe du crontab. |
| `banc.sh` | monte le banc. |
| `installer-profils.sh` | les profils de la console, un par rôle. `--dry-run` par défaut. |
| `crontab` | la forme directe, six réveils. Root porte les heures. |
| `crontab-repartiteur` | la forme recommandée : une ligne, et plus jamais root. |

## Les quatre choses que ces scripts ne font pas

1. **Ils ne décident pas.** Pas un nom de modèle, pas un abonnement, pas
   une liste de rôles n'est écrit ici : tout se demande à `python3 -m
   atelier`. Un shell qui tient une table finit par tenir deux tables qui
   divergent.
2. **Ils ne fusionnent pas.** L'intégration vit sur GitHub, et
   `atelier fusionner` refuse — il continue de refuser.
3. **Ils n'appellent jamais le rôle suivant.** C'est le réveil d'après
   qui le fait. C'est ce qui rend un tour interrompu sans conséquence.
4. **Ils ne passent aucune clé d'API à un agent.** Une clé bascule la
   facture de l'abonnement vers l'unité : l'agent doit trouver sa
   session. `ANTHROPIC_API_KEY`, `CURSOR_API_KEY` et `OPENAI_API_KEY`
   sont retirés avant chaque invocation, et un test le mesure.

## Le fuseau

Les heures du registre sont celles de Paris ; les champs d'un crontab
sont lus en UTC. La forme directe arme donc chaque ligne aux **deux**
heures UTC possibles — Paris est à UTC+1 l'hiver, UTC+2 l'été — et c'est
la garde d'heure de `reveil.sh` qui tranche : elle ne laisse passer
qu'une des deux. Une ligne écrite à une seule heure UTC tombe à côté la
moitié de l'année.

La forme au répartiteur n'a pas ce problème : elle tourne chaque minute,
et c'est le profil qui compare l'heure.

## Quand ça casse

| symptôme | le geste |
|---|---|
| `atelier-boucle etat` dit ATTENTION | aucun cron n'appelle le répartiteur — ni `/etc/cron.d/forgeatelier`, ni le crontab de ton compte : le profil est posé mais aucun réveil ne part. |
| la ligne `veille` porte un FAIL | un agent ne démarre plus ou n'est plus connecté. Le rapport entier est dans `~/.atelier/veille.txt`, et il nomme le geste. |
| la ligne `veille` dit « jamais passée » | la veille de 06:45 n'a pas encore tourné, ou le profil n'est pas armé. |
| une carte dans `echec/` | `journalctl` non, `~/.atelier/logs/<rôle>.log` oui. La cause est un mot sur la carte ; certaines se reprennent seules au réveil suivant. |
| un tour ne démarre jamais | un verrou est tenu : `atelier-boucle etat` dit lequel. Un verrou par rôle, jamais un verrou global. |
| le coder refuse de préparer sa branche | son worktree porte du travail non enregistré. L'atelier ne l'efface pas : `atelier ranger`, ou range à la main. |
| un lot immobile | `python3 -m atelier feuille etat --projet .` dit qui tient ses fichiers. |

**Rien ne se relance tout seul** au-delà des reprises bornées inscrites
sur la carte. Un agent tombé pour une cause qui ne se retente pas reste
tombé jusqu'à ce que quelqu'un lise pourquoi.

## Les tests

Ces scripts sont joués sur un banc, avec de faux exécutables en tête du
`PATH` — c'est la règle 13 du dépôt produit, et elle a coûté un contrôle
qui ne rougissait pas parce qu'il n'existait pas.

```bash
cd atelier_meta && PYTHONPATH=.. python3 -m pytest tests/ -q
shellcheck -x -s bash crons/*.sh crons/atelier-boucle crons/profils/*.sh
```

Aucun de ces tests n'appelle `claude`, `agent`, `hermes` ni `llmquota` :
la CI ne dépense aucun quota.
