# viewer/

Regard mince sur une photographie `sim/`. Aucune logique métier : le
paquet lit un snapshot et montre les cellules déjà photographiées. Ce n'est
pas une seconde simulation.

Le regard local est un **tableau de bord** : carte au centre, bandeau de
totaux lus du snapshot, distribution de la couche active. Les chiffres
viennent de `/dashboard.json`, agrégat des cellules déjà présentes. Un
champ manquant s'affiche *absent* ; il n'est pas inventé.

## Preuve SVG (sans navigateur, sans serveur)

```
py -m sim --ticks 0 --seed 0 --snapshot-json /tmp/world.json
py -m viewer --snapshot /tmp/world.json --proof-svg /tmp/carte.svg
```

Comparaison de deux photographies :

```
py -m viewer --snapshot /tmp/a.json --compare /tmp/b.json --proof-svg /tmp/diff.svg
```

## Tableau de bord local (stdlib uniquement)

```
py -m sim --ticks 0 --seed 0 --snapshot-json /tmp/monde.json
py -m viewer --snapshot /tmp/monde.json
```

Hôte par défaut `127.0.0.1`, port `8765`. Si le port est pris, la commande
refuse (code 2) au lieu d'en choisir un autre en silence.

Pour comparer deux instants, photographier à part (le bandeau suit le
snapshot chargé, il ne resimule pas) :

```
py -m sim --ticks 20 --seed 0 --snapshot-json /tmp/monde-t20.json
py -m viewer --snapshot /tmp/monde-t20.json --port 8766
```

Le viewer ne recalcule rien, ne lit que le snapshot, et ne charge
aucune ressource réseau.

## La cellule découpée en lieux

Depuis `jeu/`, dessiner les lieux d'une cellule de la photographie :

```bash
python3 -m vues.tableau --snapshot /tmp/monde.json --cellule <id> --proof-svg /tmp/cellule.svg
```

Le clic sur une cellule affiche le même dessin, servi par `/cellule/<id>.svg`.
Le bourg est le rang 0 ; chaque carte porte la surface, les habitants et le
panier photographiés. La vue lit les lieux de la photographie, elle n'en
calcule aucun. Des lieux manquants s'affichent « lieux absents de la photographie » ;
des lieux illisibles sont refusés. `--cellule` refuse `--compare`.
