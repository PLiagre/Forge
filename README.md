# Citadelle — Guerre

Batailles tactiques de 5 000 à 10 000 hommes autour d'une citadelle alpine
vers 1400. C'est un projet séparé de Forge (`../ForgeLocal3D`), qui n'est ni
modifié ni importé.

- **Pourquoi et quoi :** [VISION.md](VISION.md)
- **Où on en est :** [ROADMAP.md](ROADMAP.md)

## Lancer

| fichier | effet |
|---|---|
| `Jouer.cmd` | lance le joueur compilé |
| `Ouvrir_Unity.cmd` | ouvre le projet dans Unity 6000.0.43f1 |
| `Mesurer.cmd` | reconstruit, compile et passe les preuves des jalons 1 et 2, avec leurs contre-épreuves |

En jeu :
- **clic gauche** choisit un régiment bleu ; **glisser** trace une boîte ; **Maj + clic** ajoute ou retire ; **Ctrl + A** choisit toute l'armée ;
- **clic droit** y envoie le groupe, qui garde sa disposition ;
- **clic droit glissé** trace la ligne de bataille : sa longueur fixe le front, et les régiments font face au loin ;
- **Retour arrière** commande la halte ;
- **ZQSD** déplace la caméra ; **molette** zoome ; **A / E** ou **clic molette** tourne la caméra ;
- **F** revient à la vue générale ; **Espace** met en pause ; **H** masque l'aide.

## Commandes

```powershell
powershell -File outils/atelier.ps1 construire          # pipeline, vallée, scène
powershell -File outils/atelier.ps1 joueur              # + joueur Windows dans sorties/joueur
powershell -File outils/atelier.ps1 mesurer             # + preuves des jalons 1 et 2, et contre-épreuves
powershell -File outils/atelier.ps1 mesurer -soldats 20000
```

Tout ce qui est dans `unity/Assets/Guerre/Settings`, `Carte` et `Scenes` est
régénéré par `Construire.cs`. Pour une modification durable, changer le code.

## Architecture

| fichier | rôle |
|---|---|
| `Runtime/Composants.cs` | `Soldat`, `Regiment` et le relief lu par les jobs |
| `Runtime/Systemes.cs` | marche des régiments ; pilotage des soldats (place, élan, corps et appuis par grille spatiale) ; cohésion du régiment ; couleurs |
| `Runtime/Bataille.cs` | lève les armées dans le monde ECS ; transmet les ordres et reclasse les hommes |
| `Runtime/Commandement.cs` | caméra, sélection, ordres, tracés au sol, aide à l'écran |
| `Runtime/Mesure.cs` | mesure du jalon 1 dans le joueur, écrite dans `sorties/mesure/mesure.json` |
| `Runtime/Essais.cs` | essai du jalon 2 (formations, obstacle), écrit dans `sorties/essai-ordres/` |
| `Editor/Construire.cs` | URP Forward+, vallée, scène, build |

## Machine de référence

RTX 3070 Ti, i7-13700K, 1920 × 1080. Le budget d'image est de 16,67 ms au
95e centile, soit 60 images/s.

## Dépôt

Il est local et privé. Aucun pack de l'Asset Store n'y entre (`unity/Assets/Vendor/`
est ignoré).
