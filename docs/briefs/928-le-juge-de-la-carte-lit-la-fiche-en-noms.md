# Lot #928 — Le juge de la carte lit la fiche en noms
Jalon : J4 · Machine : vps · Taille prévue : 280 lignes

## But
L'épreuve de la carte juge la fiche de survol écrite en noms (bourg, villes, habitants, date, jours de faim, masse de dette) contre `/carte`, `/monde` et `/lieu?cell=C`, et refuse une fiche qui parle encore en identifiants ou en ticks.

## Le joueur
Le joueur n'y voit rien encore, mais l'épreuve refusera une fiche qui parle en identifiants. Lot de fond, sous-lot 1 de #912, lui-même issu de #884, #872 et #856 (« La fiche parle en noms, pas en identifiants », `CAP.md`, jalon 4, lot 18). Le geste qu'il prépare : le joueur survole une terre, lit « Metz », « 1 234 habitants · jour 31 de 1400 », « 2 jours de manque », « 12,5 kg », reconnaît sa capitale et y descend sans traduire « Cellule 10437 » ni « tick 30 ». Le sous-lot 2 de #912 (pc, après celui-ci) branche cette fiche à l'écran et fait passer l'épreuve réelle.

## Règle du monde
Sans objet : lot d'outil. Aucun nombre du monde ne change ; ni `jeu/sim/`, ni `MODELE.md`, ni le service, ni le C# ne sont touchés. Le juge suit `FicheDeCellule.Decrire(c, monde, nomDuBourg)` (lot #910) : le bourg est le rang 0 du `/lieu` de la terre, la date est celle que sert `/monde`, −1 reste « non calculée » et 0 est une mesure.

## Périmètre
pc/epreuve_carte.py
jeu/ville/tests/test_epreuve_carte.py
docs/briefs/928-le-juge-de-la-carte-lit-la-fiche-en-noms.md

## Conditions de succès
Depuis la racine, sur le VPS. `TESTS` = `python3 -m pytest jeu/ville/tests/test_epreuve_carte.py -q`. Les cas neufs s'écrivent d'abord, et on les voit rouges. `NBSP` = U+00A0. `METZ` = 10437 ; dans la carte servie, sa seule ville est « Metz » et elle n'a pas de maison.

**Ce que devient `pc/epreuve_carte.py`.** Les regex `_TETE`, `_HABITANTS`, `_FAIM`, `_DETTE` disparaissent avec l'ancien format. Les fonctions de #911 (`nombre`, `jours`, `date`, `masse`, `bourg`) ne changent pas.
- `lire_fiche(texte)` rend des écrits, pas des nombres : `{"bourg", "villes", "puissance", "maison", "habitants", "date", "faim", "dette"}`. Il faut 6 lignes. Ligne 1 : le bourg, puis, après le premier « · », les villes séparées par « , » (aucun « · » : liste vide ; rien après « · » : illisible). « Bourg en lecture » (constante `EN_LECTURE`) se lit `None`. Lignes 2 et 3 : comme aujourd'hui (`AUCUNE` → `None`). Ligne 4 : `Habitants : (-?\d{1,3}(?:NBSP\d{3})*) (habitants?) · (jour \d+ de \d+)` en `fullmatch`, sinon illisible ; `habitants` = les deux premiers groupes séparés par une espace, `date` = le troisième. Lignes 5 et 6 : préfixes « Faim : » et « Dette de nourriture : » exigés ; le reste est l'écrit. Toute autre forme lève `ValueError` « fiche illisible ».
- `references(carte, monde, lieu, cellule)` rend les mêmes clés, écrites par le juge : `bourg` = `bourg(lieu)` ; `villes` = les noms servis par `/carte`, dans l'ordre, sans ceux qui valent le bourg ; `puissance`, `maison` comme aujourd'hui ; `habitants` = `nombre(p)` + « habitant » si p vaut 0 ou 1, « habitants » sinon ; `date` = `date(monde["date"])` ; `faim` = « non calculée » si −1, sinon `jours(h)` + « de manque » ; `dette` = « non calculée » si < 0, sinon `masse(kg)`. Un `lieu["cell_id"]` différent de `cellule` lève `ValueError` qui cite les deux identifiants ; une erreur de `bourg` remonte.
- `juger(rapport, carte, monde, lieu, cellule)` garde ses gardes (cellules, carte non posée, défaut, `survolee`), puis une ligne par clé, dans l'ordre ci-dessus : `f"{champ} : fiche {vu!r} · service {valeur!r} · égal"` ou `· ÉCART`. L'identité de la terre est tenue par `survolee` et par le bourg du `/lieu` de C.
- `main` lit `/lieu?cell=C` avec `/carte` et `/monde`, avant tout décalage, et appelle `references(carte, monde, lieu, cellule)` dans le même `try` : un `/lieu` d'une autre terre sort à 2 (« épreuve impossible »), avant Unity. La docstring dit les trois lectures.

