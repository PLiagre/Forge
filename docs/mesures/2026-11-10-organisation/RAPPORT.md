# Forge — refonte de l'organisation de développement

Audit et proposition du 10 novembre 2026. **Rien n'a été modifié** : ni le dépôt, ni GitHub, ni le VPS, ni la configuration Claude. Ce document attend ta validation.

Mesuré sur `origin/master` = `1c5cb709` (la copie locale `D:\Forge` a 28 commits de retard), sur GitHub (477 PR, 573 issues), sur le VPS en lecture seule (journal du pilote) et sur ce PC (Claude Code 2.1.312).

---

## 0. L'essentiel en une page

1. **La chaîne est à l'arrêt depuis le 9 novembre, 06 h 20 UTC** (37 h au moment de l'audit). Elle tourne — un tour toutes les deux minutes — et répond « RIEN ». Neuf lots sont bloqués : sept attendent une réponse de toi (depuis 52 à 214 h), deux attendent qu'on ajoute `--retry` à un `curl` dans un fichier qu'aucun agent n'a le droit de toucher. Tout le reste des jalons 5 et 6 attend derrière eux.
2. **Le problème n'est plus la taille des lots.** La refonte du 7 novembre l'a traité (plafond passé de 300 à 1 500 lignes, preuve dans la même PR), et les trois lots livrés depuis font 637 à 1 381 lignes, fusionnés en 1 à 6 h. **Le problème est l'autorité** : personne d'autre que toi ne peut décider, et personne d'autre que toi ne peut réparer la chaîne.
3. **Le mode qui marche existe déjà : c'est le mode direct.** Les 7 et 8 novembre, sept PR de 700 à 2 100 lignes (modificateurs, pays et jauges, bâtiments de province, soudure, tick de 213 à 52 ms) sont entrées en une douzaine d'heures, chacune fusionnée moins de 1 h 10 après son ouverture. Une session, un contexte continu, quelqu'un qui tranche au fil de l'eau. L'organisation cible consiste à **donner à la chaîne les propriétés du mode direct**, pas à lui ajouter des rôles.
4. **Ce que je recommande** : trois niveaux (une direction Fable appelée aux moments de décision, un chef de fonctionnalité Opus qui garde son contexte du plan à la fusion, des développeurs Sonnet en sous-agents), trois couloirs de fichiers au lieu d'équipes, une relecture indépendante à verdict structuré, et une échelle de décision à quatre niveaux qui ne te laisse que le jeu et l'irréversible.
5. **Ce que je ne recommande pas** : Agent Teams (expérimental, et inopérant en mode `-p`, vérifié dans la documentation), huit équipes (une seule réserve de quota et deux processeurs sur le VPS), des briefs « extrêmement détaillés » (le brief écrit à froid par un agent pour un autre est aujourd'hui le maillon qui casse le plus).
6. **Le plafond réel est le quota.** L'application lit ton abonnement comme **« Pro »**, à 69 % de la limite hebdomadaire tous modèles (remise à zéro le 13 novembre), Fable à 7 % de la sienne. Aucune organisation ne produira plus que ce que l'abonnement sert ; la cible est donc d'abord de **gaspiller moins d'appels** (4,3 appels à froid par lot aujourd'hui).
7. **Une contradiction à trancher avant tout** : ta mission dit qu'Europa Universalis, Total War et Manor Lords sont trois dimensions non négociables ; `docs/VISION.md` (décisions 24 à 33 et 40, prises par toi) fait d'EU4 le modèle, range la capitale 3D en « vue » avec ses lots à la Réserve, et renvoie la bataille 3D après le premier siècle. Les agents suivent VISION.md. Question 1 de la section 9.

---

## Livrable 1 — Diagnostic de l'existant

### 1.1 État réel du projet

| | mesuré |
|---|---|
| Moteur (`jeu/sim/`) | 45 modules, 12 092 lignes ; `engine.py` 2 042 lignes, `service.py` 931, `constants.py` 746 |
| Tests du moteur | 40 fichiers, 35 505 lignes, 1 208 tests Python au total ; 121 mentions d'empreintes épinglées dans 12 fichiers |
| Unity (`3d/unity/`) | 326 fichiers C#, environ 33 000 lignes ; 471 tests ; assemblies `Forge.Pont`, `Forge.Interface` et deux paquets `Victoria.CityMode` hérités ; 132 fichiers hors assembly, dont 110 dans `Editor/` |
| Preuves Unity par lot | 69 fichiers `Editor/Captures/Lot<n>.cs`, 6 839 lignes, jamais retirés |
| Chaîne (`atelier/`) | 5 600 lignes de code, 4 600 de tests ; 69 des 369 commits de master depuis le 27 septembre y touchent |
| CI | `tests` : 24 à 40 minutes sur les 30 derniers runs ; master exige `tests` et `gitleaks`, aucune relecture ; Unity ne fait que compiler, sur ton PC, sans être exigé |
| Avancement | J1 à J4 atteints ou clos ; 132 issues ouvertes, dont une centaine pour J5 à J9 |
| Le monde | tient la première année, pas dix : Paris à 26 %, Milan à 5 %, Flandre et Florence vides (rapport du 7 novembre). Le lot qui doit le corriger, #1026, est bloqué sur une question |

### 1.2 Les forces — à garder telles quelles

- **Une architecture de jeu saine dans son principe** : une seule simulation, les vues ne décident aucun nombre, l'IA passe par les intentions du joueur, `cell_id` seule clé. C'est exactement ce qui permet de faire coexister carte, ville et bataille.
- **Une culture de la preuve qui peut échouer** et de la mesure (`docs/mesures/`), rare et précieuse.
- **Un état sans mémoire locale** : tout vit sur GitHub, un tour interrompu ne perd rien.
- **Des gardes déterministes** dans le pilote (chemins interdits retirés, verrous, plafonds).
- **Le pont sim ↔ Unity** existe, avec une dépendance propre (`Forge.Interface` → `Forge.Pont`).
- **La refonte du 7 novembre** a déjà corrigé la taille des lots et la séparation code / preuve.

### 1.3 Les problèmes, par gravité

**P1 — Personne ne peut décider à ta place. (critique, en cours)**
47 questions t'ont été posées depuis septembre. Délai médian de réponse : **19 h** (Q1 12 h, Q3 38 h, max 162 h) ; 1 236 heures de lot cumulées en attente. `docs/WORKFLOW.md` note lui-même que tu répondais toujours la recommandation. La cause est dans la règle : toute question qui touche un test existant ou une règle du monde est classée « jeu », donc pour toi. Or avec trois lignes de test pour une ligne de moteur et des empreintes épinglées, **presque toute fonctionnalité réelle touche un test**. Le principe 8 (« un test ne s'assouplit jamais ») est bon ; son application (« donc on demande au propriétaire ») fait de toi le goulot. Sur les sept questions ouvertes aujourd'hui, cinq se déduisent de VISION.md ou portent sur un seuil réglable dans les données.

**P2 — Personne ne peut réparer la chaîne à ta place. (critique, en cours)**
21 blocages « la chaîne est en cause, mode direct ». Exemple en cours : #1031 et #1046 sont rouges parce que le téléchargement de gitleaks a reçu un 504. Le dépanneur a posé le diagnostic exact et écrit le correctif en une ligne — puis s'est arrêté, parce que `.github/` est interdit aux agents et qu'il ne sait pas rejouer un travail. Le codeur a été rappelé deux fois « pour corriger » un code qui n'avait rien. Deux jours perdus pour un `--retry`. 47 des 99 PR en mode direct portent sur la chaîne elle-même : **tu es l'ingénieur d'exploitation de ton usine**.

**P3 — Des agents sans mémoire, qui recommencent à froid. (majeur)**
Chaque étape est un appel `claude -p` isolé : le chef lit tout et écrit un brief ; le codeur repart de zéro avec ce brief ; le relecteur aussi ; chaque correction aussi, avec 6 000 caractères de journal de CI. Bilan mesuré le 7 novembre : 1 071 appels pour 248 lots (4,3 par lot), 33 % de relectures `CORRIGER`, 131 blocages sur 81 lots, 63 appels coupés par leur délai, 36 échecs du chef sur 194. Le codeur a interdiction de jouer la suite (elle dure 25 à 40 minutes) : il découvre ses échecs par la CI, donc par un nouvel appel à froid. Le verdict est un texte lu par expression régulière (« verdict illisible »), et le coût de chaque appel n'est pas relevé (`--output-format text`).

**P4 — Le quota est le plafond, et il est partagé par tout. (majeur)**
Un seul abonnement, lu « Pro » par l'application, pour le chef, les codeurs, les relecteurs, le dépanneur, le journal et tes sessions directes. 47 h d'attente de quota en octobre, 145 h pour une session expirée. Chaque appel à froid relit `AGENTS.md`, `CAP.md` (64 Ko), `VISION.md`, `MODELE.md`.

**P5 — L'unité de travail est une ligne de liste, pas une fonctionnalité qui a un responsable. (majeur, à moitié traité)**
Le pilote prend le plus petit numéro prêt. Une fonctionnalité qui traverse le moteur et l'écran (« le panneau du pays ») reste deux lots sur deux machines, sans personne qui la porte de bout en bout. Avant le 7 novembre, une ligne du CAP devenait 3,9 issues et un lot sur trois n'était qu'une preuve.

**P6 — Pas de contrats écrits, et un moteur monolithique. (majeur pour le parallélisme)**
- `engine.py` porte tout le tick ; tout lot du moteur touche `engine.py`, `intentions.py`, `service.py` ou `world.py`. Deux lots du moteur en parallèle se marchent dessus : c'est la vraie raison des files « Dépend de ».
- Le contrat sim ↔ Unity est implicite : du JSON écrit à la main des deux côtés (`service.py`, `ClientPays.cs`, un `LecteurJson.cs` maison). Seule la ville a un schéma (`jeu/ville/`).
- Aucun document d'architecture : la carte du code tient en cinq lignes d'`AGENTS.md`. 283 briefs dorment dans `docs/briefs/`. `3d/unity/README.md` décrit encore un projet sans binaires et un « lot 101 ».
- Aucune règle de dépendance vérifiée entre modules.

**P7 — Le savoir d'exploitation n'est pas partagé. (moyen)**
Le projet n'a aucune configuration Claude Code : ni `.claude/settings.json`, ni sous-agents, ni skills, ni hooks, ni MCP. Une trentaine de leçons payées cher (Unity pendu à « Cleanup mono », `-assemblyNames` séparé par « ; », `py -c` sous PowerShell, empreintes Windows/Linux…) vivent dans la mémoire privée de la session de ce PC. Les agents du VPS et du runner ne les voient jamais et les redécouvrent.

**P8 — Le PC est un point unique. (moyen, structurel)**
50 à 60 % des lots livrés étaient `pc`. Unity ne tourne que sur ta machine, quand elle est allumée. Les tests Unity ne sont pas un contrôle exigé par master.

**P9 — Les plus gros changements entrent sans relecture. (moyen)**
Le mode direct fusionne sur CI verte, sans relecteur. C'est par lui que sont entrés le registre des modificateurs, le pays et les bâtiments.

**P10 — Un risque d'architecture non instruit : la performance du moteur. (à instruire, pas urgent)**
Le tick coûte 40 à 52 ms en Python pour 596 cellules et 36 maisons. La partie visée fait 182 500 ticks (1400–1900), avant les petits seigneurs, la guerre, la monnaie et la dynastie. Et la bataille « dans `sim/` » ne pourra pas être une bataille à 5 000 hommes en Python pur. Aucune décision n'est écrite là-dessus. Ce n'est pas à trancher maintenant, mais c'est exactement le genre de sujet qu'une direction technique doit instruire avant le jalon 7.

### 1.4 Pourquoi le jeu avance lentement, en une phrase

La chaîne livre vite quand elle roule (brief → fusion : 1,4 h de médiane), mais elle s'arrête dès qu'il faut **décider** ou **se réparer**, parce que ces deux pouvoirs n'appartiennent qu'à toi ; et entre deux arrêts elle dépense son quota à faire relire le projet par des agents qui ne se souviennent de rien.

### 1.5 Ce que je n'ai pas pu vérifier

- Le contenu détaillé des revues de PR (une requête GitHub a échoué en 502 ; les taux de `CORRIGER` viennent du rapport du 7 novembre, pas d'un nouveau relevé).
- Unity : je n'ai ni ouvert le projet ni joué ses tests ; l'audit C# est structurel.
- Je n'ai pas joué la suite Python.
- Fable répond en `claude -p` sur ce PC ; je ne l'ai pas essayé sur le VPS.
- Le coût en quota d'un lot : la chaîne ne le relève pas.
- La nature exacte de l'abonnement : « Pro » est ce que lit l'application.

---

## Livrable 2 — Architecture cible

### 2.1 Trois architectures comparées

| | A. Régler la chaîne actuelle | B. Agent Teams natif | **C. Sessions de fonctionnalité + direction (recommandée)** |
|---|---|---|---|
| Principe | garder chef → codeur → relecteur → dépanneur, élargir leurs droits | un chef de file et des coéquipiers qui se parlent | une session Opus continue par fonctionnalité, des sous-agents Sonnet, une direction Fable appelée sur décision |
| Contexte | perdu à chaque étape | propre à chaque coéquipier | **gardé du plan à la fusion** (`--resume`) |
| Coût en quota | élevé (4,3 appels à froid par lot) | « nettement plus » qu'une session seule, d'après la documentation | le plus bas des trois |
| Disponibilité | oui | **expérimental, désactivé par défaut, inopérant en `-p`** | oui : `--resume`, `--json-schema`, `.claude/agents/`, vérifiés dans la CLI installée |
| Risque | on garde 5 600 lignes à entretenir | instable, non pilotable depuis le VPS | une migration à conduire |

A traite P1 et P2 mais pas P3 à P5. B contredit ta propre exigence de simplicité et ne tourne pas sans écran. **C** est la seule qui reproduit ce qui a marché les 7 et 8 novembre.

### 2.2 Organigramme

```
                         PROPRIÉTAIRE
          vision · jeu · irréversible · argent — un condensé par jour
                               │
                 ┌─────────────┴──────────────┐
                 │   DIRECTION  (Fable 5.2)   │   appelée, pas permanente :
                 │   plan · arbitrage ·       │   plan hebdomadaire, escalades,
                 │   contrats · chaîne        │   relecture moteur/contrat
                 └──┬──────────┬───────────┬──┘
        couloir MONDE   couloir PAYS/CARTE   couloir PLATEFORME
       (jeu/sim cœur)  (gestes, IA, service, (atelier, CI, tests,
                         Unity Interface)     performance)
            │                  │                    │
   CHEF DE FONCTIONNALITÉ (Opus 5.5) — une session par fonctionnalité,
   du plan à la fusion ; conçoit, code le difficile, intègre
            │
   DÉVELOPPEURS (Sonnet 5.5) — sous-agents de la session : tâches bornées,
   tests, corrections, écrans Unity, documentation
            ┆
   RELECTEUR INDÉPENDANT — autre session, lecture seule, verdict structuré
     moteur / contrat : Fable · le reste : Opus · jamais le rang de l'auteur ou moins
            ┆
   PETITES MAINS (Haiku 5.5) — extraire l'erreur d'un journal de CI,
     écrire le journal du matin, trier
            ┆
   RÉPARTITEUR + PORTE DE FUSION — du code Python, sans modèle :
     choisit, lance, reprend, vérifie, fusionne
```

### 2.3 Rôles et modèles

| rôle | modèle | fait | ne fait jamais |
|---|---|---|---|
| **Direction** | Fable 5.2, effort élevé | tient le plan (CAP), écrit les fiches de fonctionnalité, tranche les escalades, garde les contrats, relit moteur et contrats, répare la chaîne, écrit le condensé du jour | coder une fonctionnalité ; changer la vision |
| **Chef de fonctionnalité** | Opus 5.5 | conçoit, pose le contrat en premier commit, code le cœur difficile, délègue, intègre, tient la PR jusqu'à la fusion | sortir de son couloir ; fusionner |
| **Développeur** | Sonnet 5.5 | tâches bornées dans la session du chef ; seul sur les fonctionnalités simples (écran, données, outil) | toucher un contrat ; décider d'une règle |
| **Relecteur** | Fable (moteur, contrat, chaîne) ou Opus (le reste) | lit la fiche et le diff, rejoue des tests, rend un verdict JSON | écrire ; lire le récit de l'auteur avant le diff |
| **Petites mains** | Haiku 5.5 | résumer un journal, écrire le journal du matin | juger |
| **Répartiteur, porte** | aucun | les gestes Git et GitHub, les gardes, la fusion | interpréter |

Ton hypothèse de départ (Fable dirige, Opus conçoit et code le dur, Sonnet code le courant) est juste dans son étagement. Je la corrige sur quatre points :

1. **Fable n'est pas un chef présent en permanence.** Un agent qui « supervise » lit tout et coûte cher sans produire. Fable intervient à quatre moments : le plan de la semaine, une escalade, la relecture d'un changement de moteur ou de contrat, une panne de la chaîne. Sa limite hebdomadaire est séparée et presque intacte (7 %) : c'est une réserve à dépenser sur les décisions, pas sur la lecture.
2. **Le brief change de nature.** La direction écrit une **fiche courte** (le joueur, la règle, le contrat, les preuves, le couloir) ; la conception détaillée est faite par la session qui code, et vit dans la PR. Un brief très détaillé écrit par un agent pour un autre agent qui n'a pas son contexte est le maillon le plus fragile de la chaîne actuelle.
3. **Haiku manque à ta liste.** Il répond sur ce PC, et il suffit pour le journal et l'extraction d'erreurs de CI.
4. **La relecture « indépendante » ne peut plus être une autre famille de modèle.** L'indépendance se construit autrement : autre session, rang de modèle au moins égal à celui de l'auteur, et une information différente (la fiche et le diff, pas le compte rendu).

### 2.4 Trois couloirs plutôt que huit équipes

Une « équipe » d'agents sans mémoire n'a pas de sens : ce qui évite les conflits, c'est **qui a le droit d'écrire où, en même temps**. Trois couloirs, déclarés dans un fichier, calés sur le code réel :

| couloir | chemins | machine | en vol |
|---|---|---|---|
| **MONDE** | `jeu/sim/` cœur (production, commerce, population, migration), `jeu/data/` du monde | VPS | 1, puis 2 quand `engine.py` sera découpé |
| **PAYS et CARTE** | gestes, jauges, modificateurs, IA, `service.py`, `3d/unity/Assets/Interface`, `Forge.Pont` | VPS + PC | 1 |
| **PLATEFORME** | `atelier/`, `.github/`, tests lents, performance, outils | VPS | 1 |

La ville 3D (`ForgeLocal3D`, Blender) sera un quatrième couloir le jour où elle sortira de la Réserve. Trois fonctionnalités en vol, c'est aussi ce que le quota et les deux processeurs du VPS supportent.

### 2.5 Délégation, coordination, communication

- **Une fonctionnalité = une fiche = une session = une PR** (deux PR empilées au plus quand elle traverse moteur et Unity).
- **Les agents ne se parlent pas.** Ils communiquent par des objets : la fiche, le contrat, la PR, le registre des décisions. Aucune réunion, aucun message libre.
- **Le contrat d'abord.** Une fonctionnalité qui change ce que le service rend commence par un commit qui change le schéma et ses exemples ; le moteur et Unity codent ensuite contre ces exemples, chacun de son côté.
- **L'état se dérive de GitHub**, comme aujourd'hui. Aucun fichier d'avancement tenu à la main.
- **Validation** : la porte de fusion (section 5) est du code ; le relecteur juge ; la direction arbitre ; toi seul sur la liste N3.

---

## Livrable 3 — Nouveau workflow opérationnel

```
 ①  PLAN — direction (Fable), le lundi ou quand un couloir se vide
     lit CAP, VISION, l'état GitHub, les mesures du monde
     produit : 3 à 6 fiches docs/fonctionnalites/<id>.md, ordonnées par couloir
     humain : non — sauf si une fiche demande un choix de jeu (N3)
        │
 ②  PRISE — répartiteur (code)
     un couloir libre → la première fiche prête ; crée branche, worktree, session nommée
        │
 ③  CONCEPTION — chef de fonctionnalité (Opus), même session jusqu'à ⑨
     lit la fiche et le code ; écrit le plan dans la PR brouillon ;
     premier commit = contrat et ses exemples, s'il change
     contrôle : le plan reste dans le couloir, sinon escalade N2
        │
 ④  DÉVELOPPEMENT — chef + sous-agents Sonnet
     le chef code le cœur ; délègue des tâches bornées (un fichier, un test, un écran)
        │
 ⑤  TESTS AVANT POUSSÉE — la session
     la suite rapide (moins de 5 min) + les tests de ce qu'elle touche ;
     un hook refuse de rendre la main sur du rouge
        │
 ⑥  CI — GitHub : suite complète, gitleaks, Unity si 3d/unity/ est touché
     une panne d'infrastructure (réseau, téléchargement) se rejoue seule, 3 fois, sans compter d'essai
     rouge réel → Haiku extrait l'erreur → la session REPREND (--resume), elle n'est pas relancée
        │
 ⑦  RELECTURE — autre session, lecture seule, verdict JSON
     { verdict, constats[{fichier, ligne, gravité, quoi}], promesse_joueur_tenue, tests_changés_justifiés }
        │
 ⑧  CORRECTIONS — la session du chef reprend avec les constats
     trois tours au plus ; un constat contesté deux fois monte à la direction
        │
 ⑨  PORTE DE FUSION — code : toutes les conditions de la section 5.1 → fusion
        │
 ⑩  VALIDATION DANS LE JEU — code + direction
     mesure du monde (1 an, 10 ans), budget du tick, capture ; régression → retour arrière automatique
        │
 ⑪  DOCUMENTATION ET PLAN — dans la même PR (MODELE.md, contrats) ;
     la direction coche le CAP et ajuste les fiches suivantes
        │
 ⑫  CONDENSÉ DU JOUR — Haiku rédige, la direction signe : livré, décidé (avec droit de veto), à trancher
```

| étape | déclenche | agit | document produit | automatique | toi |
|---|---|---|---|---|---|
| ① plan | horloge, ou couloir vide | Fable | fiches, CAP ajusté | oui | choix de jeu seulement |
| ② prise | répartiteur | code | branche, PR brouillon | oui | non |
| ③ conception | ② | Opus | plan dans la PR, contrat | oui | non |
| ④ ⑤ développement, tests | ③ | Opus + Sonnet | code, tests | oui | non |
| ⑥ CI | poussée | GitHub | statuts | oui | non |
| ⑦ relecture | CI verte | Fable ou Opus | verdict JSON | oui | non |
| ⑧ corrections | verdict | Opus (reprise) | commits | oui | non |
| ⑨ fusion | porte verte | code | — | oui, sauf liste N3 | un clic sur la liste N3 |
| ⑩ validation | fusion | code + Fable | mesure, capture | oui | non |
| ⑪ ⑫ | fusion | Fable, Haiku | condensé, registre | oui | **lire, 5 minutes** |

---

## Livrable 4 — Infrastructure IA

### 4.1 Ce qu'on prend de l'écosystème Claude, et ce qu'on laisse

| | verdict | pourquoi |
|---|---|---|
| Claude Code en `-p` + `--resume` | **oui, le socle** | garde le contexte entre conception, correction et relance |
| `--output-format json`, `--json-schema` | **oui** | verdicts structurés, coût relevé par appel ; fin des verdicts « illisibles » |
| Sous-agents (`.claude/agents/*.md`, champ `model`) | **oui** | Sonnet sous Opus, dans la même session |
| Skills | **oui** | le savoir d'exploitation chargé à la demande plutôt qu'un `AGENTS.md` qui gonfle |
| Hooks | **oui, comme gardes** | chemins protégés, « pas de rouge rendu », déterministes |
| `CLAUDE.md` par dossier | **oui** | règles du moteur, d'Unity, de la chaîne chargées seulement là où on travaille |
| Worktrees | **oui** | déjà en place |
| `--fallback-model` | **oui** | Opus à court → Sonnet pour une correction, sans attendre |
| Agent Teams | **non** | expérimental, inopérant en `-p`, coûteux |
| Serveur MCP Unity | **essai borné, plus tard** | piloter un éditeur ouvert éviterait les démarrages à froid qui pendent ; dépendance communautaire que je n'ai pas vérifiée |
| MCP GitHub | non | `gh` suffit |
| Tâches planifiées dans le cloud | non | le cron du VPS fait le travail, et le cloud n'a pas Unity |
| `ultrareview` | non | facturé à part |
| Mémoire automatique | **à rapatrier** | ce qui est durable passe dans le dépôt (skills) ; la mémoire privée ne sert qu'à ce PC |

### 4.2 Fichiers à créer ou modifier

| fichier | rôle | contenu attendu |
|---|---|---|
| `AGENTS.md` | modifié | l'échelle de décision N0–N3 (section 5.2), les couloirs, « une fonctionnalité, une session, une PR » ; reste sur une page |
| `.claude/settings.json` | créé | permissions (refus de `push --force`, de `gh pr merge` hors porte), hooks ci-dessous |
| `.claude/hooks/garde_chemins.py` | créé | refuse une écriture hors du couloir de la session, et sur la liste sensible |
| `.claude/hooks/pas_de_rouge.py` | créé | à l'arrêt, refuse de rendre la main si la suite rapide n'a pas été jouée ou est rouge |
| `.claude/agents/direction.md` | créé | Fable ; lecture + écriture des fiches, du registre, du CAP hors définitions de jalon |
| `.claude/agents/chef-de-fonctionnalite.md` | créé | Opus ; le cycle ③–⑧, la règle « contrat d'abord », quand escalader |
| `.claude/agents/developpeur.md` | créé | Sonnet ; tâche bornée, rend un compte rendu court |
| `.claude/agents/relecteur.md` | créé | lecture seule ; la grille de relecture ; sortie au schéma |
| `.claude/agents/lecteur-de-ci.md` | créé | Haiku ; d'un journal de CI à « quel test, quelle erreur, quelle ligne » |
| `.claude/skills/forge-tests/` | créé | suite rapide et suite lente, durées, pièges Windows (`py`, `--basetemp`, `PYTHONUTF8`) |
| `.claude/skills/forge-unity/` | créé | mode batch, `-assemblyNames` avec « ; », la pendaison à « Cleanup mono », chemins des captures |
| `.claude/skills/forge-contrat/` | créé | comment changer un contrat sim ↔ Unity sans casser l'autre côté |
| `.claude/skills/forge-mesure/` | créé | mesurer le monde et le tick, lire une empreinte, la recapturer proprement |
| `.claude/skills/forge-escalade/` | créé | le gabarit d'une remontée : diagnostic, essais, options, recommandation |
| `jeu/sim/CLAUDE.md`, `3d/unity/CLAUDE.md`, `atelier/CLAUDE.md` | créés | les règles propres à chaque zone |
| `docs/architecture/ARCHITECTURE.md` | créé | la carte des modules, qui dépend de qui, les règles vérifiées par test |
| `jeu/contrats/*.schema.json` + exemples | créés | un schéma par route du service (`/pays`, `/lieu`, `/carte`, `/modificateurs`, `/intention`…) |
| `jeu/sim/tests/test_dependances.py` | créé | échoue si une vue importe l'intérieur du moteur, si le moteur importe l'IA |
| `docs/decisions/REGISTRE.md` + `docs/decisions/NNN-*.md` | créés | les décisions N2 (une ligne, datée, réversible ou non, ton veto) et les décisions d'architecture |
| `docs/fonctionnalites/<id>.md` | créé, remplace `docs/briefs/` | la fiche : le joueur, la règle, le contrat, les preuves, le couloir, hors périmètre |
| `atelier/couloirs.toml` | créé | chemins de chaque couloir, nombre en vol, liste sensible |
| `atelier/repartiteur.py`, `atelier/porte.py` | créés | remplacent la machine à états par rôle de `pilote.py` |
| `atelier/prompts.py`, rôles chef / codeur / dépanneur | retirés en phase 4 | remplacés par les définitions d'agents |
| `.github/workflows/tests.yml` | modifié | un travail `rapide` ; la suite lente inchangée |
| `.github/workflows/security.yml` | modifié | reprises sur le téléchargement |
| `.github/workflows/unity.yml` | modifié | tests EditMode en plus de la compilation ; statut exigé quand `3d/unity/` change |
| `3d/unity/Assets/ForgeLocal3D/Editor/*.asmdef` | créé | sortir `Editor/` et `Captures/` de l'assembly par défaut |
| `3d/unity/README.md` | réécrit | il décrit un projet qui n'existe plus |

### 4.3 Contre la perte de contexte, les doublons, les boucles

- **Perte de contexte** : la session de fonctionnalité est reprise, jamais relancée ; les décisions sont dans le registre, pas dans des commentaires.
- **Doublons et conflits de fichiers** : un couloir, une fonctionnalité en vol ; le hook refuse d'écrire hors couloir.
- **Coût de coordination** : aucun message entre agents ; des objets versionnés.
- **Boucles sans fin** : trois tours de relecture, deux escalades par fonctionnalité, un budget d'appels par fiche ; au-delà, la direction re-découpe ou abandonne et le dit.

---

## Livrable 5 — Pull Requests et blocages

### 5.1 La porte de fusion

Une PR entre **seule** quand toutes ces conditions sont vraies, sur le commit exact de sa tête :

1. `tests` vert, suite complète ; `gitleaks` vert ; Unity (compilation et tests EditMode) vert si `3d/unity/` est touché.
2. Verdict `ACCEPTE` d'un relecteur indépendant, de rang au moins égal à celui de l'auteur.
3. Le diff reste dans le couloir de la fiche.
4. **Tests existants** : tout test supprimé, toute assertion ou empreinte changée figure dans la section « Tests changés » de la PR, avec la règle qui a changé et l'assertion aussi stricte qui la remplace. Une garde compare cette section au diff ; un écart est rouge.
5. Les empreintes du monde sont identiques, ou leur changement est déclaré avec la mesure avant / après.
6. Le budget du tick n'est pas dépassé.
7. Si une route du service change, le schéma et ses exemples changent dans la même PR.
8. Le relecteur a vérifié la promesse « Le joueur » de la fiche ; pour un écran, la capture est jointe et regardée.

Elle **attend ton accord** (un clic) quand elle touche :

- `docs/VISION.md`, la définition ou la preuve d'un jalon dans `CAP.md` ;
- la porte et ses gardes (`atelier/porte.py`, les hooks, `couloirs.toml`) ;
- un workflow qui tourne sur ton PC, des permissions, des secrets ;
- une dépendance, un asset ou une licence nouvelle ;
- le format d'une donnée figée (la carte, une future sauvegarde) ;
- une décision classée irréversible au registre.

La compilation seule ne valide rien : les conditions 2, 4, 5 et 8 sont là pour ça.

### 5.2 L'échelle de décision

| niveau | qui | quoi | trace |
|---|---|---|---|
| **N0** | l'agent | tout ce qui tient dans sa fiche et son couloir ; rejouer un contrôle tombé pour une panne ; fusionner master dans sa branche | le commit |
| **N1** | le chef de fonctionnalité | réécrire un test que la fiche rend faux, **par une assertion aussi stricte** ; recapturer une empreinte avec mesure ; ajouter une constante de niveau 2 dans les données ; découper sa fonctionnalité | section « Tests changés » de la PR |
| **N2** | la direction | changer un contrat ; arbitrer deux couloirs ; réordonner un jalon ; un seuil ou une définition de preuve **réversible** ; toute question que VISION, CAP ou le registre tranchent déjà ; réparer la chaîne | registre, repris dans le condensé, **veto 7 jours** |
| **N3** | toi | la vision ; une règle que le joueur ressent et que VISION ne tranche pas ; une preuve de jalon affaiblie ; l'irréversible ; l'argent ; les droits | ta réponse |

Avant de monter d'un niveau, un agent doit avoir **essayé deux approches distinctes** et le montrer. Toute remontée a quatre parties, et la porte refuse celle qui en manque une : **diagnostic** (avec la preuve), **essais** (ce qui a été tenté, ce que ça a donné), **options** (deux à quatre, avec leur coût), **recommandation**.

Les questions N3 ne bloquent plus qu'une fonctionnalité : elles arrivent **groupées dans le condensé du jour**, et le couloir passe à la fiche suivante en attendant.

### 5.3 Quatre exemples, pris dans le dépôt

**Une PR refusée par le relecteur.** Verdict : « la jauge est écrite depuis la vue, `BarreDuPays.cs` ligne 88 ; contredit le principe 1 ». La session du chef est **reprise** avec ce constat : elle sait déjà pourquoi elle avait fait ce choix, déplace le calcul dans `jauges.py`, ajoute le cas de test, rejoue la suite rapide, pousse. Deuxième relecture sur le seul écart. Si le chef conteste (« c'est un affichage, pas un nombre décidé ») et que le relecteur maintient, la direction tranche en un appel, écrit la règle dans `ARCHITECTURE.md`, et les deux s'y tiennent.

**Un conflit d'intégration.** Deux fonctionnalités du couloir MONDE ne peuvent plus être en vol ensemble : le cas disparaît par construction tant qu'`engine.py` n'est pas découpé. Entre couloirs (`service.py` touché par MONDE et PAYS) : la session dont la PR arrive en second fusionne master, résout — elle connaît son propre code —, rejoue les tests des deux côtés. Si le conflit porte sur le sens (deux champs qui veulent dire deux choses), ce n'est plus un conflit de fichier mais de contrat : N2.

**Un bogue difficile.** Le cas réel de #1031 et #1046 : `gitleaks` rouge. Aujourd'hui : deux passages du codeur pour rien, un diagnostic juste du dépanneur, deux jours d'attente. Demain : la porte voit que le travail est tombé **avant** son étape de contrôle, le rejoue (N0, sans compter d'essai). S'il retombe trois fois, le couloir PLATEFORME ouvre une PR sur `security.yml` ; elle ne touche ni un travail du PC ni un secret, Fable la relit, elle entre. Tu la lis le lendemain dans le condensé.
Pour un vrai bogue de moteur (une empreinte qui change sans raison) : la session isole le tick où le monde diverge, par dichotomie sur les empreintes ; essaie deux pistes ; si elle échoue, elle monte avec le tick, la cellule et la grandeur en cause. La direction choisit : corriger, ou revenir en arrière et rouvrir la fiche.

**Une incompatibilité d'architecture.** Une fiche Unity a besoin d'un nombre que `/pays` ne rend pas, et le chef est tenté de le calculer dans la vue. Le hook ne le voit pas, mais le relecteur le voit (principe 1) et la garde 7 le rend impossible à faire en douce. Le chef monte en N2 avec deux options : étendre le contrat (une PR de contrat d'abord, moteur puis vue), ou changer l'écran. La direction choisit, met le schéma à jour, et la fonctionnalité repart le jour même. Autre cas, N3 celui-là : une fiche qui demanderait une seconde clé spatiale, ou un geste qui n'existerait qu'en 3D. Cela touche un principe de VISION : la direction te le remonte, avec sa recommandation.

---

## Livrable 6 — Plan de migration

Aucune bascule d'un coup : l'ancienne chaîne continue de livrer pendant que la nouvelle fait ses preuves sur quelques fonctionnalités.

**Phase 0 — Débloquer (une demi-journée, mode direct, sans changer l'organisation)**
- Objectif : la chaîne repart.
- Modifications : reprises sur le téléchargement de gitleaks ; le pilote rejoue seul un contrôle tombé sur une panne ; tes sept réponses (tableau en section 9, question 7).
- Dépendances : aucune. Risques : aucun notable.
- Réussite : plus de « RIEN » tant qu'il reste un lot prêt ; #1031 et #1046 fusionnés.
- Gain : trois lots par jour au lieu de zéro.

**Phase 1 — Le pouvoir de décider et de réparer (semaine 1)**
- Objectif : sortir de ton chemin critique (P1, P2).
- Modifications : l'échelle N0–N3 dans `AGENTS.md` ; un rôle `direction` (Fable) qui reçoit les questions avant toi ; le registre et le condensé du jour ; le couloir PLATEFORME autorisé à toucher `atelier/` et `.github/` sous garde ; sorties en JSON avec coût relevé.
- Dépendances : phase 0 ; ta réponse aux questions 2 et 3.
- Risques : une décision de jeu prise à tort par la direction → champ limité au réversible, registre, veto 7 jours, retour arrière. Une modification dangereuse de la chaîne → liste sensible qui garde ton clic.
- Réussite : au plus trois questions par semaine pour toi ; aucun blocage d'infrastructure de plus de 4 h ; coût par lot connu.
- Gain : l'essentiel du temps perdu aujourd'hui.

**Phase 2 — La fonctionnalité de bout en bout (semaines 2 et 3)**
- Objectif : la continuité de contexte (P3, P5).
- Modifications : `.claude/` (agents, skills, hooks) ; fiches ; session reprise ; suite rapide ; verdict structuré ; relecture du mode direct. **En pilote sur deux ou trois fonctionnalités du jalon 5**, étiquetées à part ; le reste continue dans l'ancienne chaîne.
- Dépendances : phase 1.
- Risques : une session longue qui dérive → budget d'appels par fiche et compaction ; un pilote qui cache un défaut → comparaison chiffrée avec l'ancienne chaîne.
- Réussite : chaque fonctionnalité pilote fusionnée avec une escalade au plus ; moins d'appels et moins de quota par millier de lignes fusionnées que l'ancienne chaîne.
- Gain : moins de quota par fonctionnalité, moins de `CORRIGER`.

**Phase 3 — Contrats et couloirs (semaines 3 à 5)**
- Objectif : permettre le parallèle sans conflit (P6, P7).
- Modifications : `ARCHITECTURE.md` ; schémas des routes et tests des deux côtés ; test de dépendances ; `couloirs.toml` ; **découpe d'`engine.py` en phases du tick, sans changer un octet du monde** (les empreintes existantes en sont la preuve) ; assembly pour `Editor/` ; règle de retrait des `Lot<n>.cs`.
- Dépendances : phase 2 pour la découpe du moteur (elle a besoin d'un chef de fonctionnalité fiable).
- Risques : la découpe du moteur est le geste le plus risqué du plan → une phase du tick par PR, empreintes identiques exigées, aucune autre fonctionnalité MONDE en vol pendant ce temps.
- Réussite : deux fonctionnalités MONDE en vol sans conflit ; un contrat cassé exprès fait rougir un test de chaque côté.
- Gain : un couloir de plus en parallèle.

**Phase 4 — Retirer l'ancien (à partir de la semaine 5)**
- Objectif : ne plus entretenir deux chaînes.
- Modifications : retrait des rôles chef, codeur, dépanneur et de l'analyse de texte dans `atelier/` ; `docs/briefs/` archivé ; les indicateurs de la section 7 dans le journal ; la boussole devient la revue hebdomadaire de la direction.
- Dépendances : phases 2 et 3 réussies sur leurs critères.
- Risques : retirer trop tôt → on ne retire un rôle que lorsqu'aucune fonctionnalité ne l'a utilisé depuis deux semaines.
- Réussite : `atelier/` réduit d'au moins moitié ; moins de deux PR par semaine en mode direct sur la chaîne.
- Gain : ton temps.

**À instruire en parallèle, sans urgence** : une note de décision sur la performance du moteur avant le jalon 7 (mesures, options, coût) ; la dépendance au PC.

---

## Livrable 7 — Mesure de la performance

Référence relevée sur les données existantes ; cibles à huit semaines.

| indicateur | référence | cible | d'où vient la référence |
|---|---|---|---|
| D'une fiche prête à sa fusion, médiane | 9,9 h (16,1 h depuis le 28 octobre) | moins de 6 h | rapport du 7 novembre |
| Fonctionnalités complètes par semaine | 47 lots par semaine en octobre, mais 299 lignes de médiane et jusqu'à un sur trois sans rien de jouable ; depuis le 7 novembre, environ 3 par jour quand la chaîne roule, 0 depuis le 9 | 10 à 15 lignes du CAP par semaine, **tenues**, chacune avec sa preuve | PR et issues |
| Temps où la chaîne ne fait rien alors qu'un lot est prêt | 33 à 44 % des tours ; 100 % depuis 37 h | moins de 10 %, hors quota | journal du pilote |
| PR ouverte → fusion, médiane | 1,4 h | garder moins de 2 h pour des PR quatre fois plus grosses | PR |
| Relectures `CORRIGER` | 33 % (23 % depuis le 28 octobre) | moins de 20 % | rapport du 7 novembre |
| Correction autonome (lots finis sans toi) | environ 67 % (81 lots bloqués sur 248) | plus de 90 % | rapport du 7 novembre |
| Questions pour toi | 47 en six semaines, 19 h de médiane | 3 par semaine au plus, groupées ; aucune ne bloque plus d'un couloir | commentaires d'issues |
| PR en mode direct sur la chaîne | 47 en six semaines | moins de 2 par semaine | PR |
| Appels d'agent par fonctionnalité | 4,3 par lot de 300 lignes | 3 à 5 par fonctionnalité de 1 000 lignes | rapport du 7 novembre |
| Quota par millier de lignes fusionnées | **non mesuré** | mesuré dès la phase 1, puis en baisse | — |
| Régressions (master rouge) | 6 échecs sur les 200 derniers runs ; 5 réparations du mécanicien | ne pas dépasser | CI |
| Temps perdu en conflits | 3 blocages pour conflit (faible, parce que tout est en file) | rester sous 1 par semaine avec trois couloirs en parallèle | commentaires d'issues |
| Le monde tient | Paris à 26 % à dix ans | la preuve du jalon 5 verte, puis rejouée chaque semaine | rapport du 7 novembre |

Le dernier indicateur est le seul qui parle du jeu. Les autres mesurent l'usine ; il ne faut pas les confondre avec lui.

---

## 9. Ce que toi seul peux trancher

1. **La vision.** Ta mission pose EU + Total War + Manor Lords comme non négociables ; VISION.md (décisions 24 à 33, 40) fait d'EU4 le modèle, met la capitale 3D en vue avec ses lots à la Réserve, et la bataille 3D après le premier siècle. Lequel fait foi ? Je recommande de **garder VISION.md pour les jalons 5 et 6** (le monde ne tient pas encore dix ans : c'est le socle des trois dimensions), mais d'**écrire dans le CAP à quel jalon la ville à la main et la bataille menée reviennent**, pour que l'architecture les protège dès maintenant.
2. **La délégation du jeu réversible.** Acceptes-tu que la direction tranche les questions de jeu réversibles (un seuil, une durée, une définition de preuve aussi stricte), inscrites au registre avec un veto de sept jours ? Sinon elles restent chez toi, groupées une fois par jour. Je recommande la délégation.
3. **La chaîne réparée par les agents.** Acceptes-tu que le couloir PLATEFORME modifie `atelier/` et `.github/` sous garde et relecture Fable, ton accord restant requis sur la liste sensible ? Je recommande oui.
4. **L'abonnement.** Il plafonne tout le reste. Je recommande de mesurer le coût par fonctionnalité en phase 1, puis de décider d'un passage à une offre supérieure sur ce chiffre, pas avant.
5. **Le PC.** Reste-t-il la seule machine Unity ? Je recommande oui pour l'instant, en faisant en sorte qu'une fonctionnalité du moteur n'attende jamais le PC.
6. **La relecture du mode direct.** Bloquante pour `jeu/sim/`, consultative ailleurs ? Je recommande oui.
7. **Les sept questions en attente.** Mon avis sur chacune, à confirmer d'une lettre sur l'issue :

| lot | question | recommandation du chef | mon avis |
|---|---|---|---|
| #1026 | mesurer « perd la moitié » aux habitants restants | A | **A**, réversible |
| #1027 | ce que la preuve exige d'une IA repue | A | **à toi** : A affaiblit la preuve du jalon 5 écrite au CAP ; B la garde mais coûte un lot |
| #1029 | la famine dure-t-elle après la faim | A | **A**, la durée est une donnée |
| #1035 | seuil du Droit « bas » | A | **A**, seuil réglable |
| #1037 | tout pays jouable, ordres militaires refusés | A | **A**, c'est la décision 26 et la décision 10 |
| #977 | Tlemcen sans chef connu | A | **A**, rien ne change |
| #860 | surbrillance des terres de départ | A | **A**, c'est la décision 26 ; la question a été reposée parce qu'un commentaire de la refonte a été pris pour ta réponse |
