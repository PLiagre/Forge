# Règles du projet

- Lire [VISION.md](VISION.md) et [ROADMAP.md](ROADMAP.md) avant de toucher au code.
- Ce projet ne modifie jamais `../ForgeLocal3D`. Il peut le lire.
- Un jalon est fait seulement si `outils/atelier.ps1 mesurer` est vert dans le
  joueur compilé et que sa contre-épreuve échoue.
- L'émergence plutôt que la règle : pas de modificateur de moral ou de dégâts
  écrit en dur. Le comportement vient des soldats.
- Les scènes, la vallée et les réglages sont générés par `Editor/Construire.cs` :
  modifier le code, pas les assets.
- Aucun pack sous licence dans git.
