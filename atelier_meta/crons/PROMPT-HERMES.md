# Le prompt d'installation, à donner à Hermes sur le serveur

Copie tout ce qui est entre les deux lignes et colle-le à Hermes.

Ce n'est pas le rôle de pilote — c'est une tâche d'installation, une
fois. Le pilote, lui, ne touche à rien : son prompt est construit par
`atelier invocation --role pilote`, et il ne fait que rendre compte.

---

```text
Tu installes l'atelier de Forge sur ce serveur. C'est une tâche unique.
Tu travailles dans un terminal, tu ne codes rien, tu n'ouvres aucune PR.

CE QUE TU FAIS, DANS CET ORDRE :

1. Vérifie que git, python3 (≥ 3.11), flock et timeout sont là.
   Installe ce qui manque avec apt, et rien d'autre.

2. Clone le dépôt, si /srv/Forge n'existe pas déjà :
   git clone -b claude/remote-project-vps-control-ffe0f1 \
       https://github.com/PLiagre/Forge.git /srv/Forge
   Si /srv/Forge existe : ne le remplace pas. Fais `git -C /srv/Forge status`
   et dis-moi ce que tu vois, puis arrête-toi.

3. Lance l'installateur, une fois, sans argument :
   /srv/Forge/atelier_meta/crons/installer.sh
   Il pose tout : les arbres de travail, la configuration, le cron, la
   commande `atelier-boucle`. Il est sans risque à rejouer. Il n'a besoin
   d'aucun sudo.

4. Lis ce qu'il affiche à la fin. Il te dira soit « c'est en marche »,
   soit quels agents manquent.

5. Si des agents manquent, installe ceux-ci et connecte-les :
   - claude  : installe Claude Code, puis `claude setup-token`
               (jeton longue durée, pour un serveur sans écran).
               N'utilise JAMAIS ANTHROPIC_API_KEY : ça bascule la
               facture de l'abonnement vers la facturation à l'unité.
   - agent   : Cursor CLI, puis sa commande de connexion.
               Vérifie son nom exact avec `agent --help`.
   Pour chaque connexion qui demande d'ouvrir une page web : donne-moi
   l'URL, je l'ouvre sur mon navigateur et je te rends le code.

6. Vérifie que tout est vu, sans rien dépenser :
   ATELIER_PROJET=/srv/Forge /srv/Forge/atelier_meta/crons/veille.sh
   Il ne lance aucun agent. Il dit ce qui est là et ce qui est connecté.

7. Fais tourner le banc, qui ne coûte rien et prouve la chaîne :
   /srv/Forge/atelier_meta/crons/banc.sh
   atelier-boucle atelier
   Attends cinq minutes, puis : atelier-boucle etat
   Puis regarde ~/.atelier/logs/*.log et dis-moi si une carte est passée
   de a-coder à a-relire.

8. Reviens au vrai : atelier-boucle jour

CE QUE TU NE FAIS JAMAIS :

- Tu ne fusionnes rien, tu ne pousses sur aucune branche, tu ne touches
  pas à master. L'intégration vit sur GitHub, pas ici.
- Tu ne mets aucune clé d'API dans un fichier, une variable ou un
  message. Si une commande t'en demande une, arrête-toi et dis-le-moi.
- Tu n'inventes pas un chemin, un nom de commande ou une option. Si une
  commande n'existe pas, lis son --help et dis-moi ce que tu as trouvé.
- Tu ne modifies aucun script de /srv/Forge. Si quelque chose ne marche
  pas, tu me le décris ; tu ne le répares pas toi-même.
- Tu n'utilises sudo que pour installer des paquets standards.

CE QUE TU ME RENDS, EN DIX LIGNES MAXIMUM :

- installé : oui / non
- cron : posé / absent
- agents connectés : la liste
- banc : la carte est passée / bloquée à telle étape
- profil actif : jour / atelier / arret
- ce qui te bloque, s'il y a quelque chose, en une phrase

Si tu ne peux pas finir, dis où tu t'es arrêté et pourquoi. Ne fais pas
semblant d'avoir réussi : une installation à moitié faite qui se dit
finie coûte plus cher qu'un échec annoncé.
```

---

## Après l'installation

Hermes n'a plus rien à faire : le cron réveille les rôles tout seul.
Son seul rôle quotidien est celui de **pilote**, à 07:00, et son prompt
est construit par l'atelier — pas par toi.

Les quatre commandes que tu tapes toi-même :

```bash
atelier-boucle etat      # où ça en est
atelier-boucle arret     # tout arrêter
atelier-boucle jour      # repartir
atelier-boucle atelier   # mode banc, sans quota
```
