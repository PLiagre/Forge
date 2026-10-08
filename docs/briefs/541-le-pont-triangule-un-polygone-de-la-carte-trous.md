# Lot #541 — Le pont triangule un polygone de la carte, trous compris
Jalon : J3 · Machine : pc · Taille prévue : 270 lignes

## But
Le pont sait changer un polygone de la carte de 1400, trous compris, en triangles Unity posés à plat, en kilomètres autour d'une origine. Chaque point du polygone est couvert une fois et une seule, même quand ses anneaux se croisent.

## Le joueur
Lot de fond. Il prépare l'écran du jalon 3, « la carte du joueur, dans Unity », et le premier geste qui s'y fait : ouvrir sa carte (#403), puis y choisir sa terre (#404) et y régler sa part (#405). Après ce lot, Unity sait remplir chaque morceau de royaume, îles et enclaves comprises, sans tache doublée ni trou bouché. Le joueur ne voit encore rien de neuf. C'est le sous-lot 1 de #522 (sous-lot 3 de #403). Le sous-lot 2 de #522 maillera toute la carte, et le sous-lot 4 de #403 (la scène de la carte) lui montrera ses royaumes.

## Règle du monde
Sans objet : c'est un lot d'outil, un calcul de vue. Aucun nombre du monde n'est décidé ici, et `jeu/` n'est pas touché. Niveau de fidélité : sans objet. Les polygones viennent de `/carte`, décrite dans `jeu/sim/MODELE.md`, « La carte et les terres servies, vue dérivée ». Ils sont lus par `ClientCarte` (#520) en `PolygoneDeCarte` : l'extérieur puis les trous, en mètres EPSG:3035 entiers, anneaux fermés.

### Ce que le chef a mesuré (08/10/2026, master 2f723cb, `/carte` seed 0, prototype Python)
- 675 polygones, dont 45 à trous (71 trous) ; 746 anneaux. Les extérieurs sont horaires (y vers le nord) et les trous anti-horaires. C'est l'inverse de la RFC 7946 : on ne s'en sert pas, la règle pair-impair ne lit pas le sens.
- **29 anneaux se croisent eux-mêmes**, dans 24 cellules (35 croisements). Ils viennent de l'arrondi au mètre et de Douglas-Peucker. Exemple : le polygone 0 de 10025 est un nœud de 4 points. Le service ne peut pas les réparer sans rougir `_verifier_distance` : le maillage doit les tolérer.
- Des sommets sont partagés entre anneaux d'un même polygone : en 10326 entre un trou et l'extérieur, en 10386 entre deux trous. Aucun trou ne croise son extérieur, et aucune île n'est dans un trou.
- La méthode ci-dessous donne, sur toute la carte, 76 206 triangles, aucune cellule sans triangle et au plus 11 040 sommets par cellule. Un oracle par grille (152 259 points) l'a confirmée : chaque point est couvert exactement une fois quand il est dedans au sens pair-impair, sinon jamais. Les 71 trous restent vides.
- Origine de la carte : le centre de la boîte des contours, **(4 549 691,5 ; 2 747 267,5) m**. À 2 174 km de l'origine, un float a un demi-ulp d'environ 12 cm. D'où la tolérance d'aire **relative** de 1e-4, et le filtre des triangles sur les floats.
- Mesures avec cette origine, en sommant les aires des triangles calculées en double sur les coordonnées float :
  - îlot de 10196 : 3,0563270 km² (exact : 3,0563985), soit un écart relatif de 2,3e-5 ;
  - polygone troué de 10196 : 25 868,263526 km² (exact : 25 868,261169) ;
  - le même extérieur sans le trou : 25 921,465860 km² (exact : 25 921,464329).

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/TriangulationDeCarte.cs
3d/unity/Assets/ForgeLocal3D/Pont/TriangulationDeCarte.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TriangulationDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TriangulationDeCarteTests.cs.meta

Précisions :

- **`TriangulationDeCarte.cs`**, espace de noms `Forge.Pont`, `using UnityEngine;` (l'assembly `Forge.Pont` référence déjà le moteur). Il n'y a ni `MonoBehaviour`, ni `Mesh`, ni réseau, ni aléa : c'est un calcul pur. On ne touche à aucun autre fichier, `ClientCarte.cs` compris.
  - `MaillageDePolygone` (immuable) :
    - `IReadOnlyList<Vector3> Sommets`, trois par triangle et non partagés ;
    - `IReadOnlyList<int> Triangles`, les indices dans `Sommets` : `Triangles[i] == i`, de sorte que `Triangles.Count == Sommets.Count`, un multiple de 3.
    - Les deux listes sont copiées en `ReadOnlyCollection`.
  - `public static class TriangulationDeCarte`, avec `public static MaillageDePolygone Trianguler(PolygoneDeCarte polygone, PointCarte origine)` :
    - un `polygone` nul lève `ArgumentNullException`. Une origine dont X ou Y est NaN ou infini lève `ArgumentOutOfRangeException` ;
    - **conversion**, pour un point (x, y) en mètres : `X = (float)((x − origine.X) / 1000.0)`, `Y = 0f`, `Z = (float)((y − origine.Y) / 1000.0)`. X est l'est, Z le nord, et tout le calcul est en `double` jusqu'à cette conversion ;
    - **anneaux** : l'extérieur et tous les trous, ensemble. Une arête relie deux points consécutifs d'un anneau, qui est fermé, sans arête de retour à ajouter. Une arête horizontale (même y) est ignorée pour les bandes ;
    - **ordonnées de coupe** : les y de tous les sommets de tous les anneaux, **plus** les y de tous les croisements propres entre deux arêtes quelconques du polygone, d'un même anneau ou de deux anneaux. Un croisement est propre quand il est strictement intérieur aux deux segments (0 < t < 1 et 0 < u < 1, le dénominateur non nul). On les trie et on retire les doublons exacts ;
    - **bandes** : pour deux ordonnées consécutives y0 < y1, les arêtes actives sont celles avec min(y) ≤ y0 et max(y) ≥ y1. On les trie par leur x à mi-hauteur (y0 + y1) / 2, puis on les apparie (0,1), (2,3)… : c'est la règle pair-impair, la même que `point_dans_geometrie` de `jeu/sim/villes.py`. Un nombre impair d'arêtes actives est une faute du calcul et lève `InvalidOperationException` (impossible sur un anneau fermé) ;
    - **trapèze** : pour une paire (gauche g, droite d), A = (g(y0), y0), B = (d(y0), y0), C = (d(y1), y1), D = (g(y1), y1), où g(y) est le x de l'arête à l'ordonnée y. Il donne les triangles (A, D, C) puis (A, C, B), dans cet ordre ;
    - **filtre** : un triangle (a, b, c) n'est gardé que s'il est **tourné vers le haut une fois converti en float**. On calcule en `double`, sur les coordonnées float déjà converties : `(b.z − a.z)·(c.x − a.x) − (b.x − a.x)·(c.z − a.z) > 0`. C'est `Vector3.Cross(b − a, c − a).y > 0`, le sens horaire vu d'en haut, la face qu'Unity montre à une caméra qui regarde vers le bas. Ce filtre retire aussi les triangles plats (A == B ou C == D) ;
    - un polygone sans surface (tous ses points alignés) rend un maillage vide, sans exception. Le sous-lot 2 déclarera une cellule sans triangle.
  - Un commentaire en tête dit pourquoi on fait des bandes et non des oreilles : 29 anneaux servis se croisent, et des sommets sont partagés entre anneaux.
- **`TriangulationDeCarteTests.cs`**, espace de noms `Forge.Pont.Tests`. Tous les polygones sont des **littéraux** en mètres : on ne lit ni fichier, ni service, ni `ClientCarteTests`.
  - L'aide `Verifier(maillage)` est appelée par chaque cas qui rend des triangles. Elle exige :
    - `Sommets.Count == Triangles.Count`, un multiple de 3, `Triangles[i] == i` ;
    - tout `Y == 0f` ;
    - pour chaque triangle, le produit du filtre ci-dessus > 0.
  - L'aide `Aire(maillage)` rend la somme des moitiés de ce produit, en `double`, en km².
  - L'aide `Couverture(maillage, xM, yM, origine)` convertit le point en km, en `double` (`(x − ox) / 1000`), puis compte les triangles qui le contiennent **strictement**. Un triangle (a, b, c) contient P quand s(a,b,P) > 0, s(b,c,P) > 0 et s(c,a,P) > 0, avec s(p,q,r) = `(q.z − p.z)·(r.x − p.x) − (q.x − p.x)·(r.z − p.z)`. Les points des tests sont choisis hors des lignes de coupe et des arêtes : le chef les a vérifiés sur le prototype.

## Conditions de succès

**SC1 — Unity compile et joue les tests (PC).**
Le workflow `unity` (poussée sur la branche) est vert, sans aucune `error CS`. Ensuite, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-541.xml -logFile <temp>\pont-541.log
```
(sans `-quit`). On attend un code de sortie 0 et `failed="0"` dans le XML. Le XML compte **au moins 8 cas** de `TriangulationDeCarteTests`, dont aucun ignoré. Il compte aussi tous les cas des autres classes de `Forge.Pont.Tests`, en même nombre et sous les mêmes noms que sur master. Zéro cas `TriangulationDeCarteTests` est un échec.
Contre-épreuve, faite à la main et dite dans la PR : écrire les tests d'abord et garder le rouge (classe absente ou `Trianguler` qui rend un maillage vide). Puis les trois contre-épreuves de SC2 à SC4.

**SC2 — les deux polygones de 10196 ont leur aire, le trou reste vide (PC, dans SC1).**
L'origine est celle de la carte, (4 549 691,5 ; 2 747 267,5) m. Les littéraux sont ceux de 10196 dans `/carte` seed 0, anneaux fermés :
- îlot : (3255813, 2017207), (3258432, 2014942), (3252950, 2017349), (3255813, 2017207) ;
- extérieur : (3260904, 2014373), (3258233, 2018288), (3248052, 2019499), (3178677, 2049953), (3214016, 2181858), (3242818, 2196329), (3344599, 2164419), (3381106, 2073504), (3289024, 2001514), (3260904, 2014373) ;
- trou : (3256797, 2044933), (3258232, 2047203), (3254327, 2044953), (3245580, 2036516), (3242003, 2025951), (3242985, 2024693), (3248295, 2030701), (3247211, 2035050), (3251211, 2041050), (3256797, 2044933).

Exigé, l'écart d'aire étant **relatif** : |aire − attendue| ≤ 1e-4 × attendue.
- **îlot** seul : aire 3,0563985 km² ; (3255732, 2016499) couvert 1 fois, (3300000, 2100000) couvert 0 fois ;
- **polygone troué** (extérieur + trou) : aire 25 868,261169 km² ; (3244636, 2029118), dans le trou, couvert 0 fois ; (3300000, 2100000) couvert 1 fois ; (3255732, 2016499), dans l'îlot donc hors de ce polygone, couvert 0 fois ;
- **le même extérieur sans trou** : aire 25 921,464329 km², et (3244636, 2029118) couvert 1 fois. Ce cas montre que c'est bien le trou qui retire 53,2 km².

Contre-épreuve, à la main, dite dans la PR : écrire le trapèze dans l'autre sens, (A, C, D) et (A, B, C). Le filtre retire alors tout, les aires tombent à 0 et SC2 rougit. Remettre l'ordre le rétablit.

**SC3 — le nœud n'est jamais couvert deux fois (PC, dans SC1).**
Le nœud synthétique est (0, 0), (2000, 2000), (2000, 0), (0, 2000), (0, 0) m, sans trou, avec pour origine (1000, 1000) m. Ses deux lobes se touchent au croisement (1000, 1000) m.
- L'aire vaut 2,0 km² à 1e-6 près.
- **Grille** : pour i de 0 à 19 et j de 0 à 18, le point en km x = −0,95 + 0,1·i, z = −0,9 + 0,1·j (soit, en mètres, 1000 + 1000·x, 1000 + 1000·z) est couvert **1 fois si |z| < |x|, 0 fois sinon**. Cela fait 380 points, sans aucun écart. Le test donne le nombre de points en écart dans son message.
- **Points nommés**, en km autour de l'origine : (0 ; 0,5) et (0 ; −0,5) couverts 0 fois ; (−0,5 ; 0,1) et (0,5 ; −0,1) couverts 1 fois.

Contre-épreuve, à la main, dite dans la PR : retirer les ordonnées des croisements. L'aire passe alors à 4,0 km², (0 ; 0,5) est couvert **2 fois** et la grille compte 100 écarts : SC3 rougit. SC2 et SC4 restent verts, car ils n'ont aucun croisement. Remettre les croisements le rétablit.

**SC4 — un trou qui touche l'extérieur par un sommet (PC, dans SC1).**
L'extérieur est (0, 0), (0, 2000), (0, 4000), (4000, 4000), (4000, 0), (0, 0) m, horaire. Le trou est (0, 2000), (2000, 1000), (2000, 3000), (0, 2000), anti-horaire. Le sommet (0, 2000) est partagé, comme en 10326. L'origine est (2000, 2000) m.
- L'aire vaut 14,0 km² à 1e-6 près.
- En km autour de l'origine :
  - couverts 0 fois : (−1 ; 0,1) et (−0,5 ; 0,5), dans le trou ;
  - couverts 1 fois : (−1,5 ; 0,5), (−1,95 ; 0,5), le coin entre le trou et le bord, (1 ; 0,4) et (−1,5 ; −1,5).

Contre-épreuve, à la main, dite dans la PR : retirer le filtre « tourné vers le haut ». Le triangle plat (A, D, C) avec D == C, dans la bande 1000–2000 m, est alors gardé, et `Verifier` rougit SC4. Remettre le filtre le rétablit.

**SC5 — les entrées refusées et le polygone plat (PC, dans SC1).**
- `Trianguler(null, origine)` lève `ArgumentNullException` ;
- une origine (NaN, 0) ou (0, +∞) lève `ArgumentOutOfRangeException` ;
- le polygone plat (0, 0), (1000, 0), (2000, 0), (0, 0) rend 0 sommet et 0 triangle, sans exception ;
- deux appels sur le polygone troué de 10196 rendent des `Sommets` égaux un à un : le calcul ne dépend d'aucun ordre caché.

**SC6 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
```
La suite du jeu reste verte. Le diff ne nomme que les quatre fichiers du Périmètre et ce brief. Les `.meta` sont ceux qu'Unity génère. Hors brief, `git diff --stat` reste sous 300 lignes ajoutées : un test paramétré (`TestCase`) vaut mieux que des cas recopiés.

## Hors périmètre
- Mailler toute la carte, fixer l'origine de la carte dans le code, colorer les puissances, construire un `Mesh`, la fixture `carte-graine0.json` : sous-lot 2 de #522.
- La scène de la carte, la caméra, `Jouer --carte`, la capture : sous-lots 4 et 5 de #403.
- Réparer les anneaux qui se croisent, côté service ou côté pont ; partager les sommets entre triangles ; simplifier ou lisser les contours ; dessiner les frontières.
- Toucher `ClientCarte.cs`, `PolygoneDeCarte`, les autres fichiers du pont, les asmdef, les autres tests, `jeu/` (service, carte servie, `MODELE.md`).
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Sans objet : le lot ne change rien de ce qu'on voit à l'écran. `TriangulationDeCarte` est un calcul que rien n'appelle encore : aucune scène, aucun outil d'éditeur, aucun panneau. Le sous-lot 4 de #403 (la scène de la carte) dessinera les triangles et portera le scénario de capture.
