# Lot #870 — Les mots du monde
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Le Pont sait écrire la date servie, une durée en jours, une masse en kilos ou en tonnes et un grand nombre de la même façon partout, cacher une raison d'absence qui montre un identifiant, et juger un texte qui laisse passer un identifiant ou un nombre sans unité.

## Le joueur
Partout où il lira son monde, le joueur lira des dates, des tonnes et des grands nombres écrits de la même façon : « jour 8 de 1400 » et non « tick 7 », « 41,7 t » et non « 41712 kg », « 5 631 habitants » avec son espace, « 12 jours ». Une absence lui dit « déclaré absent par le monde » au lieu d'un « lieu 10340-1 ». Il sent un registre tenu par un clerc, pas un relevé de machine. C'est un lot de fond, le premier des huit sous-lots de #856 « La fiche parle en noms » (`CAP.md`, jalon 4, « La prise en main de la carte »). Il prépare le geste du jalon : **trouver sa capitale, lire son grenier et sa part, puis descendre dans sa ville sans chercher**. Ce lot ne touche aucun écran. Les sous-lots suivants de #856 le rendront visible : la fiche de survol et le bandeau, le dossier du territoire, les comptes de la maison, les légendes, le plan et les chantiers. L'épreuve de #856 se servira de son juge.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service. La date écrite est celle que le service sert (`DateDuMonde`, lue par `ServiceLocal.Date`) : Unity ne la calcule jamais depuis un tick.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/TexteDuMonde.cs
3d/unity/Assets/ForgeLocal3D/Pont/TexteDuMonde.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TexteDuMondeTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TexteDuMondeTests.cs.meta
docs/briefs/870-les-mots-du-monde.md

Tout autre chemin est interdit, et les `.meta` sont générés par Unity. Aucun fichier de `Assets/Interface/`, aucun écran, aucune capture ni aucun test existant ne change. Budget : environ 80 lignes de classe, 100 de tests, 22 de `.meta` et 75 de brief.

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`, sur le PC, éditeur fermé, depuis la racine, en PowerShell. `PONT` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot870-pont.xml -logFile 3d/unity/Temp/lot870-pont.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et les cas nommés réellement exécutés : zéro cas est un échec. Les tests s'écrivent d'abord et se voient rouges avant le code.

`public static class TexteDuMonde`, espace de noms `Forge.Pont`. Les nombres s'écrivent avec un `NumberFormatInfo` posé à la main : virgule décimale et séparateur de milliers U+00A0. Jamais la culture `fr-FR` du système : selon le runtime, elle donne U+202F. Une entrée nulle lève `ArgumentNullException`, un nombre NaN ou infini `ArgumentException`. Les fonctions :
- `string Nombre(long n)` : « 5 631 », « 1 234 567 », « 12 » ; « -5 631 » pour un négatif ;
- `string Date(DateDuMonde d)` : « jour 8 de 1400 ». L'année n'a pas de séparateur. Un jour hors de 1…366 ou une année < 1 lève `ArgumentOutOfRangeException` ;
- `string Jours(long n)` : « 0 jour », « 1 jour », « 12 jours », « 1 234 jours ». Un négatif lève `ArgumentOutOfRangeException` ;
- `string Masse(double kg)` : une valeur qui, arrondie au centième, reste sous 1 000 s'écrit comme aujourd'hui (`0.##` et « kg »). Au-delà, elle passe en tonnes, à trois chiffres utiles comptés après arrondi : deux décimales sous 10 t, une sous 100 t, des tonnes entières avec séparateur à partir de 100 t. Un négatif garde la règle sur sa valeur absolue, précédé de « - » ;
- `string Interdit(string texte, params string[] identifiants)` : rend le premier mot interdit, tel qu'écrit dans le texte, ou `null`. Sont interdits : les mots entiers « Cellule », « rang », « tick », « ticks », sans tenir compte des majuscules ; un identifiant de lieu (`\d+-\d+` collé à aucun chiffre ni aucune lettre) ; chaque identifiant donné, en mot entier et en comparant à l'octet. Un identifiant nul ou blanc lève `ArgumentException`. « Premier » veut dire au plus petit indice dans le texte ;
- `string SansUnite(string texte)` : rend le premier nombre, tel qu'écrit, qui n'a ni unité ni place dans une date, ou `null`. Un nombre est une suite de chiffres qui ne suit ni une lettre ni un chiffre. Ses groupes de trois chiffres peuvent être séparés par U+00A0, U+202F ou une espace, et une partie décimale peut suivre après une virgule. Son unité suit, après une espace facultative (ordinaire ou U+00A0), et finit au bout du texte ou avant un caractère qui n'est pas une lettre. La liste des unités est fermée, à la casse près : kg, t, %, jour, jours, an, ans, habitant, habitants, foyer, foyers, personne, personnes, bras, lieu, lieux, maison, maisons, chantier, chantiers, km, m. Les deux nombres de « jour N de AAAA » (« jour » et « de » sans tenir compte des majuscules) sont à leur place ;
- `string Absence(string raison, params string[] identifiants)` : si `Interdit(raison, identifiants)` ou `SansUnite(raison)` trouve quelque chose, appelle `Debug.Log("TexteDuMonde : absence déclarée par le monde : " + raison)` et rend « déclaré absent par le monde ». Sinon, elle rend la raison telle quelle, sans rien écrire au journal. Une raison nulle ou blanche lève `ArgumentException`.

