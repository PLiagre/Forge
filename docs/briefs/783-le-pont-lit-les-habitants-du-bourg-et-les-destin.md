# Lot #783 — Le pont lit les habitants du bourg et les destinations servies
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Le pont Unity transmet les habitants du bourg, les débouchés des rues et les bras des chantiers publiés par le monde pour préparer une circulation fidèle à la capitale.

## Le joueur
Lot de fond découpé de #421 « Les gens du bourg circulent dans les rues » : il prépare le geste du J4, entrer dans sa capitale et y marcher parmi ses habitants, dans la ville que tient le monde. Le joueur pourra sentir que ses rues desservent des lieux réels et que ses chantiers occupent ses gens ; #421 rendra ces lectures visibles en faisant circuler les passants. Ce lot seul ne change rien à l'écran. Les données nécessaires existent déjà dans `/lieu` et `/plan`, notamment depuis #642 pour les bras du jour.

## Règle du monde
Sans objet : lecture de vue, sans nouvelle règle ni écriture dans le monde. Contrats de `jeu/sim/MODELE.md`, « Les lieux d'une cellule, vue dérivée », « Le plan du bourg », « Le plan de base » et « Le chantier et ses bras », de niveau 2 inchangé. L'identité reste le `cell_id` de l'enveloppe et le rang local ; le rang 0 est le bourg. La population cellulaire et les métiers cellulaires ne donnent pas sa population. Les rues de base peuvent viser une cellule voisine ; une route posée peut porter une porte commerciale. Les bras réellement employés viennent du relevé du dernier jour, jamais d'un quota de foyers, du travail cumulé ou de `en_chantier`.

Compléter les objets immuables et leur lecture, en gardant les signatures appelées actuellement (paramètres facultatifs ajoutés en fin ou surcharges) :

- `LieuPlace` expose `long? Population` et `string AbsenceDePopulation`. Lire `lieux[i].population` pour chaque entrée, dans l'ordre reçu : entier ≥ 0 et < 2^53. Clé absente : population nulle et raison nommant le chemin ; zéro présent : mesure, sans raison. Une valeur présente nulle ou invalide refuse toute la lecture. Le bourg se retrouve par `Rang == 0`, jamais par la première entrée ; sans ce rang ou sans sa population, aucun repli sur `Lieu.Population`, les métiers ou les maisons de base.
- `RueDeBase` expose `long? VersCellId`, lu dans `base.rues[i].vers_cell_id` ; `RueDuPlan` expose `long? PorteCellId`, lu dans `rues[i].porte_cell_id`. Clé absente ou `null` : aucun débouché déclaré vers une autre cellule ; entier ≥ 0 et < 2^53 : valeur exacte, zéro compris. Toute autre valeur refuse le plan avec son chemin. Ne déduire aucune porte des points ou de la sorte de rue.
- `PlanLu` expose `IReadOnlyList<ChantierDuJour> ChantiersDuJour` et `string AbsenceDesChantiersDuJour`. Clé `chantiers_du_jour` absente : liste nulle, raison nommant la clé ; tableau vide : liste vide présente, sans raison. Présent, le tableau est copié en lecture seule, sans tri ni filtre. Chaque entrée expose `Nature`, `Identifiant`, `Bras`, `GrainPayeKg`, `MotifArret` depuis les cinq clés exigées `nature`, `identifiant`, `bras`, `grain_paye_kg`, `motif_arret`. Nature non blanche parmi `rue`, `parcelle`, `batiment` ; identifiant et bras entiers ≥ 0 et < 2^53 ; kilos finis ≥ 0, sans arrondi ; motif nul ou texte non blanc, sans fermer la liste des motifs. Une entrée mal formée refuse tout le plan, chemin compris. Les trois natures peuvent partager le même identifiant ; un chantier achevé ce jour reste lisible, même si `en_chantier` est faux. Aucun recalcul de salaire ni rapprochement qui supprimerait cette observation.

Une donnée nouvelle absente ne rend pas les autres données illisibles. Les clés inconnues restent ignorées. Les anciens constructeurs déclarent les nouvelles mesures absentes ; ils ne fabriquent pas de zéros. Préserver intégralement les validations déjà présentes, dont celles du travail des parcelles et bâtiments. Aucun besoin d'ajouter les quotas de foyers ou les compteurs de travail des rues pour ce lot.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientLieu.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientPlan.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs
docs/briefs/783-le-pont-lit-les-habitants-du-bourg-et-les-destin.md

