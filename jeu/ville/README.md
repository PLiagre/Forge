# ville/ — le contrat entre le monde et sa vue ville

La frontière de données entre `jeu/sim/`, qui possède le monde, et `3d/unity/`,
qui le montre. Elle est du texte : schémas, exemples, matrice d'autorité — donc elle
se lit, se versionne et se teste sans ouvrir Unity.

| fichier | ce qu'il dit |
|---|---|
| `FORGEHISTORY_CITY_MODE_CONTRACT.md` | la décision, la matrice d'autorité, le protocole v1 |
| `CITY_MODE_HOST_API.md` | ce que l'hôte expose |
| `Schemas/forgehistory-city-mode-v1.schema.json` | le schéma filaire, JSON Schema 2020-12 |
| `Schemas/forgehistory-city-mode-v1.examples.json` | cinq exemples cohérents |
| `UNITY_RENDER_DEPENDENCY_MATRIX.md` | ce que le rendu exige de chaque côté |
| `cellule_du_desert.py` | la cellule par défaut des épreuves, dérivée de la carte |

## La règle qui tient tout

**Une seule simulation.** Le monde appartient à `sim/` : les identités, le
temps, l'économie, la sauvegarde. La vue ville rend des snapshots versionnés,
collecte des intentions, et présente les reçus. Elle ne possède jamais une
seconde source de vérité.

Une intention est corrélée, idempotente, ordonnée par tick et révision, et
explicitement acceptée ou refusée. Rien ne s'applique en optimiste dans la vue.

## Ce que ce contrat attend encore

Rien que le moteur ne produise déjà : chaque message porte `cell_id`, l'entier
de `data/world-1400.json` et la seule clé spatiale de `sim/`
([`sim/MODELE.md`](../sim/MODELE.md)). Aucune identité de ville n'y figure.
`tests/` juge les exemples d'après le schéma lu.

Le lieu, subdivision de la cellule, existe : `GET /lieu?cell=N` porte `lieux`,
la liste des lieux de la cellule rangée par rang, chacun avec `rang`,
`surface_km2`, `population`, `stocks`, `maitre` (identifiant de maison, ou
`None` pour un état manuel), `point`, `nom` (repris du bloc `noms`) et
`flux_30j` (`preleve_kg`, `partis_personnes`, `arrives_personnes` sur trente
jours, sans arrondi). Sans noms ou flux fournis, ces deux champs valent `None`. Son identité est le couple (`cell_id`
de la réponse, `rang`) : **dérivée** de `cell_id`, jamais une seconde clé ; un
lieu publié ne porte ni `cell_id` recopié ni `lieu_id`.

Le bloc frère `noms` publie `lieux` (`rang`, `nom`) et `maisons`, dictionnaire par identifiant de `maitre` avec `nom` et `prenom_chef` (`null` si historique). Il égale celui de la photographie ; les lectures HTTP utilisent les octets figés.

## La cellule par défaut des épreuves

