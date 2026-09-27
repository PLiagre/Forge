# Contrat ForgeHistory ↔ City Mode — version 1

Statut : contrat, lifecycle de présentation et stratégie URP CityLab prêts à
être implémentés par l'hôte ; adaptateur ForgeHistory non disponible. Source
auditée en lecture seule :
`PLiagre/ForgeHistory@268e8aab151452b0c740a44a7cc97ca3fd37e311`
(`master`, observé le 13 août 2026).

**Amendement 21 août 2026 (ADR-0002).** La simulation de production des
villes appartient à ForgeHistory `sim/` (couche 2), pas à
`unity/game_unity` ni à `LocalCitySimulation`. CityLab reste le
laboratoire Unity et la vue. Le protocole v1 ci-dessous (contexte,
snapshot, intention, révision) ne change pas ; seul le propriétaire
amont de l'autorité économique est rappelé. Toute évolution de `sim/`
passe par `hermes/requests/`, jamais par un patch depuis ce dépôt.

## Décision

City Lab n'est plus un jeu autonome à porter scène par scène. Il devient une vue
ville chargeable par ForgeHistory. ForgeHistory reste l'unique propriétaire du
monde, de l'horloge, de la simulation et de la sauvegarde. City Mode possède la
présentation, les entrées utilisateur et un état de vue jetable. Toute action
métier traverse une intention corrélée ; toute donnée affichée provient d'un
snapshot révisionné.

La scène `Main.unity`, `MapDisplaySystem` et `PilotMapProvider` ont été audités
pour comprendre le point d'entrée, mais ne sont ni copiés ni modifiés depuis ce
dépôt. Les changements requis dans ForgeHistory sont consignés plus bas comme
demandes amont pour Hermes.

## Pourquoi un portage naïf échouerait

| Sujet | ForgeHistory audité | CityLab historique | Règle v1 |
|---|---|---|---|
| Autorité | simulation unique hors Unity exigée par `VISION.md` | `LocalCitySimulation` tourne dans Unity | ForgeHistory seul en production |
| Démarrage | carte principale `Main.unity` | bootstrap global `AfterSceneLoad` | création/destruction explicite par l'hôte |
| Identité | cellule/marqueur de carte | `cityId = 1001` et fixture locale | identifiants opaques fournis dans le contexte |
| Temps | horloge du monde | horloge/pause/vitesses locales | politique du monde explicite, jamais deux ticks |
| Sauvegarde | sauvegarde monde à construire/étendre | `CitySaveService` et autosave local | une seule sauvegarde ForgeHistory |
| Données | `StreamingAssets`, backend et providers | `Resources.Load` et snapshots CityLab | snapshot versionné fourni par l'hôte |
| Rendu | Built-in + Entities au commit épinglé | URP, Input System, AI Navigation | URP 17.0.4 retenu après prototype bit-identique ; Input/Navigation restent des adaptateurs |
| Chargement | ville non implémentée | scène/laboratoire autonome | transition asynchrone détenue par l'hôte |

## Matrice d'autorité

| Donnée ou action | Autorité de production | Copie City Mode | Persistance | Mutation |
|---|---|---|---|---|
| campagne, monde, graine | ForgeHistory | lecture dans le contexte | sauvegarde monde | jamais depuis la vue |
| `cityId`, cellule et appartenance | ForgeHistory | opaque, durée de session | sauvegarde monde | backend seulement |
| tick, date, saison, vitesse | ForgeHistory | snapshot | sauvegarde monde | intention si exposée |
| politique de temps pendant la vue | ForgeHistory | contexte immuable | contexte de vue | hôte seulement |
| population, foyers, emplois | backend ForgeHistory | snapshot révisionné | sauvegarde monde | intention |
| stocks, marchés, production | backend ForgeHistory | snapshot révisionné | sauvegarde monde | intention |
| bâtiments, parcelles, chantiers | backend ForgeHistory | snapshot révisionné | sauvegarde monde | intention |
| richesse, culture, crises, guerre | backend ForgeHistory | projection de snapshot | sauvegarde monde | intention/événement monde |
| caméra, sélection UI, panneaux | City Mode | autoritative pour la vue | optionnel dans contexte de retour | locale uniquement |
| catalogue visuel et LOD | hôte Unity | références chargées | manifeste de build | hôte/outillage |
| progression de chargement | hôte Unity | affichage | non persistée | hôte seulement |
| fichier de sauvegarde | ForgeHistory | aucun accès en production | atomique côté monde | ForgeHistory seulement |

`LocalCitySimulation`, `CitySaveService`, les fixtures `Resources` et le
bootstrap automatique restent autorisés dans l'adaptateur de laboratoire. Ils
doivent être absents ou inaccessibles dans une session hébergée.

## Protocole v1

Les contrats C# sont dans
`Packages/com.victoria.citymode.contracts/Runtime/ForgeHistoryCityModeContracts.cs`. Le
schéma filaire est
`Docs/Integration/Schemas/forgehistory-city-mode-v1.schema.json` et les exemples
sont adjacents. Les charges `payloadJson` sont opaques au transport afin que le
schéma métier ForgeHistory évolue séparément du cycle Unity.

### Ouverture

`CityLaunchContext` corrèle une session, une ville et une cellule à un tick et
une révision précis. Il transporte aussi le viewport de retour. Les identifiants
sont des chaînes opaques : City Mode ne leur applique aucune arithmétique.

La politique de temps est obligatoire :

| Valeur | Politique | Échelle |
|---:|---|---:|
| 1 | monde en pause pendant City Mode | 0 |
| 2 | monde à vitesse normale | 1000 |
| 3 | vitesse imposée par l'hôte | 1–4000 |

