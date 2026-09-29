# AGENTS.md — les règles, en une page

Forge est un jeu de grande stratégie : une petite dynastie réelle de 1400,
de sa capitale à l'État, contre une IA qui a ses outils, dans **une seule
simulation** ([docs/VISION.md](docs/VISION.md)). L'ordre dans lequel on le
construit : [CAP.md](CAP.md). Tout s'écrit en **français clair**.

## 1. Le mode direct — le propriétaire est là

Quand le propriétaire ouvre un agent dans `D:\Forge` (PC) ou `~/Forge` (VPS),
l'agent modifie **directement**, sans issue, sans brief, sans relecture :

1. une branche `direct/<sujet>` partie de `origin/master` ; sur le VPS, dans un
   worktree (`git -C ~/Forge worktree add .atelier/direct/<sujet> -b direct/<sujet> origin/master`) :
   `~/Forge` reste sur master, c'est de là que tourne le pilote ;
2. une PR, puis `gh pr merge --auto --squash` : elle entre seule quand `tests`
   et `gitleaks` sont verts ;
3. avant de commencer, il regarde les lots en cours
   (`gh pr list --search "head:lot/"`, puis `gh pr diff <n> --name-only`) et
   **prévient seulement** si l'un touche les mêmes fichiers.

Seul le mode direct touche `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`,
`CLAUDE.md` et `CAP.md`.

## 2. La chaîne — le propriétaire n'est pas là

- **Un lot = une issue** : un jalon (milestone `J1`…`J9`, ou `Réserve` que le
  pilote ne prend jamais ; obligatoire), un état
  (`idee` → `pret` → `en-cours` → `livre`, ou `bloque` avec sa raison en
  commentaire), l'étiquette `pc` s'il demande Unity ou Blender. Le formulaire
  « Demander un lot » les pose.
- **Reprendre un lot bloqué** : corriger la cause, retirer `bloque`, remettre
  `pret`. Si sa PR est ouverte, le pilote la reprend où elle en est, sans
  relancer le chef, essais remis à zéro ; sinon le chef reprend le lot.
- **Un lot `pc` n'avance que quand le PC est allumé** : un PC en veille garde
  le travail en file ; ses agents qui ne peuvent pas répondre le disent sur la
  PR (attente, renvoyée dans l'heure, sans compter d'essai).
- **Les jalons suivent CAP.md** : chaque section « ## Jalon n — Titre » est
  un milestone, que le pilote crée ou renomme seul. Un jalon qui n'a
  encore rien de prêt, en cours ou livré se fait découper par le chef.
- **Le pilote** (`python3 -m atelier tour`, sur le VPS, toutes les deux
  minutes) prend le lot suivant du jalon courant ; une machine qui n'y a plus
  rien à prendre prend dans le jalon suivant (la **fenêtre de deux jalons**).
  Le **chef** écrit le brief dans la branche `lot/<n>-<slug>` et ouvre la PR
  (moins de 300 lignes, sinon il découpe ; hors de son jalon, il refuse).
  Le **codeur** code, la CI joue les tests, le **relecteur** — jamais la
  famille de modèle qui a écrit, quel que soit l'outil — rend
  `ACCEPTE` (fusion automatique) ou `CORRIGER` (le codeur corrige, deux fois
  au plus, puis `bloque`).
- **Les agents éditent des fichiers ou rendent un texte.** Commit, poussée,
  PR, commentaire, étiquette et fusion appartiennent au pilote.
- **Un lot ne touche jamais** `atelier/`, `.github/`, `atelier.toml`,
  `AGENTS.md`, `CLAUDE.md`, `CAP.md` : le pilote retire ces changements.
- Les rôles et leurs modèles : `python3 -m atelier agents`. Changer de modèle,
  c'est changer une ligne de [`atelier.toml`](atelier.toml).
- Chaque matin, le journal paraît dans sa propre issue, épinglée : « Journal
  du JJ/MM/AAAA » ; celle de la veille se ferme. Détail de la chaîne : [docs/WORKFLOW.md](docs/WORKFLOW.md).

