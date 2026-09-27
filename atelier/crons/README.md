# atelier/crons — la chaîne sur le VPS

La seule pièce qui a besoin d'une machine allumée. Le reste décide en Python
(`python3 -m atelier`) ; ces scripts réveillent un rôle et s'arrêtent.

| fichier | rôle |
|---|---|
| `installer.sh` | installer ou réinstaller, sans sudo, rejouable |
| `repartiteur.sh` | appelé chaque minute par la crontab ; lit le profil, lance les rôles du moment |
| `profils/jour.sh` | la cadence : pilote toutes les 10 min, veille 06:45, journal 07:15, boussole lundi 07:45 |
| `tour.sh <rôle>` | un verrou par rôle, la base à jour, puis Python |
| `atelier-boucle <jour\|arret\|etat>` | armer, désarmer, regarder |
| `veille.sh` | ce qui manque pour tourner, à la main |
| `lib.sh` | ce que tous les scripts partagent (chemins, PATH, clés retirées) |

## Installer

```bash
cd ~/Forge && git pull --ff-only
atelier/crons/installer.sh                  # pose la ligne de crontab, le profil reste « arret »
atelier/crons/atelier-boucle jour           # armer
atelier/crons/atelier-boucle etat           # regarder
```

L'installateur écrit `~/.atelier/config` (le dépôt, et l'identité git des
commits de la chaîne, reprise de l'ancienne config), et remplace toute ligne de
crontab qui appelait un ancien répartiteur.

## Les jetons

- **GitHub** : la session `gh` de l'utilisateur (`gh auth status`). La chaîne
  commente, étiquette et fusionne sous ce compte ; il n'y a plus de second
  compte relecteur.
- **Claude Code** : `claude setup-token` rend un jeton longue durée ; le
  ranger dans `~/.atelier/claude.token`, mode 600. La chaîne le passe à
  `claude` par l'environnement, jamais par la ligne de commande.
- **Codex, Cursor** : leurs sessions (`codex login`, `cursor-agent login`).
- Aucune clé d'API : `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` et `CURSOR_API_KEY`
  sont retirées de l'environnement de chaque agent.

## Vérifier

```bash
python3 -m atelier veille          # binaires, jetons, accès GitHub
python3 -m atelier sonde           # chaque agent répond-il, avec son modèle, en non interactif ?
python3 -m atelier tour --a-sec    # ce que le pilote ferait, sans rien faire
```

## Où regarder

| quoi | où |
|---|---|
| ce que le pilote a fait | `~/.atelier/logs/pilote.log` |
| pourquoi la chaîne a attendu | `~/.atelier/journal.jsonl` |
| la dernière veille | `~/.atelier/veille.txt` |
| les worktrees des lots | `~/Forge/.atelier/chantiers/` (ignorés par git) |
