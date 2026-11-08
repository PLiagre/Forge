# Lot #1032 — La barre porte les jauges et les points du pays
Jalon : J6 · Machine : pc · Taille prévue : 1050 lignes

## But
En haut de la carte, la barre montre au joueur les trois jauges de son pays et ses trois réserves de points, lues sur `GET /pays` au tick du monde lu, avec ce que chaque réserve gagne par mois, le sens de la dernière variation de chaque valeur, et une infobulle qui dit d'où vient chaque valeur.

## Le joueur
En haut de la carte, sous la date et les comptes de sa maison, le joueur lit d'un coup d'œil :
- la Concorde, le Renom et le Droit de son pays ;
- ses points de Plume, de Sceau et d'Épée, avec ce qu'ils gagnent par mois.

Une valeur qui vient de baisser porte « en baisse », une valeur qui vient de monter porte « en hausse ». Le mot se lit sans la couleur. Exemple : il dépense 30 points de Sceau pour asseoir son droit, et le jour suivant il lit « Sceau 1,5 point, +4,5 points/mois, en baisse » et « Droit 60 points, en hausse ».

Au survol, chaque valeur dit d'où elle vient :
- pour une réserve : la compétence de son chef ;
- pour une jauge : ses bornes, son neutre, et ce qu'elle pose à son pays (« Pose au pays : Prélèvement +2 % »).

Le seigneur de Bar gagne 5 points de Plume par mois. Le roi des Valois n'en gagne aucun : son chef a 0 en gestion, et la barre écrit « +0 point/mois », un vrai zéro. L'émir du Zab, dont le monde ne connaît pas le chef, lit « chef non connu », jamais un zéro inventé.

