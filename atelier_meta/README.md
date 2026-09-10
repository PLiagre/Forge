# atelier_meta/ — d'où vient l'atelier

Le runtime de l'atelier vit dans [`../atelier/`](../atelier/). Ce dossier
garde ce qui l'accompagne : sa provenance, ses profils, ses crons, ses skills
et ses propres tests.

`UPSTREAM.md` dit à quel commit la copie est épinglée.

## Pourquoi il est dans l'arbre

Avant la fusion, l'atelier n'existait comme dépôt nulle part : une branche
détachée dans un dépôt, une copie vendorisée dans l'autre. Deux chaînes qui
divergeaient en silence — et, mesuré au moment de la fusion, sept tests rouges
dans le premier dépôt du seul fait que l'atelier n'était pas sur le
`PYTHONPATH`.

Un dépôt unique n'a pas à aller chercher son propre outil ailleurs. Le
détacher en dépôt à part redeviendra utile le jour où un second projet le
consommera : c'est le lot 100, et il n'est pas pressé.
