# Règles du projet

- Lire [VISION.md](VISION.md) et [ROADMAP.md](ROADMAP.md) avant de toucher au code.
- Ce projet vit dans le dépôt Forge, archivé sous `3d/archives/citadelle-guerre/`
  jusqu'au jalon 6 de [CAP.md](../../../CAP.md). Il lit le kit de la Citadelle
  dans `3d/local3d/citadelle/sorties` du même dépôt ; il ne le modifie jamais.
- Un jalon est fait seulement si `outils/atelier.ps1 mesurer` est vert dans le
  joueur compilé et que sa contre-épreuve échoue.
- L'émergence plutôt que la règle : pas de modificateur de moral ou de dégâts
  écrit en dur. Le comportement vient des soldats.
- Les scènes, la vallée et les réglages sont générés par `Editor/Construire.cs` :
  modifier le code, pas les assets.
- Aucun pack sous licence dans git.
