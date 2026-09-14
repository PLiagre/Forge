# Le prompt d'installation, à donner à Hermes

Tient en moins de 2000 caractères : il se colle dans Discord d'un bloc.

`--sans-claude` n'est pas un détail. Une console d'installation peut
porter une règle absolue « je ne lance pas le binaire d'un autre agent »,
et cette règle vaut mieux qu'un contrôle d'installation : elle protège un
quota et une séparation des rôles. Le drapeau la respecte au lieu de
demander de l'enfreindre — un test le prouve avec un faux `claude` piégé.

Ce n'est pas le rôle de pilote. C'est une tâche d'installation, une fois.
Le prompt du pilote, lui, est construit par `atelier invocation --role
pilote` — il ne s'écrit pas à la main.

---

```text
Reprends l'installation de l'atelier Forge. Tu ne codes rien.

1) git -C ~/Forge pull --ff-only
Si ~/Forge n'existe pas : git clone https://github.com/PLiagre/Forge.git ~/Forge

2) ~/Forge/atelier_meta/crons/installer.sh --sans-claude
Ce drapeau garantit qu'aucune commande `claude` n'est lancée : tu n'enfreins
donc pas ta règle. Il pose tout — dossiers, config, cron, cadence.

3) ~/Forge/atelier_meta/crons/banc.sh
atelier-boucle atelier
Attends 5 min, puis : atelier-boucle etat
Dans ~/.atelier/logs/ : une carte est-elle passée de a-coder à a-relire ?

4) atelier-boucle jour

La connexion de Claude n'est pas ton travail : je m'en occupe moi-même.
Ne lance jamais `claude`, pas même `claude auth status`.

JAMAIS : fusionner, pousser, toucher master. Écrire une clé API où que ce soit.
Inventer un chemin ou une option (lis --help). Modifier un script (décris-moi le
problème, ne le répare pas). sudo hors paquets standards.

RENDS-MOI 6 LIGNES : installé / cron / agents vus / banc passé ou bloqué où /
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
