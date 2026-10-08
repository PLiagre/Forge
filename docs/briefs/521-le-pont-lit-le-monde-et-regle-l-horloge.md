# Lot #521 — Le pont lit le monde et règle l'horloge
Jalon : J3 · Machine : pc · Taille prévue : 290 lignes

## But
Unity sait relire la date, les habitants, la faim et la dette des cellules du monde, ainsi que lire et régler l'horloge du service local, en déclarant toute absence.

## Le joueur
« Le joueur ne voit rien encore ; prépare la date qui avance, la pause et la fiche d'une cellule sur sa carte. » Ce lot de fond prépare l'observation des habitants et de leur faim dans le temps, nécessaire pour décider de prendre moins ou de rouvrir son grenier en J3. La scène de carte issue de #403 rendra ces lectures et la pause visibles ; #405 y ajoutera les gestes de prélèvement et de restitution. Le joueur pourra alors arrêter le temps pour examiner sa terre et comprendre ce que vivent ses gens. Ici, aucun écran ne change.

## Règle du monde
Sans objet : clients de vue et de commande, sans modification de la simulation ni de ses règles. Niveau de fidélité : sans objet. Références de lecture : `jeu/sim/MODELE.md`, « La base de temps », « Le déficit alimentaire et la mortalité » et « Ce que veut dire “affamée” ». La dette est alimentaire, en kg ; la faim est une durée en ticks, jamais déduite d'un stock vide. `cell_id` reste la seule clé spatiale. Le service tient seul l'horloge ; Unity relit la date servie et transmet une vitesse, sans avancer ni recalculer le monde.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientMonde.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientMonde.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/ClientHorloge.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientHorloge.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientMondeHorlogeTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientMondeHorlogeTests.cs.meta
docs/briefs/521-le-pont-lit-le-monde-et-regle-l-horloge.md

Tout autre chemin est interdit. Dépend de : aucun lot restant ; le service, `LecteurJson` et les assemblages `Forge.Pont` / `Forge.Pont.Tests` existent. Aucun besoin de `ClientCarte` : ces clients peuvent être construits séparément.

