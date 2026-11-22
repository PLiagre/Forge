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
  la sortie de l'agent s'écrit dans un fichier au fil de l'eau
  (`~/.atelier/appels/`), et sa mesure entre dans la marque du commentaire
  que le pilote pose : le coût d'un lot se relève sur GitHub. Une session
  reprise rend son coût depuis son premier appel : `journal.couts_par_appel`
  en tire celui de chaque appel.
- **Chaque rôle rend un objet dont le harnais vérifie la forme**
  (`consignes.SCHEMA_*`) : rien ne se lit par expression régulière dans un
  texte libre.
- **Un agent ne lance ni la suite entière ni une simulation longue** :
  `garde_commandes.py` les refuse avant qu'elles partent, et aucune tâche ne
  tourne en arrière-plan (`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`).
- **Un agent ne tourne jamais avec une clé d'API dans son environnement** :
  elle ferait basculer la facture de l'abonnement vers l'unité. Jamais
  `--bare` non plus : il ne chargerait pas les règles du dépôt.
- **Un secret ne passe ni par l'argv ni par un journal.**
- **Seul le compte du propriétaire commande** (`[projet].proprietaire`). Le
  dépôt est public : ce qu'un autre compte écrit sur une issue n'est ni une
  réponse, ni une consigne, ni un « oui », et n'arrive jamais à un agent.
  Le pilote écrit sous le même compte : tout commentaire qu'il pose sur une
  issue porte une marque, sinon il serait lu comme la parole du propriétaire.

## Les tests

- `python3 -m pytest atelier/tests -q` : un GitHub en mémoire et des agents
  dictés, aucun quota dépensé.
- **Un test n'écrit jamais dans le vrai `~/.atelier`** : il reçoit son
  journal et ses verrous dans un dossier temporaire.
- **Sur le PC**, lancer pytest avec `PYTHONUTF8=1`, `--basetemp=<dossier>`
  et `-p no:cacheprovider`. Les verrous y tiennent par `msvcrt`, sous Linux
  par `flock` : leurs tests se jouent sur les deux.

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
  par un compte rendu ou une attente, et une attente est renvoyée au bout
  d'un quart d'heure. La variable `PC_ACTIF = non` le met en pause sans que
  ce soit une panne.
- **Le PC mène `[machines] pc` lots Unity à la fois, un par chantier**
  (`.atelier/chantiers/pc`, `pc-2`…). Le pilote nomme le chantier à l'envoi
  (la marque `envoye` le porte) et le lot le garde. Un chantier ne porte
  qu'un passage à la fois (verrou `chantier-<nom>`), et les passages se
  partagent les verrous `git` et `captures`. Le PC a deux runners
  (`pc-forge`, `pc-forge-2`), un par lot ; chaque chantier a sa copie du
  code de la chaîne (`.atelier/pilote-<chantier>`), et le build de la nuit
  son propre chantier (`.atelier/chantiers/build`) : aucun travail ne
  remet sur master un dossier où un autre travaille.
- **`sonde-pc.yml` lancée deux fois de suite sonde les deux runners** :
  chacun en prend une, et le nom du runner se lit sur le travail.
- **Une session d'agent ne se reprend que sur sa machine, dans le dossier
  du lot** : un lot ne change ni de machine ni de chantier en cours de route.
- **La démo ne suit pas la semaine** : le cron regarde toutes les dix
  minutes (`demo`), et elle part quand l'étape n'a plus de lot ouvert. Le
  tour suivant fait proposer l'étape d'après au CTO, d'avance.

## Les pièges

- **Le pilote prend le plus petit numéro prêt.** Pour imposer un ordre,
  écrire « Dépend de : #n » dans l'issue.
- **Un lot attend aussi les morceaux d'un lot découpé** : pour savoir ce qui
  retient un lot, calculer `lots.bloquantes` avec les issues fermées.
- **La branche `journal` se pousse après un `fetch`** : sans lui, une image
  publiée entre-temps par l'autre machine fait refuser la poussée.