Il en sent ce qu'il peut se payer, et à quel rythme. C'est la décision du jalon 6 (`CAP.md`) : quand dépenser sa Plume pour affermir la concorde, son Sceau pour asseoir son droit. C'est aussi « la barre et ses jauges » de l'écran du jalon. Le geste de dépenser depuis Unity vient avec le panneau du pays (#1033). Ici, le scénario de la photo dépose lui-même la dépense par le chemin des intentions, celui du joueur.

## Règle du monde
Sans objet : c'est un lot de vue, et aucun nombre du monde ne change. Le mois des jauges, leurs causes, leurs gestes et leurs modificateurs restent ceux de `jeu/sim/MODELE.md`, « Le pays et ses jauges » (#1039).

Une seule chose change dans le service : `document_des_jauges` (donc `/pays`) sert aussi les mots que les données ont déjà :
- le `dit` de chaque jauge et de chaque réserve (`data/jauges.toml`) ;
- le `nom` de chaque grandeur sur laquelle une jauge pose (`data/modificateurs.toml` : « Départs », « Commerce », « Prélèvement »).

Une phrase s'ajoute pour le dire au paragraphe « Le pays d'un seul tenant » de cette section. Niveau 2 inchangé pour toutes les valeurs.

## Périmètre
jeu/sim/jauges.py
jeu/sim/tests/test_pays_et_jauges.py
jeu/sim/MODELE.md
3d/unity/Assets/ForgeLocal3D/Pont/ClientPays.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientPays.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/TexteDuMonde.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPaysTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPaysTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TexteDuMondeTests.cs
3d/unity/Assets/Interface/BarreDuPays.cs
3d/unity/Assets/Interface/BarreDuPays.cs.meta
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/LecturePartie.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/Interface/Tests/LecturePartieTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1032.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1032.cs.meta
docs/briefs/1032-la-barre-porte-les-jauges-et-les-points-du-pays.md

Tout autre chemin est interdit, en particulier :
- `jeu/sim/service.py`, `jeu/sim/pays.py`, `jeu/data/` ;
- `ClientMaison.cs`, `ClientMonde.cs`, `SocleInterface.cs`, `Infobulle.cs`, `DossierMaison.cs` ;
- les scénarios `Lot549`, `Lot658`, `Lot690`, `Lot944`, `Lot965`, `Lot1001`, `Lot1004`, et `PassageALaCapitale*`.

Chaque `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master 2f2b55c4 (#1039, #1040 et #1041 fusionnés). Il ne dépend d'aucun lot ouvert.

**`jeu/sim/jauges.py`** — `document_des_jauges` ajoute :
- `"dit"` à chaque entrée de `"jauges"` et de `"points"`, la valeur de `data/jauges.toml` ;
- une clé `"grandeurs"` : `{grandeur: nom}` pour chaque grandeur que posent les `modificateurs` des jauges des règles, lue dans `sim.modificateurs.charger_donnees().grandeurs[g].nom`. On l'ajoute toujours, même quand aucune pose n'est active.

Rien d'autre ne change dans ce fichier. Le document reste gardé au tick par `octets_du_pays`, sans le toucher.

**`ClientPays.cs`** (espace `Forge.Pont`, style de `ClientMaison`). `ClientPays(int port, TimeSpan delai)` lit `GET /pays?maison=<id échappé>` par `ServiceLocal`, avec le préfixe d'absence `"pays : "`. `Lire(string id)` rend une `Lecture<PaysLu>`. Une faute refuse toute la réponse, et l'absence nomme la clé fautive.

`PaysLu` porte :
- `MaisonId` : `maison.id`, qui doit égaler l'identifiant demandé ;
- `Nom` : `maison.nom`, un texte non vide ;
- `Tick` : `tick`, un entier ≥ 0 ;
- `Date` : `date`, lue par `ServiceLocal.Date` ;
- `Jauges` : sous `jauges.jauges`, chaque entrée a `nom`, `dit` (texte non vide), `valeur`, `minimum`, `maximum` et `neutre` (nombres finis, minimum ≤ valeur ≤ maximum) ;
- `Points` : sous `jauges.points`, chaque entrée a `nom`, `dit`, `valeur` (≥ 0), `plafond`, `domaine` et `ParMois` (`double?`) ;
- `Competences` : un dictionnaire `domaine → entier ≥ 0`, ou nul ;
- `SansChef` : la raison `jauges.absents.competences`, ou nulle ;
- `Poses` : sous `jauges.modificateurs`, chaque pose a `grandeur`, `NomDeLaGrandeur` (lu dans `jauges.grandeurs`), `valeur` (nombre fini) et `Jauge`, tirée de `source` = `jauge:<jauge>:<maison>`.

La lecture refuse :
- des `competences` nulles sans raison, ou une raison avec des `competences` présentes ;
- un `par_mois` nul alors que les compétences sont connues, ou un nombre alors qu'elles sont absentes ;
- un `domaine` absent des compétences présentes ;
- une pose dont la source ne vise pas cette maison ou une jauge servie, ou dont la grandeur manque à `grandeurs`.

Le client ne lit ni les lieux, ni les totaux, ni les gestes, ni les bâtiments.

**`TexteDuMonde.cs`** gagne :
- l'unité `points?` dans `Unite`. C'est l'unité des jauges et des réserves (« points de Plume », `data/jauges.toml`). Aucun cas existant ne change ;
- `Points(double v)`. Il lève `ArgumentException` pour une valeur non finie. Sinon il arrondit au dixième (`AwayFromZero`), écrit avec le format `Fr` du fichier (« 0.# »), puis ajoute `" point"` si |arrondi| < 2, `" points"` sinon. Par exemple `-1 point`, `1,5 point`, `31,5 points`.

**`LecturePartie.cs`** gagne :
- un 6ᵉ paramètre optionnel `Func<string, Lecture<PaysLu>> pays = null`, et `Pays { get; private set; }`. Il est lu au même passage que les comptes, seulement avec une maison du joueur. Il est remis à nul avec les comptes dans le `catch` ;
- dans `Locale(port)`, `id => { using var c = new ClientPays(port, TimeSpan.FromSeconds(10)); return c.Lire(id); }`.

**`BarreDuPays.cs`** (espace `Forge.Interface`) est une classe simple, pas un `MonoBehaviour`. `new BarreDuPays(RectTransform bandeau)` pose dans le bandeau un conteneur `"Jauges du pays"` (constante `BarreDuPays.NOM`) en (24, 98), de 1872 × 26. Il porte :
- un `Text` d'état `"Lecture du pays…"`, de 1872 de large ;
- six `Text` nommés `Concorde`, `Renom`, `Droit`, `Plume`, `Sceau`, `Épée`, posés par `SocleInterface.Texte(…, taille: 16)`, couleur « papier », `supportRichText = false`. Ils vont en x 0, 240, 480 (240 de large) puis 720, 1104, 1488 (384 de large), tous à y 0 et 26 de haut.

Chaque cellule porte une `Infobulle` dont la `phrase` est récrite à chaque affichage. `Afficher(Lecture<MondeAvecMaisonLu> monde, Lecture<PaysLu> pays)` suit l'ordre de `CabinetDeCarte.Barre` :
- **pas de monde lu** : l'état dit `Lecture du pays…` ;
- **monde absent** : `Pays indisponible : <TexteDuMonde.Absence>` ;
- **pas de maison du joueur** : le conteneur reste vide, état et cellules inactifs ;
- **pays nul, pays d'une autre maison, ou d'un autre tick que le monde lu** : `Jauges en attente du monde` ;
- **pays absent** : `Jauges indisponibles : <TexteDuMonde.Absence(raison, id)>`. Une jauge ou une réserve de l'ordre ci-dessus que le service ne sert pas donne aussi « indisponibles », en la nommant ;
- **sinon** : l'état est inactif et les six cellules sont actives.

Le texte de chaque cellule :
- **une jauge** : `<nom servi> <Points(valeur)>`, par exemple `Concorde -1 point` ;
- **une réserve dont le chef est connu** : `<nom> <Points(valeur)>, +<Points(par_mois)>/mois` ;
- **une réserve sans chef connu** : `<nom> <Points(valeur)>, chef non connu`, sans gain et sans « /mois » ;
- **le sens** : `, en baisse` ou `, en hausse` à la fin, quand la barre a vu la valeur changer (voir plus bas).

La phrase de chaque infobulle, dont chaque nombre porte son unité :
- **une jauge** :
  - `<nom> : <dit>. <Points(valeur)>, de <Points(min)> à <Points(max)>, neutre à <Points(neutre)>.` ;
  - puis `Pose au pays : <NomDeLaGrandeur> <±valeur × 100, fr-FR « 0.## »> %.` pour chacune de ses poses, ou `À son neutre, elle ne pose rien.` ;
- **une réserve** :
  - `<nom> : <dit>. <Points(valeur)>, au plus <Points(plafond)>.` ;
  - puis `Gagne <Points(par_mois)> par mois : la <domaine> du chef, <compétence> point(s).` (la compétence écrite par `Points`). Sans chef : `Le monde ne connaît pas le chef de cette maison : ce qu'elle gagne par mois est absent, pas nul (<TexteDuMonde.Absence(SansChef, id)>).` ;
- **le sens** : `En baisse depuis le <TexteDuMonde.Date> : de <Points(avant)> à <Points(après)>.` (ou « En hausse ») ;
- **à la fin** : `Relevé au <TexteDuMonde.Date(date servie)>.`

**Le sens.** La barre garde, pour la maison qu'elle montre, la dernière lecture faite à un tick plus grand que la précédente. Quand une valeur diffère de la lecture d'avant, la barre retient ce changement : son sens, son avant, son après, et la date de la lecture. Le mot reste tant que la valeur ne change plus. Une autre maison, ou un tick plus petit, efface tout ce qui est retenu. La première lecture n'a pas de sens. La barre compare deux valeurs servies : elle n'ajoute aucune règle au monde.

**`CabinetDeCarte.cs`** :
- le bandeau passe de 100 à 124 de haut. 124, c'est le haut de chaque panneau posé sous lui : les feuillets, « Votre maison », le plan du bourg, le menu, et le panneau de passage à `(-24, -124)` ;
- `Construire` crée `new BarreDuPays(bandeau)` après la barre des comptes ;
- `Afficher` appelle `Afficher(Partie.Monde, Partie.Pays)` juste après `barre.text = Barre(…)`.

Le `Text` « Lecture de la maison… », son cadre (24, 72, 1872 × 26), son texte et `Barre` ne changent pas. Aucun bouton ne s'ajoute au bandeau.

**`Lot1032.cs`** est une `static class Lot1032`, dans le style de `Lot1001`. Ses trois scénarios se jouent dans l'ordre de leur nom, sur le même service. La première faute lève une `InvalidOperationException` qui la nomme.

Le scénario écrit lui-même :
- **le texte attendu de chaque cellule**, depuis une lecture indépendante (`new ClientPays(port, …).Lire(id)`), sans appeler `BarreDuPays`. Il ne rend `internal` aucune fonction privée ;
- **le jugement**, fait dans la même image et sans `yield` :
  - le tick lu par `Partie.Pays` égale le tick servi, sinon `barre lue au tick T, pays servi au tick T'` ;
  - chaque cellule active égale son texte attendu ;
  - chaque phrase contient le `dit` servi et ses poses, ou `chef non connu` ;
  - chaque texte et chaque phrase passent `TexteDuMonde.Interdit(t, id)` et `SansUnite` ;
  - chaque cellule tient dans son cadre (`preferredWidth` ≤ largeur + 0,5) et passe `Lot690.DansLeChamp`.

1. **`barre-1-petit-seigneur`.**
   - Il ouvre la carte par `Lot549.Ouvrir`, puis attend `Lot690.LecturePrete`. Le tick lu doit égaler `-forgeTicks` (30 par défaut, lu comme `Lot658.Depart`).
   - Il choisit le départ dont le siège est « Bar-le-Duc », pousse un tick, puis attend que la barre de cette maison soit à jour au tick du monde lu.
   - **Lecture R1.** Il la juge, sans sens. Avec `-forge1032Avance`, il pousse d'abord un tick, dans la même image : le jugement doit échouer.
   - **Sans `-forge1032Depense`.** Il pousse trente ticks, attend, puis juge la lecture R2. Les trois réserves portent `, en hausse`, et les trois jauges aucun sens. Le sens attendu est le signe de R2 − R1.
   - **Avec `-forge1032Depense`.** Il dépose `{"type":"depenser_jauge","maison":"<id de Bar>","geste":"asseoir_le_droit"}` par `ClientIntention`. Le reçu doit être accepté. Il pousse un tick, puis juge R2 :
     - `Sceau 1,5 point, +4,5 points/mois, en baisse` ;
     - `Droit 60 points, en hausse` ;
     - la phrase du Droit contient `Pose au pays : Prélèvement +2 %.`
   - Il passe la toile en `ScreenSpaceCamera` comme `Lot658` (`Lot549.Photographier`, `camera.rect` plein, `planeDistance` à `nearClipPlane + 0.2`). Il montre l'infobulle de la Plume par `Infobulle.Montrer` sur la cellule (celle du Droit avec `-forge1032Depense`), puis laisse passer 10 images.
2. **`barre-2-royaume`.** Le monde ne laisse pas encore le joueur prendre un royaume (#1037). Le scénario pose donc la maison du joueur côté Unity :
   - Il remplace `cabinet.Partie`, une fois libre, par une `LecturePartie` faite des clients de `Locale`. Son lecteur de monde rend le monde servi avec `MaisonDuJoueur` = le suzerain de Bar, lu dans `ClientMaison.LireComptes`. Ce suzerain doit être une maison sans suzerain, qui tient plus de lieux que Bar.
   - Le service, `/pays`, son tick et la barre sont les vrais.
   - Il juge R1, pousse trente ticks, puis juge R2. La Plume des Valois reste `0 point, +0 point/mois`, sans sens. Il montre l'infobulle de la Plume.
   - La trace dit `maison posée par le scénario`.
3. **`barre-3-sans-chef`.** Il pose de même la maison `seigneurie-6`. `/pays` doit la nommer « Banou Mozni » et déclarer `absents.competences`, sinon `la maison sans chef a un chef`. Il juge :
   - les trois réserves finissent par `, chef non connu` ;
   - aucune cellule ne contient `+0` ni `/mois`.

   Il montre l'infobulle de la Plume.

Chaque scénario écrit `CAPTURE_1032 <nom> maison « <nom servi> » au tick T, pays servi au tick T : <les six cellules sur une ligne>`.

## Conditions de succès
On lance depuis la racine. Python : `cd jeu && python3 -m pytest -q` (tout le jeu).

Sur le PC, éditeur fermé, en PowerShell, `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Deux commandes de tests :
- `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot1032-interface.xml -logFile 3d/unity/Temp/lot1032-interface.log` ;
- `P` = la même avec `-assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot1032-pont.xml -logFile 3d/unity/Temp/lot1032-pont.log`.

Chacune sort 0, sans échec ni cas ignoré, et ses cas neufs réussissent. Chaque pays témoin porte la date que le service servirait à son tick : `new DateDuMonde(1400, tick + 1)`.

**SC1 — `/pays` dit ses jauges en mots (`test_pays_et_jauges.py`).** Cas `test_le_service_dit_les_jauges_et_ce_qu_elles_posent`, sur `ServeurMonde(("127.0.0.1", 0), 0, 0)` et `octets_du_pays("seigneurie-1")` :
- chaque `jauges.jauges[n].dit` et `jauges.points[n].dit` égale celui des règles ;
- `jauges.grandeurs` vaut `{"commerce": "Commerce", "departs": "Départs", "prelevement": "Prélèvement"}`, chaque nom relu dans `modificateurs.charger_donnees()` ;
- sur une copie du monde de départ où `asseoir_le_droit` a été appliqué à `seigneurie-1` (`J.appliquer_geste`), chaque grandeur des `modificateurs` de `document_des_jauges` est une clé de `grandeurs`.

Contre-épreuve : un document sans `grandeurs`, ou sans `dit`, rougit le cas. `test_le_service_sert_le_pays_et_ses_jauges` passe sans changer.

**SC2 — Le pays se lit en entier ou pas du tout (`ClientPaysTests.cs`, `P`).**
- `Le_pays_se_lit_avec_ses_jauges_ses_points_et_ses_poses` : un document témoin (Bar, tick 31, Droit 60 avec sa pose sur `prelevement`) donne chaque valeur, `ParMois` et `NomDeLaGrandeur` = « Prélèvement ».
- `Sans_chef_le_gain_est_absent_pas_nul` : `competences` nulles avec leur raison donnent `Competences == null`, `SansChef` non nul, et chaque `ParMois == null`.
- `Un_pays_mal_servi_est_refuse` : chaque refus de la section Périmètre est essayé un à un. On y ajoute un `tick` absent, négatif ou décimal, un `maison.id` autre que celui demandé, un `dit` vide, et une valeur hors de ses bornes. Chacun donne une lecture absente qui nomme sa clé.

Contre-épreuve : un client qui lit un `par_mois` nul comme 0 rougit `Sans_chef_…`.

**SC3 — Les points s'écrivent avec leur unité (`TexteDuMondeTests.cs`, `P`).** Cas `Points_s_ecrivent_avec_leur_unite` :
- `Points` donne `0 point`, `1 point`, `1,5 point`, `2 points`, `31,5 points`, `-1 point`, `-3 points`, `999 points` ;
- `Points(double.NaN)` lève ;
- chaque texte passe `Interdit` et `SansUnite`, et `"+4,5 points/mois"` aussi ;
- `SansUnite("Droit 50")` vaut toujours `"50"`, et `SansUnite("5 pointsx")` vaut `"5"`.

Tous les cas existants de `TexteDuMondeTests` passent sans changer. Contre-épreuve : sans `points?` dans `Unite`, le cas rougit.

**SC4 — La partie lit le pays au même passage (`LecturePartieTests.cs`, `I`).** Cas `Le_pays_se_lit_avec_la_maison` :
- monde sans maison : aucun appel au lecteur de pays, et `Pays` nul ;
- monde qui nomme `identifiant-servi` : un appel avec cet identifiant ;
- une `LecturePartie` à cinq paramètres laisse `Pays` nul ;
- un lecteur de monde qui lève laisse `Pays` nul.

Contre-épreuve : lire le pays sans maison rougit le cas.

**SC5 — Les jauges de la barre égalent le pays servi au même tick (`CabinetDeCarteTests.cs`, `I`).** Cas `Les_jauges_de_la_barre_egalent_le_pays_servi_au_meme_tick`. Monde au tick 1, puis `Poser(partie, "Pays", …)` d'un pays témoin de `JOUEUR` au tick 1 : Concorde 0, Renom 12,34, Droit 50, Plume 5 (+5), Sceau 0 (+0), Épée 3,5 (+3,5). Les six cellules valent exactement :
- `Concorde 0 point`, `Renom 12,3 points`, `Droit 50 points` ;
- `Plume 5 points, +5 points/mois`, `Sceau 0 point, +0 point/mois`, `Épée 3,5 points, +3,5 points/mois`.

Ensuite :
- au tick 0, au tick 2, et pour `B` au tick 1 : l'état vaut `Jauges en attente du monde`, les cellules sont inactives, et aucun `Text` du bandeau ne contient `12,3` ;
- avec un pays absent (`"refus témoin"`) : `Jauges indisponibles : refus témoin` ;
- après `Proposer()` : rien d'actif dans `Jauges du pays`.

Le texte de la barre des comptes (SC1 de #1001) ne change pas. Contre-épreuve : une barre qui ne compare pas le tick rougit le cas.

**SC6 — Sans chef connu, l'absence et pas un zéro (`CabinetDeCarteTests.cs`, `I`).** Cas `Sans_chef_connu_la_barre_dit_l_absence` :
- le même pays sans compétences donne `Plume 0 point, chef non connu` (de même pour le Sceau et l'Épée). Aucune cellule ne contient `+0` ni `/mois`, et chaque phrase contient `absent, pas nul` ;
- le même pays avec des compétences à 0 et des `par_mois` à 0 donne `Plume 0 point, +0 point/mois`.

Contre-épreuve : les deux textes diffèrent. Une barre qui écrit le gain absent comme 0 rougit le cas.

**SC7 — Une jauge qui baisse se voit (`CabinetDeCarteTests.cs`, `I`).** Cas `Une_jauge_qui_baisse_se_voit` :
- **lecture 1, tick 1** (Concorde 0, Sceau 31,5, Droit 50) : aucun sens ;
- **lecture 2, tick 2** (Concorde −1, Sceau 1,5, Droit 60), monde remis au même tick :
  - `Concorde -1 point, en baisse`, `Sceau 1,5 point, +4,5 points/mois, en baisse`, `Droit 60 points, en hausse` ;
  - la phrase de la Concorde contient `En baisse depuis le jour 3 de 1400 : de 0 point à -1 point.` et `Pose au pays : Départs +5 %.` ;
- **lecture 3, tick 3**, mêmes valeurs : les mots restent ;
- **le pays de `B`, puis un tick plus petit** : plus aucun sens.

Contre-épreuve : la lecture 1 seule n'a aucun mot. Une barre qui compare au neutre plutôt qu'à la lecture d'avant rougit le cas.

**SC8 — Chaque valeur dit d'où elle vient, et tient dans la barre (`CabinetDeCarteTests.cs`, `I`).** Cas `Chaque_jauge_dit_d_ou_vient_sa_valeur` :
- sur le témoin de SC5 (tick 1), chaque cellule a une `Infobulle` dont la phrase commence par `<nom> : <dit>.` et finit par `Relevé au jour 2 de 1400.` ;
- la Plume dit `la gestion du chef, 10 points`, et la Concorde au neutre `À son neutre, elle ne pose rien.` ;
- chaque phrase passe `Interdit(t, JOUEUR, B)` et `SansUnite`.

Cas `Les_jauges_tiennent_dans_le_bandeau` :
- le bandeau a `sizeDelta` (1920, 124), et `Jauges du pays` est son enfant, en (24, −98), de 1872 × 26 ;
- les six cadres ne se chevauchent pas, tiennent dans le conteneur et tiennent au-dessus de y 124 ;
- avec les textes les plus longs (`Concorde -3 points, en baisse`, `Renom 100 points, en baisse`, `Droit 100 points, en hausse`, `Plume 999 points, +5 points/mois, en baisse`, `Sceau 999 points, +5 points/mois, en hausse`, `Épée 999 points, +5 points/mois, en baisse`), chaque `preferredWidth` ≤ la largeur de sa cellule et chaque `preferredHeight` ≤ 26 ;
- `SansHorlogeRecueLesCommandesDuTempsRestentInactives` compte toujours trois boutons.

Si un texte le plus long ne tient pas à 16, le codeur passe les six cellules à 15 et le dit au compte rendu. Il ne change pas leurs cadres. `Aucun_dossier_ne_recouvre_la_barre` passe sans changer, sur le bandeau agrandi. Contre-épreuve : des cellules de 200 de large rougissent le cas.

**SC9 — Sur le vrai service, la photo et ses contre-épreuves.** Les trois commandes de la section Photo.
- `PHOTO` sort 0, avec `*--barre-1-petit-seigneur.png`, `*--barre-2-royaume.png`, `*--barre-3-sans-chef.png` et trois traces `CAPTURE_1032`. La trace du petit seigneur montre `+5 points/mois` et `, en hausse`. Celle du royaume montre `+0 point/mois`. Celle du Zab montre `chef non connu`.
- `AVANCE` sort 1, sans image, et son journal dit `barre lue au tick`.
- `DEPENSE` sort 0 avec ses trois images. Sa trace du petit seigneur montre `Sceau 1,5 point, +4,5 points/mois, en baisse` et `Droit 60 points, en hausse`.

Le codeur ouvre chaque image lui-même et dit ce qu'il y voit.

**SC10 — Les scénarios qui lisent le bandeau restent verts.** `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 944 -forgeCaptures 3d/unity/Temp/lot1032-944 -logFile 3d/unity/Temp/lot1032-944.log` sort 0 : chaque texte actif du cabinet, les jauges comprises, est jugé sans mot interdit ni nombre nu. Les mêmes commandes sortent aussi 0 avec `-forgeLot 965` (le bandeau ne bouge pas au changement de mode) et avec `-forgeLot 1004` (rien de coupé ni de recouvert dans le bandeau agrandi, à 1280 × 720). Chacune a son dossier `lot1032-965` et `lot1032-1004`, et son journal.

**SC11 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `I`, `P` et `python3 -m pytest -q` passent en entier.
- `git diff origin/master -- 3d/unity/Assets/Interface/Tests 3d/unity/Assets/ForgeLocal3D/Pont/Tests jeu/sim/tests` ne montre que des lignes ajoutées.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 1 500 lignes, brief compris.

## Hors périmètre
- Dépenser ses jauges depuis Unity, le panneau du pays et ses alertes (#1033). Ici, seul le scénario dépose la dépense, par le chemin des intentions.
- Prendre un royaume ou n'importe quel pays (#1037). La barre du royaume est photographiée avec la maison posée côté Unity par le scénario, et le compte rendu le dit.
- L'infobulle des modificateurs du lieu survolé (#1031), et la langue du cabinet appliquée à la barre (#849, #850).
- Toute cause neuve des jauges, l'IA qui joue ses jauges (#1035), et les événements (#1038).
- Le service (`service.py`), `pays.py`, les données, la barre des comptes de #1001 et sa fonction `Barre`.
- La définition du PNG : la chaîne l'écrit à 1600 × 900.

## Photo
Trois images par session, la carte et son cabinet en entier.

1. **Le petit seigneur : Bar, au jour 62 de 1400 (tick 61).** En haut, le bandeau, avec en dessous la barre des comptes de Bar. Sous elle, la ligne des jauges :
   - `Concorde 0 point · Renom 0 point · Droit 50 points` ;
   - `Plume 10 points, +5 points/mois, en hausse`, `Sceau 9 points, +4,5 points/mois, en hausse`, `Épée 7 points, +3,5 points/mois, en hausse`.

   L'infobulle de la Plume est ouverte : « la gestion du chef, 10 points ».
2. **Le royaume des Valois, suzerain de Bar**, posé par le scénario au tick 61, photographié trente jours plus tard. On y lit `Plume 0 point, +0 point/mois`, un vrai zéro, et son infobulle « la gestion du chef, 0 point ».
3. **Le Zab des Banou Mozni, sans chef connu.** Ses trois réserves disent `chef non connu`, et l'infobulle de la Plume le dit « absent, pas nul ».

Dans la session `DEPENSE` (monde poussé au tick 210, Bar choisi, sept mois de points : 31,5 de Sceau), la première image montre `Sceau 1,5 point, +4,5 points/mois, en baisse` et `Droit 60 points, en hausse`, avec l'infobulle du Droit : « Pose au pays : Prélèvement +2 % ». Le scénario `Lot1032.cs` (Périmètre) joue ces étapes et la chaîne écrit chaque image à la fin de son scénario.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1032 -forgeCaptures 3d/unity/Temp/lot1032-photo -logFile 3d/unity/Temp/lot1032-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1032 -forgeCaptures 3d/unity/Temp/lot1032-avance -forge1032Avance -logFile 3d/unity/Temp/lot1032-avance.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1032 -forgeCaptures 3d/unity/Temp/lot1032-depense -forgeTicks 210 -forge1032Depense -logFile 3d/unity/Temp/lot1032-depense.log
```

Les trois sessions :
- **`PHOTO`**, la première, donne la photo : elle sort 0 avec ses trois images ;
- **`AVANCE`** est la contre-épreuve du même tick : elle sort 1, sans image ;
- **`DEPENSE`** joue la jauge qui baisse : elle sort 0, avec ses images et ses traces jointes au compte rendu.

Les PNG restent hors du dépôt.
