# Lot #871 — Le nom de chaque terre et de chaque lieu
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Le Pont sait donner le nom servi de chaque lieu et le nom du bourg de chaque terre, sans jamais le remplacer par un identifiant, et un dossier sait lire la date servie avec son relevé.

## Le joueur
Quand ses dossiers parleront, le joueur lira « Övre vik » et non « Cellule 9922 », « Övre dal » et non « lieu 9922-1 », et la date du relevé qu'il regarde, celle que le monde a servie. Un nom que le monde ne connaît pas reste absent et le dit ; il n'est jamais remplacé par un numéro. Le joueur sent qu'il gouverne des terres et des bourgs qui ont un nom, pas des cases d'un tableau. C'est un lot de fond, le deuxième des huit sous-lots de #856 « La fiche parle en noms » (`CAP.md`, jalon 4, « La prise en main de la carte »). Il prépare le geste du jalon : **trouver sa capitale, lire son grenier et sa part, puis descendre dans sa ville sans chercher**. Ce lot ne touche aucun écran. Les sous-lots suivants de #856 le rendront visible : la fiche de survol et le bandeau, le dossier du territoire et « Votre maison », les comptes, les légendes, le plan et les chantiers.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service. Les noms sont ceux que `GET /lieu?cell=` sert déjà (`lieux[i].nom`, écrit par `lieux_en_photographie`) ; la date est la clé `date` déjà servie par chaque document. Unity ne fabrique ni nom ni date.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientLieu.cs
3d/unity/Assets/ForgeLocal3D/Pont/NomsDesTerres.cs
3d/unity/Assets/ForgeLocal3D/Pont/NomsDesTerres.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs
3d/unity/Assets/Interface/LectureDossier.cs
3d/unity/Assets/Interface/Tests/LectureDossierTests.cs
docs/briefs/871-le-nom-de-chaque-terre-et-de-chaque-lieu.md

