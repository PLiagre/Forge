# ROADMAP — où on en est

Ce fichier dit **où on en est** et **dans quel ordre on avance**. Il ne dit
jamais quoi faire pour un lot donné : ça, c'est le brief.

La destination vit dans [OBJECTIF.md](OBJECTIF.md) et prime en cas de conflit.
Le fonctionnement du monde vit dans [`sim/MODELE.md`](sim/MODELE.md). Les
règles vivent dans [AGENTS.md](AGENTS.md). La chaîne est décrite dans
[docs/WORKFLOW.md](docs/WORKFLOW.md).

**L'état d'un lot ne s'écrit qu'à un seul endroit : sa fiche, dans le
[registre](#le-registre-des-lots).** La prose de ce fichier raconte le monde ;
elle ne dit jamais qu'un lot est prêt ou livré. Si une phrase et une fiche se
contredisent, la fiche a raison et la phrase est à corriger.

---

## La V1 est atteinte

Ce dépôt est né de la fusion de trois projets. Sa première tâche était une
**V1 stable** : un dépôt, une chaîne, une simulation qui tient debout, et de
quoi la regarder. Les quatre conditions sont vertes.

| # | condition | ce qui la prouve |
|---|---|---|
| **V1-1** | un dépôt, une chaîne | `atelier.toml` déclare sept contrôles ; l'atelier vit dans l'arbre, plus sur une branche détachée ; un seul registre |
| **V1-2** | une simulation qui ne s'effondre pas | plafond de survie **1,250** ; sur une année simulée la population passe de 36 969 739 à 38 330 077, soit **+3,7 %** |
| **V1-3** | la carte de statistique | `python3 -m vues.relief --lecture population --carte carte.png` ; six lectures, quinze contrôles, aucun GPU requis |
| **V1-4** | les trois vues sur un snapshot | `python3 -m forge` écrit `monde.json`, `carte.png`, `tableau.svg` et `planche.html` depuis **une** simulation |

Ce qui reste hors V1, et l'ordre dans lequel ça vient, est plus bas.

### Ce que la V1 a réparé, chiffré

Avant la fusion, le monde amorçait **1,45 bouche pour chaque bouche que sa
terre nourrit** — plafond de survie 0,691 — et perdait 86 % de ses habitants
la première année simulée. Ce n'était pas une famine émergente : aucun
événement du jeu ne la causait. C'était l'amorçage, qui posait 10 habitants au
kilomètre carré sans jamais regarder ce que la terre produisait.

La population d'une cellule est maintenant **dérivée de ce que cette cellule
produit**, par la même et unique formule que le tick emploie. Mesuré :

| | avant | après |
|---|---:|---:|
| plafond de survie à l'amorçage | 0,691 | **1,250** |
| population à 365 ticks | 9 555 814 | **38 330 077** |
| part survivante après un an | 14 % | **104 %** |
| cellules affamées à 30 ticks | 238 | 15 |

Le monde ne survit plus : il croît, et quelques cellules souffrent — ce qui
est exactement ce qu'on attend d'un monde vivant.

---

## Les cinq couches

| # | couche | où on en est |
|---|---|---|
| 1 | **Monde vivant** — carte, terrain, climat, ressources, population, économie locale, commerce | **faite, et elle tourne** |
| 2 | **Villes** — subdivision en lieux, urbanisation, métiers, routes | **ouverte** — le métier, le bourg et la fabrication existent ; subdiviser reste |
| 3 | **États** — fiscalité, lois, diplomatie, technologies, culture, religion | non commencée |
| 4 | **Armées** — recrutement, logistique, ravitaillement, stratégie | non commencée |
| 5 | **Batailles tactiques** — sur les mêmes données que tout le reste | non commencée |

## Couche 1 — ce que le monde sait faire

La carte est **figée** : `data/world-1400.json`, un seul fichier lu par `sim/`.
Elle porte 596 cellules, leurs arêtes d'adjacence, le relief en cinq classes,
les déterminants du climat et les gisements nommés de 1400. Les compter se
fait par une commande, jamais en recopiant un nombre ici :

```bash
python3 -m sim --ticks 0 --json
```

Le tick joue, dans cet ordre : fabrication, extraction minière, production
agricole, commerce, consommation, faim, mortalité, natalité, migration. Le
monde compte les ticks qu'il a terminés et en dérive sa date depuis 1400. Le relief module
le rendement d'une cellule et le débit d'une arête ; le climat joue par la
durée du jour, donc par la saison ; les gisements font qu'une part des
habitants cesse de cultiver pour extraire — c'est le premier métier ; le
commerce transporte n'importe quelle marchandise, par terre et par mer ; la
population naît, meurt de faim et migre.

### Ce que le monde ne sait pas encore faire

Fabriquer, se dater et montrer le bourg ont été livrés — les fiches 049, 053,
051 et 052 le disent. Il reste une seule chose, et c'est la plus lourde :

- **Se subdivider.** Une cellule couvre 11 186 km² en moyenne — une région,
  pas un lieu. Tant qu'un lieu n'a pas d'identité stable, la ville ne peut
  pas se jouer. C'est le lot pivot, 122.

## Couche 2 — les villes, et le mur qui reste

Une ville est un endroit qui **ne produit pas ce qu'il mange**. Le métier
existe, la mer porte les marchandises, le bourg se compte, la matière se
façonne en objet, et les trois vues le montrent. Plus aucune condition
d'existence ne manque.

Puis vient le mur véritable, et il est d'échelle. `sim/MODELE.md` a tranché que
le bourg serait une **vue dérivée** — sans identité, sans `city_id` — et c'était
juste tant qu'on ne jouait pas dedans. Le contrat de la vue ville, lui, exige
une identité stable. La décision est prise dans `OBJECTIF.md` : **on subdivise
la cellule en lieux**. C'est le lot 122, et il touche la carte, le tick, les
trois vues et le contrat.

---

## Le registre des lots

**C'est ici, et seulement ici, que l'état d'un lot s'écrit.** Une machine le
lit : `python3 -m atelier feuille valider --projet .` refuse toute fiche mal
formée, tout numéro dupliqué, tout brief attendu qui manque, toute dépendance
qui n'existe pas. Un humain le lit aussi : une fiche par lot, deux lignes, et
**l'ordre des fiches est la priorité** — parmi les lots prêts, le premier de la
liste part le premier.

Les numéros portent leur origine : **001–099** le moteur et les vues,
**100–149** la fusion, **200–249** la ville et les assets (les lots de l'ancien
dépôt Unity, augmentés de 200 — 004 est devenu 204, 040 deviendra 240).

<!-- lots:debut -->

### [262 — Une PR de fiche en conflit est réécrite sur master](briefs/262-une-pr-de-fiche-en-conflit-est-reecrite-sur.md)
état : a-briefer · couche : — · dépend de : 256 · PR : —

### [261 — Les règles disent qui tient chaque geste](briefs/261-les-regles-disent-qui-tient-chaque-geste.md)
état : a-briefer · couche : — · dépend de : 256 · PR : —

### [256 — Une PR qui touche la zone protégée attend le propriétaire](briefs/256-une-pr-qui-touche-la-zone-protegee-attend-le.md)
état : a-briefer · couche : — · dépend de : — · PR : —

### [255 — Le relecteur rend un verdict, la machine pose la revue](briefs/255-le-relecteur-rend-un-verdict-la-machine-pose-la.md)
état : a-briefer · couche : — · dépend de : 241 · PR : —

### [258 — Les lots en vol sont bornés](briefs/258-les-lots-en-vol-sont-bornes.md)
état : a-briefer · couche : — · dépend de : 256 · PR : —

### [243 — Chaque carte du kanban nomme son geste suivant](briefs/243-chaque-carte-du-kanban-nomme-son-geste-suivant.md)
état : pret · couche : — · dépend de : 242 · PR : —

### [244 — Une carte qui ne se retente pas repart d'un cran, pas chez le propriétaire](briefs/244-une-carte-qui-ne-se-retente-pas-repart-d-un-cran.md)
état : a-briefer · couche : — · dépend de : — · PR : —

### [242 — La page de pilotage devient un kanban par état](briefs/242-la-page-de-pilotage-devient-un-kanban-par-etat.md)
état : livre · couche : — · dépend de : — · PR : 64

### [245 — Une PR fermée sans fusion décide elle-même du sort de son lot](briefs/245-une-pr-fermee-sans-fusion-decide-elle-meme-du.md)
état : a-briefer · couche : — · dépend de : — · PR : —

### [241 — L'atelier relit les PR brief et feuille](briefs/241-l-atelier-relit-les-pr-brief-et-feuille.md)
état : pret · couche : — · dépend de : — · PR : —

### [254 — La machine publie son battement](briefs/254-la-machine-publie-son-battement.md)
état : a-briefer · couche : — · dépend de : — · PR : —

## La ville du désert — vertical slice de city builder

### [263 — Le joueur trace une route qui épouse le relief](briefs/263-le-joueur-trace-une-route-qui-epouse-le-relief.md)
état : a-briefer · couche : — · dépend de : — · PR : —
note : attend la fusion de la V0 (branche v0/atelier-3d), qui apporte le terrain Unity. Plan : local3d/desert/VILLE.md, V1.

### [264 — Les routes se croisent en carrefours et forment un graphe](briefs/264-les-routes-se-croisent-en-carrefours-et-forment.md)
état : a-briefer · couche : — · dépend de : 263 · PR : —

### [265 — La caméra de city builder survole la ville et descend dans la rue](briefs/265-la-camera-de-city-builder-survole-la-ville-et.md)
état : a-briefer · couche : — · dépend de : — · PR : —

### [266 — Le kit de pisé s'emboîte sur la trame de 0,75 m](briefs/266-le-kit-de-pise-s-emboite-sur-la-trame-de-0-75-m.md)
état : a-briefer · couche : — · dépend de : — · PR : —

### [267 — Les matériaux photographiés remplacent les procéduraux](briefs/267-les-materiaux-photographies-remplacent-les.md)
état : a-briefer · couche : — · dépend de : — · PR : —
note : téléchargements CC0 (Poly Haven, ambientCG) à confirmer par le propriétaire.

### [268 — Une parcelle se découpe en lots et chaque lot reçoit sa maison](briefs/268-une-parcelle-se-decoupe-en-lots-et-chaque-lot.md)
état : a-briefer · couche : — · dépend de : 263, 266 · PR : —

### [269 — L'arrière-cour se remplit de vie](briefs/269-l-arriere-cour-se-remplit-de-vie.md)
état : a-briefer · couche : — · dépend de : 268 · PR : —
note : accessoires par IA payante seulement sur accord ; sinon liste de prompts et dossier d'import vérifié.

### [270 — L'enceinte suit le tracé du joueur et ses portes naissent des routes](briefs/270-l-enceinte-suit-le-trace-du-joueur-et-ses-portes.md)
état : a-briefer · couche : — · dépend de : 263, 266 · PR : —

### [271 — Les bâtiments singuliers se posent à la main et le ksar redevient le noyau](briefs/271-les-batiments-singuliers-se-posent-a-la-main-et.md)
état : a-briefer · couche : — · dépend de : 263 · PR : —

### [272 — Le chantier se voit pousser](briefs/272-le-chantier-se-voit-pousser.md)
état : a-briefer · couche : — · dépend de : 268 · PR : —

### [273 — Un habitant animé par textures se dessine mille fois](briefs/273-un-habitant-anime-par-textures-se-dessine-mille.md)
état : a-briefer · couche : — · dépend de : — · PR : —
note : Mixamo demande un compte Adobe ; sinon silhouette et marche fabriquées dans Blender.

### [274 — Les habitants et les bêtes circulent sur le graphe des routes](briefs/274-les-habitants-et-les-betes-circulent-sur-le.md)
état : a-briefer · couche : — · dépend de : 264, 268, 273 · PR : —

### [275 — La ville fume, sèche son linge, garnit ses étals et s'éclaire la nuit](briefs/275-la-ville-fume-seche-son-linge-garnit-ses-etals.md)
état : a-briefer · couche : — · dépend de : 268 · PR : —

### [276 — La ville dense tient 60 images par seconde](briefs/276-la-ville-dense-tient-60-images-par-seconde.md)
état : a-briefer · couche : — · dépend de : 268 · PR : —

### [277 — La lumière du désert : sondes, occlusion, brume et heure du jour](briefs/277-la-lumiere-du-desert-sondes-occlusion-brume-et.md)
état : a-briefer · couche : — · dépend de : 267 · PR : —

### [278 — La démo rejoue la partie et mesure la ville de fin de partie](briefs/278-la-demo-rejoue-la-partie-et-mesure-la-ville-de.md)
état : a-briefer · couche : — · dépend de : 264, 265, 269, 270, 271, 272, 274, 275, 276, 277 · PR : —
note : critère final : 400 à 600 maisons, 800 habitants, 95e centile sous 16,7 ms en 1920×1080 sur RTX 3070 Ti.

## Couche 1 — ce qui reste au monde

### [055 — Le monde nourrit ceux qu'il amorce](https://github.com/PLiagre/ForgeHistory/blob/master/briefs/055-le-monde-nourrit-ceux-qu-il-amorce.md)
état : archive · couche : 1 · dépend de : — · PR : —
note : livré par le commit de fondation, avant qu'aucune PR n'existe ici. Plafond de survie porté de 0,691 à 1,250 — c'est la condition V1-2. Son brief vit dans le dépôt d'origine, où il était resté orphelin.

### [051 — Le snapshot photographie le bourg](briefs/051-le-snapshot-photographie-le-bourg.md)
état : livre · couche : 2 · dépend de : — · PR : 22, 28

### [052 — Le regard mince montre le bourg](briefs/052-le-regard-mince-montre-le-bourg.md)
état : livre · couche : 2 · dépend de : 051 · PR : 37

### [049 — Fabriquer : le minerai devient un objet](briefs/049-fabriquer-le-minerai-devient-un-objet.md)
état : livre · couche : 2 · dépend de : — · PR : 40

### [053 — Le monde porte sa date](briefs/053-le-monde-porte-sa-date.md)
état : livre · couche : 1 · dépend de : — · PR : 58

### [054 — Cohérence globale : inventaire du produit face à la vision](briefs/054-coherence-globale-inventaire-produit-vision.md)
état : livre · couche : — · dépend de : — · PR : 26

## La fusion — ce qui reste à finir

### [100 — L'atelier redevient un dépôt à lui](briefs/100-atelier-depot.md)
état : idee · couche : — · dépend de : — · PR : —
note : l'atelier est vendorisé sous `atelier/` pour que la V1 tienne debout seule. Le détacher reste souhaitable si un second projet le consomme un jour.

### [101 — Les assets Unity rejoignent le dépôt](briefs/101-assets-unity.md)
état : idee · couche : — · dépend de : — · PR : —
note : le code Unity et les paquets sont là ; les 199 Mo de binaires LFS ne l'étaient pas dans le clone de fusion et restent à migrer depuis une machine qui les porte.

### [102 — La protection de master et la page de pilotage](briefs/102-protection-et-pages.md)
état : abandonne · couche : — · dépend de : — · PR : —
note : fait hors du cycle, et constaté le 19 septembre 2026 : `master` est protégée (sept contrôles requis, `enforce_admins`) et la page de pilotage est publiée par Pages. Ce n'étaient pas du code ; il n'y a plus rien à y faire.

### [103 — Un lot traverse le cycle entier](briefs/103-preuve-du-cycle.md)
état : abandonne · couche : — · dépend de : 102 · PR : —
note : fait par la chaîne elle-même. Le cycle entier a tourné sans main pour le lot 054 (PR 26, 17 septembre 2026) puis le lot 049 (PR 40) ; l'intégration a rejoué la PR 41 en retard le 19. Le dépôt d'un palier reste à voir, et le premier palier le montrera : ce n'est pas un lot à écrire.

## La carte, et ce qu'elle ne montre pas encore

### [104 — La géographie porte la statistique](briefs/104-statistique-sur-le-relief.md)
état : idee · couche : — · dépend de : — · PR : —
note : aujourd'hui la grandeur devient le terrain. Colorier les vraies montagnes par une grandeur indépendante demande un canal que forge3d n'expose pas dans la 1.36.

### [105 — La chronique montre la carte de statistique](briefs/105-chronique-et-statistique.md)
état : idee · couche : — · dépend de : — · PR : —

## Couche 2 — le lot pivot

### [122 — La cellule se peuple de lieux](briefs/122-la-cellule-se-subdivise.md)
état : idee · couche : 2 · dépend de : — · PR : —
note : le lot le plus lourd du projet. Il touche la carte, le tick, les trois vues et le contrat de la ville.

### [123 — Un lieu porte une identité stable](briefs/123-identite-du-lieu.md)
état : idee · couche : 2 · dépend de : 122 · PR : —

### [124 — La distribution intérieure cesse d'être gratuite](briefs/124-transport-interieur.md)
état : idee · couche : 2 · dépend de : 122 · PR : —

### [125 — Le modèle et le contrat de ville se réconcilient](briefs/125-reconcilier-modele-contrat.md)
état : idee · couche : 2 · dépend de : 123 · PR : —

## La ville et les assets — l'ancien dépôt Unity, augmenté de 200

### [204 — Vider la dette matière des orphelins](briefs/204-dette-matiere-orphelins.md)
état : pret · couche : — · dépend de : 202, 203 · PR : —

### [205 — Planche de contact C-10](briefs/205-planche-contact-c10.md)
état : pret · couche : — · dépend de : 203 · PR : —
note : jugement artistique humain ; aucune mesure technique ne le remplace.

### [207 — Ornement sous budget](briefs/207-ornement-sous-budget.md)
état : pret · couche : — · dépend de : 203 · PR : —

### [208 — Preuve Unity Windows](briefs/208-preuve-unity-windows.md)
état : pret · couche : — · dépend de : 203 · PR : —

### [206 — Carte MetallicGloss empilée](briefs/206-metallic-gloss-pack.md)
état : pret · couche : — · dépend de : 204, 208 · PR : —

### [209 — Approbation artistique Factory](briefs/209-approbation-artistique-factory.md)
état : pret · couche : — · dépend de : 205, 208 · PR : —

### [210 — Adaptateur snapshot/intention factice](briefs/210-adaptateur-sim-factice.md)
état : pret · couche : 1 · dépend de : — · PR : —

### [211 — Adaptateur de simulation réel](briefs/211-adaptateur-sim-reel.md)
état : idee · couche : 2 · dépend de : 210, 125 · PR : —

### [212 — Première ville intégrée](briefs/212-premiere-ville-integree.md)
état : idee · couche : 3 · dépend de : 211 · PR : —

### [213 — Usure, réparation et démolition](briefs/213-usure-reparation-demolition.md)
état : idee · couche : 3 · dépend de : 212 · PR : —

### [214 — Bible artistique](briefs/214-bible-artistique.md)
état : idee · couche : 3 · dépend de : 212 · PR : —

### [215 — Environnement et population](briefs/215-environnement-population.md)
état : idee · couche : 3 · dépend de : 214 · PR : —

### [216 — Agrégation LOD](briefs/216-aggregation-lod.md)
état : idee · couche : 2 · dépend de : 212 · PR : —

### [217 — Synchronisation carte-ville](briefs/217-synchronisation-carte-ville.md)
état : idee · couche : 2 · dépend de : 216 · PR : —

### [218 — Multi-ville](briefs/218-multi-ville.md)
état : idee · couche : 3 · dépend de : 217 · PR : —

### [219 — Streaming et cache](briefs/219-streaming-cache.md)
état : idee · couche : 3 · dépend de : 218 · PR : —

### [220 — Sauvegarde monde](briefs/220-sauvegarde-monde.md)
état : idee · couche : 2 · dépend de : 217 · PR : —

### [221 — Foyers et cycle de vie](briefs/221-foyers-cycle-vie.md)
état : idee · couche : 2 · dépend de : 212 · PR : —

### [222 — Santé et maladies](briefs/222-sante-maladies.md)
état : idee · couche : 2 · dépend de : 221 · PR : —

### [223 — Foi et sépulture](briefs/223-foi-sepulture.md)
état : idee · couche : 2 · dépend de : 221 · PR : —

### [224 — Ordre et criminalité](briefs/224-ordre-criminalite.md)
état : idee · couche : 2 · dépend de : 221 · PR : —

### [225 — Fiscalité et trésor](briefs/225-fiscalite-tresor.md)
état : idee · couche : 3 · dépend de : 221 · PR : —
note : premier lot de la couche « États » — c'est par lui que l'ascension du seigneur vers l'État devient jouable.

### [226 — Incendies et catastrophes](briefs/226-incendies-catastrophes.md)
état : idee · couche : 2 · dépend de : 221 · PR : —

### [227 — Parcours de huit heures](briefs/227-parcours-huit-heures.md)
état : idee · couche : 3 · dépend de : 212, 217, 220 · PR : —

### [228 — Tutoriel carte-ville](briefs/228-tutoriel-carte-ville.md)
état : idee · couche : 3 · dépend de : 227 · PR : —

### [229 — Sauvegarde robuste](briefs/229-sauvegarde-robuste.md)
état : idee · couche : 2 · dépend de : 220 · PR : —

### [230 — Contenu urbain](briefs/230-contenu-urbain.md)
état : idee · couche : 3 · dépend de : 212, 214 · PR : —

### [231 — Art final](briefs/231-art-final.md)
état : idee · couche : 3 · dépend de : 214, 215, 230 · PR : —

### [232 — Animations de production](briefs/232-animations-production.md)
état : idee · couche : 3 · dépend de : 215 · PR : —

### [233 — Audio de ville](briefs/233-audio-ville.md)
état : idee · couche : 3 · dépend de : 214 · PR : —

### [234 — UX et lisibilité](briefs/234-ux-lisibilite.md)
état : idee · couche : 3 · dépend de : 227 · PR : —

### [235 — Performance à 500 habitants](briefs/235-performance-500.md)
état : idee · couche : 3 · dépend de : 219, 227 · PR : —

### [236 — Équilibrage backend](briefs/236-equilibrage-backend.md)
état : idee · couche : 2 · dépend de : 212 · PR : —

### [237 — Régression intégrée](briefs/237-regression-integree.md)
état : idee · couche : 3 · dépend de : 227, 229, 235 · PR : —

### [238 — Accessibilité](briefs/238-accessibilite.md)
état : idee · couche : 3 · dépend de : 234 · PR : —

### [239 — Localisation français-anglais](briefs/239-localisation-fr-en.md)
état : idee · couche : 3 · dépend de : 228, 234 · PR : —

### [240 — Packaging City Mode](briefs/240-packaging-city-mode.md)
état : idee · couche : 3 · dépend de : 231, 232, 233, 236, 237, 238, 239 · PR : —

## Livrés avant la fusion — le code est là, les briefs vivent dans les dépôts archivés

### [201 — Kit matière et silhouette](briefs/201-kit-matiere-silhouette.md)
état : livre · couche : — · dépend de : — · PR : 29, 30

### [202 — Porte matière hors Unity](briefs/202-porte-matiere-unity.md)
état : livre · couche : — · dépend de : 201 · PR : 30

### [203 — Schémas de construction](briefs/203-schemas-de-construction.md)
état : livre · couche : — · dépend de : 201 · PR : 30, 31, 32, 33, 34

### [044 — Un métier : le mineur](https://github.com/PLiagre/ForgeHistory/blob/master/briefs/044-un-metier-le-mineur.md)
état : archive · couche : 2 · dépend de : — · PR : 184, 188

### [046 — La mer est un port commun](https://github.com/PLiagre/ForgeHistory/blob/master/briefs/046-la-mer-est-un-port-commun.md)
état : archive · couche : 1 · dépend de : — · PR : 206

### [047 — Le bourg est une agrégation dérivée](https://github.com/PLiagre/ForgeHistory/blob/master/briefs/047-le-bourg-est-une-agregation-derivee.md)
état : archive · couche : 2 · dépend de : — · PR : 214

### [048 — Tableau de bord : stats mêlées à la carte](https://github.com/PLiagre/ForgeHistory/blob/master/briefs/048-dashboard-stats-carte.md)
état : archive · couche : — · dépend de : — · PR : 201

### [050 — On migre aussi par la mer](https://github.com/PLiagre/ForgeHistory/blob/master/briefs/050-on-migre-aussi-par-la-mer.md)
état : archive · couche : 1 · dépend de : — · PR : 243

<!-- lots:fin -->

---

## Le cycle d'un lot

Les six états, les transitions permises, le palier et ce qu'on fait quand ça
casse sont décrits dans [docs/WORKFLOW.md](docs/WORKFLOW.md), avec le schéma.
Ce fichier ne les paraphrase pas.

---

## D'où vient ce dépôt

Trois dépôts et un outil orphelin y ont été réunis :

| origine | ce qu'elle a apporté |
|---|---|
| **ForgeHistory** | le moteur `sim/`, la carte, les trois vues, la chaîne d'intégration, les briefs |
| **VictoriaCityLab** | les paquets Unity, le contrat de la vue ville, la fabrique d'assets, 40 lots |
| **forge3d** | rien — c'est un fork intact de l'amont, consommé comme dépendance épinglée |
| **ForgeAtelier** | l'invocation des agents, qui n'était un dépôt nulle part : une branche détachée d'un côté, une copie vendorisée de l'autre |

Les deux dépôts d'origine restent en lecture, et les fiches `archive`
ci-dessus pointent leurs briefs.
