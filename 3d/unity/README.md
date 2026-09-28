# unity/ — la vue ville

Le projet Unity de la vue ville, venu de Victoria CityLab. Unity
`6000.0.43f1`, pipeline URP `17.0.4`.

## Ce qui est là

| | |
|---|---|
| `Packages/com.victoria.citymode` | le laboratoire et les contrats portables |
| `Packages/com.victoria.citymode.contracts` | `ICityStateSource`, `ICityCommandSink`, le protocole v1 |
| `Packages/com.victoria.citymode.presentation` | la présentation, isolée du laboratoire |
| `Packages/com.victoria.citymode.assets` | le catalogue visuel |
| `ProjectSettings/` | les réglages du projet |

Le contrat de données vit à côté, dans [`../ville/`](../ville/) : schéma JSON
2020-12, cinq exemples, matrice d'autorité.

## Ce qui manque, et pourquoi

**Les binaires ne sont pas là.** `Assets/` pesait 199 Mo dans le dépôt
d'origine — FBX, textures, sons — tous en Git LFS. Le clone qui a servi à la
fusion ne portait que les **pointeurs** LFS, pas les objets : recopier ces
pointeurs aurait donné un projet qui référence des fichiers introuvables, ce
qui est pire qu'un projet incomplet, parce que ça se voit tard.

Ils restent donc à migrer depuis une machine qui les porte vraiment. C'est le
**lot 101** du registre. En attendant, ce dossier porte le code et les
contrats — qui sont du texte, donc intégralement transportables — et le projet
ne s'ouvre pas complet dans l'éditeur.

La migration, le jour venu :

```bash
git lfs install
git clone https://github.com/PLiagre/VictoriaCityLab
cd VictoriaCityLab && git lfs pull
# puis recopier Assets/ ici, et pousser avec LFS activé sur ce dépôt
```

## Ce que la vue ville attend du moteur

Rien de plus que ce qu'il produit : le contrat
([`jeu/ville/`](../../jeu/ville/README.md)) identifie chaque message par
`cell_id`, l'entier du monde et sa seule clé spatiale. Côté C#, le champ
s'appelle aussi `cell_id` et vaut `-1` tant qu'il n'est pas posé ; la
validation le refuse. Le lieu, subdivision de la cellule, viendra au jalon 3
avec une identité **dérivée** de `cell_id`, jamais une seconde clé.

## Les tests

Unity n'est pas sur une VM Linux. Les tests EditMode réels passent par un
worker Windows, sur le SHA exact, et le contrôle ne s'arme que si le lot touche
ce dossier.