`pc\Jouer.cmd` démarre le service de `sim/`, puis le jeu. Il ne passe
`-forgeCell <cell_id>` qu'avec `--cellule <cell_id>`. Sans cette option, le jeu
lit la maison du joueur au service : il ouvre sa capitale si sa terre a un kit,
sinon la carte de 1400 ; une donnée absente est dite par le jeu (lot #688).
Chaque lancement démarre un service neuf, sans choix : il ouvre donc la carte,
où le joueur choisit sa terre. L'entrée dans la capitale depuis la carte vient
avec les lots #681 et #410.

Les épreuves `pc/epreuve_jalon1.py` et `pc/epreuve_carte.py` gardent leur cellule
par défaut, calculée par `cellule_du_desert.py` :

- **la règle** : la cellule dont `climat.insolation_annuelle_mj_m2` est la plus
  forte ; à égalité, le plus petit `cell_id` ;
- **pourquoi l'insolation** : la carte ne porte aucune température ; l'insolation
  annuelle est sa seule mesure de chaleur. La cellule la plus ensoleillée tombe
  au sud de la carte (niveau de fidélité 1) ;
- **les refus** : une cellule sans cette clé, ou une carte sans cellule, lève une
  `ValueError` qui nomme la clé et le `cell_id` ; aucune valeur par défaut,
  aucune cellule écrite à la main.

Le numéro n'est écrit nulle part : il se recalcule depuis les données.

```bash
py ville/cellule_du_desert.py      # depuis jeu/ : écrit le cell_id seul
```

Pour ouvrir une autre cellule : `pc\Jouer.cmd --cellule <cell_id>`.

Pour ouvrir le jeu sur la carte de 1400 : `pc\Jouer.cmd --carte` (lot #524). Le
lanceur passe `-forgeCarte` au jeu, qui quitte la ville au lancement pour la scène
`Forge_Carte`. On s'y déplace en glissant (bouton gauche ou du milieu) et on
zoome à la molette, vers le point sous la souris, sans sortir de la carte servie.
En haut à droite, la date et la vitesse du monde, lues au service (lot #525) :
Espace ou « Pause » arrête le monde et le relance à sa vitesse, + et − (ou les
boutons) passent d'un palier à l'autre (0,5 à 20 jours par seconde).
En bas à gauche, la fiche de la cellule sous la souris (lot #526) : ses villes,
sa puissance et sa maison lues dans `/carte`, ses habitants, sa faim et sa dette
lus dans `/monde`, avec le tick de cette lecture. Ce que le monde ne nomme pas ou
ne calcule pas, la fiche le dit.

## L'épreuve du jalon 1

Le panneau du lieu doit montrer les mêmes nombres que la photographie de `sim/`,
pour la même graine, le même tick et la même cellule. Depuis la racine du dépôt :

```bash
py pc\epreuve_jalon1.py --sortie <dossier>
```

La capture Unity lance le service de `sim/`, ouvre la scène du désert en Play,
écrit le texte du panneau, et le script le compare nombre par nombre à
`py -m sim --ticks N --seed S --snapshot-json`.

- **0** — égalité exacte : `verdict.txt` commence par `ÉGALITÉ` ;
- **1** — un écart : le verdict nomme chaque champ, la valeur du panneau et celle de la photographie ;
- **2** — l'épreuve n'a pas pu se jouer (Unity introuvable, port déjà pris, photographie ou capture absente ou antérieure à l'essai, service laissé ouvert).

La contre-épreuve pousse le service un tick plus loin que la photographie ; elle doit sortir **1** :

```bash
py pc\epreuve_jalon1.py --sortie <dossier> --decalage 1
```

La capture que la chaîne prend ensuite lance ce même service (sans choisir de cellule) : le panneau publié au journal porte les chiffres du monde, pas une absence.

## L'épreuve du jalon 4
Unity joue une route, une parcelle et une scierie à Biskra, après le choix de l'émirat du Zab ; Python rejoue leur journal. Ce n'est pas la preuve complète (#508). L'éditeur est fermé ; la scène et les données sont celles de #386 (`py local3d/atelier_desert.py terrain` depuis `3d/`).

`--avec-unity` fixe la graine 0 et 11 ticks. La cellule de Biskra est lue dans la table. Le script dépose le choix du Zab au tick 0, appliqué au tick 1 ; Unity pose la route, la parcelle et la scierie aux ticks 1, 2 et 3. Le témoin rejoue le choix seul. Au tick 11, sur `monde-service.json`, la rue est à 50/200, la parcelle 14/14 aux bornes, la scierie 30/271 aux piquets.

Rouge d'abord, sur master `f081666` (`pc/epreuve_jalon4.py` à l'octet de cette révision) : `py pc\epreuve_jalon4.py --avec-unity --sortie <dossier>` rend **1**. Le verdict porte `code : 1` et le motif « égalité du monde — journal : type absent ou inattendu ».

```powershell
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-583-normal"
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-583-sourd" --service-sourd
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-583-locale" --ville-locale
py pc\epreuve_jalon4.py --avec-unity --sortie "$env:TEMP\forge-583-maison" --sur-une-maison
```

**0** preuve valide : le verdict dit « octets égaux sur 11 ticks » et « ticks 1, 2 et 3 » ; les rapports portent la cellule de Biskra. **1** invariant violé : le service sourd nomme « bâtiment absent » et « écart entre monde servi et monde rejoué » ; la ville locale nomme « empreinte des rues », « c'est le redessin qui échoue » et « l'égalité Python peut rester vraie » ; `--sur-une-maison` nomme « maison de 1400 » (le monde refuse la rue). **2** essai impossible (Unity, scène, port, délai, rapport absent ou ancien, exception dans les défauts, aucune route sur une maison que le relief accepte) : une panne ne vaut pas contre-épreuve. Verdicts : [normal](../../docs/mesures/583-preuve-unity-biskra/verdict.txt), [service sourd](../../docs/mesures/583-preuve-unity-biskra/verdict-service-sourd.txt), [ville locale](../../docs/mesures/583-preuve-unity-biskra/verdict-ville-locale.txt), [sur une maison](../../docs/mesures/583-preuve-unity-biskra/verdict-sur-une-maison.txt).

Le parcours Python, sans Unity, bâtit à Biskra après le choix appliqué de l'émirat du Zab. La cellule est celle du siège, lue dans la table. Le journal garde ce choix au tick 0, puis la route, la parcelle et le bâtiment aux ticks 2, 3 et 5. Le rejeu complet reprend les quatre entrées ; le témoin rejoue seulement le choix, au même tick.

```bash
python3 pc/epreuve_jalon4.py --sortie <dossier>
python3 pc/epreuve_jalon4.py --sortie <dossier> --service-sourd
```

**0** le départ est le même dans les trois mondes, Biskra porte les trois gestes, le service et le rejeu sont égaux à l'octet. **1** le service sourd : le bâtiment manque. Ces deux commandes sont celles que le lot #408 valide.

## L'épreuve de la carte

Le joueur peut se fier à sa carte (lot #527) : elle dessine autant de cellules
que `/carte` en sert, et la fiche d'une cellule dit `/carte` (villes, puissance,
maison) et `/monde` au même tick (habitants, faim, dette), nombre par nombre.
Depuis la racine du dépôt :

```bash
py pc\epreuve_carte.py --sortie <dossier> [--cellule C] [--ticks N] [--seed S]
```

Le script lance le service (en pause, poussé au tick N) et lit `/carte` et
`/monde` ; Unity ouvre `Forge_Carte` en Play (`ForgeLocal3D.EpreuveCarte.Jouer`),
survole la cellule C (par défaut celle du lanceur) et écrit `rapport.json` ; le
verdict, dans `verdict.txt`, cite chaque valeur des deux côtés. **0** égalité,
**1** écart, **2** épreuve impossible (Unity introuvable, port pris, référence
illisible, Unity en erreur, rapport absent ou antérieur à l'essai).

Les trois contre-épreuves doivent sortir **1** : `--decalage 1` (le service lu
par Unity a un tick d'avance), `--retirer-une-cellule` (Unity retire une cellule
du dessin) et `--sans-service` (le service s'arrête avant Unity : la carte dit
que le monde ne répond pas). Verdicts du 9 octobre 2026 :
[normal](../../docs/mesures/527-epreuve-de-la-carte/verdict-normal.txt),
[décalé](../../docs/mesures/527-epreuve-de-la-carte/verdict-decale.txt),
[cellule retirée](../../docs/mesures/527-epreuve-de-la-carte/verdict-retiree.txt),
[sans service](../../docs/mesures/527-epreuve-de-la-carte/verdict-sans-service.txt).

## La session du choix de la terre

Le joueur clique sur une terre de la carte de 1400, puis sur une autre, et le
monde refuse le second choix (lot #651, moitié Unity de l'épreuve #615).
Depuis la racine du dépôt :

```bash
Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveChoix.Jouer \
      -forgeEpreuve <rapport.json> -forgeTerre N -forgeSecondeTerre M [-logFile <journal>]
```

Le service se lance à la main dans un second terminal, depuis `jeu/` :
`py -m sim.service --seed 0 --jours-par-seconde 0` (port 8000, tick 0, en
pause), et s'arrête après chaque essai. Unity ouvre `Forge_Carte` en Play,
attend les six repères des terres de départ, lit `/departs`, clique comme le
joueur (par `SurvolDeCarte`) sur le repère de la terre N, attend son reçu, puis
clique aussitôt sur celui de M, avant tout tick : la session ne touche jamais
`/tick` ni `/vitesse`. Un rapport relatif se lit depuis le dossier de lancement.

Le rapport porte `terre`, `seconde_terre`, `reperes` (repères posés),
`tick_avant` et `tick_apres` (le tick de `/departs` avant le premier clic et
après le second reçu), `premier` et `second` (chaque reçu : `statut` 200, 400 ou
409, ou −1 absent ; `tick` du dépôt accepté, −1 sinon ; `raison` du refus ou de
l'absence), `premier_texte` et `second_texte` (le panneau du choix, tel
qu'affiché) et `defaut`. **0** les deux reçus relevés, quels qu'ils soient ;
**1** session impossible (`defaut` dit pourquoi ; le rapport est écrit) ; **2**
arguments fautifs (aucun rapport). La session ne juge rien : le jugement est
celui de [l'épreuve du choix](#lépreuve-du-choix), qui compare au monde.
Rapports du 16 octobre 2026 :
[normal](../../docs/mesures/651-session-choix-moree/rapport-normal.json),
[départ déjà choisi](../../docs/mesures/651-session-choix-moree/rapport-deja-choisi.json),
[sans service](../../docs/mesures/651-session-choix-moree/rapport-sans-service.json).

## La session de l'épreuve de la capitale

Le joueur choisit sa terre dans le cabinet de la carte et, au tick suivant,
passe à sa ville ou lit « Pas encore de kit pour cette terre » (lot #702,
moitié Unity de l'épreuve #684). Depuis la racine du dépôt :

```bash
Unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuveCapitale.Jouer \
      -forgeEpreuve <rapport.json> -forgeTerre N [-logFile <journal>]
```

Le service se lance à la main comme pour la session du choix (`py -m
sim.service --seed 0 --jours-par-seconde 0` depuis `jeu/`), neuf pour chaque
essai. Unity ouvre `Forge_Carte` en Play, attend que le cabinet ait lu le monde
et les départs, choisit la terre N, laisse le passage voir le départ, pousse un
seul `POST /tick?n=1` (jamais `/vitesse`), puis relève ce que le passage fait :
la ville qu'il charge lui-même, comme dans le jeu, ou son message. Rien n'est
remplacé dans le chargement.

Le rapport porte `terre`, `tick_avant` et `tick_apres` (le tick du monde avant
le choix et après le passage), `choix` (le reçu, comme dans la session du
choix), `scene_active`, `cellule` et `tick_ouverture` (lus sur l'outil de la
ville, −1 sans ville), `panneau_lieu` (la première ligne du panneau du lieu),
`message_passage` et `defaut`. **0** une ville ou un message relevé, quel qu'il
soit ; **1** session impossible (`defaut` dit pourquoi ; le rapport est écrit) ;
**2** arguments fautifs (aucun rapport). Le rapport écrit, Unity sort du Play et
laisse 12 s aux lectures de la carte avant de rendre son code : sans service, il
pendait sinon à sa fermeture. La session ne juge rien : le jugement est
celui de [l'épreuve de la capitale](#lépreuve-de-la-capitale). Rapports du 18 octobre 2026 :
[le Zab](../../docs/mesures/702-session-capitale/rapport-zab.json),
[Bar](../../docs/mesures/702-session-capitale/rapport-bar.json).

## L'épreuve de la capitale

Le joueur se fie au passage (lot #703, épreuve #684). Depuis la racine, éditeur fermé :

```bash
py pc\epreuve_capitale.py --sortie <dossier> [--seed S] [--unity CHEMIN]
```

Un service neuf par terre, trouvée par son nom. Unity seul pousse le tick ;
Python ne poste ni intention, ni tick, ni vitesse, et n'envoie à Unity que
l'id de la terre. La cellule attendue est `siege.cell_id` de
`GET /maison?id=seigneurie-<id>`. **0** égalité, **1** écart, **2** épreuve
impossible. Contre-épreuve sans PC :
`python3 -m pytest jeu/ville/tests/test_epreuve_capitale.py -q -k contre_epreuve -s`.
Verdicts du 18 octobre 2026 :
[normal](../../docs/mesures/703-epreuve-capitale/verdict-normal.txt),
[jugement d'une copie, pas une mesure PC](../../docs/mesures/703-epreuve-capitale/verdict-contre-epreuve.txt).

## L'épreuve du choix

Le joueur peut se fier à son geste (lot #652, épreuve #615) : la terre qu'il
clique sur la carte de 1400 est celle que le monde retient, et le second choix
est refusé pour la raison que le panneau lui affiche. Depuis la racine du dépôt,
éditeur fermé :

```bash
py pc\epreuve_moree.py --sortie <dossier> [--terre N] [--seed S] [--unity CHEMIN]
```

Le script lance le service (graine S, en pause) et lit `/departs` ; il y trouve
la Morée par son nom (« Despotat de Morée », jamais par son id), la terre
cliquée (N, la Morée par défaut) et la seconde terre (la première servie d'un
autre id). Il joue la [session du choix](#la-session-du-choix-de-la-terre)
telle quelle, lit `/monde` avant le tick, pousse un tick et relit `/monde`.

Le verdict, dans `verdict.txt`, juge contre la Morée servie et le monde, jamais
contre la terre demandée : la session n'a pas fait avancer le monde ;
`/monde` ne porte pas `maison_du_joueur` avant le tick ; le premier reçu est
accepté au tick de `/departs` ; le second est refusé (409) par « départ déjà
choisi : seigneurie-<id de la Morée> » ; le tick poussé est le suivant et la
maison retenue après lui est la seigneurie de la Morée ; les deux textes du
panneau sont ceux attendus, mot pour mot. **0** égalité, **1** écart, **2**
épreuve impossible (Unity introuvable, port pris, référence illisible, session
en erreur, rapport absent ou antérieur à l'essai, monde illisible après la
session).

La contre-épreuve `--terre 6` fait cliquer le Zab puis Bar : le monde retient
`seigneurie-6`, le verdict sort **1**. Verdicts du 16 octobre 2026 :
[normal](../../docs/mesures/615-epreuve-du-choix/verdict-normal.txt),
[terre 6](../../docs/mesures/615-epreuve-du-choix/verdict-terre-6.txt).
