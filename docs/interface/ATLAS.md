# Le cabinet, papier et pigments

Les 108 références sont regardées sur les douze planches. Le conseil, les
greniers et l’imprimerie guident le contraste bois/papier ; les paysages, les
tissus et les blasons guident les couleurs mates et les ornements rares.
Noto Serif et Noto Sans sont embarquées avec leur licence
([TYPOGRAPHIE.md](TYPOGRAPHIE.md)). Les matières, les cadres et la cire sont
communs à tous les écrans ([MATIERES.md](MATIERES.md)).

La carte conserve les familles de couleurs politiques reçues, réduit leur
saturation et leur luminosité et pose une mer ardoise. Les libellés emploient
la même serif que les dossiers ; ceux qui se recouvrent se masquent à cette
échelle et réapparaissent au zoom. Aucun lieu n’est supprimé du monde. Les
signes de livre, bannière et bourg sont dessinés pour les commandes, avec leurs
libellés ; ce ne sont pas des armoiries historiques.

Le menu montre toute l’aide. Les feuillets laissent un espace au-dessus du
guide. La carte prend tout l’écran, vue d’en haut, nord en haut, sous la barre
du haut ; « Votre maison » s’ouvre de son icône, la fiche d’une terre d’un clic
sur elle, et chaque panneau se ferme de sa croix ; « Ma capitale » ramène la
vue sur le siège. Le sceau distingue l’engagement à
confirmer, les boutons grisés signalent l’indisponibilité.

## Le socle

La mer, la police des noms et le pigment vivent dans le socle
(`SocleInterface.Couleur("mer")`, `Police`, `Pigment`) : la carte ne pose
aucune couleur à elle. Un test vérifie que le pigment garde la teinte servie à
moins de 15° ; repeint d’une teinte fixe, il échoue. Les jetons et les
interdits sont dans [DA.md](DA.md).

La vérification visuelle porte sur 1080p ; le réglage à 150 % reste ouvert.
