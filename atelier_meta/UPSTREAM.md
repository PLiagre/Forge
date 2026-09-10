# Provenance de ForgeAtelier

Cette copie est epinglee a :

- depot : `PLiagre/ForgeHistory` ;
- branche source : `cursor/forgeatelier-ced6` ;
- commit : `dc52bb52d2ec8027864fd2d6c85b18813c28333b` ;
- date d'audit : 4 septembre 2026.

La branche est une histoire Git separee de `ForgeHistory/master` et doit etre
traitee comme le depot ForgeAtelier, jamais fusionnee dans le produit
ForgeHistory. Cette distribution embarque le runtime, les crons, les profils,
les skills, la documentation et les tests amont. Les fichiers de gouvernance et
les briefs de developpement propres au depot ForgeAtelier ne sont pas recopies ;
leur workflow CI est adapte dans la CI racine de CityLab.

Les ajouts `profiles/victoria-citylab.toml` et
`crons/profils/citylab.sh`, ainsi que la commande `atelier-boucle citylab`, sont
l'adaptation locale Victoria CityLab.

Le runtime amont porte encore deux limites documentees dans sa propre roadmap :
la porte `[projet].tests` n'est pas encore executee avant la relecture, et
l'etat distant d'une PR n'est pas encore rapproche automatiquement. CityLab
n'invente pas que ces deux lots sont livres.
