# atelier — la chaîne

Ce que la chaîne fait, en une page : [docs/WORKFLOW.md](../docs/WORKFLOW.md).
Elle ne se change qu'en mode direct. Chaque mécanisme qu'on y ajoute répond
à un défaut mesuré, et se retire quand le défaut a disparu.

## Les règles de la zone

- **L'état se dérive de GitHub** : les étiquettes de l'issue, la PR, et les
  marques `<!-- atelier {…} -->` dans les commentaires. Rien ne se garde
  ailleurs ; un tour interrompu reprend où les faits disent qu'on en est.
- **Ce qui se décide se décide dans `lots.py`, en fonction pure** ; le
  pilote fait les gestes.
- **Un agent édite des fichiers ou rend un texte.** Le pilote seul commit,
  pousse, commente et fusionne : un avis ne peut pas être falsifié par celui
  qui le donne.
- **Personne ne répond (quota, session, outil qui ne démarre pas) : le lot
  attend**, sans essai compté. Ce n'est jamais un échec.
- **Chaque appel laisse son coût et sa trace**, même coupé par son délai :
  la sortie de l'agent s'écrit dans un fichier au fil de l'eau.
- **Un agent ne tourne jamais avec une clé d'API dans son environnement** :
  elle ferait basculer la facture de l'abonnement vers l'unité. Jamais
  `--bare` non plus : il ne chargerait pas les règles du dépôt.
- **Un secret ne passe ni par l'argv ni par un journal.**

## Les tests

- `python3 -m pytest atelier/tests -q` : un GitHub en mémoire et des agents
  dictés, aucun quota dépensé.
- **Un test n'écrit jamais dans le vrai `~/.atelier`** : il reçoit son
  journal et ses verrous dans un dossier temporaire.
- **Sur le PC**, sept tests de `test_pilote.py` échouent sur `fcntl` (les
  verrous sont faits pour Linux) : c'est attendu, la CI les joue verts. Pour
  juger un changement sur le PC, comparer au même lancement sur master.

## Les machines

- **Le pilote tourne sur le VPS**, sous l'utilisateur `hermes`
  (`ssh hermes-boost`), depuis `~/Forge` resté sur master. Le cron appelle
  `crons/repartiteur.sh` chaque minute ; le profil actif est
  `~/.atelier/etat/profil` (`jour`, `arret`), qu'on change par
  `crons/atelier-boucle jour` ou `arret`.
- **Ses journaux** : `~/.atelier/logs/pilote.log` (un bloc par tour),
  `~/.atelier/journal.jsonl` (un fait par ligne). « RIEN » : aucun lot à
  prendre.
- **Le VPS n'a que deux processeurs** : deux lots au plus, et jamais la
  suite entière du jeu pendant qu'un agent travaille.
- **Le `gh` du VPS est ancien** (2.45) : toujours lire en JSON (`--json`).
- **Le PC ne travaille qu'allumé.** Le pilote lui envoie un passage par
  `workflow_dispatch` (`lot-pc.yml`) ; le runner répond toujours sur la PR,
  par un compte rendu ou une attente. La variable `PC_ACTIF = non` le met en
  pause sans que ce soit une panne.
- **Une session d'agent ne se reprend que sur sa machine, dans le dossier
  du lot** : un lot ne change pas de machine en cours de route.

## Les pièges

- **Le pilote prend le plus petit numéro prêt.** Pour imposer un ordre,
  écrire « Dépend de : #n » dans l'issue.
- **Un lot attend aussi les morceaux d'un lot découpé** : pour savoir ce qui
  retient un lot, calculer `lots.bloquantes` avec les issues fermées.
- **La branche `journal` se pousse après un `fetch`** : sans lui, une image
  publiée entre-temps par l'autre machine fait refuser la poussée.
