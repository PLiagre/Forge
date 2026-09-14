# Le prompt d'installation, à donner à Hermes

Tient en moins de 2000 caractères : il se colle dans Discord d'un bloc.

Ce n'est pas le rôle de pilote. C'est une tâche d'installation, une fois.
Le prompt du pilote, lui, est construit par `atelier invocation --role
pilote` — il ne s'écrit pas à la main.

---

```text
Installe l'atelier Forge sur ce serveur. Tâche unique, tu ne codes rien.

1) git clone https://github.com/PLiagre/Forge.git /srv/Forge
Si /srv/Forge existe déjà : ne remplace rien, dis-le-moi, arrête-toi.

2) /srv/Forge/atelier_meta/crons/installer.sh
Il pose tout (dossiers, config, cron, commande). Aucun sudo. Rejouable sans risque.

3) Lis sa sortie. S'il manque des agents, installe-les et connecte-les :
- claude : puis `claude setup-token`. JAMAIS ANTHROPIC_API_KEY, ça facture à l'unité.
- agent (Cursor) : vérifie sa commande avec `agent --help`.
Si une page web s'ouvre : donne-moi l'URL, je te rends le code.

4) Preuve, sans rien dépenser :
/srv/Forge/atelier_meta/crons/banc.sh
atelier-boucle atelier
Attends 5 min, puis : atelier-boucle etat
Dans ~/.atelier/logs/ : une carte est-elle passée de a-coder à a-relire ?

5) atelier-boucle jour

JAMAIS : fusionner, pousser, toucher master. Écrire une clé API où que ce soit.
Inventer un chemin ou une option (lis --help). Modifier un script (décris-moi le
problème, ne le répare pas). sudo hors paquets standards.

RENDS-MOI 6 LIGNES : installé / cron / agents connectés / banc passé ou bloqué où /
profil actif / ce qui bloque.

Pas fini ? Dis où tu t'es arrêté. Ne fais pas semblant d'avoir réussi.
```

---

## Pourquoi il est si court

Tout ce qui pouvait être écrit une fois l'a été : `installer.sh` pose les
dossiers, la configuration, le cron et la commande, puis dit lui-même ce
qui manque. Un prompt qui répète ce que le script sait faire est un
second endroit où la vérité peut se périmer.

## Après

Hermes n'a plus rien à faire : le cron réveille les rôles tout seul.
Quatre commandes, et jamais d'autre :

```bash
atelier-boucle etat      # où ça en est
atelier-boucle arret     # tout arrêter
atelier-boucle jour      # repartir
atelier-boucle atelier   # mode banc, sans quota
```
