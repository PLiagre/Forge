# ville/ — le contrat entre le monde et sa vue ville

La frontière de données entre `jeu/sim/`, qui possède le monde, et `3d/unity/`,
qui le montre. Elle est du texte : schémas, exemples, matrice d'autorité — donc elle
se lit, se versionne et se teste sans ouvrir Unity.

| fichier | ce qu'il dit |
|---|---|
| `FORGEHISTORY_CITY_MODE_CONTRACT.md` | la décision, la matrice d'autorité, le protocole v1 |
| `CITY_MODE_HOST_API.md` | ce que l'hôte expose |
| `Schemas/forgehistory-city-mode-v1.schema.json` | le schéma filaire, JSON Schema 2020-12 |
| `Schemas/forgehistory-city-mode-v1.examples.json` | cinq exemples cohérents |
| `UNITY_RENDER_DEPENDENCY_MATRIX.md` | ce que le rendu exige de chaque côté |
| `cellule_du_desert.py` | la cellule par défaut du lanceur `pc\Jouer.cmd`, dérivée de la carte |

## La règle qui tient tout

**Une seule simulation.** Le monde appartient à `sim/` : les identités, le
temps, l'économie, la sauvegarde. La vue ville rend des snapshots versionnés,
collecte des intentions, et présente les reçus. Elle ne possède jamais une
seconde source de vérité.

Une intention est corrélée, idempotente, ordonnée par tick et révision, et
explicitement acceptée ou refusée. Rien ne s'applique en optimiste dans la vue.

## Ce que ce contrat attend encore

Rien que le moteur ne produise déjà : chaque message porte `cell_id`, l'entier
de `data/world-1400.json` et la seule clé spatiale de `sim/`
([`sim/MODELE.md`](../sim/MODELE.md)). Aucune identité de ville n'y figure.
`tests/` juge les exemples d'après le schéma lu.

Le lieu, subdivision de la cellule, existe : `GET /lieu?cell=N` porte `lieux`,
la liste des lieux de la cellule rangée par rang, chacun avec `rang`,
`surface_km2`, `population`, `stocks` et `maitre` (identifiant de maison, ou
`None` pour un état manuel). Son identité est le couple (`cell_id`
de la réponse, `rang`) : **dérivée** de `cell_id`, jamais une seconde clé ; un
lieu publié ne porte ni `cell_id` recopié ni `lieu_id`.

## La cellule par défaut du lanceur

`pc\Jouer.cmd` démarre le service de `sim/`, puis ouvre le jeu avec
`-forgeCell <cell_id>`. Sans autre indication, ce `cell_id` est calculé par
`cellule_du_desert.py` :

- **la règle** : la cellule dont `climat.insolation_annuelle_mj_m2` est la plus
  forte ; à égalité, le plus petit `cell_id` ;
- **pourquoi l'insolation** : la carte ne porte aucune température ; l'insolation
  annuelle est sa seule mesure de chaleur. La cellule la plus ensoleillée tombe
  au sud de la carte (niveau de fidélité 1) ;
- **les refus** : une cellule sans cette clé, ou une carte sans cellule, lève une
  `ValueError` qui nomme la clé et le `cell_id` ; aucune valeur par défaut,
  aucune cellule écrite à la main.

Le numéro n'est écrit nulle part : il se recalcule depuis les données.

```bash
py ville/cellule_du_desert.py      # depuis jeu/ : écrit le cell_id seul
```

Pour ouvrir une autre cellule : `pc\Jouer.cmd --cellule <cell_id>`.

