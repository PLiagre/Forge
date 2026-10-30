# Lot #911 — Le juge de la carte écrit comme le clerc
Jalon : J4 · Machine : vps · Taille prévue : 190 lignes

## But
Le juge de l'épreuve de la carte sait écrire, à l'octet, un nombre, une durée, une masse et une date comme `TexteDuMonde`, et sait lire le nom du bourg d'un `/lieu` servi.

## Le joueur
Rien ne change encore à l'écran. Lot de fond : l'épreuve de la carte pourra exiger la fiche en noms. Le geste qu'il prépare est celui du jalon 4, « La fiche parle en noms, pas en identifiants » (#856, `CAP.md`, jalon 4, lot 18) : le joueur survole une terre et lit « Metz · Övre vik », « 1 234 habitants », « 12,5 kg », « jour 31 de 1400 », jamais « Cellule 10437 » ni « tick 30 ». Ce lot donne au juge la même plume que le Pont, pour qu'il refuse une fiche qui écrit autrement. Le lot qui le rend visible est le sous-lot 3 de #884 (pc, après celui-ci) : il branche la fiche en noms à l'écran et fait juger cette fiche par `pc/epreuve_carte.py`. C'est le sous-lot 2 de #884, lui-même sous-lot de #872 et de #856.

## Règle du monde
Sans objet : c'est un lot d'outil. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service, ni le C# ne sont touchés. Le modèle recopié est `3d/unity/Assets/ForgeLocal3D/Pont/TexteDuMonde.cs` (lot #870) ; la lecture du bourg suit `ClientLieu` : le bourg est le lieu de rang 0 de `lieux`, où qu'il soit dans la liste, sans repli (`Lieu.Bourg`).

## Périmètre
pc/epreuve_carte.py
jeu/ville/tests/test_epreuve_carte.py
docs/briefs/911-le-juge-de-la-carte-ecrit-comme-le-clerc.md

## Conditions de succès
On lance depuis la racine, sur le VPS. `TESTS` = `python3 -m pytest jeu/ville/tests/test_epreuve_carte.py -q`. Les cas neufs s'écrivent d'abord, et on les voit rouges (fonctions absentes). `NBSP` = U+00A0.

