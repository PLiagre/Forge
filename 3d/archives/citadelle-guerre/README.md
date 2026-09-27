# Citadelle — Guerre

Batailles tactiques de 5 000 à 10 000 hommes autour d'une citadelle alpine
vers 1400. C'est un projet Unity à part, rangé dans le dépôt Forge le
27 septembre 2026 et **archivé** sous `3d/archives/citadelle-guerre/` : il
attend le jalon 6 de [CAP.md](../../../CAP.md) (la colonne), dont il sera la
base. Il ne lit pas `jeu/sim/`, et Forge ne le lit pas.

- **Pourquoi et quoi :** [VISION.md](VISION.md)
- **Où on en est :** [ROADMAP.md](ROADMAP.md)

## Lancer

| fichier | effet |
|---|---|
| `Jouer.cmd` | lance le joueur compilé |
| `Ouvrir_Unity.cmd` | ouvre le projet dans Unity 6000.0.43f1 |
| `Mesurer.cmd` | fabrique les soldats, reconstruit, compile et passe les preuves des jalons 1 à 8, avec leurs contre-épreuves (environ 50 min) |

En jeu :
- **clic gauche** choisit un régiment bleu ; **glisser** trace une boîte ; **Maj + clic** ajoute ou retire ; **Ctrl + A** choisit toute l'armée ;
- **clic droit** y envoie le groupe, qui garde sa disposition ; **sur un régiment rouge**, il l'attaque (des arbalétriers s'approchent à portée et tirent) ;
- **clic droit glissé** trace la ligne de bataille : sa longueur fixe le front, et les régiments font face au loin ;
- **Retour arrière** commande la halte ;
- **ZQSD** déplace la caméra ; **molette** zoome ; **A / E** ou **clic molette** tourne la caméra ;
- **F** revient à la vue générale ; **Espace** met en pause ; **H** masque l'aide.

## Commandes

```powershell
powershell -File outils/atelier.ps1 soldats             # soldats modelés et animés dans Blender 5.2
powershell -File outils/atelier.ps1 construire          # + pipeline, vallée, scène
powershell -File outils/atelier.ps1 joueur              # + joueur Windows dans sorties/joueur
powershell -File outils/atelier.ps1 mesurer             # + preuves des jalons 1 à 8, et contre-épreuves
powershell -File outils/atelier.ps1 mesurer -soldats 20000
```

Tout ce qui est dans `unity/Assets/Guerre/Settings`, `Carte` et `Scenes` est
régénéré par `Construire.cs`. Pour une modification durable, changer le code.

## Architecture

| fichier | rôle |
|---|---|
| `fabrique/soldats.py` | soldats et cavalier modulaires, squelettes, allures cuites en `.vat` (Blender) |
| `Shaders/Soldat.shader` | rejoue l'animation cuite sur le GPU, instance par instance |
| `Runtime/Composants.cs` | `Soldat`, `Regiment`, `AnimEtat` et le relief lu par les jobs |
| `Runtime/Systemes.cs` | marche des régiments ; pilotage des soldats (place, élan, corps et appuis par grille spatiale) ; cohésion du régiment ; couleurs |
| `Runtime/Bataille.cs` | lève les armées dans le monde ECS ; transmet les ordres et reclasse les hommes |
| `Runtime/Commandement.cs` | caméra, sélection, ordres, tracés au sol, aide à l'écran |
| `Runtime/Mesure.cs` | mesure du jalon 1 dans le joueur, écrite dans `sorties/mesure/mesure.json` |
| `Runtime/Essais.cs` | essai du jalon 2 (formations, obstacle), écrit dans `sorties/essai-ordres/` |
| `Runtime/EssaisMelee.cs` | essai du jalon 4 (trois duels de profondeur), écrit dans `sorties/essai-melee/` |
| `Runtime/Rangs.cs` | reclassement des hommes après un ordre ou des pertes |
| `Runtime/EssaisMoral.cs` | essai du jalon 5 (vingt épreuves de flanc et de réserve), écrit dans `sorties/essai-moral/` |
| `Runtime/SystemePavois.cs` | les pavois : plantés, laissés, repris, tombés |
| `Runtime/EssaisTir.cs` | essai du jalon 6 (salve de masse, tir tendu contre pavois), écrit dans `sorties/essai-tir/` |
| `Runtime/EssaisCavalerie.cs` | essai du jalon 7 (vingt charges, sur un rang non préparé ou sur des piques), écrit dans `sorties/essai-cavalerie/` |
| `Runtime/Carte.cs` | données de la carte, grille des obstacles au mètre, routes des régiments, planificateur (A* avec dégagement) |
| `Runtime/EssaisCarte.cs` | essai du jalon 8 (parcours de la vallée, du pont et des rues), écrit dans `sorties/essai-carte/` |
| `Editor/ConstruireCitadelle.cs` | l'éperon, le ravin et le pont ; l'enceinte, les rues, la cathédrale et les maisons, avec le kit de Forge |

La simulation avance à pas fixe (60 pas par seconde simulée) : ses issues ne dépendent pas
de la cadence d'affichage.
| `Editor/Construire.cs` | URP Forward+, vallée, scène, build |
| `Editor/ImportSoldats.cs` | `.vat` → maillage, texture d'animation, matériau |

## Machine de référence

RTX 3070 Ti, i7-13700K, 1920 × 1080. Le budget d'image est de 16,67 ms au
95e centile, soit 60 images/s.

## Dépôt

C'est le dépôt Forge, qui est public. Aucun pack de l'Asset Store n'y entre
(`unity/Assets/Vendor/` est ignoré). Les images, les FBX et les gros assets
Unity sont en LFS.

## Le kit de la Citadelle

Les murs, les tours, la porte, le pont, les maisons, la cathédrale et les sapins
viennent du kit de la Citadelle de Forge. `Construire.cs` les relit à chaque
construction dans `3d/local3d/citadelle/sorties` du dépôt (sans jamais
y écrire) et les copie dans `unity/Assets/Guerre/Kit/`, qui n'entre pas dans git :
le kit appartient à Forge. Les textures du kit (`sorties/textures/`) ne sont pas
versionnées : elles sont refaites par la fabrique Blender de la Citadelle. Sans
elles, la construction s'arrête.