Tout autre chemin est interdit, et le `.meta` est généré par Unity. Aucun écran, aucune capture, aucun fixture `.json` ne change. Dans les deux fichiers de tests, on ajoute des cas : aucun cas existant ne change, ni dans son corps ni dans son nom. Budget : environ 15 lignes dans `ClientLieu.cs`, 55 pour `NomsDesTerres.cs`, 11 de `.meta`, 10 dans `LectureDossier.cs`, 85 de tests dans `ClientLieuTests.cs`, 20 dans `LectureDossierTests.cs` et 75 de brief.

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`, sur le PC, éditeur fermé, depuis la racine, en PowerShell. `PONT` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot871-pont.xml -logFile 3d/unity/Temp/lot871-pont.log`. `INTERFACE` = la même commande avec `-assemblyNames Forge.Interface.Tests`, `-testResults 3d/unity/Temp/lot871-interface.xml` et `-logFile 3d/unity/Temp/lot871-interface.log`. Aucune des deux ne prend `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et les cas nommés réellement exécutés : zéro cas est un échec. Les tests s'écrivent d'abord et se voient rouges avant le code.

**Le nom d'un lieu.** `LieuPlace` gagne `string Nom` et `string AbsenceDuNom`, deux paramètres facultatifs ajoutés **à la fin** du constructeur (`nom = null, absenceDuNom = null`), pour que chaque appel existant compile tel quel. Même invariant que `Population` : `AbsenceDuNom` vaut `null` quand `Nom` est lu, sinon la raison donnée, ou « nom non fourni ». Dans `ClientLieu.Places`, la clé `nom` de chaque entrée se lit ainsi :
- clé absente : `Nom` nul, raison « clé absente : lieux[i].nom » ;
- `null` : `Nom` nul, raison « clé lieux[i].nom : null déclaré, nom non fourni » ;
- texte non blanc : `Nom` est ce texte, à l'octet ;
- tout autre valeur (nombre, booléen, objet, texte blanc) : tout le lieu est refusé, comme pour `maitre`, et l'absence nomme `lieux[i].nom`.

Jamais de repli : un nom nul n'est remplacé ni par le rang, ni par la cellule, ni par le maître.

**Le cache `NomsDesTerres`.** `public sealed class NomsDesTerres`, espace de noms `Forge.Pont`, une classe simple (pas un `MonoBehaviour`), utilisée seulement depuis le fil principal :
- `NomsDesTerres(Func<long, LectureLieu> lire)` : un `lire` nul lève `ArgumentNullException` ;
- `static NomsDesTerres Local(int port)` : chaque lecture ouvre un `ClientLieu(port, ClientDeparts.DelaiMinimal)`, lit, puis le dispose ;
- `const double ATTENTE_APRES_ECHEC_S = 2` ; `bool LectureEnVol` ;
- `string Nom(long cellId, long rang, double maintenant)` relève d'abord une lecture finie. Si sa `LectureLieu` est présente, elle est gardée pour toute la session. Si elle est absente, ou si `lire` a levé une exception (changée en absence qui porte son message), la cause est gardée et la cellule ne se relit pas avant `maintenant + ATTENTE_APRES_ECHEC_S`, `maintenant` étant celui de l'appel qui relève l'échec. La fonction rend ensuite le `Nom` du lieu de ce rang, s'il a été lu. Sinon elle rend `null` et, si aucune lecture n'est en vol et que l'attente est passée, lance `Task.Run(() => lire(cellId))`. **Une seule lecture à la fois**, toutes cellules confondues ;
- `string Bourg(long cellId, double maintenant)` = `Nom(cellId, 0, maintenant)` : le lieu de rang 0, où qu'il soit dans la liste (`Lieu.Bourg`) ;
- `string Raison(long cellId, long rang)` : `null` quand le nom est connu. Sinon une des raisons suivantes : « nom en cours de lecture » tant que rien n'est lu, la cause du dernier échec, `AbsenceDesLieux`, « aucun lieu de ce rang dans la terre », ou `AbsenceDuNom`. `Raison` ne lance ni ne relève aucune lecture.

**La date d'un dossier.** `DocumentDuMonde` gagne `long? Annee` et `long? JourDeLAnnee`. La clé `date` absente : les deux sont nulles et le document se lit comme aujourd'hui. Si elle est présente, elle doit être un objet avec `annee` (entier ≥ 1) et `jour_de_l_annee` (entier de 1 à 366), lus par `DocumentDuMonde.Entier`. Sinon le constructeur lève `ArgumentException` (`null` compris) : une date fausse n'est jamais lue comme absente.

**SC1 — Chaque lieu porte son nom servi.** `PONT`, cas `ChaqueLieuPorteSonNomServi`. Sur `lieu-graine0-tick3.json`, chaque `LieuPlace` a le `Nom` du texte servi, relu par `LecteurJson` (pas par le nouveau code), et `AbsenceDuNom` nul ; `Lieux[0].Nom` vaut « Övre vik » et `Lieux[1].Nom` « Övre dal ». Le nom du second lieu remplacé par « Mistra » se relit « Mistra », et le premier ne change pas. Contre-épreuve : un client qui lit le nom du rang 0 pour tous, ou qui ne lit rien, rougit.

**SC2 — Un nom absent reste nul, une faute refuse le lieu.** `PONT`, cas `UnNomAbsentOuNulResteNulAvecSaRaison` et `UnNomMalFormeRefuseToutLeLieu` (cas « nombre » `27`, « blanc » `" "`, « booléen » `true`). Clé `nom` retirée du second lieu : `Nom` nul, `AbsenceDuNom` contient « lieux[1].nom » et « absente », et `Rang`, `Maitre` et `Population` restent lus. Avec `"nom":null`, `AbsenceDuNom` contient « null déclaré ». Dans les deux cas, `Nom` est exactement `null`, jamais « 1 », « 9922 », « 9922-1 » ni le maître. Les fautes donnent une `LectureLieu` absente qui contient « lieux[1].nom », et le test vérifie, avec `LecteurJson`, que la mutation est bien dans le texte servi. Contre-épreuves : un repli sur le rang ou le maître rougit ; un nom `27` lu comme « 27 » rougit.

**SC3 — Le cache lit le service et garde ce qu'il a lu.** `PONT`, cas `LesNomsDesTerresViennentDuService`. Avec le faux service et `lieu-graine0-tick3.json`, `NomsDesTerres.Local(port)`. Le premier `Bourg(9922, 0)` rend `null` et `Raison(9922, 0)` contient « en cours ». Ensuite `SpinWait.SpinUntil(() => !noms.LectureEnVol, 10000)` attend la fin de la lecture. `Bourg(9922, 0.1)` rend alors « Övre vik », `Nom(9922, 1, 0.1)` « Övre dal », `Nom(9922, 999, 0.1)` `null` avec la raison « aucun lieu de ce rang dans la terre ». Le service fermé, `Bourg(9922, 5)` rend toujours « Övre vik ». Contre-épreuve : un cache qui relit à chaque appel rend `null` service fermé et rougit.

**SC4 — Une lecture à la fois, hors du fil principal.** `PONT`, cas `UneSeuleLectureALaFoisHorsDuFilPrincipal`. Un `lire` injecté compte ses appels par cellule, note `Thread.CurrentThread.ManagedThreadId` et attend un `ManualResetEventSlim`. Après `Bourg(1, 0)`, `Bourg(2, 0)` et `Bourg(1, 0)`, il y a exactement un appel, pour la cellule 1, et sur un autre fil que celui du test. Une fois libéré et fini, `Bourg(2, 0.5)` rend `null` et lance la cellule 2 ; `Bourg(1, 0.5)` rend le nom de la 1, sans nouvel appel. Contre-épreuves : une lecture synchrone (même fil) ou deux lectures en même temps rougissent.

**SC5 — Un échec se retente deux secondes plus tard.** `PONT`, cas `UnEchecSeRetenteDeuxSecondesPlusTard`. Un `lire` injecté rend d'abord `LectureLieu.Absent("service coupé")`, puis un lieu dont le rang 0 s'appelle « Biskra ». À `t = 10`, `Bourg(1, 10)` lance la lecture ; une fois finie, un nouveau `Bourg(1, 10)` relève l'échec et rend `null`, et `Raison(1, 0)` contient « service coupé ». À `t = 11.99`, il y a toujours un seul appel et aucune lecture en vol. À `t = 12`, une deuxième lecture part, et `Bourg(1, 12.1)` rend « Biskra » une fois qu'elle est finie. Le même déroulé avec un `lire` qui **lève** `InvalidOperationException("panne")` donne `null`, une raison qui contient « panne », et aucune exception remontée au test. Un lieu lu dont le nom vaut `null` rend `null` avec son `AbsenceDuNom`, et ne se relit plus. `new NomsDesTerres(null)` lève `ArgumentNullException`. Contre-épreuves : une relance immédiate fait deux appels à 11,99 et rougit ; une absence jamais relancée reste `null` à 12,1 et rougit.

**SC6 — La date servie d'un dossier.** `INTERFACE`, cas `La_date_servie_est_lue_et_son_absence_reste_nulle`. `{"tick":7,"date":{"annee":1400,"jour_de_l_annee":8}}` donne `Annee` 1400 et `JourDeLAnnee` 8. Le fichier `ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json`, lu par `Application.dataPath`, donne 1400 et 4, avec `Tick` 3. `{"tick":7}` donne deux nulles. Lèvent `ArgumentException` : `"date":null`, `"date":{"annee":1400}`, un jour à 0, à 367 ou à 1.5, une année à 0, `"date":"1400"`. Contre-épreuves : une date absente lue comme 0 ou comme 1400, ou une date fausse lue comme absente, rougit.

**SC7 — Rien d'autre ne bouge.** Les commandes :
- `PONT` et `INTERFACE` passent sur toute l'assemblée ;
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs 3d/unity/Assets/Interface/Tests/LectureDossierTests.cs` ne montre aucune ligne retirée ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ;
- `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes.

Contre-épreuve : un cas existant modifié, un écran touché ou un fichier hors du Périmètre refuse la livraison.

## Hors périmètre
- Faire parler un écran : la fiche de survol, le bandeau, `DossierTerritoire`, « Votre maison », les comptes, les légendes, le plan, les chantiers et les voisins sont les sous-lots suivants de #856, qui appelleront `NomsDesTerres`, `LieuPlace.Nom`, `DocumentDuMonde.Annee` et `TexteDuMonde`.
- Écrire une date ou cacher une raison : c'est le travail de `TexteDuMonde` (#870), qu'on ne touche pas ici.
- Relire un nom déjà lu : un nom que le service changerait en cours de partie, après un changement de maître, sera rafraîchi par un lot suivant, s'il le faut.
- Les noms des maisons (`/maison` les sert déjà), le service Python, les fixtures et `ServiceLocal.Date`.

## Photo
sans objet : ce lot ajoute une clé lue, un cache et une date au Pont et à `DocumentDuMonde`, sans rien changer à l'écran ; aucun écran ne les appelle encore. Les sous-lots 3 à 7 de #856 porteront leurs scénarios de capture, où les dossiers montreront ces noms et ces dates.
