# État de l’interface — 28 octobre 2026

## Livré

- Direction artistique validée : papier clair sur cadre sombre, ornements discrets, plusieurs dossiers simultanés. Les 108 références ont été regardées ; [DA](DA.md). Révisée le 28 octobre (#839) : pierre, bois brûlé, registre ; ses lots sont dans [CAP.md](../../CAP.md), « La langue visuelle ».
- Socle et états de lecture (#630–631), choix confirmé de maison (#633), cabinet de carte et matériau compilé (#666–667).
- Lecture fiable et dossiers de territoire (#668–669), confirmation unique des intentions (#670), terres et comptes (#671), menu, aide et navigation clavier (#672).
- Calques puissances/habitants (#673), journal réel des autres maisons (#674), plan consultable du bourg avec retour à la carte (#677).
- Prélèvement et secours (#676), avec confirmation et reçu du monde ; [preuve](COMMANDES.md). Tracé de rue sur le plan du bourg (#708) ; [preuve](RUE.md).
- Polices Noto embarquées avec leur licence (#715) ; papier, cadres et cire du cabinet (#716) ; [MATIERES.md](MATIERES.md).
- Par la chaîne : le panneau « Ma maison » avec sa part, son grenier et ses trente jours (#757), le curseur de part et le bouton du grenier (#759), les lieux à la couleur de leur maître (#760), les flèches vers le siège et le suzerain (#761) ; le jeu s’ouvre sur la carte (#747), un double-clic sur son siège descend dans sa ville et une touche en remonte (#748, #749).
- Dossier des chantiers (#713) : travail fourni et requis, grain payé, motifs d’arrêt ; [preuve](CHANTIERS.md).
- Carte apaisée, reprise de la passe Codex du 21 octobre : pigments mats qui gardent la teinte servie, mer ardoise, noms en serif qui ne se chevauchent plus, signes des commandes, menu et feuillets sans coupure ; [preuve](ATLAS.md).

Contrôle du 28 octobre, code de la passe atlas : 1016 tests Unity verts (92 d’interface, 924 du pont), captures du vrai cabinet regardées.

## Défauts connus

- La légende des lieux (#657) passe sous le feuillet ouvert à gauche et sa première ligne dépasse, coupée ([capture](preuves/atlas-reprise-feuillet-e23b34bc.png)). Confié au lot « La carte et ses dossiers ».
- `LieuxDeCarte` et `FlechesDeCarte` posent encore leurs couleurs hors du socle (rouge, orange, violet) ; même lot.
- L’aperçu Windows compilé par Codex (17 et 21 octobre, hors du dépôt) ne contient ni les chantiers ni les lots de la chaîne : le jeu se lance par `pc\jouer.py --carte`.

## Prochaine étape

1. Les lots de la langue visuelle (CAP.md, jalon 4) : le cabinet, puis la carte et ses dossiers, puis la capitale et ses outils ; au jalon 9, le siècle dans une seule langue.
2. Les parcelles, bâtiments et l’enceinte depuis le plan du bourg ; le coût d’un chantier (#419).
3. Les écrans dynastiques, diplomatiques, militaires et les autres contrats absents, dans une démonstration explicitement séparée, comme demandé dans [BESOINS-SIM.md](BESOINS-SIM.md).

Le relief, les trajets détaillés et les contrôles de lisibilité à toutes les tailles restent ouverts. Toute l’interface n’est pas terminée. Aucun changement de la simulation dans ces branches.