**SC1 — La date et les jours.** `PONT`, cas `LaDateServieSEcritEnJourDeLAnnee` et `LesJoursSAccordent`. `Date(new DateDuMonde(1400, 8))` vaut « jour 8 de 1400 » ; `(1401, 1)` vaut « jour 1 de 1401 » ; les jours 0 et 367 et l'année 0 lèvent l'exception. `Jours` rend exactement « 0 jour », « 1 jour », « 12 jours » et « 1\u00A0234 jours » ; -1 lève l'exception. `Nombre(5631)` vaut « 5\u00A0631 » et `Nombre(-5631)` « -5\u00A0631 ». Contre-épreuve : une date écrite « 1 400 » ou contenant « tick », ou « 1 jours », rougit.

**SC2 — Les masses.** `PONT`, cas `LesKilosPassentEnTonnesATroisChiffres`. Les valeurs exactes attendues : 0 donne « 0 kg », 12,5 « 12,5 kg », 999,5 « 999,5 kg », 999,996 « 1,00 t », 1 000 « 1,00 t », 1 234,5 « 1,23 t », 9 996 « 10,0 t », 41 712 « 41,7 t », 99 960 « 100 t », 123 456 « 123 t », 5 631 000 « 5\u00A0631 t », -1 234,5 « -1,23 t ». NaN et l'infini positif lèvent l'exception. Aucune sortie ne contient U+202F. Contre-épreuves : « 1234,5 kg », « 1000 kg », « 100,0 t » ou la culture `fr-FR` du système rougissent.

**SC3 — Le juge des identifiants.** `PONT`, cas `InterditTrouveLePremierIdentifiant`. Les cas qui passent (`null`) : « orange », « arrangé », « ticket », « jour 8 de 1400 », « 1,23 t », et « 103405 » avec l'identifiant « 10340 ». Les cas qui échouent, avec le mot attendu : « Cellule 7 » donne « Cellule », « CELLULE » « CELLULE », « tick 7 » « tick », « 3 ticks » « ticks », « 10340-1 » « 10340-1 », « lieu 10340-1 absent » « 10340-1 », « rang 2 de la Cellule 7 » « rang », « Paris, 10340 » avec l'identifiant « 10340 » donne « 10340 », « maison_bar » avec « maison_bar » donne « maison_bar ». « Maison_Bar » avec « maison_bar » passe. Un identifiant blanc lève l'exception. Contre-épreuve : un juge par `Contains` rougit sur « orange », un juge qui ignore les identifiants donnés rougit sur « Paris, 10340 ».

**SC4 — Le juge des unités.** `PONT`, cas `SansUniteTrouveLeNombreNu`. Passent : « 41,7 t », « 5\u00A0631 habitants », « 50 % », « 50% », « 12 jours », « jour 8 de 1400 », « Jour 8 de 1400 », « Mistra, J4 ». Échouent, avec le nombre attendu : « 5 631 » donne « 5 631 », « 5 631 Paris » « 5 631 », « Ville 7 » « 7 », « 12 kgx » « 12 », « 12,5 » « 12,5 », « de 1400 » « 1400 ». Puis chaque sortie de `Date`, `Jours` et `Masse` dans SC1 et SC2 passe `Interdit` et `SansUnite` ; `Nombre` seul n'a pas d'unité, l'écran la pose. Contre-épreuve : un juge qui accepte tout mot après un nombre rougit sur « 5 631 Paris », un juge qui coupe « 5 631 » en deux nombres rend « 5 » et rougit.

**SC5 — Une absence ne montre jamais un identifiant.** `PONT`, cas `UneAbsenceQuiNommeUnIdentifiantSeTait`. « lieu 10340-1 absent du service » et « Population absente du territoire 10340 » rendent « déclaré absent par le monde ». Avec l'identifiant « maison_bar », « maison_bar sans siège » le rend aussi. Chacun est attendu au journal par `LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : " + raison)`. « Maison en attente » revient telle quelle, et `LogAssert.NoUnexpectedReceived()` passe. Une raison blanche lève l'exception. Contre-épreuves : une raison rendue telle quelle, ou cachée sans journal, rougit.

**SC6 — Rien d'autre ne bouge.** Les commandes :
- `PONT` passe sur toute l'assemblée ;
- `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot870-interface.xml -logFile 3d/unity/Temp/lot870-interface.log` passe sans échec ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ;
- `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes.

Contre-épreuve : un écran, un test existant ou un fichier hors du Périmètre touché refuse la livraison.

## Hors périmètre
- Faire parler un écran : la fiche de survol, le bandeau, les dossiers, les légendes, le plan, les chantiers et les voisins (« il y a N jours ») sont les sous-lots suivants de #856, qui appelleront `TexteDuMonde`.
- Les noms servis des lieux et des terres (`ClientLieu`, `DocumentDuMonde`), l'épreuve de #856 et sa photo.
- Le service Python, le calcul d'une date depuis un tick, un mois ou un jour de la semaine.
- Les pourcentages de la part (« 50 % » reste écrit par les écrans) et toute autre unité que les kilos et les tonnes.

## Photo
sans objet : ce lot ajoute seulement une classe de texte et ses tests au Pont, sans changement de ce qu'on voit à l'écran ; aucun écran ne l'appelle encore. Les sous-lots suivants de #856 porteront leurs scénarios de capture, où les dossiers parleront en dates, en tonnes et en noms.
