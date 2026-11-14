# La chaîne — la semaine, les rôles, le chemin d'un lot

La chaîne fait le travail de la semaine sans le propriétaire. Un pilote en
Python (`python3 -m atelier tour`, sur le VPS, toutes les deux minutes) relit
GitHub, fait avancer chaque lot d'un pas, et lance au plus un agent par tour.
Le PC Windows fait tourner Unity quand il est allumé. Tout l'état vit sur
GitHub : un tour interrompu ne perd rien.

## La semaine

| quand | qui | quoi |
|---|---|---|
| **samedi** | le propriétaire | joue la démo, et écrit sur l'issue du palier ce qu'il veut réorienter |
| | le CTO | en tire le palier suivant : un lot par piste au moins, chacun une fiche ; il les propose sur la même issue |
| | le propriétaire | valide d'un mot (« oui »), ou corrige : le CTO repropose. Au « oui », les lots sont ouverts et la chaîne part |
| **la semaine** | la chaîne | fait les lots |
| **chaque matin** | le lecteur | écrit le journal : ce qui est livré, en cours, bloqué, ce que le CTO a décidé seul (« à revoir samedi »), et ce que les appels ont coûté |
| **vendredi soir** | le PC, le CTO | un build figé du palier, et une note d'une page sur l'issue du palier : quoi essayer, ce qui marche, ce qui manque |

Pendant la semaine, aucune question n'attend le propriétaire. Le CTO prend le
choix réversible, le note dans « à revoir samedi », et le lot continue. Seuls
l'irréversible, l'argent et les droits lui arrivent tout de suite : le lot est
bloqué, et l'issue le dit.

## Les rôles

Cinq, par niveau de jugement. Leur modèle, leur effort et leur délai sont une
ligne chacun dans [`atelier.toml`](../atelier.toml) ; `python3 -m atelier
agents` les affiche.

| rôle | modèle | quand il est appelé | ce qu'il rend |
|---|---|---|---|
| **le CTO** | Fable, lecture seule | le samedi ; un lot bloqué ; un désaccord entre le chef et le relecteur ; un lot qui touche le cœur du moteur, à relire ; master rouge ; le vendredi soir | des fiches ; une décision avec ses raisons et ses bornes ; un verdict ; la note de démo |
| **le chef de lot** | Opus | à la prise du lot, puis à chaque étape et à chaque correction, **dans la même session** | un plan en étapes, puis du code et un compte rendu par étape |
| **le développeur** | Sonnet | par le chef, dans sa session, pour une tâche bornée ; ou à la place du chef pour un lot simple (données, écran courant) | des fichiers, et un compte rendu d'une ligne au chef |
| **le relecteur** | Opus, autre session, lecture seule | quand la CI est verte | un verdict structuré : `ACCEPTE` ou `CORRIGER`, ses constats (fichier, ligne, gravité), la promesse au joueur tenue ou non, les tests changés justifiés ou non |
| **le lecteur** | Haiku, lecture seule | une CI rouge ; chaque matin | le résumé d'un journal de CI (quel test, quelle erreur, quelle ligne) ; le journal du matin |

Le lecteur ne juge jamais. Le CTO ne code jamais. Le chef ne relit jamais son
propre lot. Le développeur ne décide jamais d'une règle du monde : il la
demande au chef, qui la demande au CTO.

## Le chemin d'un lot

```
 la fiche        le CTO écrit l'issue : ce que je joue de plus, ce que je vois
    │            samedi, la règle du monde, les preuves, la piste
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
    ▼
 la fusion       ACCEPTE et CI verte : la PR entre seule, l'issue est livrée
```

- **Un lot = une issue = une session = une PR.** L'issue porte l'étiquette
  `lot`, son état (`pret`, `en-cours`, `bloque`, `livre`), sa piste (`monde`,
  `ville`, `interface`), `pc` s'il demande Unity, et le jalon GitHub de son
  palier.
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
| le quota manque, la session a expiré, l'outil ne démarre pas | le lot **attend**, sans essai compté ; le tour suivant réessaie |
| un appel est coupé par son délai | son coût et sa trace sont écrits ; la session reprend au tour suivant ; à la troisième coupure de suite, le lot est bloqué |
| la CI tombe avant d'avoir rien contrôlé (réseau, installation) | le pilote rejoue le travail, trois fois au plus, sans appeler personne |
| seul le test chronométré est rouge | le pilote le rejoue une fois avant d'appeler le chef |
| master est rouge | les lots attendent ; le CTO écrit une fiche de réparation, prise avant toute autre |
| le chef a une question | il la pose avec deux à quatre réponses et sa recommandation ; le CTO tranche, et sa décision arrive au chef en entier : la réponse, ses raisons, ses bornes |
| le relecteur dit `CORRIGER` | le chef corrige dans sa session, deux fois au plus ; s'il conteste un constat et que le relecteur le maintient, le CTO tranche |
| un lot est bloqué (essais épuisés, coupures, CI rouge qui dure) | le CTO lit tout et décide : le relancer avec une consigne, le redécouper en lots neufs, ou, pour l'irréversible, l'argent et les droits seulement, le laisser au propriétaire |
| deux lots s'attendent l'un l'autre | le pilote voit la boucle, la nomme sur les deux issues, et le CTO retire la dépendance de trop |
| le propriétaire écrit sur une issue | sa consigne suit le lot : le chef et le relecteur la reçoivent ; un lot bloqué repart |

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
- **Le PC** : Unity, un passage à la fois, envoyé par `workflow_dispatch`
  (`lot-pc.yml`). Il répond toujours sur la PR. `PC_ACTIF = non` le met en
  pause.
- **Arrêter et relancer** : `atelier/crons/atelier-boucle arret` et
  `atelier-boucle jour`, sur le VPS.
