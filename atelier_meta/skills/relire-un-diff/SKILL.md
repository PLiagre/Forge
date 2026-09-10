---
name: relire-un-diff
description: >
  Relire une PR en invocation neuve. Tu n'as pas écrit ce code et
  tu ne le corriges pas. Liste de constats, pas de correctif.
---

# Relire le diff

Tu n'as pas écrit ce code et tu ne le corriges pas.

Vérifie dans cet ordre :

1. le diff ne sort pas du « Périmètre » du brief ;
2. chaque condition de succès est réellement mesurée, pas affirmée ;
3. aucun test existant n'a été modifié, renommé ou relâché ;
4. aucun contrôle ne nomme sa propre référence, et aucun échantillon
   vide ne passe en silence.

Rends la liste des constats, du plus grave au plus léger, avec le
fichier et la ligne. Pas de correctif, pas de PR, pas de fusion.

Un constat étiquette ce qu'il avance : FACT, INFERENCE, ASSUMPTION
ou UNKNOWN. Un dissensus se conserve ; il ne se lisse pas en prose.