## 3. Les principes du jeu, non négociables

Leur raison est dans [docs/VISION.md](docs/VISION.md), dans le même ordre.

1. **Une seule simulation** : `jeu/sim/`. Les vues (tableau, chronique,
   relief, Unity) lisent ; elles ne décident jamais un nombre. La bataille
   tactique n'est pas une vue : elle reçoit du monde ses hommes et son
   terrain, et lui rend ses pertes.
2. **Le monde raisonne en monde.** Interdit : « si famine alors +20 % de
   criminalité ». Exigé : ils ont faim, ils cherchent, certains volent. Les
   personnages et l'IA aussi.
3. **L'économie est physique.** Tout kilo et toute pièce ont une origine, un
   transport, un stockage, une destination.
4. **L'IA a les outils du joueur.** Tout geste est une intention déposée dans
   `sim/` (ou dans la bataille, pour un ordre de combat) ; l'IA passe par le
   même chemin, sans bonus. Un geste de jeu qui n'existe qu'en 3D n'existe pas.
5. **Les rails posent un fait, jamais une issue.** Une étincelle historique
   arrive à sa date et à son lieu ; le monde décide de la suite.
6. **Chaque décision pèse.** Les gestes demandés au joueur par année de jeu ne
   grandissent pas avec son royaume ; ce qui se répète se délègue.
7. **Réel quand on sait, plausible sinon.** Niveau 1 : juste dans les grandes
   lignes, obligatoire ; des sources publiques (atlas, encyclopédies)
   suffisent. Niveau 2 : plausible, jamais sourcé, une anomalie n'est pas un
   défaut. Niveau 3 : pas simulé. Tout brief qui touche le monde dit son niveau.
8. **Une capacité n'existe que si sa preuve peut échouer.** Prouver le rouge
   d'abord ; un échantillon vide échoue ; **un test existant ne s'assouplit
   jamais** pour passer — un lot ajoute ses cas.

`cell_id` est la seule clé spatiale ; ce qui s'en dérive (province, bourg,
lieu) ne se stocke pas comme une seconde clé ([jeu/sim/MODELE.md](jeu/sim/MODELE.md)).

## 4. Les règles payées par un vrai défaut

- `py` sur Windows, `python3` sur Linux, jamais `python` nu.
- Un contrôle **dérive** sa référence et ses compteurs des données ; `-1`
  veut dire « non calculé », `0` est une mesure.
- Une absence de donnée se **déclare** ; le code refuse de deviner.
- Une garde placée après l'effet qu'elle doit empêcher ne protège rien.
- **Regarder les captures soi-même** : des suites 100 % vertes ont laissé
  passer des défauts visibles à l'œil.
- Sous `bash -e` (la CI), un code de retour se lit par `cmd || code=$?`.
- **Jamais un pack de l'Asset Store dans git** (le dépôt est public) :
  `**/Assets/Vendor/` est ignoré.
- Après toute poussée LFS, vérifier que les objets sont sur le serveur.
- Jamais de force-push sur master ; jamais de secret affiché ni committé.

## 5. Où vit quoi

| chemin | quoi |
|---|---|
| `jeu/` | le jeu en Python : `sim/` (le moteur), `vues/`, `forge/` (la commande de bout en bout), `ville/` (le contrat avec Unity), `data/` (la carte figée). Commandes depuis `jeu/`. |
| `3d/` | `unity/` (le projet unique, kit désert), `local3d/` (Blender), `archives/` (les prototypes qui dorment) |
| `atelier/` | la chaîne : pilote, rôles, journal ; `crons/` pour le VPS |
| `pc/` | les lanceurs Windows |
| `docs/` | notice, workflow, vision, objectif, briefs, mesures |

```bash
cd jeu && python3 -m forge --ticks 365 --seed 0 --sortie sortie   # le jeu, une année
python3 -m pytest jeu -q                                          # les tests du jeu
python3 -m pytest atelier/tests -q                                # les tests de la chaîne
python3 -m atelier agents                                         # la table des rôles
```