## Conditions de succès
SC1 — Compilation et preuves Unity. Sur le PC, depuis la racine, avec Unity 6000.0.43f1 indiqué dans `ProjectSettings/ProjectVersion.txt`, exécuter cette commande, sans `-quit` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults <temp>/pont-521.xml -logFile <temp>/pont-521.log
```
Exiger code de sortie 0, XML présent, aucun test échoué ni ignoré dans `ClientMondeHorlogeTests`, et des cas exécutés pour SC2 à SC5. Les tests existants gardent leurs noms, leurs assertions et leur nombre de cas. Contre-épreuve : exécuter d'abord les nouveaux tests avec les capacités manquantes et conserver le résultat rouge ; après implémentation, retirer temporairement l'envoi de vitesse fait rougir SC3. Rétablir le code et rejouer la commande. Aucun test existant n'a besoin de changer.

SC2 — Lecture fidèle du monde. La commande Unity de SC1 exerce `ClientMonde(int port, TimeSpan delai).Lire()` contre un `HttpListener` sur un port libre de `127.0.0.1`, comme les tests du pont existants. Le faux service retient méthode, chemin, requête et corps ; il peut rendre des réponses successives, un statut fautif ou rester muet. Il se ferme après chaque cas. La réponse témoin est :
```
{"tick":5,"date":{"annee":1400,"jour_de_l_annee":6},"cell_count":2,"cells":[{"cell_id":9922,"population":123,"hunger_ticks":3,"food_deficit_kg":12.5},{"cell_id":10417,"population":0,"hunger_ticks":-1,"food_deficit_kg":-1}]}
```
Exiger `GET /monde`, sans requête ni corps, et l'égalité exacte de chaque valeur, dans l'ordre reçu ; conserver les deux champs de date, le tick, le compte et toutes les cellules dans des données accessibles en lecture seule. `population=0` est une mesure ; `hunger_ticks=-1` et `food_deficit_kg=-1` restent « non calculé », jamais zéro. Une seconde réponse au tick 6, jour 7, avec une population et une dette différentes, est réellement relue par le même client. Une clé supplémentaire (`stocks` ou `maison_du_joueur`) est ignorée. Contre-épreuve : remplacer temporairement la dette lue par la population, ou rendre la première réponse à la seconde lecture, fait échouer cette commande.

SC3 — Horloge lue et réglée. La commande Unity de SC1 exerce `ClientHorloge(int port, TimeSpan delai).Lire()` et `.Regler(double joursParSeconde)`. `Lire` envoie `GET /horloge` sans requête ; `Regler` envoie `POST /vitesse?jours_par_seconde=<nombre>`, sans corps, avec le nombre écrit en culture invariante. Les deux rendent la même forme de lecture : tick, année, jour de l'année, jours par seconde. Le témoin est :
```
{"tick":5,"date":{"annee":1400,"jour_de_l_annee":6},"jours_par_seconde":2.5,"duree_dernier_tick_ms":42.25,"budget_tick_ms":100}
```
Les deux mesures de diagnostic peuvent être ignorées. Vérifier exactement les requêtes pour `Regler(0)` (pause) et `Regler(2.5)` sous culture `fr-FR`, puis les valeurs des réponses. Le faux service répond à la demande de 2.5 avec une vitesse de 1.25 et un tick de 8 : la lecture doit rendre 1.25 et 8, prouvant qu'elle vient du service. Une réponse sans diagnostic reste valable. Aucun appel ne vise `/tick`. Contre-épreuve : remplacer la vitesse reçue par celle demandée, utiliser GET pour le réglage ou écrire `2,5` fait échouer cette commande.

SC4 — Absence déclarée. La commande Unity de SC1 ajoute des cas paramétrés pour les trois opérations (`Lire` monde, `Lire` horloge, `Regler`). Chaque résultat porte soit les données et aucune absence, soit une absence non vide et aucune donnée. Service fermé, service muet avec délai de 300 ms, statut 400/500 avec corps, redirection 302 et JSON cassé donnent une absence préfixée `monde : ` ou `horloge : ` qui nomme la cause ; le statut et le corps reçus figurent dans un refus HTTP, la durée dans un délai dépassé. Aucune redirection n'est suivie. Après une lecture réussie, une panne rend une absence nouvelle, sans ancienne donnée présentée comme actuelle. Utiliser `HttpClient` réutilisé et libéré par `Dispose`, `LecteurJson` inchangé et une minuterie couvrant toute la réponse ; mutualiser les aides internes dans les nouveaux fichiers pour tenir la taille. Contre-épreuve : faire rendre des données vides ou la dernière lecture lors d'un 500 fait rougir les assertions d'absence.

SC5 — Aucune donnée obligatoire devinée. La commande Unity de SC1 retire tour à tour chaque clé lue de la racine, de la date et d'une cellule, puis remplace une valeur par `null` ou un mauvais type. Toute faute refuse la réponse entière avec le chemin de la clé, même dans la seconde cellule. Exiger des nombres finis ; tick, compte, identifiants et population entiers ≥ 0, année et jour entiers positifs ; faim entière ≥ 0 ou exactement -1, dette ≥ 0 ou exactement -1, vitesse ≥ 0. Refuser aussi `cells` vide, compte différent de sa longueur et `cell_id` répété. Les entiers lus en double doivent rester strictement sous 2^53. Les constructeurs refusent ports hors 1..65535 et délais non finis ou non positifs ; `Regler` refuse négatif, NaN et infinis avant tout envoi. Le faux service prouve l'absence de requête pour ces vitesses. Contre-épreuve : restaurer chaque témoin rend une lecture présente ; remplacer un champ absent par zéro fait échouer son cas. Les tests utilisent des mutations vérifiées du témoin et des cas paramétrés, sans multiplier les aides ni les fichiers.

## Hors périmètre
`ClientLieu.cs`, les autres clients, `LecteurJson.cs`, les assemblages et tous les tests existants ; `jeu/` et le contrat HTTP ; scène, panneau, fiche visible, maillage, capture et rafraîchissement automatique. Aucun calcul économique, stock ajouté au modèle Unity, règle de prélèvement, nouvelle clé spatiale ou horloge Unity. L'ajustement automatique de la vitesse au changement de vue relève de #410, pas de ce lot. Aucun lancement de service réel n'est nécessaire aux tests Unity de ce lot.

## Photo
sans objet : ce lot ajoute seulement deux clients du service et leurs tests ; il ne change rien de ce qu'on voit à l'écran.
