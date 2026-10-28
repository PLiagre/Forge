# Le cabinet, papier et pigments — 21 octobre 2026

Les 108 références ont été regardées sur les douze planches. Le conseil,
les greniers et l’imprimerie guident le contraste bois/papier ; les paysages,
les tissus et les blasons guident les couleurs mates et les ornements rares.
Noto Serif et Noto Sans sont embarquées avec leur licence (#715). Les matières,
les cadres et la cire sont communs aux écrans existants (#716).

Cette passe conserve les familles de couleurs politiques reçues, réduit
leur saturation et leur luminosité et pose une mer ardoise. Les libellés
emploient la même serif que les dossiers ; ceux qui se recouvrent se masquent
à cette échelle et réapparaissent au zoom. Aucun lieu n’est supprimé du monde.
Les signes de livre, bannière et bourg sont dessinés pour les commandes,
avec leurs libellés ; ce ne sont pas des armoiries historiques.

Le menu montre à nouveau toute l’aide. Les feuillets laissent un espace
au-dessus du guide. Maison, territoire et dossier restent visibles ensemble ;
la caméra conserve 67 % de la largeur au repos. Le sceau distingue l’engagement
à confirmer, les boutons grisés signalent l’indisponibilité.

## Preuves Unity

Code `cc1e581f`, Unity 6000.0.43f1, 1920 × 1080, vraie simulation en pause,
596 cellules. Captures regardées et corrigées après constat : pigments encore
trop clairs, noms trop grands, dernière ligne d’aide coupée, feuillet trop haut.

- [Partie](preuves/atlas-partie-cc1e581f.png) et [dossier](preuves/atlas-dossier-cc1e581f.png).
- [Menu](preuves/atlas-menu-cc1e581f.png) et [plan du bourg](preuves/atlas-bourg-cc1e581f.png).
- [Confirmation](preuves/atlas-confirmation-cc1e581f.png) et [habitants](preuves/atlas-habitants-cc1e581f.png).
- [64 tests verts et parcours de capture](preuves/atlas-cc1e581f.zip).

La suite du projet de contrôle inclut aussi les tests du dossier des chantiers
#713, qui reste une PR séparée. L’aperçu ne prétend pas intégrer la ville 3D
complète ni les futurs écrans dynastiques, diplomatiques ou militaires.
La vérification visuelle porte sur 1080p ; le réglage à 150 % reste ouvert.

## Reprise du 28 octobre 2026

Codex ne tourne plus (abonnement coupé le 26/10) : sa branche, jamais
poussée, est reprise telle quelle sur master, après les chantiers (#713) et
les lots #655–#658 de la chaîne. Le propriétaire garde les pigments ; la
révision de [DA.md](DA.md) le dit. La mer, la police des noms et le pigment
passent dans le socle (`SocleInterface.Couleur("mer")`, `Police`, `Pigment`) :
la carte ne pose plus de couleur à elle. Un test vérifie que le pigment garde
la teinte servie à moins de 15° ; repeint d’une teinte fixe, il échoue
(contre-épreuve jouée, deux rouges).

Code `e23b34bc`, Unity 6000.0.43f1 sur le PC, EditMode
`Forge.Interface.Tests;Forge.Pont.Tests` : **1016 verts** (92 d’interface,
924 du pont). Captures des scénarios de la chaîne (#655, #656, #657) et d’un
parcours du plan du bourg, vrai service, 1600 × 900, regardées :
[feuillet des comptes](preuves/atlas-reprise-feuillet-e23b34bc.png),
[part confirmée](preuves/atlas-reprise-part-e23b34bc.png),
[lieux et départs](preuves/atlas-reprise-lieux-e23b34bc.png),
[plan du bourg : Chantiers, Tracer une rue, Revenir](preuves/atlas-reprise-bourg-e23b34bc.png).

Constat à l’œil, laissé au lot « La carte et ses dossiers » (CAP.md, jalon 4) :
la légende des lieux (#657), posée en haut à gauche de la carte, passe sous
le feuillet ouvert de ce côté et sa première ligne dépasse, coupée. Ce défaut
est déjà sur master ; cette passe ne le crée ni ne le corrige.
