# Lot #1045 — Le panneau du pays se lit au même tick que /pays
Jalon : J6 · Machine : pc · Taille prévue : 1200 lignes

## But
Une icône « Le pays », posée dans le bandeau hors des « Dossiers de la barre », ouvre un feuillet qui montre le pays du joueur tel que `GET /pays` le sert au tick du monde lu : ses lieux, son suzerain et ses vassaux en noms servis, ses gens, sa récolte des trente derniers jours, ses greniers, ses chantiers et ses bâtiments.

## Le joueur
En haut de la carte, à côté du titre, le joueur clique sur l'icône « Le pays » (une couronne). Un feuillet s'ouvre et lui dit, d'un seul tenant, ce qu'il gouverne :
- qui est au-dessus de lui (« Suzerain : Valois ») et qui est en dessous (« Vassaux : 115 maisons », puis leurs noms) ;
- combien de lieux il tient, lui et ses vassaux, et combien de gens y vivent ;
- le grain récolté sur ses terres pendant les trente derniers jours, son grenier, et celui de ses vassaux ;
- les chantiers ouverts dans ses bourgs ;
- ses bâtiments de province, achevés ou en chantier, avec le travail fait. Exemple : « Moulin à Bar-le-Duc : en chantier, 20 jours de travail sur 600 jours ».
- ses lieux, terre par terre (« Bar-le-Duc et 3 lieux : … »), puis ceux de ses vassaux.

Chaque nom est celui que le monde sert : jamais un identifiant, jamais un nom inventé. Ce qui manque est dit absent. Les nombres sont ceux du jour que montre la carte : le feuillet attend plutôt que de mêler deux jours.

Le seigneur de Bar y lit un petit pays : quatre lieux autour de son siège, son suzerain des Valois, son moulin en chantier. Le roi des Valois y lit un royaume : plus de cent vassaux, près de trois cents lieux, deux millions et demi d'habitants, et, chez son vassal de Bar, le même moulin.

Il en sent la taille de ce qu'il tient, et ce que son grain peut payer. C'est « le panneau du pays et ses bâtiments » de l'écran du jalon 6 (`CAP.md`), et la première moitié de sa preuve : « un royaume et un petit seigneur […] donnent chacun un panneau égal à la photographie au même tick ». Il prépare la décision du jalon : où va le grain de l'année, à quel bâtiment de quelle province. Le geste de bâtir depuis la carte vient avec #1034, celui de dépenser ses jauges avec le second morceau de #1033. Ici, le scénario de la photo dépose lui-même le moulin par le chemin des intentions, celui du joueur.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, et aucun fichier de `jeu/` n'est touché. Le feuillet lit le document de `jeu/sim/MODELE.md`, « Le pays et ses jauges » (« Le pays d'un seul tenant », #1039) et « Les bâtiments de province » (#1040), tel quel.

