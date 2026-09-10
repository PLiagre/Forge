# Convergence Unity, rendu et dépendances — M3-FH-03

Statut : stratégie retenue et prototype prouvé le 13 août 2026 sur
`PLiagre/ForgeHistory@268e8aab151452b0c740a44a7cc97ca3fd37e311`. Les essais
ForgeHistory ont été exécutés dans deux extractions `git archive` jetables ; le
dépôt amont est resté en lecture seule.

La décision versionnée et ses empreintes sont dans
`unity-render-convergence-v1.json`.

## Décision

Le build intégré cible **URP 17.0.4** sous Unity `6000.0.43f1`. La carte
ForgeHistory conserve son shader `Victoria/MapPolitical` et son chemin
UI Toolkit/`RenderTexture` : le prototype prouve qu'ils rendent sans modification
sous URP. City Mode ne force cependant aucune dépendance de rendu dans son cœur
portable ; le pipeline appartient à l'hôte Unity.

Cette convergence doit être appliquée dans ForgeHistory par son propriétaire.
CityLab ne modifie pas `Main.unity`, `GraphicsSettings.asset`, le manifeste ou le
shader amont.

## Matrice de packages

| Élément | ForgeHistory épinglé | Laboratoire CityLab | Cible intégrée | Règle |
|---|---:|---:|---:|---|
| Unity | `6000.0.43f1` | `6000.0.43f1` | `6000.0.43f1` | aucune montée moteur |
| Pipeline | Built-in | URP `17.0.4` | URP `17.0.4` | l'hôte possède le pipeline |
| Entities | `1.3.15` | absent | `1.3.15` | reste une dépendance ForgeHistory, jamais du cœur City Mode |
| Burst | `1.8.19` | lock `1.8.19` | `1.8.19` | version commune |
| Collections | manifeste `2.5.3`, lock `2.5.7` | lock `2.5.1` | `2.5.7` | la résolution Entities de l'hôte fait autorité |
| Mathematics | `1.3.2` | lock `1.3.2` | `1.3.2` | version commune |
| Input System | absent ; carte sur `UnityEngine.Input` | `1.13.1` | adaptateur ville optionnel | aucune référence dans contrats/présentation ; la carte garde son entrée héritée jusqu'à un pont hôte explicite |
| AI Navigation | module AI seulement | `2.0.6` | adaptateur de contenu optionnel | absent du cœur ; introduit avec les vues/assets qui en ont réellement besoin |
| Test Framework | `1.4.6` | `1.4.6` | `1.4.6` | version commune |

`com.victoria.citymode.contracts` ne dépend d'aucun package Unity et
`com.victoria.citymode.presentation` ne dépend que des contrats. Input System,
AI Navigation, URP et Entities restent donc des choix d'hôte ou d'adaptateur,
pas une dette transitive imposée au protocole.

## Prototype Built-in → URP

Deux copies propres du même commit ont exécuté `V1095GpuMapTests`. La copie URP
a ajouté `com.unity.render-pipelines.universal@17.0.4`, résolu Collections
`2.5.7`, créé un `UniversalRenderPipelineAsset` avec son renderer puis construit
le player Windows de `Main.unity`.

| Capture 960×720 | SHA-256 Built-in | SHA-256 URP | Résultat |
|---|---|---|---|
| `01_gpu_monde.png` | `CEB78A31…D99BA8` | `CEB78A31…D99BA8` | identique |
| `02_gpu_apres_conquete.png` | `86ED4E41…7717B` | `86ED4E41…7717B` | identique |
| `03_cpu_meme_fenetre.png` | `E2D95319…9B19B` | `E2D95319…9B19B` | identique |

Le test URP mesure 787 couleurs, 40,3 % de mer, 99,6 % d'accord terre/mer
GPU↔CPU et six verdicts verts. Le player URP construit pèse 178 175 782 octets.
Son parcours `--ui-capture-dir` sort avec le code 0 et produit un framebuffer
1920×1080 complet (HUD, labels et carte), hash
`21F05F3E…7EE0D`, avec 0 pixel magenta détecté. La capture ville de référence,
hash `A370D0FA…1B3B6`, contient elle aussi 0 pixel magenta.

## Profil CPU/GPU

Les mesures sont des diagnostics comparatifs sur la machine de session, pas des
budgets matériels définitifs :

| Chemin carte, ms/image | Built-in | URP | Budget |
|---|---:|---:|---:|
| blit GPU direct | 0,042 | 0,031 | 16,7 |
| chemin GPU réellement câblé | 1,475 | 0,266 | 16,7 |
| raster CPU équivalent | 126,247 | 101,512 | 16,7 |

Le GPU reste très sous le budget sous les deux pipelines. Le raster CPU ne
respecte pas 60 FPS et demeure uniquement la référence de comparaison/fallback.
L'empreinte du monde est identique avant/après le rendu, donc le prototype ne
déplace aucune autorité de simulation.

## Conditions de portage

1. Hermes ajoute URP `17.0.4` et un pipeline asset avec renderer dans
   ForgeHistory, puis rejoue les captures et le build avant fusion.
2. Le shader politique reste inchangé tant que ses goldens demeurent identiques ;
   tout remplacement doit conserver les trois hashes ou documenter une nouvelle
   baseline revue visuellement.
3. La carte conserve `UnityEngine.Input`. City Mode reçoit des actions via un
   pont d'hôte ; l'adaptateur Input System du laboratoire ne rejoint pas le cœur.
4. AI Navigation n'est importé qu'avec un catalogue ville qui en a besoin et
   reste absent de la carte et du package de présentation minimal.
5. Entities/Burst/Collections/Mathematics sont épinglés par l'hôte à la matrice
   ci-dessus. City Mode n'emploie pas ces types dans ses contrats publics.
6. Les matériaux CityLab portés à partir de `M3-FH-06` doivent être URP natifs et
   passer la détection de pixels magenta dans le player intégré.

Validation locale :

```powershell
py -3 Tools/validate_unity_render_convergence.py
py -3 -m unittest Tools.tests.test_unity_render_convergence -v
```
