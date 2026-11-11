# AGENTS.md — les règles, en une page

Forge est un jeu de grande stratégie à la manière d'Europa Universalis IV : un
monde de 1400 qui tourne seul, et un pays réel qu'on y fait évoluer depuis la
carte — ses gestes jouent sur des modificateurs et des jauges paramétrables,
posés sur une économie physique —, contre une IA qui a ses outils, dans
**une seule simulation** ([docs/VISION.md](docs/VISION.md)). L'ordre dans lequel on le
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
`CLAUDE.md` et `CAP.md`. Une exception, gardée : quand le dépanneur dit que la
chaîne est en cause, le mécanicien la répare dans une PR `meca/chaine-…`, que
la direction relit avant qu'elle entre. Cette réparation ne touche que
`[projet].reparables` (`atelier/`, deux workflows, `docs/WORKFLOW.md`), jamais
`sensibles` (la garde `atelier/garde.py` et ses tests, le cron), ni les
droits, les secrets, la machine ou les déclencheurs d'un workflow ; le reste
de cette liste reste au mode direct.

## 2. La chaîne — le propriétaire n'est pas là

- **Un lot = une issue** : un jalon (milestone `J1`…`J9`, ou `Réserve` que le
  pilote ne prend jamais ; obligatoire), un état
  (`idee` → `pret` → `en-cours` → `livre`, ou `bloque` avec sa raison en
  commentaire), l'étiquette `pc` s'il demande Unity ou Blender. Le formulaire
  « Demander un lot » les pose.
- **Un lot dit d'abord ce que le joueur y gagne** : ce qu'il peut faire, voir
  ou décider après lui — ou, pour un lot de fond, le geste qu'il prépare. Le
  brief le reprend dans sa section « Le joueur », le chef refuse un lot qui
  n'en a pas, le relecteur vérifie que c'est vrai
  ([CAP.md](CAP.md), « La règle d'un lot »).
- **Le dépanneur passe d'abord** : un lot que le pilote bloque (essais
  épuisés, CI rouge, relecture `CORRIGER`) est lu par le dépanneur, en
  lecture seule. Il le relance avec une consigne que le codeur et le
  relecteur reçoivent (`depannages_max` fois au plus par lot), le change en
  question au propriétaire, ou le laisse bloqué en disant ce qu'il faut
  corriger dans la chaîne. Une question au propriétaire ne passe jamais par
  lui.
- **Reprendre un lot bloqué** : corriger la cause s'il le faut, puis
  **répondre par un commentaire sur l'issue** (une lettre suffit quand le
  chef a posé une question) : au tour suivant, le pilote remet le lot
  `pret`. Si sa PR est ouverte, il la reprend où elle en est, sans relancer
  le chef, essais remis à zéro ; sinon le chef reprend le lot et lit la
  réponse. Retirer `bloque` et remettre `pret` à la main marche aussi.
- **Le chef pose ses questions** : un lot qui demande une décision du
  propriétaire (un test ou une règle du monde à changer) est bloqué avec la
  question, deux à quatre réponses possibles et la recommandation du chef ;
  le journal du matin la pose telle quelle.
- **L'échelle de décision** : chacun décide à son niveau, et ne monte au
  suivant qu'avec un diagnostic, ce qu'il a essayé, des réponses possibles et
  une recommandation.

  | niveau | qui | quoi |
  |---|---|---|
  | N0 | l'agent | ce qui tient dans son brief et son Périmètre ; le pilote rejoue seul une panne de la CI |
  | N1 | le pilote | une question `technique` (un test réécrit aussi strict, un format) : il suit la recommandation, deux fois au plus par lot |
  | N2 | la **direction** (Fable, lecture seule) | une question posée au propriétaire, quand `docs/VISION.md`, `CAP.md` ou une décision déjà écrite la tranchent, ou que le choix est réversible (un seuil, une durée, une donnée de `jeu/data/`) ; deux fois au plus par lot |
  | N3 | le propriétaire | la vision et ses principes ; une règle que le joueur ressent et que la vision ne tranche pas ; une preuve de jalon ou un test rendu moins exigeant ; l'irréversible ; l'argent |

  Une décision de la direction s'écrit sur l'issue avec ce qui la fonde, suit
  le lot comme une réponse du propriétaire, et le journal du matin la rappelle
  sept jours (« Décidé sans toi »). Le propriétaire garde la main : bloquer
  le lot, écrire sa réponse, remettre `pret`. Dans le doute, la direction lui
  laisse la question, avec son avis.
- **Un lot `pc` n'avance que quand le PC est allumé** : un PC en veille garde
  le travail en file ; ses agents qui ne peuvent pas répondre le disent sur la
  PR (attente, renvoyée dans l'heure, sans compter d'essai). Le propriétaire
  peut le mettre en pause : variable `PC_ACTIF` = `non` (fenêtre
  `pc\Disponibilite.cmd`, ou GitHub → Variables) ; ce n'est pas une panne.
