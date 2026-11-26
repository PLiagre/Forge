# La chaîne — l'étape, les rôles, le chemin d'un lot

La chaîne fait le travail d'une étape sans le propriétaire. Un pilote en
Python (`python3 -m atelier tour`, sur le VPS, toutes les deux minutes) relit
GitHub, fait avancer chaque lot d'un pas, et lance au plus un agent par tour ;
plusieurs tours tournent ensemble, un par lot en cours. Le PC Windows fait
tourner Unity quand il est allumé. Tout l'état vit sur GitHub : un tour
interrompu ne perd rien.

## L'étape

Une étape de [CAP.md](../CAP.md) se compte en jours et ne suit aucun jour de
la semaine. Elle a son issue épinglée (« Palier n ») et son jalon.

| quand | qui | quoi |
|---|---|---|
| **l'ouverture** | le testeur, ou le propriétaire | le verdict du testeur sur l'étape d'avant ouvre la proposition posée sur son issue ; ou le propriétaire y répond « oui ». Les lots sont ouverts, et la chaîne part dans la minute |
| **l'étape** | la chaîne | fait les lots, tous ceux qui sont prêts à la fois : deux sur le VPS, deux sur le PC. Un lot n'attend que ce qu'il écrit dans « Dépend de » |
| **chaque matin** | le lecteur | écrit le journal : ce qui est livré, en cours, bloqué, ce que le CTO a décidé seul (« à revoir à la démo »), ce que le testeur a trouvé, ce que les appels ont coûté et où en sont les limites de l'abonnement, et, dans « Pour toi », ce qui attend le propriétaire |
| **le dernier lot fermé** | le PC | dans les dix minutes, à toute heure : un build figé de l'étape, que le pilote attend |
| **le build figé** | le testeur | le joue sur le PC, par l'écran seul, dès que le propriétaire a quitté clavier et souris depuis dix minutes : il ne connaît que la promesse de l'étape. Son rapport est posé sur l'issue : le parcours objectif par objectif, ce que l'écran n'explique pas, ce qui est faux ou brouillon, les trois défauts à corriger d'abord, ses photos, son verdict |
| **le verdict rendu** | le CTO | une note d'une page sur l'issue : quoi essayer, ce qui marche, ce qui manque, d'après le rapport du testeur. Puis la suite, sur la même issue : l'étape suivante de `CAP.md` (avec les défauts à corriger d'abord) si l'étape est tenue ; ce qui la corrige si elle ne l'est pas |
| **la suite proposée** | le pilote | l'ouvre sur le verdict du testeur, sans attendre. Cinq « non tenue » de suite : il n'ouvre plus rien et appelle le propriétaire |
| **quand il veut** | le propriétaire | joue le build figé, seul. Ce qu'il écrit sur l'issue de l'étape passe devant le verdict : le CTO repropose en commençant par ce qui corrige, et rien ne s'ouvre plus sur cette issue sans son « oui » |

Le testeur qui ne peut pas jouer ne retient pas l'étape : après six heures
sans écran libre, ou deux passages sans récit prouvé, la note de démo part
sans verdict, le dit, et la suite attend le « oui » du propriétaire, comme
avant lui. `[testeur] ouvre = false`, dans `atelier.toml`, rend ce « oui »
nécessaire à chaque étape : le testeur informe alors, et ne décide plus.

Pendant une étape, aucune question n'attend le propriétaire. Le CTO prend le
choix réversible, le note dans « à revoir à la démo », et le lot continue.
Seuls l'irréversible, l'argent et les droits lui arrivent tout de suite : le
lot est bloqué, et l'issue le dit.

Une retouche vue en jouant (un bouton qui ne répond pas, un texte faux, un
réglage) ne passe pas par un lot : le propriétaire ouvre une session en mode
direct, et elle entre dans la journée ([AGENTS.md](../AGENTS.md), section 2).

## Les rôles

Six : cinq par niveau de jugement sur le code, et le testeur, qui ne voit
jamais le code. Leur modèle, leur effort et leur délai sont une ligne chacun
dans [`atelier.toml`](../atelier.toml) ; `python3 -m atelier agents` les
affiche.

| rôle | modèle | quand il est appelé | ce qu'il rend |
|---|---|---|---|
| **le CTO** | Fable, lecture seule | une étape que le testeur a jouée (sa note de démo, puis la suite) ; une parole du propriétaire sur l'issue de l'étape ; un lot bloqué ; un désaccord entre le chef et le relecteur ; un lot qui touche le cœur du moteur, à relire après le relecteur ; master rouge | des fiches ; une décision avec ses raisons et ses bornes ; un verdict ; la note de démo |
| **le chef de lot** | Opus | à la prise du lot, puis à chaque étape et à chaque correction, **dans la même session** | un plan en étapes, puis du code et un compte rendu par étape |
| **le développeur** | Sonnet | par le chef, dans sa session, pour une tâche bornée ; ou à la place du chef pour un lot simple (données, écran courant) | des fichiers, et un compte rendu d'une ligne au chef |
| **le relecteur** | Opus, autre session, lecture seule | quand la CI est verte, sur tout lot ; le pilote range les captures du lot dans son dossier, et lui dit le temps qu'il a | un verdict structuré : `ACCEPTE` ou `CORRIGER`, ses constats (fichier, ligne, gravité), la promesse au joueur tenue ou non, les tests changés justifiés ou non |
| **le lecteur** | Haiku, lecture seule | une CI rouge ; chaque matin | le résumé d'un journal de CI (quel test, quelle erreur, quelle ligne) ; le journal du matin |
| **le testeur** | Opus, sur le PC, deux outils : son outil de jeu et la lecture de ses photos | une étape qui n'a plus de lot ouvert, quand son build est figé | un récit structuré : chaque objectif de la promesse (du premier coup, après N essais, bloqué, pas joué) avec ses photos, ce que l'écran n'explique pas, les défauts (règle, histoire, chiffre, écran, finition) et leur gravité, les trois à corriger d'abord, un verdict |

Le lecteur ne juge jamais. Le CTO ne code jamais. Le chef ne relit jamais son
propre lot. Le développeur ne décide jamais d'une règle du monde : il la
demande au chef, qui la demande au CTO. Le testeur ne lit jamais le code, le
service ni un journal : une garde refuse tout autre appel que son outil de
jeu et la lecture de son dossier (`atelier/garde_testeur.py`).

### Le testeur

Il joue comme un joueur averti qui découvre le jeu. Il reçoit la promesse de
l'étape (son but, et ce que chaque lot livré dit que le joueur joue de plus),
la vision du jeu, et les repères de 1400 (`atelier/reperes-1400.md` : des
ordres de grandeur pour reconnaître un chiffre ou une carte absurdes). Il ne
reçoit ni « ce que je vois à la démo », qui dirait où cliquer, ni la règle du
monde, qui parle de fichiers.

- **Cinq essais sans trouver, c'est bloqué** ; soixante gestes au plus.
- **Son verdict ne se croit pas sur parole.** La chaîne le recalcule d'après
  son récit et garde le plus dur : un objectif bloqué, pas joué, ou trouvé
  après plus de cinq essais, ou un défaut bloquant, et l'étape n'est pas
  tenue ; un objectif trouvé au deuxième essai ou un défaut gênant, et elle
  l'est avec peine. Une réussite qu'aucune photo ne montre ne compte pas : le
  passage est rejoué.
- **Il joue sur l'écran du propriétaire, et ne le lui prend jamais.** Rien ne
  se lance tant qu'il est au clavier (dix minutes sans entrée), qu'une
  application tient tout l'écran, que la session est verrouillée ou qu'un
  Forge tourne déjà. Dès qu'il touche la souris ou change de fenêtre, le
  testeur s'arrête, ferme le jeu, et rejoue plus tard.
- **Il ne joue pas chaque lot.** Un build et un écran libre par lot
  remettraient sur chaque fusion l'attente qu'on a retirée ; le relecteur
  garde les captures du lot.

## Le chemin d'un lot

```
 la fiche        le CTO écrit l'issue : ce que je joue de plus, ce que je vois
    │            à la démo, la règle du monde, les preuves, la piste
    ▼
 le plan         le chef de lot ouvre sa session, lit la fiche et le code, et
    │            rend son plan en étapes ; le pilote ouvre la PR, le plan dedans
    ▼
 les étapes      la session est reprise pour chaque étape : le chef code le
    │            difficile, confie les tâches bornées au développeur, joue les
    │            tests de ce qu'il touche ; le pilote enregistre, pousse, coche
    ▼
 la CI           verte : relecture. Rouge : le lecteur résume le journal, la
    │            session du chef reprend avec ce résumé et corrige
    ▼
 la relecture    une autre session, en lecture seule, rend son verdict
    │            CORRIGER : la session du chef reprend avec les constats
    │            ACCEPTE d'un lot qui touche le cœur du moteur : le CTO le
    │            relit à son tour, avec la relecture du relecteur
    ▼
 la fusion       ACCEPTE et CI verte : la PR entre seule, l'issue est livrée
```

- **Un lot = une issue = une session = une PR.** L'issue porte l'étiquette
  `lot`, son état (`pret`, `en-cours`, `bloque`, `livre`), sa piste (`monde`,
  `ville`, `interface`), `pc` s'il demande Unity, et le jalon GitHub de son
  étape.
- **La session ne repart jamais à froid.** Elle est reprise (`--resume`) à
  chaque étape et à chaque correction ; coupée par son délai, elle reprend au
  tour suivant où elle en était, et ce qu'elle avait déjà écrit est gardé.
- **Le plan vit dans la PR**, pas dans un fichier du dépôt : une liste
  d'étapes que le pilote coche. Une étape dit ce qu'elle fait, qui la fait
  (le chef ou le développeur) et les tests qu'elle joue.
- **Les tests avant la poussée.** Chaque étape joue les tests de ce qu'elle
  touche, jamais la suite entière ni une simulation longue : la CI joue la
  suite rapide, la nuit joue les longues preuves.
- **Les tests changés se disent.** Tout fichier de test modifié figure dans
  la section « Tests changés » de la PR, avec la règle qui a changé ; le
  pilote la compare au diff, le relecteur la juge.
- **Le pilote fait les gestes** : commit, poussée, PR, commentaire,
  étiquette, fusion. Il retire tout changement d'un lot sur les chemins
  interdits (`atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`,
  `CLAUDE.md`, `CAP.md`).

## Quand ça coince

| ce qui arrive | ce que fait la chaîne |
|---|---|
| le quota manque, la session a expiré, l'outil ne démarre pas | le lot **attend**, sans essai compté ; le tour suivant réessaie, et le PC est renvoyé au bout d'un quart d'heure |
| un appel est coupé par son délai | son coût et sa trace sont écrits ; la session du meneur reprend au tour suivant ; à la troisième coupure de suite, le lot est bloqué. Une relecture coupée ne rend rien : le relecteur sait donc son délai, et qu'une relecture a déjà été perdue |
| la CI tombe avant d'avoir rien contrôlé (réseau, installation) | le pilote rejoue le travail, trois fois au plus, sans appeler personne |
| seul le test chronométré est rouge | le pilote le rejoue une fois avant d'appeler le chef |
| master est rouge | les lots attendent ; le CTO écrit une fiche de réparation, prise avant toute autre |
| le chef a une question | il la pose avec deux à quatre réponses et sa recommandation ; le CTO tranche, et sa décision arrive au chef en entier : la réponse, ses raisons, ses bornes |
| le relecteur dit `CORRIGER` | le chef corrige dans sa session, deux fois au plus ; s'il conteste un constat et que le relecteur le maintient, le CTO tranche |
| un lot est bloqué (essais épuisés, coupures, CI rouge qui dure) | le CTO lit tout et décide : le relancer avec une consigne, le redécouper en lots neufs, ou, pour l'irréversible, l'argent et les droits seulement, le laisser au propriétaire |
| deux lots s'attendent l'un l'autre | le pilote voit la boucle, la nomme sur les deux issues, et le CTO retire la dépendance de trop |
| le propriétaire écrit sur une issue | sa consigne suit le lot : le chef et le relecteur la reçoivent ; un lot bloqué repart |
| le testeur n'a pas d'écran (le propriétaire est au clavier, la session est fermée, un lot fait tourner le jeu) | il **attend** : son passage guette l'écran trois quarts d'heure, puis répond par une attente, que le pilote renvoie au quart d'heure ; au bout de six heures, la note de démo part sans lui |
| le propriétaire reprend son écran pendant que le testeur joue | le testeur s'arrête au geste suivant et ferme le jeu ; ce qu'il avait trouvé est posé sur l'issue sans valoir verdict, et le passage est rejoué |
| le testeur dit l'étape non tenue | le CTO propose ce qui la corrige, et ce tour s'ouvre seul ; à la cinquième fois de suite, le propriétaire décide |

## Ce que coûte la chaîne

Chaque appel écrit ce qu'il a coûté, même coupé : le rôle, le lot, la durée,
les jetons par modèle, le coût au prix de l'API (notionnel sous un
abonnement), et la part de la limite de cinq heures et de la limite
hebdomadaire de l'abonnement avant et après. Ces mesures vivent dans les
marques des commentaires, sur GitHub : celles du PC remontent comme celles du
VPS. Le journal du matin les additionne par rôle et par lot.

