# fabrique/ — l'Asset Factory, hors Unity

Elle fabrique les modèles et les textures de la ville avec Blender, **sans
jamais lancer Unity**. C'est ce qui permet de la jouer sur une machine Linux,
en CI, et de rendre ses sorties déterministes : même recette, même graine,
même fichier au bit près.

| | |
|---|---|
| `citylab_factory.py` | l'outil : `doctor`, `scan`, `recipe-check`, `admission-check` |
| `publish_*.py` | les passes de publication, en dry-run par défaut |
| `qa_factory_release.py` | la QA transversale : UV, LOD, noms, budgets, licences |
| `donnees/` | les recettes, catalogues, manifests et rapports |

Ce qu'elle a déjà produit : 56 FBX, 24 prefabs de bâtiments, 8 personnages sur
un rig Humanoid partagé, et un trim sheet PBR 2048² en six cartes.

## Les règles qui la gouvernent

**Une source Vendor ne se modifie jamais.** Elle est inventoriée par SHA-256,
sa provenance et sa licence sont obligatoires, et seules des copies normalisées
entrent dans le jeu.

**La publication est en dry-run par défaut.** Rien n'est copié tant que
`publication-check` n'est pas appelé avec `--publish`. Une passe qui écrirait
par accident est une passe qu'on ne peut pas rejouer.

**L'auteur des assets ne signe pas leur réception.** L'approbation artistique
est un jugement humain ; aucune mesure technique ne le remplace. C'est le lot
205, et il est resté ouvert exprès.

## Ce qui ne marche pas encore ici

Les chemins internes des scripts visent encore la disposition de l'ancien
dépôt (`Tools/AssetFactory/`, `AssetFactory/`). Ils sont à recâbler sur
`fabrique/` et `fabrique/donnees/`. Ce n'est pas urgent : la fabrique ne peut
de toute façon rien produire tant que les binaires ne sont pas revenus — voir
[`../unity/README.md`](../unity/README.md) et le lot 101.