La première intégration doit utiliser `PauseWorld`. Les deux autres valeurs ne
deviennent acceptables qu'après preuve que le backend peut progresser pendant
le chargement et la vue sans divergence.

### Lecture

`CitySnapshotEnvelope` est un snapshot complet, identifié par `cityId`,
`worldTick` et `stateRevision`. Le SHA-256 porte sur les octets UTF-8 exacts de
`payloadJson`. Une révision ne peut jamais décroître au sein d'une session. Une
diff partielle est exclue de v1 pour privilégier la resynchronisation simple.

### Écriture

`CityIntentEnvelope` contient un `intentId` unique et la révision attendue. Le
backend applique l'intention de façon atomique ou la refuse. Rejouer le même
`intentId` ne réapplique jamais l'effet : il retourne le reçu original ou le
statut `Duplicate`.

`CityIntentReceipt` rend explicites acceptation, refus, duplicata et conflit de
révision. En conflit, City Mode relit un snapshot complet avant de proposer une
nouvelle intention ; il ne modifie jamais son état local pour masquer l'écart.

## Cycle de chargement

1. La carte ForgeHistory sélectionne un marqueur et capture son viewport.
2. L'hôte construit puis valide `CityLaunchContext`.
3. L'hôte applique la politique de temps avant tout chargement.
4. Il charge la scène et les catalogues City Mode de façon asynchrone.
5. Il fournit un snapshot complet et lie `ICityModeSnapshotSource` /
   `ICityModeIntentSink`.
6. City Mode devient interactif seulement après concordance ville/tick/révision.
7. À la sortie, l'hôte bloque les entrées, termine ou refuse les intentions en
   vol, libère les assets, restaure la carte et son viewport, puis reprend le
   temps selon sa politique.

Annulation, timeout, hôte indisponible et snapshot absent ramènent à la carte
sans créer de simulation ou de sauvegarde de secours. Une erreur interne garde
le dernier état autoritaire intact et fournit un message récupérable.

## Découpage de portage attendu

| Couche | Contenu | Importable dans ForgeHistory |
|---|---|---|
| contrats | DTO, validation, interfaces, session explicite, versions | oui, assembly sans Unity |
| présentation | lifecycle Unity host-owned et port `ICityModePresentationView` isolés ; caméra, HUD, vues et interpolation à brancher après convergence rendu | oui ; socle sans URP/Input/Navigation déjà prouvé dans l'hôte minimal |
| catalogues/assets | package `com.victoria.citymode.assets`, catalogues révisionnés, textures/FBX approuvés et LOD | oui par manifeste source→cible ; chargement `common→biome→city`, jamais par copie aveugle ni `Resources.Load` |
| adaptateur ForgeHistory | snapshot, intentions, lifecycle | côté hôte, après décision amont |
| adaptateur laboratoire | `LocalCitySimulation`, fixtures, save local | non dans le build intégré |

On ne porte donc pas `Main.unity` dans CityLab et on ne déplace pas la scène
CityLab entière dans ForgeHistory. Le package devient portable, puis l'hôte
compose une scène ville et choisit explicitement ses adaptateurs.

Le port v1 d'assets conserve les sources sous `Assets/CityLabHost`, crée des
GUID cible Unity distincts et versionnés dans le package portable, et consigne
hashes identiques, LFS, provenance et licence dans
`city-mode-asset-port-v1.json`. Les scènes de partition et leurs adresses
restent une responsabilité de l'hôte. Le package ne contient aucun Vendor
direct, transport, état monde, tick ou sauvegarde.

## Demandes amont à soumettre à Hermes

Ces demandes ne sont pas des changements dans ForgeHistory :

1. définir un `CityDescriptor` stable pour les marqueurs (ville, cellule,
   graine et capacité à ouvrir City Mode) ;
2. exposer depuis la carte une commande d'ouverture et un état de viewport
   sérialisable/restaurable ;
3. décider où vit le backend urbain et publier lecture de snapshot + application
   idempotente d'intention avec tick/révision ;
4. choisir la politique d'horloge pendant City Mode et pendant le chargement ;
5. intégrer l'état urbain à l'unique sauvegarde monde et à ses migrations ;
6. définir le transport runtime (in-process au départ recommandé) et la stratégie
   de reprise après perte de session ;
7. fournir un point d'extension Unity explicite pour charger/détruire City Mode ;
8. appliquer dans ForgeHistory la stratégie URP `17.0.4` et la matrice
   Entities/Burst/Collections/Mathematics prouvées par `M3-FH-03`, puis rejouer
   build, goldens et profil, importer le package d'assets au commit retenu et
   rejouer ses budgets avant toute migration importante de contenu.

Les incréments dépendants restent `BLOCKED` jusqu'à acceptation de ces points
par le propriétaire de ForgeHistory.

## Portes de validation

- validation C# pure sans référence Unity ;
- schéma et exemples JSON v1 cohérents ;
- contexte incomplet, révision négative et politique de temps incohérente
  refusés avant chargement ;
- snapshot sans hash et reçu statut/erreur incohérent refusés ;
- test de contrat Unity présent pour la future CI ;
- hôte Unity minimal sans scène/fixture/laboratoire, zéro auto-démarrage et une
  seule présentation explicite par session ;
- shell asynchrone piloté par un port d'hôte, rollback sur annulation/timeout/
  échec, double entrée refusée et restauration du viewport/sélection ;
- aucune mutation du dépôt ForgeHistory.

Commande hors Unity :

```bash
python3 -m unittest Tools.tests.test_forgehistory_city_mode_contract -v
python3 Tools/validate_forgehistory_city_mode_contract.py
```