## Les machines

- **Le VPS** (deux processeurs) : le pilote et les lots du monde, deux à la
  fois au plus.
- **Le PC** : Unity, deux lots à la fois, chacun dans son chantier
  (`.atelier/chantiers/pc` et `pc-2`), que le pilote nomme à l'envoi et que
  le lot garde. Chaque passage est envoyé par `workflow_dispatch`
  (`lot-pc.yml`) et répond toujours sur la PR. Un runner passe un travail à
  la fois : le PC en a deux (`pc-forge`, `pc-forge-2`), et les deux lots
  avancent ensemble. Le build de la nuit a son propre chantier : il peut
  tourner pendant qu'un lot travaille. `PC_ACTIF = non` met le PC en pause.
- **L'écran du PC** : les runners tournent en service et n'ont pas de bureau ;
  le jeu n'y démarre pas. Le testeur passe donc par `testeur-pc.yml`, qui
  démarre la tâche planifiée « ForgeTesteur » : Windows la lance dans la
  session ouverte du propriétaire, sans fenêtre de console. Elle s'inscrit
  une fois (`pc\Installer_Testeur.cmd`, sans élévation) et n'a aucun horaire.
  `gh workflow run testeur-pc.yml -f sonde=oui` dit si l'écran est libre,
  sans rien lancer.
- **L'abonnement** borne le tout : un lot prend 35 à 50 % d'une fenêtre de
  cinq heures. Quand elle est pleine, les lots attendent sa remise à zéro ;
  rien n'échoue.
- **Arrêter et relancer** : `atelier/crons/atelier-boucle arret` et
  `atelier-boucle jour`, sur le VPS. Figer un build et poser la note sans
  attendre la fin de l'étape ni le testeur : `python3 -m atelier demo
  --maintenant`. Faire jouer un build au testeur à la main, sur le PC, sans
  rien publier : `py -m atelier testeur --palier 2 --maintenant
  --sans-publier`.