Les noms viennent du service, par deux lectures qui existent déjà :
- le nom de chaque maison (le pays, son suzerain, ses vassaux, le maître d'un bâtiment) : `GET /maisons`, une seule lecture, comme le feuillet « Les autres maisons » ;
- le nom de chaque lieu : `GET /lieu`, une lecture par terre, gardée pour la session, par `NomsDesTerres`, comme « Terres et comptes ».

`/pays` ne sert pas les noms, et ce lot ne les y ajoute pas. `test_le_service_sert_le_pays_et_ses_jauges` fige `/pays` à l'égal de `pays()`, plus ses jauges, sa date et ses bâtiments. Les noms coûtent une seconde de calcul sur tout le monde (`puissances_depuis_monde`, `noms_depuis_monde`) : `pays()` ne peut pas les calculer à chaque appel.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientPays.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPaysTests.cs
3d/unity/Assets/Interface/DossierPays.cs
3d/unity/Assets/Interface/DossierPays.cs.meta
3d/unity/Assets/Interface/EmblemeCommande.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/LecturePartie.cs
3d/unity/Assets/Interface/Tests/DossierPaysTests.cs
3d/unity/Assets/Interface/Tests/DossierPaysTests.cs.meta
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/Interface/Tests/LecturePartieTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1045.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1045.cs.meta
docs/briefs/1045-le-panneau-du-pays-se-lit-au-meme-tick-que-pays.md

Tout autre chemin est interdit, en particulier :
- tout `jeu/` : `service.py`, `pays.py`, `batiments.py`, les données, les tests Python ;
- `BarreDuPays.cs`, `DossierMaison.cs`, `DossierVoisins.cs`, `Feuillet.cs`, `SocleInterface.cs`, `NomsDesTerres.cs`, `ClientLieu.cs`, `ClientMaison.cs`, `TexteDuMonde.cs` ;
- les scénarios `Lot549`, `Lot690`, `Lot944`, `Lot1002`, `Lot1004`, `Lot1032`.

Chaque `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master 9f500b3d (#1032 fusionné). Il ne dépend d'aucun lot ouvert.

**`ClientPays.cs`** (espace `Forge.Pont`). `Lire` et `PaysLu` ne changent pas. Le commentaire de la classe dit désormais que `Lire` lit les jauges et `LireTerres` le reste.

Trois classes neuves, en lecture seule :
- `LieuDuPays(long cellId, long rang)` : `CellId`, `Rang` ;
- `BatimentDuPays` : `Identifiant`, `Nature`, `Nom`, `CellId`, `Maison`, `TravailRequis`, `TravailFourni` (des `long`, sauf les textes) et `EnChantier` (`bool`) ;
- `TerresDuPays` :
  - `MaisonId`, `Tick`, `Date` ;
  - `Suzerain` : un identifiant, ou nul ;
  - `Vassaux`, `VassauxTous` : des listes d'identifiants, dans l'ordre servi ;
  - `Lieux`, `LieuxDesVassaux` : des listes de `LieuDuPays`, dans l'ordre servi ;
  - sous `totaux` : `NombreDeLieux`, `Habitants`, `HabitantsPropres`, `Chantiers` (`long`), `Recolte30jKg`, `GreniersDesVassauxKg` (`double`), `GrenierKg` (`double?`) ;
  - `AbsenceDuGrenier` : la raison `absents.grenier`, ou nulle ;
  - `Batiments` : une liste de `BatimentDuPays`.

`LireTerres(string id)` lit `GET /pays?maison=<id échappé>` par le même `ServiceLocal`, et rend une `Lecture<TerresDuPays>`. Il ne lit ni `jauges` ni `maison.nom`. Une faute refuse toute la réponse, et l'absence nomme la clé fautive. La lecture refuse :
- un `maison.id` autre que celui demandé ; un `tick` absent, négatif ou décimal ; une date fausse (`ServiceLocal.Date`) ;
- un `suzerain` qui n'est ni nul ni un texte non vide, ou qui est la maison elle-même ;
- dans `vassaux` ou `vassaux_tous` : une entrée qui n'est pas un texte non vide, un doublon, la maison elle-même, ou un vassal direct absent de `vassaux_tous` ;
- dans `lieux` ou `lieux_des_vassaux` : un `cell_id` ou un `rang` qui n'est pas un entier ≥ 0, ou un lieu servi deux fois, dans une liste ou entre les deux ;
- `totaux.lieux` différent du nombre de lieux servis ; `habitants_propres` plus grand que `habitants` ; une masse négative ou non finie ; un `chantiers` qui n'est pas un entier ≥ 0 ;
- un grenier nul sans `absents.grenier`, ou une raison `absents.grenier` avec un grenier servi ;
- dans `batiments` : une clé manquante ; un `cell_id` qui n'est la terre d'aucun lieu servi ; un `travail_fourni` plus grand que `travail_requis` ; un `en_chantier` qui n'est pas un booléen ; un `nom` ou une `maison` vide.

**`LecturePartie.cs`** gagne :
- un 7ᵉ paramètre optionnel `Func<string, Lecture<TerresDuPays>> terres = null`, et `Terres { get; private set; }` ;
- la lecture des terres au même passage que le pays, seulement avec une maison du joueur, juste après lui. Elle est remise à nul avec lui dans le `catch` ;
- dans `Locale(port)` : `id => { using var c = new ClientPays(port, TimeSpan.FromSeconds(10)); return c.LireTerres(id); }`.

**`EmblemeCommande.cs`** : `Motif("Le pays")` rend `"couronne"`. `OnPopulateMesh` dessine ce motif avec `Trait`, dans le carré de 18 des autres : un bandeau de 14 × 3, trois fleurons de 2 × 5 au-dessus (au milieu et aux deux bords), et une pierre de 2 × 2 au centre du bandeau. Les autres motifs ne changent pas.

**`DossierPays.cs`** (espace `Forge.Interface`) est un `MonoBehaviour`, dans le style de `DossierMaison` et `DossierVoisins`. Ses constantes :
- `DossierPays.TITRE = "Le pays"`, le titre du feuillet ;
- `DossierPays.ICONE = "Le pays"`, le nom de l'icône.

`Initialiser(Transform toile, Transform barre, Func<Lecture<MondeAvecMaisonLu>> monde, Func<Lecture<TerresDuPays>> terres, LectureDossier registre, NomsDesTerres noms)` :
- pose un `Feuillet` titré `Le pays` sur la toile ;
- pose dans `barre` l'icône `EmblemeCommande.Icone(barre, "Le pays", 0, bascule, phrase)`, avec la phrase « Le pays : ouvre ou ferme le feuillet de votre pays : ses lieux, ses vassaux, ses gens, son grain et ses bâtiments. ». Le clic ouvre le feuillet fermé, et ferme le feuillet ouvert.

`TexteAffiche { get; private set; }` garde le dernier texte écrit. `Pas(double maintenant)`, appelé par `LateUpdate` avec `Time.realtimeSinceStartupAsDouble`, ne fait rien quand le feuillet est fermé. Ouvert, il fait trois choses :
- **le registre.** Il relit `/maisons` par `registre.Actualiser("/maisons")`, sans attendre, à chaque ouverture du feuillet. Il le relit aussi, au plus toutes les 2 s, tant que la lecture est en erreur ou qu'une maison à nommer manque au registre lu. Il ne le relit jamais pendant qu'une lecture est en cours ;
- **le texte.** Il écrit `Decrire(monde(), terres(), registreLu, nomDuLieu)`. `registreLu` est nul tant qu'aucun document n'est lu. Il est absent, avec sa raison, si la lecture est en erreur ou si `Registre` lève. `nomDuLieu` est `(c, r) => DossierMaison.NomDuLieu(noms, c, r, maintenant)` ;
- **l'écriture.** Le texte passe par `Feuillet.Ecrire` et va dans `TexteAffiche`.

`public static Dictionary<string, string> Registre(DocumentDuMonde document)` lit `maisons` (`id` → `nom`, un `nom` nul restant nul). Elle lève `ArgumentException` si la liste est vide, si son nombre diffère de `nombre`, ou si un `id` est vide ou répété.

`public static string Decrire(Lecture<MondeAvecMaisonLu> monde, Lecture<TerresDuPays> terres, Lecture<IReadOnlyDictionary<string, string>> registre, Func<long, long, string> nomDuLieu)` suit cet ordre, comme `BarreDuPays.Afficher` :
1. **monde nul** : `Lecture du pays…` ;
2. **monde absent** : `Pays indisponible : <TexteDuMonde.Absence(raison)>` ;
3. **pas de maison du joueur** : `Choisissez une maison pour lire son pays.` ;
4. **terres nulles, ou d'une autre maison, ou d'un autre tick que le monde lu** : `Pays en attente du monde` ;
5. **terres absentes** : `Pays indisponible : <TexteDuMonde.Absence(raison, id)>` ;
6. **registre nul** : `Lecture des noms des maisons…` ;
7. **registre absent** : `Pays indisponible : <TexteDuMonde.Absence(raison)>` ;
8. **sinon**, le pays, en lignes séparées par `\n`, sans `\n` final.

Une ligne vide sépare chaque bloc du pays. Une maison se nomme par le registre : un `nom` nul s'écrit `maison non nommée`, un identifiant absent du registre `maison absente du registre`. Un compte s'accorde au pluriel au-delà de 1 (`0 lieu`, `1 lieu`, `2 lieux`), comme `TexteDuMonde.Jours`. Les nombres s'écrivent par `TexteDuMonde.Nombre`, les masses par `TexteDuMonde.Masse`, les durées par `TexteDuMonde.Jours`.

Le texte du pays :
- **l'en-tête**, trois lignes :
  - `<nom de la maison> · relevé au <TexteDuMonde.Date(date servie)>` ;
  - `Suzerain : <nom>` ou `Suzerain : aucun` ;
  - `Vassaux : <n> maison(s)`, où n compte les vassaux directs, ou `Vassaux : aucun` ;
- **`GENS ET GRAIN`**, puis six lignes :
  - `Lieux : <n> lieu(x), dont <m> lieu(x) tenu(s) en propre` (n = `totaux.lieux`, m = les lieux propres) ;
  - `Habitants : <n> habitant(s), dont <m> habitant(s) sur ses propres lieux` ;
  - `Récolte des trente derniers jours : <masse> de grain` ;
  - `Grenier : <masse> de vivres`, ou `Grenier : <TexteDuMonde.Absence(raison, id)>` ;
  - `Greniers des vassaux : <masse> de vivres` ;
  - `Chantiers des bourgs : <n> chantier(s) en cours` ;
- **`BÂTIMENTS`**, puis un bâtiment par ligne, dans l'ordre servi, ou `aucun` :
  - en chantier : `<nom> à <bourg>[, de <maison>] : en chantier, <Jours(fourni)> de travail sur <Jours(requis)>` ;
  - achevé : `<nom> à <bourg>[, de <maison>] : achevé` ;
  - `<bourg>` est `nomDuLieu(cell, 0)`. `, de <maison>` ne s'écrit que si le bâtiment est d'une autre maison que le pays ;
- **`SES LIEUX`**, puis une ligne par terre, ou `aucun` ;
- **`SES VASSAUX`**, puis :
  - les noms des vassaux directs, dans l'ordre servi, séparés par `, `, ou `aucun` ;
  - si `vassaux_tous` en a d'autres, une ligne `Par leurs vassaux (<n> maison(s)) : <noms, dans l'ordre servi, séparés par « , »>` ;
- **`LIEUX DE SES VASSAUX`**, puis une ligne par terre, ou `aucun`.

**Une ligne de terre.** Les lieux d'une liste se groupent par `cell_id`, dans l'ordre de leur première apparition. Dans une terre, ils suivent l'ordre des rangs :
- **le bourg tenu, seul** : `<bourg>` ;
- **le bourg tenu, avec k autres lieux** : `<bourg> et <k> lieu(x) : <nom>, <nom>` ;
- **le bourg non tenu** : `Autour de <bourg> : <nom>, <nom>`.

`<bourg>` est `nomDuLieu(cell, 0)`, et chaque `<nom>` `nomDuLieu(cell, rang)`. Un nom pas encore lu s'écrit donc `nom en cours de lecture` (`NomsDesTerres.NomEnLecture`), sans un identifiant.

**`CabinetDeCarte.cs`** :
- une constante `PAYS = "Pays de la barre"` ;
- dans `Construire`, après `DossierMaison`, un conteneur `PAYS`, enfant du bandeau, ancré en haut à gauche comme `DOSSIERS`, en (408, −20), de 56 × 44. Il tient entre le titre du bandeau et la date, posée en x 480 ;
- puis `gameObject.AddComponent<DossierPays>().Initialiser(toile.transform, pays, () => Partie.Monde, () => Partie.Terres, LectureDossier.Locale(carte.port), NomsDesTerres.Local(carte.port))`.

Le bandeau garde ses trois boutons enfants directs. Les « Dossiers de la barre » gardent leurs deux icônes. Rien d'autre ne bouge dans le bandeau.

**`Lot1045.cs`** est une `static class Lot1045`, dans le style de `Lot1032`. Ses deux scénarios se jouent dans l'ordre de leur nom, sur le même service. La première faute lève une `InvalidOperationException` qui la nomme.

Le scénario écrit lui-même **le texte attendu** du feuillet, d'après le format ci-dessus, depuis trois lectures indépendantes. Il n'appelle ni `DossierPays.Decrire` ni `DossierPays.Registre`, et ne rend `internal` aucune fonction privée :
- **les noms des maisons** : `/maisons`, lu par une `LectureDossier.Locale(port)` à lui ;
- **les noms des lieux** : `new ClientLieu(port, ClientDeparts.DelaiMinimal).Lire(cell)` pour chaque terre du pays. Chaque nom doit être servi, sinon `nom de lieu absent : <terre>` ;
- **le pays** : `new ClientPays(port, …).LireTerres(id)`.

Les deux premières lectures se font avant le jugement, hors de l'image. La troisième se fait dans l'image du jugement.

**Le jugement**, dans une seule image et sans `yield` :
- **l'avance.** Avec `-forge1045Avance`, le scénario pousse d'abord un tick (`Lot690.PousserTick(port).Result`) ;
- **le même tick.** Il relit le pays. Le tick de `cabinet.Partie.Terres` doit égaler le tick servi, sinon `panneau lu au tick T, pays servi au tick T'`. Il doit aussi égaler le tick du monde lu ;
- **le même texte.** `DossierPays.TexteAffiche`, comparé ligne à ligne au texte attendu, doit lui être égal. Sinon le scénario nomme la première ligne qui diffère, avec l'attendue et la lue ;
- **les juges.** Le texte passe `TexteDuMonde.Interdit(t, <la maison>, <son suzerain>, <chaque identifiant de vassaux_tous>, <la maison de chaque bâtiment>)`, et `SansUnite` vaut nul ;
- **la place.** Le texte tient en 16 000 caractères au plus, ce qu'un `Text` d'Unity dessine en entier. Le cadre `Le pays` est actif, ses quatre coins sont dans l'image, son titre passe `Lot690.DansLeChamp`, et sa lecture défilante est en haut (`verticalNormalizedPosition` = 1).

Avant chaque jugement, le scénario attend (`Lot690.Jusqua`) trois choses : la partie libre ; `Partie.Terres` présente, de la maison voulue et au tick du monde lu ; un `TexteAffiche` qui commence par le nom de la maison et ne contient pas `nom en cours de lecture`.

1. **`pays-1-petit-seigneur`.**
   - Il ouvre la carte comme `Lot1032` (`Lot549.Ouvrir`, `Lot690.LecturePrete`, la toile en `ScreenSpaceCamera`). Le tick lu doit égaler `-forgeTicks` (30 par défaut, lu comme `Lot1032.Depart`).
   - Il choisit le départ dont le siège est « Bar-le-Duc », pousse un tick, puis attend la maison du joueur.
   - Il clique sur l'icône `Le pays` (`onClick.Invoke`). Le feuillet doit s'ouvrir.
   - **Jugement R1** : la ligne `Suzerain : Valois`, et `aucun` sous `BÂTIMENTS`.
   - Il dépose `{"type":"batir_dans_une_province","maison":"<id de Bar>","cell":<terre du siège de Bar>,"nature":"moulin"}` par `ClientIntention`. Le reçu doit être accepté. Il pousse un tick.
   - **Jugement R2** : une seule ligne sous `BÂTIMENTS`, qui commence par `Moulin à Bar-le-Duc : en chantier, `. Le pays servi doit compter un bâtiment, de nature `moulin`, sur la terre du siège.
   - Il laisse passer 10 images.
2. **`pays-2-royaume`.** Comme `Lot1032.Posee`, il pose côté Unity la maison du joueur au suzerain de Bar, lu par `ClientMaison.LireComptes`. Ce suzerain doit être une maison sans suzerain, qui tient plus de lieux que Bar. Sa `LecturePartie` porte les sept lecteurs de `Locale`. Le service, `/pays`, son tick et le feuillet sont les vrais.
   - Il laisse le feuillet ouvert, le remet en haut, puis juge R1 :
     - la ligne `Suzerain : aucun` ;
     - le nom servi de Bar parmi les vassaux directs ;
     - plus de 100 vassaux directs ;
     - sous `BÂTIMENTS`, une ligne qui commence par `Moulin à Bar-le-Duc, de Bar : en chantier, `.
   - Il pousse un tick, attend, puis juge R2 : l'en-tête a changé de jour.
   - Il laisse passer 10 images. La trace dit `maison posée par le scénario`.

Chaque scénario écrit `CAPTURE_1045 <nom> pays « <nom servi> » lu au tick T, servi au tick T : lieux <n>, vassaux directs <n>, bâtiments <n>, suzerain « <nom ou aucun> », caractères <longueur>`.

## Conditions de succès
On lance depuis la racine. Sur le PC, éditeur fermé, en PowerShell, `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Deux commandes de tests :
- `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot1045-interface.xml -logFile 3d/unity/Temp/lot1045-interface.log` ;
- `P` = la même avec `-assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot1045-pont.xml -logFile 3d/unity/Temp/lot1045-pont.log`.

Chacune sort 0, sans échec ni cas ignoré, et ses cas neufs réussissent.

**Le pays témoin** des SC3 à SC5, `TerresDuPays` de `grande-3` au tick 31, date (1400, 32) :
- suzerain nul ; vassaux `seigneurie-1`, `plausible-7-0` ; `vassaux_tous` : les mêmes, puis `plausible-8-1` ;
- lieux (10, 0), (10, 1), (10, 2), (11, 1) ; lieux des vassaux (12, 0), (13, 0), (13, 3) ;
- totaux : 7 lieux, 2 450 344 habitants dont 271 528 propres, récolte 141 439 858,6 kg, grenier 754 362,1 kg, greniers des vassaux 6 862 501,4 kg, 2 chantiers ;
- deux bâtiments, dans cet ordre : un moulin achevé sur 10 de `grande-3` (600 sur 600), puis un moulin en chantier sur 12 de `seigneurie-1` (20 sur 600).

Son registre : `grande-3` → Valois, `seigneurie-1` → Bar, `plausible-7-0` → Mauléon, `plausible-8-1` → nul. Ses noms de lieux : (10, 0) Paris, (10, 1) Saint-Denis, (10, 2) Vincennes, (11, 0) Melun, (11, 1) Corbeil, (12, 0) Bar-le-Duc, (13, 0) Toul, (13, 3) Foug.

**SC1 — Les terres du pays se lisent en entier ou pas du tout (`ClientPaysTests.cs`, `P`).** Une constante neuve `TemoinTerres`, le document servi du pays témoin. `Temoin` ne change pas.
- `Les_terres_du_pays_se_lisent_avec_leurs_vassaux_et_leurs_batiments` : chaque valeur du témoin, dans l'ordre servi, les deux bâtiments compris, et un `GrenierKg` égal à 754 362,1.
- `Un_grenier_absent_se_dit_absent` : `grenier_nourriture_kg` nul avec sa raison donne `GrenierKg == null` et `AbsenceDuGrenier` égal à la raison.
- `Des_terres_mal_servies_sont_refusees` : chaque refus de la section Périmètre est essayé un à un. Chacun donne une lecture absente qui nomme sa clé. On y ajoute (12, 0) servi dans les deux listes.
- `Le_document_des_jauges_n_a_pas_de_terres` : `LireTerres` sur `Temoin` est absent et nomme `lieux`, tandis que `Lire` sur le même `Temoin` reste présent.

Tous les cas existants de `ClientPaysTests` passent sans changer. Contre-épreuve : un client qui ne compare pas `totaux.lieux` au nombre de lieux servis rougit `Des_terres_…`.

**SC2 — La partie lit les terres au même passage (`LecturePartieTests.cs`, `I`).** Cas `Les_terres_se_lisent_avec_le_pays`, sur le modèle de `Le_pays_se_lit_avec_la_maison` :
- monde sans maison : aucun appel au lecteur de terres, et `Terres` nul ;
- monde qui nomme `identifiant-servi` : un appel avec cet identifiant, après celui du pays ;
- une `LecturePartie` à six paramètres laisse `Terres` nul ;
- un lecteur de monde qui lève remet `Terres` à nul.

`Le_pays_se_lit_avec_la_maison` passe sans changer. Contre-épreuve : lire les terres sans maison rougit le cas.

**SC3 — Le feuillet écrit le pays en noms (`DossierPaysTests.cs`, `I`).** Cas `Le_feuillet_ecrit_le_pays_en_noms`. `Decrire`, avec le monde témoin de `grande-3` au tick 31, le pays témoin, son registre et ses noms de lieux, vaut exactement :

```
Valois · relevé au jour 32 de 1400
Suzerain : aucun
Vassaux : 2 maisons

GENS ET GRAIN
Lieux : 7 lieux, dont 4 lieux tenus en propre
Habitants : 2 450 344 habitants, dont 271 528 habitants sur ses propres lieux
Récolte des trente derniers jours : 141 440 t de grain
Grenier : 754 t de vivres
Greniers des vassaux : 6 863 t de vivres
Chantiers des bourgs : 2 chantiers en cours

BÂTIMENTS
Moulin à Paris : achevé
Moulin à Bar-le-Duc, de Bar : en chantier, 20 jours de travail sur 600 jours

SES LIEUX
Paris et 2 lieux : Saint-Denis, Vincennes
Autour de Melun : Corbeil

SES VASSAUX
Bar, Mauléon
Par leurs vassaux (1 maison) : maison non nommée

LIEUX DE SES VASSAUX
Bar-le-Duc
Toul et 1 lieu : Foug
```

Le même texte passe `TexteDuMonde.Interdit(t, "grande-3", "seigneurie-1", "plausible-7-0", "plausible-8-1")` et `SansUnite`.

Cas `Un_petit_seigneur_a_son_suzerain_et_aucun_vassal` : le pays de `seigneurie-1`, suzerain `grande-3`, un seul lieu (12, 0), 1 habitant, sans vassal ni bâtiment. Il donne :
- `Suzerain : Valois` et `Vassaux : aucun` ;
- `Lieux : 1 lieu, dont 1 lieu tenu en propre` et `Habitants : 1 habitant, dont 1 habitant sur ses propres lieux` ;
- `aucun` sous `BÂTIMENTS`, sous `SES VASSAUX` et sous `LIEUX DE SES VASSAUX` ;
- aucune ligne `Par leurs vassaux`.

Cas `Un_royaume_tient_dans_le_feuillet` : 115 vassaux nommés de 20 lettres, et 295 lieux sur 52 terres nommés de 14 lettres. Le texte tient en 16 000 caractères au plus.

Contre-épreuve : un feuillet qui écrit `, de Bar` pour un bâtiment du pays lui-même, ou qui compte les arrière-vassaux dans `Vassaux :`, rougit le premier cas.

**SC4 — Le feuillet dit l'absence et l'attente, sans les inventer (`DossierPaysTests.cs`, `I`).** Cas `Le_feuillet_dit_l_absence_sans_l_inventer` :
- `GrenierKg` nul et `absents.grenier` = « grenier absent pour la maison grande-3 » donnent `Grenier : déclaré absent par le monde` ;
- un registre sans `seigneurie-1` donne `maison absente du registre` à sa place, dans les vassaux et dans le bâtiment ;
- un `nomDuLieu` qui rend `NomsDesTerres.NomEnLecture` donne `nom en cours de lecture`, sans un nombre nu.

Cas `Le_feuillet_attend_le_meme_tick`, dans l'ordre de `Decrire` :
- monde nul : `Lecture du pays…` ;
- monde absent (« refus témoin ») : `Pays indisponible : refus témoin` ;
- sans maison : `Choisissez une maison pour lire son pays.` ;
- terres nulles, terres au tick 30 ou 32, terres de `seigneurie-1` : `Pays en attente du monde`, et aucun texte ne contient `Valois` ;
- terres absentes : `Pays indisponible : <raison>` ;
- registre nul : `Lecture des noms des maisons…` ; registre absent : `Pays indisponible : <raison>`.

Cas `Le_registre_se_lit_en_entier` : `Registre` rend les quatre noms du témoin, `plausible-8-1` nul compris. Il lève pour une liste vide, un `nombre` faux, et un `id` répété.

Contre-épreuve : un feuillet qui ne compare pas le tick rougit `Le_feuillet_attend_le_meme_tick`.

**SC5 — Le feuillet lit le pays servi au tick du monde lu (`DossierPaysTests.cs` et `CabinetDeCarteTests.cs`, `I`).**

Cas `Le_feuillet_egale_le_pays_servi_au_meme_tick` (`DossierPaysTests`). Sur un `GameObject` témoin avec sa toile et sa barre, un `DossierPays` est initialisé avec :
- `() => partie.Monde` et `() => partie.Terres`, d'une `LecturePartie` dont le test pose les lectures par réflexion, comme `CabinetDeCarteTests.Poser` : le monde de `grande-3` au tick 31, puis le pays témoin ;
- un registre `new LectureDossier(…)` qui rend le document `/maisons` du témoin, et compte ses appels ;
- des noms `new NomsDesTerres(…)` qui rendent les lieux témoins.

On clique sur l'icône, puis on appelle `Pas`, avec `maintenant` croissant, jusqu'à ce que les noms soient lus (au plus 100 appels) :
- `TexteAffiche` égale le texte exact de SC3 ;
- le registre a été lu une fois à l'ouverture, puis plus jamais tant qu'il est complet ;
- avec le pays au tick 32 : `Pays en attente du monde` ;
- fermé, puis rouvert : le registre est relu une fois de plus ;
- fermé, `Pas` laisse `TexteAffiche` tel quel.

Cas `Le_feuillet_du_cabinet_lit_la_partie` (`CabinetDeCarteTests`). Après `Proposer()`, on clique sur l'icône `Le pays`, puis on appelle `Pas` sur le `DossierPays` du cabinet. Le texte vaut `Choisissez une maison pour lire son pays.`

Contre-épreuve : un `Pas` qui écrit les terres sans comparer leur tick au monde lu rougit le premier cas.

**SC6 — L'icône du pays est dans le bandeau, hors des dossiers (`CabinetDeCarteTests.cs`, `I`).** Cas `L_icone_du_pays_ouvre_son_feuillet_hors_des_dossiers` :
- le conteneur `CabinetDeCarte.PAYS` est un enfant du bandeau, en (408, −20), de 56 × 44, et n'est pas `DOSSIERS` ;
- il porte un seul bouton, `Le pays`, de 56 × 44, sans texte actif, avec `Repère couronne` et sans `Repère livre` ;
- sa phrase commence par `Le pays : ` et diffère de son nom ;
- la toile n'a qu'un bouton `Le pays` ;
- le feuillet `Le pays` (avec sa `ScrollRect`) est fermé d'avance, s'ouvre au premier clic et se ferme au second ;
- le cadre de l'icône ne recouvre ni les glyphes du titre `FORGE · Le cabinet` (le `preferredWidth` du titre, depuis x 24, finit avant x 408), ni le cadre de la date, ni la barre des comptes, ni les jauges ;
- sur le bandeau, le feuillet ouvert ne recouvre pas la barre, comme dans `Aucun_dossier_ne_recouvre_la_barre`.

`Chaque_icone_de_la_barre_a_sa_phrase_et_son_motif`, `Aucun_dossier_ne_recouvre_la_barre`, `SansHorlogeRecueLesCommandesDuTempsRestentInactives` (trois boutons enfants directs), `ChaqueCommandeDuCabinetDitCeQuElleFait` et `LeCabinetMontreLaPhraseDuBoutonSurvole` passent sans changer. Contre-épreuve : l'icône posée dans `DOSSIERS` rougit `Chaque_icone_…`, et posée directement dans le bandeau, `SansHorloge…`.

**SC7 — Sur le vrai service, la photo et sa contre-épreuve.** Les deux commandes de la section Photo.
- `PHOTO` sort 0, avec `*--pays-1-petit-seigneur.png`, `*--pays-2-royaume.png` et deux traces `CAPTURE_1045` :
  - celle de Bar montre `suzerain « Valois »` et `bâtiments 1` ;
  - celle du royaume montre plus de 100 vassaux directs, et `suzerain « aucun »`.
- `AVANCE` sort 1, sans image, et son journal dit `panneau lu au tick`.

Le codeur ouvre chaque image lui-même et dit ce qu'il y voit.

**SC8 — Les scénarios qui lisent le bandeau et la partie restent verts.** Chacune de ces commandes sort 0 :
- `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 944 -forgeCaptures 3d/unity/Temp/lot1045-944 -logFile 3d/unity/Temp/lot1045-944.log` : aucun mot interdit ni nombre nu dans le cabinet ;
- la même avec `-forgeLot 1004`, son dossier `lot1045-1004` et son journal : rien de coupé ni de recouvert dans le bandeau, à 1280 × 720 ;
- la même avec `-forgeLot 1032`, son dossier `lot1045-1032` et son journal : la barre des jauges, sur une `LecturePartie` à six lecteurs.

**SC9 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `I`, `P` et `python3 -m pytest -q` (depuis `jeu/`) passent en entier.
- `git diff origin/master -- 3d/unity/Assets/Interface/Tests 3d/unity/Assets/ForgeLocal3D/Pont/Tests` ne montre que des lignes ajoutées.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 1 500 lignes, brief compris.

## Hors périmètre
- Servir les noms dans `/pays`, ou toucher quoi que ce soit dans `jeu/`.
- Les alertes du panneau (« ce qui menace »), et les gestes des jauges depuis Unity : le second morceau de #1033.
- Bâtir depuis la carte (#1034). Ici, seul le scénario dépose le moulin, par le chemin des intentions.
- Prendre un royaume ou n'importe quel pays (#1037). Le royaume est photographié avec la maison posée côté Unity par le scénario, et le compte rendu le dit.
- Montrer les lieux sur la carte depuis le feuillet, trier ou replier ses listes, le relire quand le maître d'un lieu change : les noms de lieux se gardent pour la session, comme dans « Terres et comptes ».
- La langue du cabinet appliquée au feuillet (#849, #850).
- La définition du PNG : la chaîne l'écrit à 1600 × 900.

## Photo
Deux images, la carte et son cabinet en entier. À gauche, le feuillet « Le pays » ouvert, en haut de sa lecture. Au-dessus, le bandeau, avec l'icône couronne entre le titre et la date, la barre des comptes et les jauges.

1. **Le petit seigneur : Bar, au jour 33 de 1400 (tick 32).** On lit, de haut en bas :
   - `Bar · relevé au jour 33 de 1400`, `Suzerain : Valois`, `Vassaux : aucun` ;
   - ses quatre lieux et ses quelque 24 000 habitants, la récolte de ses trente derniers jours en tonnes, son grenier ;
   - sous `BÂTIMENTS`, `Moulin à Bar-le-Duc : en chantier, …` ;
   - sous `SES LIEUX`, `Bar-le-Duc et 3 lieux : …`.
2. **Le royaume des Valois, suzerain de Bar**, posé par le scénario, un jour plus tard. On lit :
   - `Valois · relevé au …`, `Suzerain : aucun`, `Vassaux : 115 maisons` ;
   - près de 300 lieux et deux millions et demi d'habitants ;
   - sous `BÂTIMENTS`, `Moulin à Bar-le-Duc, de Bar : en chantier, …`.

   Le reste du feuillet (les noms des vassaux, les terres) défile plus bas.

Le scénario `Lot1045.cs` (Périmètre) joue ces étapes, et la chaîne écrit chaque image à la fin de son scénario.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1045 -forgeCaptures 3d/unity/Temp/lot1045-photo -logFile 3d/unity/Temp/lot1045-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1045 -forgeCaptures 3d/unity/Temp/lot1045-avance -forge1045Avance -logFile 3d/unity/Temp/lot1045-avance.log
```

Les deux sessions :
- **`PHOTO`**, la première, donne la photo : elle sort 0 avec ses deux images ;
- **`AVANCE`** est la contre-épreuve du même tick : le service a un tick d'avance sur le feuillet. Elle sort 1, sans image, et son journal est joint au compte rendu.

Les PNG restent hors du dépôt.
