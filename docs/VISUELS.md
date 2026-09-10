# Voir la simulation avancer

Note de proposition. Elle n'est pas une règle : les règles vivent dans
[AGENTS.md](../AGENTS.md). Elle répond à une question simple — *la
simulation avance, la chaîne avance, et on ne voit rien.*

## Ce qui manquait

Le dépôt savait montrer **un instant** (`viewer/`, une photographie) et
**l'état du travail** (la page de pilotage). Il ne savait pas montrer
**le monde qui change**. C'est la seule chose qui manquait, et c'est
celle qui fait qu'on a l'impression que rien n'avance.

Ce que la première chronique a montré en trente secondes, et qu'aucune
suite verte n'avait dit :

| tick | population | cellules en disette |
|---:|---:|---:|
| 0 | 66 662 588 | 0 |
| 15 | 62 102 158 | 526 |
| 30 | 35 235 006 | 49 |
| 60 | 11 302 263 | 0 |
| 180 | 9 213 277 | 0 |

**85 % du monde meurt en deux mois, puis le reste se stabilise.** Le
moteur fait exactement ce qu'on lui a dit de faire ; personne ne
l'avait regardé faire. C'est la règle 11, et c'est le premier argument
pour des visuels : ils ne décorent pas, ils font voir.

## Trois façons de montrer, et ce qu'elles coûtent

### A — La planche · **faite, elle tourne**

`python3 -m chronique --ticks 180 --pas 4 --html planche.html`

Une page HTML autonome : la carte, quatre lectures (population,
subsistances, disette, dette), une réglette qui est la courbe de la
population elle-même. 1,2 Mo, aucune bibliothèque, bibliothèque
standard seule. Voir [`chronique/README.md`](../chronique/README.md).

Direction artistique : **une planche d'atlas statistique**, pas une
carte au trésor. Papier gris-vert, traits gravés, lavis lithographiques
à paliers francs, une seule couleur forte — le madder — réservée à la
mortalité. C'est la langue visuelle de Minard et de Guerry, c'est-à-dire
exactement celle d'un document qui dit *population, subsistances et
mortalité par district*. Elle a un second mérite : 596 cellules, sur une
planche gravée, se lisent comme un choix ; sur un terrain photographique,
comme un manque de moyens.

### B — La bobine · **faite, elle tourne**

```
python3 -m chronique --chronique c.json --html p.html --bobine monde.webm
```

La planche est déjà l'animation ; la bobine n'en est que le fichier.
Chromium sans écran demande chaque instant par son adresse
(`?image=12&lecture=disette`), photographie, et `ffmpeg` assemble.
**Aucun nouveau code de rendu, aucune seconde direction artistique** —
la vidéo *est* la planche, filmée. Le jour où la planche change, la
bobine change avec elle.

Deux exécutables extérieurs, et ils sont déclarés : un Chromium et un
ffmpeg. Sans eux, la planche marche toujours. Reste à en faire un
travail de la chaîne, qui dépose la bobine à chaque tour.

### C — Le relief · **à laisser où il est**

`visualisateur/` existe déjà et parle à forge3d. Il rend un relief en
trois dimensions, joliment — mais il demande numpy, pillow et un moteur
Rust, il ne montre qu'un instant, et 596 cellules d'altitude *plausible*
(fidélité 2) ne font pas un terrain. C'est un banc d'essai pour la
couche Unity, pas la vitrine. Le laisser vivre, ne pas l'agrandir.

## Ce qui se réutilise sous Unity, et ce qui se jette

Ce qui compte n'est pas le dessin — c'est le **format**.

```
sim/  ──►  chronique  ──►  planche SVG   (aujourd'hui, stdlib)
              │   +          bobine mp4   (demain, même page filmée)
              └── da.json ─► Unity        (ensuite, mêmes fichiers)
```

Trois choses survivent au changement de moteur de rendu :

1. **La découpe décor / image.** Une géométrie chargée une fois, un flux
   d'états par tick : c'est déjà ce que fait la planche avec ses `<use>`,
   et c'est exactement ce que fera un `MeshFilter` avec un
   `ComputeBuffer`. Le format ne change pas.
2. **Les mètres.** Le décor est en EPSG:3035 ; un mètre du monde est une
   unité Unity, sans reprojection et sans facteur inventé quelque part.
3. **`da.json`.** La direction artistique est en données, pas en code.
   Le même fichier se lit depuis C#. Changer les lavis se fait à un
   endroit, pas dans deux moteurs de rendu.

Ce qui se jette : `atlas.py`, c'est-à-dire le dessin SVG lui-même. Une
centaine de lignes. C'est le bon rapport.

## Les lots que ça découpe

Cette branche est une **expérience**, pas un lot : elle ne porte pas de
fiche et l'intégration ne la fusionne pas. Ce qu'elle propose de
briefer, dans cet ordre :

1. **La chronique entre au dépôt.** `chronique/` tel quel, avec son
   invariant : `décor + image` rend la photographie au bit près.
2. **La planche se publie.** Le travail `tableau` écrit déjà une page ;
   un second travail écrit la planche à côté, sur la même Pages.
3. **La bobine.** Chromium + ffmpeg, la planche filmée, déposée à chaque
   tour.
4. **Le monde porte son année.** Aujourd'hui il porte un jour dans
   l'année, pas une année : la planche compte des ans depuis le premier
   tick et le dit, faute de mieux.
5. **Le bourg entre dans la photographie.** `sim/aggregation.py` sait
   déjà répartir bourg et campagne ; la photographie ne le porte pas, la
   planche ne peut donc pas le montrer.

Le point 1 est la dépendance de tous les autres.
