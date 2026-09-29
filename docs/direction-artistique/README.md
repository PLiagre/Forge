# Forge — direction artistique, 1400–1900

Collection de concepts originaux pour l’Europe et le pourtour méditerranéen.
Ouvrir `index.html` pour parcourir les images par catégorie, époque et région.
Le catalogue JSON conserve la consigne exacte de chaque génération.

## Intention

Faire sentir comment un domaine devient un État industriel : les habitants,
leurs bâtiments, leurs ressources et leurs transports changent ensemble.
Les scènes donnent autant de place au travail, aux stocks et aux voies de
ravitaillement qu’aux figures du pouvoir et aux armées.

Les références demandées orientent des qualités générales : la puissance
dramatique de Warhammer Fantasy, la présence humaine de Crusader Kings III,
la diversité historique d’Europa Universalis, les transformations de Victoria 3
et la vie matérielle de Manor Lords. Les compositions, personnages et emblèmes
sont des propositions propres à Forge.

## Grammaire visuelle

- Réalisme historique illustré, matières perceptibles, silhouettes lisibles.
- Lumière naturelle ; feu, forge et industrie apportent des accents localisés.
- Terre d’ombre, calcaire crème, bleu ardoise, vert mousse, rouge garance,
  cuivre patiné. La palette commune garde les différences régionales.
- Une construction repose sur des matériaux et des accès plausibles.
- Une activité laisse voir ses outils, ses stocks et ses moyens de transport.
- Les personnes ont un âge, un métier et une condition visibles ; leurs
  vêtements restent à l’échelle du corps et du travail.
- Les bâtiments anciens peuvent subsister dans les scènes tardives.

## Portée historique et usage

Niveau 2 : concepts plausibles, sans revendication de reconstitution sourcée.
Les dates situent les propositions ; les détails ne constituent pas une preuve
historique. Les maisons, dynasties et marques héraldiques sont fictives.
La marque circulaire de la Palmeraie est une invention marchande ; elle ne
prétend pas reproduire une tradition héraldique locale attestée.

Ces illustrations servent à choisir une direction, préparer les modèles 3D
et illustrer le projet. Elles ne sont pas des captures du jeu, des modèles 3D,
des textures raccordables ou des preuves de fonctionnalités déjà présentes.
Elles n’ajoutent aucune donnée au moteur et ne fixent pas les pouvoirs de 1400.

## Fabrication

Génération avec l’outil intégré `image_gen`, une consigne par image.
Les originaux PNG sont conservés dans les douze répertoires de catégories.
Les blasons et drapeaux demandent un fond transparent pour faciliter leur
réemploi. Les consignes et les propriétés réelles des fichiers sont dans
`catalogue.json`. Le contrôle technique est dans `controle.json`.

Livraison : 108 PNG distincts, neuf par catégorie, environ 320 Mo.
Définition habituelle : 1536 × 1024 ou 1024 × 1536 pixels.
Les 18 blasons et drapeaux possèdent un canal alpha de 0 à 254 : leur fond
est transparent, mais les motifs restent très légèrement translucides.
Le contrôle strict exigeant aussi des pixels à 255 reste donc en échec sur
ces 18 fichiers ; cette réserve est conservée, sans assouplir le contrôle.
Prévoir une finition du détourage avant une utilisation définitive en interface.
Les autres contrôles (présence, intégrité, définition et unicité) passent.
Quatre scènes ont reçu une retouche ciblée ; leurs consignes sont conservées
dans le champ `retouches` du catalogue, et leur fichier porte le suffixe `_v2`.

Les couples blason–drapeau reprennent neuf identités : Val-de-Rive,
Roche-Haute, Bois-Clair, Trois-Épis, Port-d’Ambre, Col-des-Vents,
Compagnie du Cuivre, Palmeraie et Union des Forges.