**Ce que gagne `pc/epreuve_carte.py`** (fonctions pures, à côté de `lire_fiche`, avec un commentaire qui nomme leur modèle C#) :
- `nombre(n)` recopie `TexteDuMonde.Nombre` : groupes de trois chiffres séparés par NBSP, signe « - » devant. Un `n` qui n'est pas un `int` (un `bool`, un flottant) lève `TypeError`.
- `jours(n)` recopie `TexteDuMonde.Jours` : `nombre(n)` + « jour » si n ≤ 1, « jours » sinon, après une espace ordinaire. n < 0 lève `ValueError`.
- `date(d)` recopie `TexteDuMonde.Date` pour la date telle que le service la sert, `{"annee": A, "jour_de_l_annee": J}` : « jour J de A », sans séparateur. Une clé absente ou non entière, J hors de 1…366 ou A < 1 lève `ValueError`.
- `masse(kg)` recopie `TexteDuMonde.Masse`. Les arrondis se font sur `decimal.Decimal(x)` (la valeur exacte du flottant) en `ROUND_HALF_UP`, jamais par `round()` ; les tonnes `t = abs(kg) / 1000` se calculent en flottant d'abord, comme en C#. Sous 1 000 kg au centième : les kilos, zéros de fin ôtés (« 0.## »), virgule décimale, « kg ». Sinon `t` au centième s'il reste sous 10 (« 0.00 »), au dixième s'il reste sous 100 (« 0.0 »), à l'unité au-delà, milliers séparés par NBSP ; puis « t ». Un kg négatif prend « - » devant, sauf si l'écrit vaut « 0 kg ». NaN ou infini lève `ValueError`.
- `bourg(lieu)` rend le `nom` de l'entrée de `lieu["lieux"]` dont `rang` vaut 0. `ValueError` dont le message contient « rang 0 » si `lieux` manque ou n'est pas une liste, si aucune entrée n'a le rang 0, ou si deux l'ont. `ValueError` dont le message contient « nom du rang 0 » si ce `nom` manque, vaut `null`, n'est pas un texte ou est blanc. Le bloc `noms` n'est pas lu.

**SC1 — Les mots du juge sont ceux du Pont, à l'octet.** `TESTS` passe. Cas neufs dans `test_epreuve_carte.py`, tables littérales reprises de `TexteDuMondeTests.cs` :
- `nombre` : 5631 → « 5 631 », -5631 → « -5 631 », 1234567 → « 1 234 567 », 12 → « 12 » (espaces = NBSP) ; `nombre(True)` et `nombre(12.0)` lèvent `TypeError`.
- `jours` : 0 → « 0 jour », 1 → « 1 jour », 12 → « 12 jours », 1234 → « 1 234 jours » ; -1 lève `ValueError`.
- `date` : (1400, 8) → « jour 8 de 1400 », (1401, 1) → « jour 1 de 1401 », (1400, 366) → « jour 366 de 1400 » ; (1400, 0), (1400, 367), (0, 8) et une date sans `annee` lèvent `ValueError`.
- `masse` : toute la table `Masses` de `TexteDuMondeTests`, le cas négatif compris (0, 12.5, 999.5, 999.996, 1000, 1234.5, 9996, 41712, 99960, 123456, 5631000, -1234.5) ; NaN et `inf` lèvent `ValueError`.
- Aucun écrit de ces tables ne contient U+0020 dans un nombre ni U+202F : la comparaison est faite par `==` sur les chaînes, jamais par un test de culture.

Contre-épreuve : un séparateur U+202F ou espace ordinaire, « 1 jours », « 0 jours », ou un seuil des 1 000 kg pris sur les kilos bruts plutôt qu'arrondis (999.996 → « 1000 kg ») rougit.

**SC2 — Les moitiés montent, comme en C#.** `TESTS`, cas neuf : `masse` rend 0.125 → « 0,13 kg », 1125 → « 1,13 t », 10250 → « 10,3 t », 100500 → « 101 t », -0.001 → « 0 kg ». Ces valeurs sont des moitiés exactes en binaire, que `Math.Round(…, MidpointRounding.AwayFromZero)` monte. Contre-épreuve : un `masse` écrit avec `round()` (moitié au pair) rend « 0,12 kg », « 1,12 t », « 10,2 t », « 100 t » et rougit ; un signe posé sans garde rend « -0 kg » et rougit.

**SC3 — Les tables du juge sont celles de `TexteDuMondeTests`.** `TESTS`, cas neuf qui lit `3d/unity/Assets/ForgeLocal3D/Pont/Tests/TexteDuMondeTests.cs` et y trouve chaque cas des tables de SC1, à l'octet, sous la forme où le C# l'écrit, NBSP remplacé par `" + NBSP + "` :
- pour `masse` : `({kg!r}, "<écrit>")`, par exemple `(5631000, "5" + NBSP + "631 t")` ;
- pour `nombre`, `jours`, `date` : `Assert.AreEqual("<écrit>", TexteDuMonde.Nombre(<n>))`, `…Jours(<n>)`, `…Date(new DateDuMonde(<A>, <J>)))`.
Contre-épreuve : une valeur de la table Python qui n'est plus celle du C# (« 41,8 t » pour 41712) rougit en nommant le cas manquant.

**SC4 — Le bourg se lit au rang 0, ou le juge le dit.** `TESTS`, cas neufs sur la fixture `3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json` (celle de `ClientLieuTests`) :
- `bourg(fixture)` vaut « Övre vik » ; la liste `lieux` retournée donne le même nom (le rang compte, pas la place) ;
- sans l'entrée de rang 0, avec deux rangs 0, sans la clé `lieux` : `ValueError` qui contient « rang 0 » ;
- avec le `nom` du rang 0 retiré, à `None`, à « » ou à « ␣␣ » : `ValueError` qui contient « nom du rang 0 ».
Chaque cas travaille sur une copie profonde ; la fixture n'est pas modifiée. Contre-épreuve : un `bourg` qui prend `lieux[0]`, qui se replie sur le rang 1, ou qui rend `None` ou « » rougit.

**SC5 — `juger` et `lire_fiche` ne changent pas, aucun test ne s'assouplit.**
- `git diff origin/master -- pc/epreuve_carte.py` ne montre aucune ligne retirée entre `def lire_fiche` et la fin de `def juger`, ni dans `main` ;
- `git diff --numstat origin/master -- jeu/ville/tests/test_epreuve_carte.py` montre 0 ligne retirée ;
- `python3 -m pytest jeu -q` passe.
Contre-épreuve : un cas existant retouché, ou un verdict de `juger` qui change, refuse la livraison.

## Hors périmètre
- Brancher ces fonctions dans `juger`, `lire_fiche` ou `references`, et lire `/lieu` dans `main` : c'est le sous-lot 3 de #884.
- Toucher au C# (`TexteDuMonde`, `FicheDeCellule`, `EpreuveCarte.cs`) ou à un test Unity.
- Recopier `Interdit`, `SansUnite` ou `Absence`.
- Partager ou refondre `_masse` de `pc/epreuve_part.py` : il reste tel quel, et `epreuve_carte.py` n'importe rien de lui.
- Lire le bloc `noms` de `/lieu`, ou un autre nom que celui du rang 0.
