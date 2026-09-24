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
| `Mesurer.cmd` | reconstruit, compile et mesure le jalon 1, avec sa contre-épreuve |

En jeu :
- **clic gauche** choisit un régiment bleu ;
- **clic droit** l'envoie à un point ;
- **ZQSD** déplace la caméra ;
- **molette** zoome ;
- **A / E** ou **clic molette** tourne la caméra ;
- **F** revient à la vue générale ;
- **Espace** met en pause ;
- **H** masque l'aide.

## Commandes

```powershell
powershell -File outils/atelier.ps1 construire          # pipeline, vallée, scène
powershell -File outils/atelier.ps1 joueur              # + joueur Windows dans sorties/joueur
powershell -File outils/atelier.ps1 mesurer             # + mesure du jalon 1 et contre-épreuve
powershell -File outils/atelier.ps1 mesurer -soldats 20000
```

Tout ce qui est dans `unity/Assets/Guerre/Settings`, `Carte` et `Scenes` est
régénéré par `Construire.cs`. Pour une modification durable, changer le code.

## Architecture

| fichier | rôle |
|---|---|
| `Runtime/Composants.cs` | `Soldat`, `Regiment` et le relief lu par les jobs |
| `Runtime/Systemes.cs` | marche des régiments ; pilotage des soldats (place, élan, écart aux voisins par grille spatiale) ; couleurs |
| `Runtime/Bataille.cs` | lève les armées dans le monde ECS |
| `Runtime/Commandement.cs` | caméra, sélection, ordres, aide à l'écran |
| `Runtime/Mesure.cs` | mesure dans le joueur, écrite dans `sorties/mesure/mesure.json` |
| `Editor/Construire.cs` | URP Forward+, vallée, scène, build |

## Machine de référence

RTX 3070 Ti, i7-13700K, 1920 × 1080. Le budget d'image est de 16,67 ms au
95e centile, soit 60 images/s.

## Dépôt

Il est local et privé. Aucun pack de l'Asset Store n'y entre (`unity/Assets/Vendor/`
est ignoré).
