---
name: isoler-un-worktree
description: >
  Un agent, un worktree, une branche. Trois agents sur le même clone
  se marchent dessus.
---

# Isoler un worktree

Avant d'écrire quoi que ce soit :

```bash
python3 -m atelier start briefs/NNN-slug.md --projet . --run
```

Ça crée le worktree, pose le verrou de fichiers, ouvre le canal
d'échange. L'agent ne sort pas de ce répertoire.

Lot fusionné par le propriétaire : retirer le worktree, lever le
verrou. L'atelier ne fusionne pas.
