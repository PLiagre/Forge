---
name: executer-un-lot
description: >
  Exécuter un brief sur une branche agent/NNN-slug, dans un worktree.
  Le brief est la seule source d'instruction. Ne pas fusionner.
---

# Exécuter un lot

Le brief est ta SEULE source d'instruction. N'écris que dans les
fichiers que sa section « Périmètre » autorise ; tout autre chemin
est interdit.

Prouve le rouge d'abord : chaque contrôle nouveau doit échouer avant
que tu corriges quoi que ce soit. Cite la sortie en échec.

Avant d'ouvrir la PR, joue les commandes `tests` et `fumee` déclarées
par `atelier.toml` du dépôt produit.

Ouvre la PR. Ne juge pas ton travail, n'écris pas de compte-rendu,
ne fusionne rien.
