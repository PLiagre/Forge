# jeu/sim — le moteur

Les règles du monde, formule par formule : [MODELE.md](MODELE.md). Un
changement du monde met MODELE.md à jour dans la même PR.

## Les règles de la zone

- **Bibliothèque standard seule.** Le moteur tourne sur une machine nue ;
  pytest ne sert qu'à le tester.
- **Déterministe.** Même graine, même monde, sur le PC comme sur le VPS.
  Aucun tirage hors du générateur du monde, aucun ordre de parcours laissé au
  hasard d'un `set` ou d'un `dict` mal trié.
- **`cell_id` est la seule clé spatiale.** Province, bourg et lieu s'en
  dérivent et ne se stockent pas comme une seconde clé.
- **Les chiffres du jeu vivent dans `jeu/data/`**, pas dans le code. Le
  moteur et l'IA lisent les mêmes.
- **Tout geste est une intention** (`intentions.py`) que le joueur et l'IA
  déposent par le même chemin.
- **Le service (`service.py`) est le contrat avec Unity.** Une réponse qui
  change de forme change ses réponses figées et le client Unity dans la même
  PR.

## Les tests

- Jouer les tests de ce qu'on touche (un fichier, `-k`), puis
  `test_no_hardcoded.py` et `test_write_coverage.py`. Jamais la suite entière
  ni une simulation d'un an ou plus pendant un lot : la CI et la nuit s'en
  chargent.
- **Un test qu'un changement du monde rend faux se met à jour dans la même
  PR**, aussi strict, et la PR dit pourquoi (section « Tests changés »). Il
  juge le monde livré : pas de drapeau, de fixture ou de paramètre qui rejoue
  l'ancienne règle pour garder l'ancien test vert.
- **Une empreinte épinglée** (un hachage du monde figé dans un test) se
  recapture dans la PR qui change ce qu'elle mesure, en disant quelles
  parties du monde diffèrent. Une empreinte qui change sans qu'on sache dire
  pourquoi est un défaut : le chercher, ne pas la recapturer.

## Les pièges

- **Windows et Linux ne donnent pas les mêmes derniers bits en
  trigonométrie** (`math.sin`, `cos`, `atan2`, `log`, la projection
  EPSG:3035). Arrondir avant d'épingler un hachage ou un témoin
  (`DECIMALES_POINT_METRES`, `DECIMALES_POINT_DEGRES` dans `constants.py`).
  Les entiers, les sommes et `random.uniform` sont reproductibles.
- **Les empreintes du monde se jugent sous Linux** (la CI, le VPS). Sur le
  PC, les calibrages chiffrés peuvent différer : un rouge local sur une
  empreinte ne prouve rien avant d'avoir été rejoué sous Linux.
- **Sur le PC**, lancer pytest avec `PYTHONUTF8=1` (les tests lisent
  MODELE.md sans encodage), `--basetemp=<dossier>` et `-p no:cacheprovider`
  (le dossier temporaire par défaut est verrouillé). Les contrôles `py -c`
  se jouent depuis bash : PowerShell 5.1 mange les guillemets doubles.
- **`CI=true` rend pytest quadratique** sur les comparaisons de mondes
  entiers : la CI vide cette variable. Un test anormalement lent sur la CI
  se reproduit sur le PC par `CI=true py -m pytest <test>`.
- **Le budget du tick** (`BUDGET_TICK_MS`, 100 ms) est tenu de peu sur les
  runners de la CI, deux fois plus lents que le PC : un rouge du seul
  travail `chronometre` se rejoue une fois avant d'accuser le lot.
- **Le temps d'un jour se mesure sur `ServeurMonde.jouer_un_tick()` en
  entier**, publication comprise. `duree_dernier_tick_ms` (servi par
  `/horloge`) ne compte que le tick et l'IA.
- **Un ordre de bâtir demande un départ** : `tracer_route` et les autres
  gestes de la ville sont refusés tant que `choisir_depart` n'a pas été
  déposé.