## Conditions de succès
SC1 — Rouge d'abord, puis tous les tests du pont verts. Sur le PC, depuis la racine, en PowerShell, avec Unity 6000.0.43f1 :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults "$env:TEMP\lot783.xml" -logFile "$env:TEMP\lot783.log"
```
Attendre la fin, sans `-quit` ; exiger un XML sans échec ni cas ignoré et les nouveaux cas réellement exécutés. Ajouter ces cas dans les deux fichiers existants, avec des témoins supplémentaires ; ne modifier aucun cas, aide, assertion ou témoin actuel. Avant l'implémentation, constater leur échec, y compris à la compilation pour les propriétés neuves. Contre-épreuve : zéro cas neuf exécuté, un XML absent ou un ancien cas rouge interdit la livraison.

SC2 — Population locale exacte. Commande : SC1. Un témoin non vide contient au moins deux rangs dans un ordre où le rang 0 n'est pas premier, des populations distinctes et un total cellulaire différent de celle du bourg. Vérifier chaque population et retrouver celle du rang 0 par son rang ; tester aussi zéro, 2^53 − 1, clé absente sur une seule entrée, liste vide et liste sans rang 0. Les absences restent déclarées, sans total de remplacement. Valeur `null`, négative, fractionnaire, booléenne, texte ou ≥ 2^53 : lecture absente, chemin `lieux[i].population` nommé. Contre-épreuves : remplacer la population locale par le total cellulaire, convertir une absence en zéro ou lire la première entrée comme bourg fait rougir les cas correspondants.

SC3 — Débouchés exacts et facultatifs. Commande : SC1. Nouveau témoin de plan avec deux débouchés distincts, l'un sous `base.rues`, l'autre sous `rues` ; comparer les valeurs exactes, puis tester pour chacun absence, `null`, zéro et 2^53 − 1. Tester négatif, fraction, booléen, texte et ≥ 2^53 : refus avec le chemin fautif, sans plan partiel. Les autres rues et la base restent exactement relues. Contre-épreuves : permuter les deux champs ou inventer une cellule d'après les points fait échouer les contrôles, notamment quand les mêmes points portent une autre destination servie.

SC4 — Relevé journalier complet. Commande : SC1. Nouveau témoin avec trois observations rue/parcelle/bâtiment portant le même identifiant et des bras et kilos distincts ; vérifier chaque champ exactement, l'ordre reçu, un paiement décimal non arrondi, un motif nul quand le chantier travaille, et deux zéros avec motif pour un arrêt. Une observation du chantier achevé reste présente. Tester clé racine absente, tableau vide et refus de mutation de la collection exposée. Contre-épreuves : confondre deux natures de même identifiant, supprimer le chantier achevé, recalculer les kilos au tarif courant ou remplacer une absence de relevé par une liste vide fait échouer ces cas.

SC5 — Faute nommée et renouvellement. Commande : SC1. Cas ajoutés : relevé `null` ou objet au lieu du tableau, entrée non objet, chacune des cinq clés retirée à son tour ; nature inconnue ou blanche, identifiant et bras négatifs, fractionnaires, booléens ou ≥ 2^53, kilos négatifs ou texte, motif blanc ou nombre. Exiger une absence totale avec le chemin fautif ; `1e309` est refusé comme JSON invalide par le lecteur existant. Chaque mutation doit changer le témoin et toucher la clé annoncée. Sur un même client, servir successivement des valeurs distinctes, puis des champs nouveaux absents, puis un statut 500 : aucune donnée précédente ne survit. Contre-épreuves : accepter une clé obligatoire manquante comme zéro ou conserver le premier relevé fait rougir ces mêmes cas.

SC6 — Compatibilité et taille. Commandes : SC1, `git diff --name-only`, `git diff --numstat`, `git ls-files --others --exclude-standard` et `git diff --check`. Compter aussi les fichiers neufs et le brief : moins de 300 lignes ajoutées et supprimées au total, budget 285 (environ 85 de lecteurs, 140 de tests et 60 de brief). Vérifier par le diff que les tests existants sont inchangés, notamment `LesAbsencesDeLieuxRestentDistinctesDesMesures`, `UnBatimentSansFoyersEstReluQuandMeme`, `UneRueSansEnChantierRefuseLePlan`, `UneParcelleOuUnBatimentMalFormeRefuseLePlan` et `UnPlanSansBaseEstLuEtDeclareLaBaseAbsente`. Les anciens témoins et constructeurs restent valides. Contre-épreuve : chemin supplémentaire, modification d'un cas actuel ou total ≥ 300 refuse la livraison.

## Hors périmètre
Le moteur, le service Python, ses contrats et ses tests ; toute règle de population, salaire ou destination ; les intentions ; le calcul des trajets, l'effectif et l'animation des passants de #421 ; tout panneau, scène, capture ou bâtiment ; l'enceinte et sa géométrie. Aucun test existant n'est réécrit ni assoupli. Tout autre chemin que ceux du Périmètre est interdit.

## Photo
sans objet : ce lot complète seulement les lecteurs de données et leurs tests, sans changement de ce qu'on voit à l'écran. #421 portera le scénario de capture qui montrera les gens du bourg circulant vers les destinations lues.
