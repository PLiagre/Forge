# chronique/

Le monde qui avance, **regardé**. `viewer/` montre un instant ; la
chronique montre la suite des instants, et c'est la seule différence.

```bash
# dérouler 180 ticks, une image tous les 4, et dessiner la planche
python3 -m chronique --ticks 180 --pas 4 --html /tmp/chronique.html

# garder la chronique pour la redessiner sans resimuler
python3 -m chronique --ticks 180 --pas 4 --json /tmp/chronique.json
python3 -m chronique --chronique /tmp/chronique.json --html /tmp/planche.html

# une page qui n'appelle personne (fontes du système)
python3 -m chronique --chronique /tmp/chronique.json --html /tmp/p.html --sans-reseau

# en faire une vidéo (demande un Chromium et un ffmpeg)
python3 -m chronique --chronique /tmp/chronique.json --html /tmp/p.html \
        --bobine /tmp/monde.webm --bobine-lecture disette
```

Un instant précis se demande par l'adresse :
`planche.html?image=12&lecture=disette`. C'est ce qui permet de filmer la
planche sans la piloter — et de pointer un lien sur un instant.

Bibliothèque standard seule, comme `sim/`, `viewer/` et `outils/`.

## L'idée : décor + image

Une photographie de `sim/` pèse deux mégaoctets, dont 95 % de géométrie
qui ne bougera jamais. Cinquante instants coûteraient cent mégaoctets pour
montrer quatre nombres par cellule qui changent.

    photographie  =  décor  +  image

- le **décor** ne bouge pas : géométrie, relief, climat, gisements,
  province. Écrit une fois.
- une **image** est ce qui bouge : par cellule, la population, le panier,
  la faim et la dette, en colonnes parallèles à l'ordre du décor.

Ce n'est pas un résumé. `recomposer(decor, image)` rend la photographie
d'origine **au bit près**, et c'est ce que le test vérifie. Une découpe
qui perdrait ou inventerait quoi que ce soit serait un second modèle du
monde — le mode de défaillance n° 4.

180 ticks, 46 images : 3,2 Mo de chronique, 1,2 Mo de planche.

## Ce qui n'est décidé nulle part dans le code

- **Les couleurs** vivent dans [`da.json`](da.json), pas dans
  `atlas.py`. Une direction artistique écrite dans du code est une
  direction artistique que le prochain moteur de rendu devra réécrire.
- **Les champs mobiles** sont mesurés par le test, pas déclarés : on joue
  des ticks, on regarde quels champs ont bougé, et la liste doit
  correspondre. Le jour où le moteur en fera bouger un de plus, ça
  rougit (règle 7).
- **Les échelles** dérivent de toute la chronique, jamais d'une image :
  une échelle par image ferait paraître identiques une cellule pleine et
  une cellule vide, et l'animation ne montrerait plus rien bouger.
- **Une lecture jamais mesurée se déclare.** Sur deux ticks personne n'a
  de dette ; la planche ferme l'onglet et écrit pourquoi, elle ne peint
  pas « zéro partout » (règles 8 et 10).

## Ce que la planche ne dit pas, et pourquoi

- **Pas d'année civile.** Le monde porte un jour dans l'année, pas une
  année : la planche compte donc des ans depuis le premier tick, en
  chiffres romains, et le dit en pied de page. Elle n'écrit pas « 1400 »,
  qui n'est nulle part dans l'état du monde.
- **Pas de bourgs.** Les disques disent la population d'une cellule. Le
  bourg est une agrégation dérivée (`sim/aggregation.py`) que la
  photographie ne porte pas encore.

## Ce qui se réutilise sous Unity

Le format, pas le dessin. Unity charge le décor une fois — un maillage,
en mètres EPSG:3035, directement des unités monde — puis consomme les
images comme un flux d'états par tick. C'est exactement ce que fait la
planche avec ses `<use>` : la géométrie n'est écrite qu'une fois, tout
le reste la référence.

`da.json` se lit aussi bien depuis C# que depuis Python : les mêmes
lavis, les mêmes hachures, les mêmes seuils. Changer la direction
artistique se fait dans un fichier, pas dans deux moteurs de rendu.

## Hors périmètre

Pas de fenêtre interactive. Pas de relief en
trois dimensions — ça, c'est `visualisateur/`, et ça demande forge3d.
