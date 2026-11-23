# Usine d'assets visuels — chaîne parallèle sur abonnement Google

Forge dispose d'une **chaîne visuelle parallèle** intégrée à `atelier` : dès
qu'un palier ou un lot de code a besoin d'icônes, de blasons, de textures PBR,
d'illustrations de DA ou de vues de référence 3D, le pilote ouvre
automatiquement un lot `asset` mené par le rôle **`artiste`** via le binaire
officiel **Antigravity CLI (`agy`)**, sur votre **abonnement Google AI Pro**
(zéro clé d'API, zéro consommation du quota Claude).

---

## 1. Activer l'usine sur le VPS (et le PC)

### Sur le VPS (chaîne 2D / PBR / DA, 24 h/24)
```bash
# 1. Installer le binaire officiel Antigravity CLI
curl -fsSL https://antigravity.google/cli/install.sh | bash

# 2. Se connecter une fois avec votre compte Google AI Pro
# (en SSH, agy affiche une URL d'autorisation à ouvrir sur votre navigateur local)
agy

# 3. Vérifier l'installation et l'absence de clé API payante
python3 -m atelier veille
python3 -m atelier sonde --role artiste
```

> **Sécurité et conformité** : la chaîne retire systématiquement
> `GEMINI_API_KEY`, `GOOGLE_API_KEY` et `NANOBANANA_API_KEY` avant chaque
> appel (`atelier/agents.py` et `atelier/crons/lib.sh`) et appelle uniquement
> le binaire officiel `agy`. Tant qu'`agy` n'est pas installé, la chaîne
> principale Claude continue normalement et les lots `asset` restent
> simplement en attente.

### Sur le PC Windows (optionnel, pour les lots `asset` + `pc` 3D)
```powershell
irm https://antigravity.google/cli/install.ps1 | iex
agy
```

---

## 2. Comment une demande est déclenchée et traitée

1. **Par le CTO** à l'ouverture d'un palier : une fiche avec `piste = "asset"`,
   `machine = "asset"` (ou `"pc"` pour la 3D) et `meneur = "artiste"`.
2. **Par un chef de lot ou un développeur** pendant son plan ou une étape :
   il renseigne `demandes_assets` dans sa sortie JSON. Le pilote déduplique
   contre `assets/manifeste.json` et les issues ouvertes, crée l'issue
   `lot` + `pret` + `asset`, et n'ajoute `Dépend de` au lot demandeur que si
   `bloquant = true`.
3. **Exécution en parallèle** : la file `[machines] asset = 1` et le plafond
   `[outils] antigravity = 1` sont indépendants des files `vps`/`pc` et du
   quota `claude`. En cas de quota Google épuisé (`RESOURCE_EXHAUSTED` /
   `QUOTA_EXHAUSTED`), le lot passe en attente sans échec et reprend
   automatiquement.

---

## 3. Le meilleur procédé par type d'asset

| Type | Procédé retenu | Commande locale (`atelier.fabrique`) |
|---|---|---|
| `planche_icones` | 1 appel `generate_image` en grille `3×3` ou `4×4` sur fond uni contrasté (9 à 16 icônes pour 1 crédit AI Pro) | `python3 -m atelier.fabrique decouper-planche <planche> --grille 3x3 --noms … --sortie <dir> --taille 128` |
| `icone` / `blason` | 1 image centrée sur fond uni contrasté, références `docs/interface/DA.md` | `python3 -m atelier.fabrique detourer <brut> <cible> --taille 128` |
| `texture_pbr` | 1 albedo orthographique sans ombre portée + synthèse locale (0 API) des 5 cartes `albedo/height/normal/roughness/ao` | `python3 -m atelier.fabrique pbr <brut> <dir> --nom <id> --taille 1024 --raccorder` |
| `illustration` | 1 image cohérente avec `docs/direction-artistique/README.md` | Enregistrement direct dans `assets/manifeste.json` |
| `prop_3d` | Vue 3/4 neutre produite par `agy`, puis maillage + 3 LOD + export FBX dans `3d/local3d/` (Blender 5.2 sur le PC) | Enregistrement et contrôle dans `assets/manifeste.json` |

### Note matérielle 3D (RTX 3070 Ti — 8 Go VRAM)
Les checkpoints complets de *TRELLIS.2* ou *Hunyuan3D* demandent 12 à 24 Go de
VRAM pour tourner à pleine résolution en local. Avec 8 Go de VRAM :
- la filière **2D / icônes / blasons / illustrations / textures PBR** tourne
  à 100 % sur le VPS via `agy` + `atelier/fabrique/` (aucun besoin GPU) ;
- pour les **props 3D**, privilégier d'abord **Blender 5.2 procédural**
  (`3d/local3d/`) habillé par les **textures PBR générées par l'usine**, ou
  un modèle Image-to-3D léger/quantifié en local (ex. variantes 8 Go) si vous
  souhaitez ajouter la reconstruction mesh sur le PC plus tard.

---

## 4. Contrôle automatique en CI

Chaque asset livré est inscrit dans `assets/manifeste.json` et contrôlé par :
```bash
python3 -m atelier.fabrique controler --strict
```
La CI (`.github/workflows/tests.yml`) échoue si un fichier manque, si les
dimensions divergent, si un asset transparent a un cœur translucide
(`alpha max < 255`), si un jeu PBR est incomplet ou si une texture raccordable
présente une couture visible.