Pour ouvrir le jeu sur la carte de 1400 : `pc\Jouer.cmd --carte` (lot #524). Le
lanceur passe `-forgeCarte` au jeu, qui quitte la ville au lancement pour la scène
`Forge_Carte`. On s'y déplace en glissant (bouton gauche ou du milieu) et on
zoome à la molette, vers le point sous la souris, sans sortir de la carte servie.
En haut à droite, la date et la vitesse du monde, lues au service (lot #525) :
Espace ou « Pause » arrête le monde et le relance à sa vitesse, + et − (ou les
boutons) passent d'un palier à l'autre (0,5 à 20 jours par seconde).
En bas à gauche, la fiche de la cellule sous la souris (lot #526) : ses villes,
sa puissance et sa maison lues dans `/carte`, ses habitants, sa faim et sa dette
lus dans `/monde`, avec le tick de cette lecture. Ce que le monde ne nomme pas ou
ne calcule pas, la fiche le dit.

## L'épreuve du jalon 1

Le panneau du lieu doit montrer les mêmes nombres que la photographie de `sim/`,
pour la même graine, le même tick et la même cellule. Depuis la racine du dépôt :

```bash
py pc\epreuve_jalon1.py --sortie <dossier>
```

La capture Unity lance le service de `sim/`, ouvre la scène du désert en Play,
écrit le texte du panneau, et le script le compare nombre par nombre à
`py -m sim --ticks N --seed S --snapshot-json`.

- **0** — égalité exacte : `verdict.txt` commence par `ÉGALITÉ` ;
- **1** — un écart : le verdict nomme chaque champ, la valeur du panneau et celle de la photographie ;
- **2** — l'épreuve n'a pas pu se jouer (Unity introuvable, port déjà pris, photographie ou capture absente ou antérieure à l'essai, service laissé ouvert).

La contre-épreuve pousse le service un tick plus loin que la photographie ; elle doit sortir **1** :

```bash
py pc\epreuve_jalon1.py --sortie <dossier> --decalage 1
```

La capture que la chaîne prend ensuite lance ce même service (sans choisir de cellule) : le panneau publié au journal porte les chiffres du monde, pas une absence.

## L'épreuve du jalon 4
Unity joue une route, une parcelle et une scierie ; Python rejoue leur journal. Ce n'est pas la preuve complète (#508). L'éditeur est fermé ; la scène et les données sont celles de #386 (`py local3d/atelier_desert.py terrain` depuis `3d/`).
```powershell
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-387-normal"
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-387-sourd" --service-sourd
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-387-locale" --ville-locale
```
**0** preuve valide. **1** invariant violé : le service sourd nomme « bâtiment absent » et « écart entre monde servi et monde rejoué » ; la ville locale nomme « empreinte des rues », « c'est le redessin qui échoue » et « l'égalité Python peut rester vraie ». **2** essai impossible (Unity, scène, port, délai, rapport absent ou ancien, exception dans les défauts) : une panne ne vaut pas contre-épreuve. Verdicts : [normal](../../docs/mesures/264-preuve-du-jalon-4/verdict.txt), [service sourd](../../docs/mesures/264-preuve-du-jalon-4/verdict-service-sourd.txt), [ville locale](../../docs/mesures/264-preuve-du-jalon-4/verdict-ville-locale.txt).

Le parcours Python, sans Unity, bâtit à Biskra après le choix appliqué de l'émirat du Zab. La cellule est celle du siège, lue dans la table. Le journal garde ce choix au tick 0, puis la route, la parcelle et le bâtiment aux ticks 2, 3 et 5. Le rejeu complet reprend les quatre entrées ; le témoin rejoue seulement le choix, au même tick.

```bash
python3 pc/epreuve_jalon4.py --sortie <dossier>
python3 pc/epreuve_jalon4.py --sortie <dossier> --service-sourd
```

**0** le départ est le même dans les trois mondes, Biskra porte les trois gestes, le service et le rejeu sont égaux à l'octet. **1** le service sourd : le bâtiment manque. Ces deux commandes sont celles que le lot #408 valide. La preuve Unity (`--avec-unity`, cellule 1175, sans le choix du Zab) n'est pas rejouée ici : un lot PC distinct, « La preuve Unity bâtit à Biskra après le choix du Zab », doit encore adapter la recette, les reçus et les parcours jouer, relance et vierge.

## L'épreuve de la carte

Le joueur peut se fier à sa carte (lot #527) : elle dessine autant de cellules
que `/carte` en sert, et la fiche d'une cellule dit `/carte` (villes, puissance,
maison) et `/monde` au même tick (habitants, faim, dette), nombre par nombre.
Depuis la racine du dépôt :

```bash
py pc\epreuve_carte.py --sortie <dossier> [--cellule C] [--ticks N] [--seed S]
```

Le script lance le service (en pause, poussé au tick N) et lit `/carte` et
`/monde` ; Unity ouvre `Forge_Carte` en Play (`ForgeLocal3D.EpreuveCarte.Jouer`),
survole la cellule C (par défaut celle du lanceur) et écrit `rapport.json` ; le
verdict, dans `verdict.txt`, cite chaque valeur des deux côtés. **0** égalité,
**1** écart, **2** épreuve impossible (Unity introuvable, port pris, référence
illisible, Unity en erreur, rapport absent ou antérieur à l'essai).

Les trois contre-épreuves doivent sortir **1** : `--decalage 1` (le service lu
par Unity a un tick d'avance), `--retirer-une-cellule` (Unity retire une cellule
du dessin) et `--sans-service` (le service s'arrête avant Unity : la carte dit
que le monde ne répond pas). Verdicts du 9 octobre 2026 :
[normal](../../docs/mesures/527-epreuve-de-la-carte/verdict-normal.txt),
[décalé](../../docs/mesures/527-epreuve-de-la-carte/verdict-decale.txt),
[cellule retirée](../../docs/mesures/527-epreuve-de-la-carte/verdict-retiree.txt),
[sans service](../../docs/mesures/527-epreuve-de-la-carte/verdict-sans-service.txt).
