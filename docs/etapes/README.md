# Les étapes préparées

Les lots de l'étape en cours vivent sur GitHub, dans son jalon : ils y font
foi. Ce dossier porte les lots de l'étape **suivante**, écrits d'avance, pour
qu'elle parte dès que l'étape en cours est jouée.

Un fichier `etape-<n>.json` a la forme d'une proposition de palier
(`atelier/consignes.py`, `schema_palier`) : un titre, un but, et des fiches
avec, pour chacune, ce que je joue de plus, ce que je vois à la démo, la
règle du monde, les preuves, la machine, et les rangs des fiches qu'elle
attend (`apres`).

Quand une étape n'a plus de lot ouvert, le testeur joue son build figé, le
CTO pose sa note de démo, puis propose l'étape suivante sur son issue : il
part du fichier préparé, le corrige de ce que le code est devenu et de ce que
le testeur demande de corriger d'abord. Elle s'ouvre sur le verdict du
testeur, ou sur le « oui » du propriétaire s'il a écrit sur l'issue. Un
fichier se retire quand son étape est ouverte.

| fichier | étape | lots | ce qui part ensemble |
|---|---|---|---|
| [etape-1.json](etape-1.json) | 1 — la carte de 1400 qu'on reconnaît | 9 | sur le VPS, la file des frontières (1, 2, 3) à côté de la forme des lieux (4) puis des noms de l'atlas (5) ; sur le PC, la carte en plein écran (6) à côté des frontières au grain du lieu (7) ; puis les pays et leurs noms (8), et les modes de carte (9) |

Ces fichiers se changent en mode direct : `atelier/tests/test_palier.py`
échoue si l'un d'eux n'a plus la forme d'un palier, ou si une fiche en attend
une qui n'existe pas.