**Réécriture selon la décision A (#856).** Le helper `fiche(...)` du test écrit la forme à trois arguments de `FicheDeCellule.Decrire` avec `nombre`, `date`, `jours`, `masse` du juge, et prend le nom du bourg. Un helper met `cell_id` et le nom du rang 0 de la fixture `lieu` (celle de #911, terre 9922, « Övre vik ») à la terre jugée. Aucun cas n'est retiré : chacun garde sa vérification, dite en noms.

**SC1 — La fiche égale reste égale.** `TESTS`. `test_la_carte_qui_dit_le_monde_servi_est_egale` : bourg « Metz », fiche « Metz » sans « · », égal ; une ligne vaut `habitants : fiche '1\xa0234 habitants' · service '1\xa0234 habitants' · égal` (écrite par `!r`) ; le témoin `maison : fiche None · service None` reste. Cas neuf : bourg servi « Övre vik », fiche « Övre vik · Metz », égal, `villes : fiche ['Metz'] · service ['Metz'] · égal`. `test_une_faim_non_calculee_se_relit` : autre terre, faim et dette −1, égal, `faim : fiche 'non calculée' · service 'non calculée' · égal`. Contre-épreuve : un `references` qui garde la ville du bourg rend `service ['Metz']` au premier cas et rougit.

**SC2 — Chaque écrit compte.** `TESTS`, chaque cas non égal avec sa ligne `ÉCART` :
- `test_un_jour_de_decalage_est_refuse` (remplace `test_un_tick_de_decalage_est_refuse`) : fiche au jour 32, `date : fiche 'jour 32 de 1400' · service 'jour 31 de 1400' · ÉCART` ;
- `test_chaque_nombre_compte`, mêmes 5 cas : population 1235 → `habitants`, faim 3 et −1 → `faim`, dette 12.25 et −1 → `dette` ;
- cas neufs : fiche « Övre vik · Metz » quand `/lieu` sert « Metz » → `bourg : fiche 'Övre vik' · service 'Metz' · ÉCART` ; fiche « Bourg en lecture · Metz » → `bourg : fiche None · service 'Metz' · ÉCART` ; fiche « Metz · Metz » → `villes : fiche ['Metz'] · service [] · ÉCART`.
Contre-épreuve : un juge qui ignore la date, le bourg ou les villes laisse un de ces cas égal et rougit.

**SC3 — Ce qui ne dit pas le monde est illisible.** `TESTS`. `test_une_absence_du_monde_n_est_jamais_lue_comme_des_zeros` : fiche en noms dont la fin est « Habitants et faim : déclaré absent par le monde » → `lire_fiche` lève « fiche illisible », `juger` non égal, dernière ligne « fiche illisible… ». Cas neuf : l'ancien texte littéral `"Cellule 10437 · Metz\nPuissance : …\nMaison : aucune, le monde n'en nomme pas\nHabitants : 1234 au tick 30\nFaim : 2 ticks de manque\nDette de nourriture : 12.5 kg"` (puissance de la fixture) → même refus. Contre-épreuve : une ligne 4 lue par simple préfixe rend l'ancien texte lisible et rougit.

**SC4 — Un `/lieu` d'une autre terre rend l'épreuve impossible.** `TESTS`, cas neufs : `references` avec la fixture `lieu` brute (9922) pour `METZ` lève `ValueError` dont le message contient « 9922 » et « 10437 » ; `main(["--sortie", …, "--unity", <fichier vide de tmp_path>, "--cellule", "10437"])`, avec `JOUER._repond` → `False`, `_lancer_service` → `None`, `_requete` qui sert la carte, le monde et la fixture `lieu` brute selon le chemin, et `JALON1._unity` qui fait échouer le test s'il est appelé : rend `IMPOSSIBLE`, stderr contient « 9922 » et « 10437 ». Contre-épreuve : un `main` qui ne lit pas `/lieu` ou ne compare pas `cell_id` lance Unity et rougit.

**SC5 — Les libellés sont ceux de la fiche en noms.** `TESTS`, `test_les_libelles_sont_ceux_de_la_fiche_et_du_rapport` cherche dans `FicheDeCellule.cs` : `"Bourg en lecture"`, `" · "`, `"\nPuissance : "`, `"\nMaison : "`, `"\nHabitants : "`, `" habitant"`, `" habitants"`, `"\nFaim : "`, `" de manque"`, `"\nDette de nourriture : "`, `AUCUNE`, `NON_CALCULEE`, et les appels `TexteDuMonde.Nombre(vivante.Population)`, `TexteDuMonde.Date(m.Date)`, `TexteDuMonde.Jours(vivante.HungerTicks)`, `TexteDuMonde.Masse(vivante.FoodDeficitKg)`. Les clés du rapport et la méthode d'`EpreuveCarte.cs` restent vérifiées. Contre-épreuve : « jours de manque » au lieu de `" de manque"` rougit.

**SC6 — Rien ne s'assouplit, rien d'autre ne bouge.**
- chaque `def test_` de `origin/master` existe encore sous son nom, sauf le renommage de SC2 ; `test_chaque_nombre_compte` garde ses 5 cas ;
- `git diff origin/master -- jeu/ville/tests/test_epreuve_carte.py` ne retire aucune ligne entre `# Lot #911` et la fin du fichier ;
- `python3 -m pytest jeu -q` passe ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ; `git diff origin/master -- 3d/` est vide ;
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.
Contre-épreuve : un cas supprimé, un fichier C# ouvert ou un diff trop gros refuse la livraison.

## Hors périmètre
- Brancher la fiche en noms à l'écran, `EpreuveCarte.cs`, `Lot526`, la capture, et l'épreuve réelle sur le PC : c'est le sous-lot 2 de #912. Jusqu'à lui, l'épreuve réelle trouve l'ancienne fiche illisible ; c'est attendu.
- Toucher au C#, à `TexteDuMonde`, au service ou à `jeu/sim/`.
- Recopier `Interdit`, `SansUnite` ou `Absence` dans le juge, ou lire le bloc `noms` de `/lieu`.
- Changer `nombre`, `jours`, `date`, `masse`, `bourg` ou leurs tests.
