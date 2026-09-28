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
([`sim/MODELE.md`](../sim/MODELE.md)). Aucune identité de ville n'y figure. Le
lieu, subdivision de la cellule, viendra au jalon 3 avec une identité
**dérivée** de `cell_id`, jamais une seconde clé. `tests/` juge les exemples
d'après le schéma lu.
