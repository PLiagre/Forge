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

## Piloter le projet depuis le VPS, en cinq commandes

```bash
# 1. le dépôt et les arbres des rôles qui écrivent
git clone git@github.com:PLiagre/Forge.git /srv/Forge
git -C /srv/Forge worktree add -b atelier/coder   /srv/Forge-coder   master
git -C /srv/Forge worktree add -b atelier/briefer /srv/Forge-briefer master

# 2. l'atelier, là où le cron ira le chercher
ln -s /srv/Forge/atelier_meta /opt/ForgeAtelier
ln -s /opt/ForgeAtelier/crons/atelier-boucle ~/bin/atelier-boucle

# 3. ce qu'on regarde avant d'armer — rien n'est lancé, rien n'est dépensé
ATELIER_PROJET=/srv/Forge /opt/ForgeAtelier/crons/veille.sh

# 4. la ligne que root pose une fois, et plus jamais
sudo install -m 644 /opt/ForgeAtelier/crons/crontab-repartiteur \
                    /etc/cron.d/forgeatelier

# 5. la cadence, qui n'est qu'un fichier
atelier-boucle jour
```

À partir de là, tout se pilote sans `sudo` et sans toucher au cron :

| commande | effet |
|---|---|
| `atelier-boucle jour` | la cadence réelle : treize réveils, de 07:00 à 21:30 |
| `atelier-boucle atelier` | la boucle courte de banc : quatre rôles en quatre minutes, zéro quota |
| `atelier-boucle arret` | plus aucun réveil ; attend le tour en vol au lieu de le couper |
| `atelier-boucle etat` | le profil, depuis quand, le prochain réveil, ce qui tourne |

C'est le point de toute la conception. `/etc/cron.d/forgeatelier`
appartient à root : tant qu'il portait les heures, changer de cadence
demandait le propriétaire. Il n'appelle plus qu'un répartiteur, chaque
minute ; le profil actif est un fichier que l'utilisateur écrit. **Ce
qu'on ne peut pas désarmer seul, on ne l'arme pas.**

---

## Le drapeau

Rien n'invoque un agent sans `ATELIER_INVOQUER=1`. Sans lui, chaque
script imprime la ligne de commande exacte qu'il aurait lancée, dit la
branche du lot, et s'arrête : aucune carte ne bouge, aucun quota n'est
dépensé.

```bash
ATELIER_PROJET=/srv/Forge /opt/ForgeAtelier/crons/tour.sh coder   # à sec
```

Le drapeau vit dans le profil, pas dans le crontab — pour la même raison
que la cadence.

## Roder avant d'armer

Le banc monte un produit pour de faux et des agents pour de faux. La
chaîne y tourne en entier, et elle ne peut pas atteindre un agent
payant : le `PATH` du banc commence par ses propres binaires.

```bash
/opt/ForgeAtelier/crons/banc.sh
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
| `veille.sh` | ce qu'on regarde avant d'armer. N'invoque personne. |
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
| `atelier-boucle etat` dit ATTENTION | `/etc/cron.d/forgeatelier` est absent : le profil est posé mais aucun réveil ne part. |
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