- **Les jalons suivent CAP.md** : chaque section « ## Jalon n — Titre » est
  un milestone, que le pilote crée ou renomme seul. Les lots de chaque jalon
  sont écrits sous sa section, en mode direct ; un jalon qu'on aurait laissé
  sans lot se fait découper par le chef.
- **Le pilote** (`python3 -m atelier tour`, sur le VPS, toutes les deux
  minutes) prend le lot suivant du jalon courant ; une machine qui n'y a plus
  rien à prendre prend dans le jalon suivant, puis dans le troisième (la
  **fenêtre de trois jalons**), qu'elle fait découper s'il n'a pas de plan.
  Une ligne de découpe sans « après » part tout de suite.
  Plusieurs tours tournent en même temps : le VPS fait avancer jusqu'à
  `[machines].vps` lots à la fois, le PC un ; Claude a un plafond d'agents
  simultanés (`[outils]`), et quand il est plein, le lot attend.
  Le **chef** (Opus) écrit le brief dans la branche `lot/<n>-<slug>` et ouvre
  la PR. **Un lot a la taille d'une ligne du CAP** : un gain que le joueur
  voit, et sa preuve dans la même PR, jusqu'à 1 500 lignes environ
  (`lignes_max`) ; plus gros, il découpe en morceaux qui gardent chacun leur
  phrase du joueur et leur preuve, jamais en un lot qui code et un lot qui
  prouve ; hors de son jalon, il refuse.
  Le **codeur** (Sonnet, lots `pc` compris) code, la CI joue les tests, le
  **relecteur** — Opus pour un lot qui touche `jeu/sim/`, Sonnet pour les
  autres, toujours dans une autre session, en lecture seule — rend
  `ACCEPTE` (fusion automatique) ou `CORRIGER` (le codeur corrige, deux fois
  au plus, puis `bloque`).
- **Les agents éditent des fichiers ou rendent un texte.** Commit, poussée,
  PR, commentaire, étiquette et fusion appartiennent au pilote.
- **Un lot ne touche jamais** `atelier/`, `.github/`, `atelier.toml`,
  `AGENTS.md`, `CLAUDE.md`, `CAP.md` : le pilote retire ces changements.
- Les rôles, leurs harnais, leurs modèles et leurs efforts :
  `python3 -m atelier agents`. Changer de modèle ou d'effort, c'est changer
  une ligne de [`atelier.toml`](atelier.toml) (`harnais/modèle@effort`).
  **Plus rien que Claude** (Opus, Sonnet), par Claude Code, sur un seul
  abonnement et une seule réserve de quota : Opus est réservé au brief et à la
  relecture du moteur ; Sonnet code et fait le reste (dépanneur, mécanicien,
  journal, boussole). Ni GPT, ni grok, ni composer : le chargement refuse le
  reste.
- Chaque matin, le journal paraît dans sa propre issue, épinglée : « Journal
  du JJ/MM/AAAA » ; celle de la veille se ferme. Détail de la chaîne : [docs/WORKFLOW.md](docs/WORKFLOW.md).

## 3. Les principes du jeu, non négociables

Leur raison est dans [docs/VISION.md](docs/VISION.md), dans le même ordre.

1. **Une seule simulation** : `jeu/sim/`. Les vues (tableau, chronique,
 relief, Unity) lisent ; elles ne décident jamais un nombre. La bataille
 n'est pas une vue : elle se calcule dans `sim/` avec les hommes et le
 terrain du monde, et lui rend ses pertes.
2. **Des modificateurs partout, sur un monde physique.** Comme dans EU4,
   bâtiments, lois, idées, conseillers, événements du monde et jauges du pays
   posent des modificateurs (nom, source, cible, grandeur du moteur, valeur,
   durée), additionnés dans un ordre fixé et détaillés par l'infobulle. Un
   modificateur change un taux ; il ne remplace pas la cause qu'il nomme et
   ne crée jamais un kilo ni une pièce. Ses chiffres vivent dans `jeu/data/`.
   Un modificateur sans source est refusé. (Remplace « le monde raisonne en
   monde » depuis le 6 novembre 2026, décision 34.)
3. **L'économie est physique.** Tout kilo et toute pièce ont une origine, un
   transport, un stockage, une destination ; un modificateur n'en crée aucun.
4. **L'IA a les outils du joueur.** Tout geste est une intention déposée dans
   `sim/` (ou dans la bataille, pour un ordre de combat) ; l'IA passe par le
   même chemin, avec les mêmes modificateurs et les mêmes jauges, sans bonus.
   Un geste de jeu qui n'existe qu'en 3D n'existe pas.
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
