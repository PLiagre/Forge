# La chaîne côté GitHub — mesures du 6 novembre 2026

Dépôt `PLiagre/Forge`, lu en **lecture seule** (requêtes GraphQL `query` et `gh … list`/`view`), collecte du 07/11/2026 09:51 au 09:55 (heure de Paris) : 556 issues, 465 PR.

- Collecte : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_collecte.py` → collecte brute dans le dossier scratch de Hermes (`chaine_github_brut.json`, corps des issues compris).
- Mesure : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_mesure.py --verifier` → ce fichier et `chaine-github.json` (issues, PR, timelines d'étiquettes, classification de chaque lot livré, lignes du CAP et leurs feuilles).
- Chaque section se refait **sans réseau** depuis `chaine-github.json` : la commande est sous son titre.

Fenêtres : **F1** = depuis le 1er octobre 2026 00:00 (Paris, UTC+2, soit 2026-09-30T22:00Z) ; **F2** = depuis le 28 octobre 2026 00:00 (Paris, UTC+1 après le 25 octobre, soit 2026-10-27T23:00Z) ; toutes deux jusqu'à la collecte. Semaines ISO, lundi → dimanche, en heure de Paris.

## 1. Les lots livrés, par jalon et par semaine ISO

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_mesure.py --compact docs/mesures/2026-11-07-refonte/brut/chaine-github.json --section 1`

Un lot livré = une issue fermée qui porte l'étiquette `livre`. **Date retenue : `closedAt` de l'issue**, en heure de Paris ; jalon = milestone **actuel** de l'issue. Semaines ISO, lundi → dimanche (la première et la dernière colonne de chaque fenêtre sont des semaines partielles).

### Fenêtre F1 — depuis le 1er octobre 2026 (01/10/2026 00:00, heure de Paris, → collecte du 07/11/2026 09:55)

| jalon | S40 (28/09–04/10) | S41 (05/10–11/10) | S42 (12/10–18/10) | S43 (19/10–25/10) | S44 (26/10–01/11) | S45 (02/11–08/11) | total |
|---|--:|--:|--:|--:|--:|--:|--:|
| J2 | 9 | · | · | · | · | · | **9** |
| J3 | 2 | 31 | 25 | 8 | · | · | **66** |
| J4 | 13 | 28 | 20 | 24 | 49 | 7 | **141** |
| J5 | · | 6 | 1 | · | 2 | 11 | **20** |
| J6 | · | · | · | 8 | 4 | · | **12** |
| **total** | **24** | **65** | **46** | **40** | **55** | **18** | **248** |

### Fenêtre F2 — depuis le 28 octobre 2026 (28/10/2026 00:00, heure de Paris, → collecte du 07/11/2026 09:55)

| jalon | S44 (26/10–01/11) | S45 (02/11–08/11) | total |
|---|--:|--:|--:|
| J4 | 47 | 7 | **54** |
| J5 | 2 | 11 | **13** |
| J6 | 3 | · | **3** |
| **total** | **52** | **18** | **70** |

Avec `mergedAt` de la PR de lot au lieu de `closedAt` : **0** lot change de case (écart maximal entre les deux dates : 2,0 min). 7 lots livrés n'ont pas de PR `lot/…` : #388, #524, #549, #525, #526, #527, #393 — livrés en mode direct (PR `direct/…` ou commit), comptés ici comme lots puisque leur issue porte `livre`.

### Les issues fermées sans `livre`, à part

Convention vérifiée sur toutes les issues : toute issue `livre` est fermée « COMPLETED » ; toute PR `lot/<n>-…` fusionnée a son issue `livre` ; aucune issue n'a deux PR de lot fusionnées. Les fermées sans `livre`, par catégorie (date = `closedAt`) :

| catégorie | depuis toujours | F1 | F2 |
|---|--:|--:|--:|
| journal (pas un lot) | 38 | 37 | 11 |
| « Découper le jalon … » | 4 | 2 | 0 |
| découpé en sous-lots | 75 | 69 | 22 |
| fermé sans suite, sans sous-lot (NOT_PLANNED) | 26 | 26 | 0 |
| fermé « terminé » sans livre | 25 | 1 | 1 |
| **total** | **168** | **135** | **34** |

Fermées sans `livre` dans F2 (hors journaux) : #416 (découpé en sous-lots), #417 (découpé en sous-lots), #422 (découpé en sous-lots), #426 (découpé en sous-lots), #789 (découpé en sous-lots), #803 (découpé en sous-lots), #848 (fermé « terminé » sans livre), #856 (découpé en sous-lots), #857 (découpé en sous-lots), #858 (découpé en sous-lots), #859 (découpé en sous-lots), #872 (découpé en sous-lots), #874 (découpé en sous-lots), #876 (découpé en sous-lots), #877 (découpé en sous-lots), #884 (découpé en sous-lots), #906 (découpé en sous-lots), #909 (découpé en sous-lots), #912 (découpé en sous-lots), #951 (découpé en sous-lots), #973 (découpé en sous-lots), #987 (découpé en sous-lots), #1000 (découpé en sous-lots).

Contre-vérification indépendante (commandes en lecture, lancées par `--verifier` à la mesure) :

- lots livrés F1 : `gh issue list -R PLiagre/Forge --state closed --label livre --search 'closed:>=2026-10-01T00:00:00+02:00' --limit 1000 --json number --jq length` → **248**
- lots livrés F2 : `gh issue list -R PLiagre/Forge --state closed --label livre --search 'closed:>=2026-10-28T00:00:00+01:00' --limit 1000 --json number --jq length` → **70**


## 2. La part des lots `pc` parmi les livrés

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_mesure.py --compact docs/mesures/2026-11-07-refonte/brut/chaine-github.json --section 2`

| fenêtre | livrés | dont `pc` | part `pc` | autres |
|---|--:|--:|--:|--:|
| F1 — depuis le 1er octobre 2026 | 248 | 124 | 50,0 % | 124 |
| F2 — depuis le 28 octobre 2026 | 70 | 42 | 60,0 % | 28 |

`pc` = étiquette actuelle de l'issue. Par jalon :

| jalon | F1 : `pc` / livrés | F2 : `pc` / livrés |
|---|--:|--:|
| J2 | 0 / 9 | · |
| J3 | 30 / 66 | · |
| J4 | 93 / 141 | 41 / 54 |
| J5 | 1 / 20 | 1 / 13 |
| J6 | 0 / 12 | 0 / 3 |

Contre-vérification indépendante (commandes en lecture, lancées par `--verifier` à la mesure) :

- lots `pc` livrés F1 : `gh issue list -R PLiagre/Forge --state closed --label livre --label pc --search 'closed:>=2026-10-01T00:00:00+02:00' --limit 1000 --json number --jq length` → **124**
- lots `pc` livrés F2 : `gh issue list -R PLiagre/Forge --state closed --label livre --label pc --search 'closed:>=2026-10-28T00:00:00+01:00' --limit 1000 --json number --jq length` → **42**


## 3. Les lots livrés qui ne sont « que » preuve, juge, test ou montage

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_mesure.py --compact docs/mesures/2026-11-07-refonte/brut/chaine-github.json --section 3`

Classement par mots **entiers** du titre de l'issue, en minuscules et sans accents (`unicodedata` NFD, marques retirées ; « ’ » lu « ' »), découpé sur tout ce qui n'est pas lettre ou chiffre — « contre-épreuve » donne « contre » + « epreuve ».

- **liste stricte** (celle de la consigne et ses flexions) : `preuve`, `preuves`, `epreuve`, `epreuves`, `juge`, `juges`, `test`, `tests`, `teste`, `testes`, `testee`, `testees`, `montage`, `montages`, `mesure`, `mesures`, `mesuree`, `mesurees`
- **liste élargie** = stricte + `prouver`, `verdict`, `banc`, `capture`, `photo`, `controler`, `controle` (des lots de vérification que la stricte manque ; à juger sur la liste ci-dessous)

| fenêtre | livrés | stricte | part | élargie | part | `pc` parmi les stricts |
|---|--:|--:|--:|--:|--:|--:|
| F1 — depuis le 1er octobre 2026 | 248 | 42 | 16,9 % | 49 | 19,8 % | 21 / 42 |
| F2 — depuis le 28 octobre 2026 | 70 | 22 | 31,4 % | 23 | 32,9 % | 8 / 22 |

Les 49 titres classés (fenêtre F1 ; F2 marquée ✓), à vérifier à l'œil :

| issue | livré le | jalon | pc | F2 | liste | mots trouvés | titre |
|---|---|---|---|---|---|---|---|
| #306 | 2026-10-03 | J2 |  |  | stricte | preuve | La preuve du jalon 2 |
| #385 | 2026-10-07 | J4 |  |  | stricte | epreuve | L'épreuve du jalon 4 rejoue le journal des gestes et compare le monde |
| #386 | 2026-10-07 | J4 | pc |  | stricte | preuve | Unity joue les gestes de la preuve et redessine la même ville |
| #387 | 2026-10-07 | J4 | pc |  | stricte | epreuve, verdict | L'épreuve du jalon 4 sur le PC : Unity joue, Python rejoue, verdict |
| #388 | 2026-10-09 | J4 | pc |  | élargie seule | capture | La capture de la capitale bâtie et de son panneau |
| #549 | 2026-10-09 | J3 | pc |  | élargie seule | photo | La scène Carte, dernière du build, et sa photo |
| #527 | 2026-10-09 | J3 | pc |  | stricte | epreuve | L'épreuve de la carte dans Unity |
| #583 | 2026-10-12 | J4 | pc |  | stricte | preuve | La preuve Unity du jalon 4 bâtit à Biskra, hors des maisons de 1400 |
| #584 | 2026-10-12 | J4 | pc |  | élargie seule | photo | La photo de la capitale relancée à Biskra avec ses gestes |
| #592 | 2026-10-12 | J3 |  |  | élargie seule | prouver | Prouver que prendre trop fait partir les foyers |
| #604 | 2026-10-14 | J3 |  |  | stricte | preuve | La photographie porte la maison du joueur et son suzerain, et la preuve rejoue |
| #652 | 2026-10-16 | J3 | pc |  | stricte | epreuve, verdict | Le verdict de l'épreuve de la Morée |
| #690 | 2026-10-17 | J4 | pc |  | élargie seule | photo | La carte pose le passage au chargement, photo de Bar |
| #702 | 2026-10-18 | J4 | pc |  | stricte | epreuve | La session Unity de l'épreuve de la capitale |
| #703 | 2026-10-18 | J4 | pc |  | stricte | epreuve, verdict | Le verdict de l'épreuve de la capitale |
| #739 | 2026-10-21 | J4 | pc |  | stricte | epreuve | La session Unity de l'épreuve de la ville de 1400 |
| #724 | 2026-10-21 | J4 |  |  | stricte | preuves | Le chantier vide les champs du bourg, la moisson ceux de chaque lieu : les preuves |
| #659 | 2026-10-21 | J3 | pc |  | stricte | epreuve | La session Unity de l'épreuve de la part |
| #763 | 2026-10-21 | J3 |  |  | stricte | juge, teste | Le juge de la part, testé sur le VPS |
| #732 | 2026-10-21 | J4 | pc |  | stricte | epreuve | La session Unity de l'épreuve de la transition |
| #764 | 2026-10-22 | J3 | pc |  | stricte | epreuve | Le lanceur de l'épreuve de la part, sur le PC |
| #406 | 2026-10-22 | J3 |  |  | stricte | preuve | La preuve du jalon 3 |
| #733 | 2026-10-22 | J4 | pc |  | stricte | epreuve, verdict | Le verdict de l'épreuve de la transition |
| #740 | 2026-10-22 | J4 | pc |  | stricte | epreuve, verdict | Le verdict de l'épreuve de la ville de 1400 |
| #799 | 2026-10-22 | J6 |  |  | élargie seule | controler | Contrôler les liens familiaux et les dates |
| #777 | 2026-10-22 | J4 |  |  | stricte | epreuve | Un service d’épreuve peut vider le panier du bourg |
| #782 | 2026-10-28 | J4 | pc | ✓ | stricte | epreuve, juge | L’épreuve juge les signes de vie contre le monde |
| #865 | 2026-10-29 | J4 |  | ✓ | stricte | preuve | La preuve de l'enceinte |
| #911 | 2026-10-30 | J4 |  | ✓ | stricte | juge | Le juge de la carte écrit comme le clerc |
| #896 | 2026-10-30 | J4 |  | ✓ | stricte | epreuve | Un service d'épreuve peut vider le bourg |
| #898 | 2026-10-30 | J4 | pc | ✓ | stricte | epreuve, juge | L'épreuve juge les passants contre le monde |
| #928 | 2026-10-30 | J4 |  | ✓ | stricte | juge | Le juge de la carte lit la fiche en noms |
| #936 | 2026-10-30 | J4 |  | ✓ | stricte | epreuve | Le service d'épreuve règle le travail de l'enceinte |
| #937 | 2026-10-31 | J4 | pc | ✓ | stricte | epreuve | La session Unity de l'épreuve de l'enceinte |
| #938 | 2026-10-31 | J4 | pc | ✓ | stricte | epreuve, juge | Le juge de l'épreuve de l'enceinte |
| #944 | 2026-10-31 | J4 | pc | ✓ | stricte | epreuve, photo | L'épreuve, aucun identifiant à l'écran, et la photo |
| #957 | 2026-11-01 | J4 |  | ✓ | stricte | epreuve, mesure | Le service d'épreuve monte la ville dense de la mesure |
| #958 | 2026-11-01 | J4 | pc | ✓ | élargie seule | banc | Le banc du temps d'image |
| #959 | 2026-11-01 | J4 | pc | ✓ | stricte | mesuree | La ville dense mesurée sur quatre vues |
| #970 | 2026-11-01 | J5 |  | ✓ | stricte | mesure | La mesure de l'IA suit les trente derniers jours |
| #972 | 2026-11-02 | J5 |  | ✓ | stricte | juge | Le juge relit la raison de la route vers le champ |
| #985 | 2026-11-05 | J5 |  | ✓ | stricte | juge | Le juge de la raison lit les deux règles |
| #986 | 2026-11-05 | J5 |  | ✓ | stricte | montage | Le montage de l'IA passe sur celui du programme |
| #965 | 2026-11-05 | J4 | pc | ✓ | stricte | preuve | La preuve des modes de carte |
| #999 | 2026-11-06 | J5 |  | ✓ | stricte | tests | Les tests de la règle des routes passent sur le programme |
| #1009 | 2026-11-06 | J5 |  | ✓ | stricte | tests | Les tests du monde ne jouent plus l'ancienne règle des routes |
| #1004 | 2026-11-06 | J4 | pc | ✓ | stricte | preuve | La preuve de la barre |
| #1010 | 2026-11-06 | J5 |  | ✓ | stricte | tests | Les tests des intentions ne jouent plus l'ancienne règle des routes |
| #988 | 2026-11-06 | J5 |  | ✓ | stricte | tests | L'ancienne règle quitte les tests |

Titres **non classés** qui contiennent un mot voisin (`session`, `lanceur`, `service d'epreuve`, `calibrage`, `planche`, `relance`, `releve`) — laissés hors des deux listes : #270 « La planche Unity des neuf étapes de chantier » ; #370 « Unity relancé repose les mêmes bâtiments » ; #603 « /lieu dit le nom, le prélevé et les départs de chaque lieu » ; #651 « La session Unity du choix de la Morée » ; #696 « Le kit du désert sait relever son terrain, en Python » ; #720 « La moisson manque de bras : calibrage à 6,2 » ; #781 « Une session Unity relève la capitale nourrie puis affamée » ; #897 « Une session Unity relève les ouvriers au chantier puis le bourg vidé » ; #952 « Le commerce par voisine se relève ».


## 4. La taille d'une PR de lot fusionnée

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_mesure.py --compact docs/mesures/2026-11-07-refonte/brut/chaine-github.json --section 4`

PR de lot = branche de tête `lot/<n>-<slug>`, fusionnée ; fenêtre = `mergedAt` (heure de Paris). Taille = `additions + deletions` de la PR. « Sans le brief » = somme `additions + deletions` des fichiers de la PR (`files(first:100){path additions deletions}`, paginé) dont le chemin ne commence pas par `docs/briefs/`. Quartiles : interpolation linéaire (`statistics.quantiles`, méthode « inclusive »).

| fenêtre | mesure | PR | Q1 | médiane | Q3 | max |
|---|--:|--:|--:|--:|--:|--:|
| F1 — depuis le 1er octobre 2026 | avec le brief | 241 | 289 | **299** | 440 | 4 218 (PR #922) |
| F1 — depuis le 1er octobre 2026 | sans `docs/briefs/*` | 241 | 203 | **242** | 332 | 4 032 (PR #922) |
| F1 | *(fichiers de brief par PR)* |  |  | 1 brief(s) : 241 PR |  |  |
| F2 — depuis le 28 octobre 2026 | avec le brief | 70 | 264,2 | **290** | 299 | 4 218 (PR #922) |
| F2 — depuis le 28 octobre 2026 | sans `docs/briefs/*` | 70 | 178,5 | **202** | 239 | 4 032 (PR #922) |
| F2 | *(fichiers de brief par PR)* |  |  | 1 brief(s) : 70 PR |  |  |

Le brief seul (lignes de `docs/briefs/*` dans la PR) :

| fenêtre | PR | Q1 | médiane | Q3 | max |
|---|--:|--:|--:|--:|--:|
| F1 — depuis le 1er octobre 2026 | 241 | 52 | 73 | 108 | 362 |
| F2 — depuis le 28 octobre 2026 | 70 | 59 | 82,5 | 96,8 | 186 |

Contrôle : pour chaque PR de lot fusionnée, nombre de fichiers lus = `changedFiles` et sommes des fichiers = `additions`/`deletions` de la PR ; écarts : aucun.

Contre-vérification indépendante (commandes en lecture, lancées par `--verifier` à la mesure) :

- PR `lot/…` fusionnées F1 : `gh pr list -R PLiagre/Forge --state merged --limit 1000 --json number,headRefName,mergedAt --jq '[.[] | select(.headRefName|startswith("lot/")) | select(.mergedAt >= "2026-09-30T22:00:00Z")] | length'` → **241**
- PR `lot/…` fusionnées F2 : `gh pr list -R PLiagre/Forge --state merged --limit 1000 --json number,headRefName,mergedAt --jq '[.[] | select(.headRefName|startswith("lot/")) | select(.mergedAt >= "2026-10-27T23:00:00Z")] | length'` → **70**
- taille max d'une PR `lot/…` F1 : `gh pr list -R PLiagre/Forge --state merged --limit 1000 --json number,headRefName,mergedAt,additions,deletions --jq '[.[] | select(.headRefName|startswith("lot/")) | select(.mergedAt >= "2026-09-30T22:00:00Z") | .additions + .deletions] | max'` → **4218**


## 5. Ce que chaque ligne de lot du CAP est devenue

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_mesure.py --compact docs/mesures/2026-11-07-refonte/brut/chaine-github.json --section 5`

Source : `CAP.md` du worktree (HEAD `17557033` ; dernier commit qui le touche : 5fa36eaf 2026-10-28T15:17:22Z CAP : la prise en main de la carte d'abord (#855–#860), la langue visuelle derrière (#849–#852) (#853)). Une ligne de lot = une ligne numérotée « n. #NNN … » sous « ## Jalon n — … ». Sous-lot = issue dont le corps contient « Découpé du lot #N » (formule exacte, relevée sur toutes les issues : « Découpé du lot #N par le chef. » ×272, « … par le dépanneur. » ×26, « … par le propriétaire. » ×3 ; ex. #679 « Découpé du lot #409 par le chef. », #861 « Découpé du lot #416 par le chef. »). On suit la découpe récursivement ; **feuille** = issue sans sous-lot ; **nœuds** = la ligne et toute sa descendance. Une issue découpée est toujours fermée sans `livre` (vérifié) ; ses feuilles portent l'état.

| jalon | lignes # | lignes découpées | nœuds | feuilles | livrées | ouvertes | fermées sans livre | feuilles / ligne | lignes « à créer » |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| J3 | 19 | 9 | 74 | **58** | 58 | 0 | 0 | 3,05 | 0 |
| J4 | 30 | 15 | 147 | **116** | 108 | 8 | 0 | 3,87 | 0 |
| J5 | 9 | 1 | 29 | **24** | 16 | 8 | 0 | 2,67 | 5 |
| J6 | 19 | 2 | 41 | **36** | 12 | 24 | 0 | 1,89 | 4 |
| J7 | 14 | 0 | 14 | **14** | 0 | 14 | 0 | 1,00 | 3 |
| J8 | 18 | 0 | 18 | **18** | 0 | 18 | 0 | 1,00 | 0 |
| J9 | 15 | 0 | 15 | **15** | 0 | 15 | 0 | 1,00 | 0 |
| **total** | 124 | 27 | 338 | **281** | 194 | 87 | 0 | 2,27 | 12 |

### Les dix lignes qui ont le plus enflé

| jalon | ligne | issue | titre au CAP | nœuds | feuilles | profondeur | livrées | ouvertes | fermées sans livre |
|---|--:|---|---|--:|--:|--:|--:|--:|--:|
| J6 | 6 | #431 | Les familles de 1400, et leurs découpes (#803 à #806, #824 à #826) | 21 | **17** | 2 | 10 | 7 | 0 |
| J5 | 7 | #426 | L'IA bâtit sa capitale quand son grenier le permet | 21 | **16** | 5 | 12 | 4 | 0 |
| J4 | 18 | #856 | La fiche parle en noms, pas en identifiants · pc | 22 | **15** | 4 | 15 | 0 | 0 |
| J4 | 7 | #409 | Le jeu ouvre la capitale du joueur · pc | 18 | **13** | 2 | 13 | 0 | 0 |
| J3 | 16 | #403 | La carte du joueur s'ouvre dans Unity · pc | 14 | **11** | 2 | 11 | 0 | 0 |
| J3 | 17 | #404 | Le joueur choisit sa terre sur la carte · pc | 14 | **10** | 3 | 10 | 0 | 0 |
| J4 | 15 | #417 | L'enceinte se dessine, et ses portes s'ouvrent sur les rues · pc | 12 | **9** | 2 | 9 | 0 | 0 |
| J3 | 18 | #405 | Le joueur règle sa part et ouvre son grenier sur la carte · pc | 11 | **9** | 2 | 9 | 0 | 0 |
| J4 | 28 | #421 | Les gens du bourg circulent dans les rues · pc | 11 | **9** | 2 | 9 | 0 | 0 |
| J4 | 27 | #420 | La ville fume, garnit ses étals et s'éclaire, d'après le monde · pc | 9 | **8** | 1 | 8 | 0 | 0 |

### Le détail, ligne par ligne

**J3 — Le lieu et son maître**

| ligne | issue | titre au CAP | nœuds | feuilles | livrées | ouvertes | fermées sans livre |
|--:|---|---|--:|--:|--:|--:|--:|
| 1 | #343 | Chaque lieu meurt de sa dette et naît de son abondance | 1 | 1 | 1 | 0 | 0 |
| 2 | #335 | Commerce et migration passent par le bourg | 1 | 1 | 1 | 0 | 0 |
| 3 | #390 | Les maisons du monde forment une pyramide | 4 | 3 | 3 | 0 | 0 |
| 4 | #391 | Chaque lieu a son seigneur | 4 | 3 | 3 | 0 | 0 |
| 5 | #392 | Les lieux et leurs seigneurs portent un nom plausible | 1 | 1 | 1 | 0 | 0 |
| 6 | #393 | Chaque lieu a sa place dans sa cellule | 1 | 1 | 1 | 0 | 0 |
| 7 | #394 | Chaque seigneur a son grenier, qui se garde mal | 1 | 1 | 1 | 0 | 0 |
| 8 | #395 | Le joueur fixe la part qu'il prend sur ses lieux | 1 | 1 | 1 | 0 | 0 |
| 9 | #396 | Le seigneur prélève sa part, et elle voyage jusqu'à son grenier | 4 | 3 | 3 | 0 | 0 |
| 10 | #397 | Le vassal envoie sa part à son suzerain | 1 | 1 | 1 | 0 | 0 |
| 11 | #398 | Le joueur ouvre son grenier à ses lieux | 1 | 1 | 1 | 0 | 0 |
| 12 | #399 | Les foyers quittent un maître qui les affame | 5 | 3 | 3 | 0 | 0 |
| 13 | #400 | Le service et la photographie disent qui tient quoi et ce qui circule | 5 | 4 | 4 | 0 | 0 |
| 14 | #401 | La carte de la forge montre les seigneurs et leurs flux | 3 | 2 | 2 | 0 | 0 |
| 15 | #402 | Le service sert la carte et les terres de départ | 1 | 1 | 1 | 0 | 0 |
| 16 | #403 | La carte du joueur s'ouvre dans Unity · pc | 14 | 11 | 11 | 0 | 0 |
| 17 | #404 | Le joueur choisit sa terre sur la carte · pc | 14 | 10 | 10 | 0 | 0 |
| 18 | #405 | Le joueur règle sa part et ouvre son grenier sur la carte · pc | 11 | 9 | 9 | 0 | 0 |
| 19 | #406 | La preuve du jalon 3 | 1 | 1 | 1 | 0 | 0 |
|  | **total** | 19 lignes | 74 | **58** | 58 | 0 | 0 |

**J4 — La capitale**

| ligne | issue | titre au CAP | nœuds | feuilles | livrées | ouvertes | fermées sans livre |
|--:|---|---|--:|--:|--:|--:|--:|
| 1 | #385 | L'épreuve du jalon 4 rejoue le journal des gestes et compare le monde | 1 | 1 | 1 | 0 | 0 |
| 2 | #386 | Unity joue les gestes de la preuve et redessine la même ville · pc | 1 | 1 | 1 | 0 | 0 |
| 3 | #387 | L'épreuve du jalon 4 sur le PC : Unity joue, Python rejoue, verdict · pc | 1 | 1 | 1 | 0 | 0 |
| 4 | #388 | La capture de la capitale bâtie et de son panneau · pc | 1 | 1 | 1 | 0 | 0 |
| 5 | #407 | La sixième terre de départ : l'émirat du Zab, en terre crue | 1 | 1 | 1 | 0 | 0 |
| 6 | #408 | On ne bâtit que sur ses terres | 1 | 1 | 1 | 0 | 0 |
| 7 | #409 | Le jeu ouvre la capitale du joueur · pc | 18 | 13 | 13 | 0 | 0 |
| 8 | #410 | Le joueur passe de la carte à sa capitale, et l'horloge suit la vue · pc | 7 | 6 | 6 | 0 | 0 |
| 9 | #411 | Chaque bourg naît avec sa ville de 1400 | 7 | 5 | 5 | 0 | 0 |
| 10 | #412 | Unity dessine la ville de 1400 d'après le service · pc | 7 | 6 | 6 | 0 | 0 |
| 11 | #413 | Le chantier se paie en vivres, pris au grenier | 4 | 3 | 3 | 0 | 0 |
| 12 | #414 | Les sans-logis bâtissent sur les parcelles libres | 1 | 1 | 1 | 0 | 0 |
| 13 | #415 | Les moissons demandent tous les bras | 9 | 6 | 6 | 0 | 0 |
| 14 | #416 | Le joueur trace l'enceinte de sa capitale | 6 | 5 | 5 | 0 | 0 |
| 15 | #417 | L'enceinte se dessine, et ses portes s'ouvrent sur les rues · pc | 12 | 9 | 9 | 0 | 0 |
| 16 | #418 | Une route vers les champs nourrit mieux le bourg | 1 | 1 | 1 | 0 | 0 |
| 17 | #855 | Un clic gauche choisit une terre et ouvre sa fiche · pc | 1 | 1 | 1 | 0 | 0 |
| 18 | #856 | La fiche parle en noms, pas en identifiants · pc | 22 | 15 | 15 | 0 | 0 |
| 19 | #857 | L'infobulle au curseur : ce que je survole, ce que fait ce bouton · pc | 4 | 3 | 3 | 0 | 0 |
| 20 | #858 | Les modes de carte : Puissances, Habitants, Flux, une légende à la fois · pc | 4 | 3 | 3 | 0 | 0 |
| 21 | #859 | Une seule barre en haut : ma maison, la date, le temps, mon grenier · pc | 5 | 4 | 4 | 0 | 0 |
| 22 | #860 | Le jeu s'ouvre en pause et dit quoi faire · pc | 1 | 1 | 0 | 1 | 0 |
| 23 | #849 | Le cabinet prend sa langue : la pierre, le bois brûlé et le registre · pc | 1 | 1 | 0 | 1 | 0 |
| 24 | #850 | La carte et ses dossiers parlent la langue du cabinet · pc | 1 | 1 | 0 | 1 | 0 |
| 25 | #851 | La capitale et ses outils parlent la langue du cabinet · pc | 1 | 1 | 0 | 1 | 0 |
| 26 | #419 | Le panneau de la capitale dit ce que coûte un chantier · pc | 1 | 1 | 0 | 1 | 0 |
| 27 | #420 | La ville fume, garnit ses étals et s'éclaire, d'après le monde · pc | 9 | 8 | 8 | 0 | 0 |
| 28 | #421 | Les gens du bourg circulent dans les rues · pc | 11 | 9 | 9 | 0 | 0 |
| 29 | #422 | La capitale dense tient 60 images par seconde · pc | 7 | 6 | 4 | 2 | 0 |
| 30 | #508 | La preuve complète du jalon 4 : la capitale du joueur, payée, murée et vivante · pc | 1 | 1 | 0 | 1 | 0 |
|  | **total** | 30 lignes | 147 | **116** | 108 | 8 | 0 |

**J5 — Le monde vivant**

| ligne | issue | titre au CAP | nœuds | feuilles | livrées | ouvertes | fermées sans livre |
|--:|---|---|--:|--:|--:|--:|--:|
| 1 | #322 | La carte montre les capitales voisines et ce que l'IA a fait | 1 | 1 | 1 | 0 | 0 |
| 2 | #423 | Chaque geste de l'IA dit sa raison | 1 | 1 | 1 | 0 | 0 |
| 3 | #424 | L'IA règle sa part sur ses projets et sur ses gens | 1 | 1 | 1 | 0 | 0 |
| 4 | #425 | L'IA ouvre son grenier quand ses gens ont faim | 1 | 1 | 1 | 0 | 0 |
| 7 | #426 | L'IA bâtit sa capitale quand son grenier le permet | 21 | 16 | 12 | 4 | 0 |
| 8 | #427 | Les petits seigneurs jouent aussi, chacun à son tour | 1 | 1 | 0 | 1 | 0 |
| 10 | #428 | Le service et la photographie montrent les voisins et leurs raisons | 1 | 1 | 0 | 1 | 0 |
| 12 | #429 | La carte de Unity montre les voisins et ce qu'ils font · pc | 1 | 1 | 0 | 1 | 0 |
| 14 | #324 | La preuve du jalon 5 | 1 | 1 | 0 | 1 | 0 |
|  | **total** | 9 lignes | 29 | **24** | 16 | 8 | 0 |

**J6 — Le pays et sa dynastie**

| ligne | issue | titre au CAP | nœuds | feuilles | livrées | ouvertes | fermées sans livre |
|--:|---|---|--:|--:|--:|--:|--:|
| 5 | #430 | Le monde porte des personnes : les chefs des maisons de 1400 | 3 | 2 | 2 | 0 | 0 |
| 6 | #431 | Les familles de 1400, et leurs découpes (#803 à #806, #824 à #826) | 21 | 17 | 10 | 7 | 0 |
| 7 | #432 | On vieillit et on meurt | 1 | 1 | 0 | 1 | 0 |
| 8 | #433 | Les couples ont des enfants | 1 | 1 | 0 | 1 | 0 |
| 9 | #434 | Chaque personne a ses traits et ses compétences | 1 | 1 | 0 | 1 | 0 |
| 10 | #435 | La loi de succession désigne l'héritier | 1 | 1 | 0 | 1 | 0 |
| 11 | #436 | À la mort du chef, les terres passent selon la loi | 1 | 1 | 0 | 1 | 0 |
| 12 | #437 | Une terre peut passer par une femme | 1 | 1 | 0 | 1 | 0 |
| 13 | #438 | Le joueur propose un mariage, et l'autre maison le pèse | 1 | 1 | 0 | 1 | 0 |
| 14 | #439 | Le joueur éduque ses enfants | 1 | 1 | 0 | 1 | 0 |
| 15 | #440 | Le joueur change sa loi de succession, à un prix | 1 | 1 | 0 | 1 | 0 |
| 16 | #441 | Républiques et Église ont leurs règles | 1 | 1 | 0 | 1 | 0 |
| 17 | #442 | Le joueur joue l'héritier, et une dynastie sans terre perd | 1 | 1 | 0 | 1 | 0 |
| 18 | #443 | Chaque héritier a ses ambitions | 1 | 1 | 0 | 1 | 0 |
| 19 | #444 | L'IA marie, éduque et choisit ses lois avec des raisons de monde | 1 | 1 | 0 | 1 | 0 |
| 20 | #445 | Le service et la photographie portent les dynasties | 1 | 1 | 0 | 1 | 0 |
| 21 | #446 | L'arbre de la dynastie dans Unity · pc | 1 | 1 | 0 | 1 | 0 |
| 22 | #447 | À la mort du chef, la carte montre l'héritier et le partage · pc | 1 | 1 | 0 | 1 | 0 |
| 23 | #448 | La preuve du jalon 6 | 1 | 1 | 0 | 1 | 0 |
|  | **total** | 19 lignes | 41 | **36** | 12 | 24 | 0 |

**J7 — La guerre**

| ligne | issue | titre au CAP | nœuds | feuilles | livrées | ouvertes | fermées sans livre |
|--:|---|---|--:|--:|--:|--:|--:|
| 1 | #449 | La guerre se déclare entre maisons | 1 | 1 | 0 | 1 | 0 |
| 3 | #450 | Le joueur lève des hommes dans ses foyers | 1 | 1 | 0 | 1 | 0 |
| 4 | #451 | L'armée marche de lieu en lieu | 1 | 1 | 0 | 1 | 0 |
| 5 | #452 | L'armée mange ce qu'elle porte et ce qu'elle prend | 1 | 1 | 0 | 1 | 0 |
| 6 | #453 | Les soldats rentrent chez eux, ou n'en reviennent pas | 1 | 1 | 0 | 1 | 0 |
| 7 | #454 | Le siège affame la place | 1 | 1 | 0 | 1 | 0 |
| 8 | #455 | La paix cède des terres | 1 | 1 | 0 | 1 | 0 |
| 9 | #456 | Le contrat de bataille : le monde envoie ses armées et son terrain, et reçoit ses pertes | 1 | 1 | 0 | 1 | 0 |
| 11 | #462 | Le chef de la dynastie peut mourir au combat | 1 | 1 | 0 | 1 | 0 |
| 12 | #465 | Une révolte naît de la faim et d'une occasion | 1 | 1 | 0 | 1 | 0 |
| 13 | #466 | L'IA fait la guerre avec des raisons de monde | 1 | 1 | 0 | 1 | 0 |
| 14 | #468 | Le service et la photographie portent les guerres et les armées | 1 | 1 | 0 | 1 | 0 |
| 15 | #469 | La colonne sur la carte · pc | 1 | 1 | 0 | 1 | 0 |
| 17 | #470 | La preuve du jalon 7 · pc | 1 | 1 | 0 | 1 | 0 |
|  | **total** | 14 lignes | 14 | **14** | 0 | 14 | 0 |

**J8 — L'argent**

| ligne | issue | titre au CAP | nœuds | feuilles | livrées | ouvertes | fermées sans livre |
|--:|---|---|--:|--:|--:|--:|--:|
| 1 | #471 | Les mines d'argent de 1400 entrent au monde | 1 | 1 | 0 | 1 | 0 |
| 2 | #472 | L'argent et l'or sortent des mines en kilos de métal | 1 | 1 | 0 | 1 | 0 |
| 3 | #473 | Le seigneur frappe monnaie | 1 | 1 | 0 | 1 | 0 |
| 4 | #474 | Chaque maison a son trésor | 1 | 1 | 0 | 1 | 0 |
| 5 | #475 | La monnaie de 1400 est déjà dans les bourses | 1 | 1 | 0 | 1 | 0 |
| 6 | #476 | Le marché du bourg fait le prix | 1 | 1 | 0 | 1 | 0 |
| 7 | #477 | Les marchands achètent où c'est bon marché et vendent où c'est cher | 1 | 1 | 0 | 1 | 0 |
| 8 | #478 | Les salaires se paient en pièces | 1 | 1 | 0 | 1 | 0 |
| 9 | #479 | Le prélèvement peut se payer en pièces | 1 | 1 | 0 | 1 | 0 |
| 10 | #480 | Le joueur dévalue sa monnaie, et les prix montent | 1 | 1 | 0 | 1 | 0 |
| 11 | #481 | Les banquiers prêtent ce qu'ils ont | 1 | 1 | 0 | 1 | 0 |
| 12 | #482 | Une dette se rembourse en pièces, ou le gage change de main | 1 | 1 | 0 | 1 | 0 |
| 13 | #483 | Le joueur achète une terre | 1 | 1 | 0 | 1 | 0 |
| 14 | #484 | La dot et la rançon se paient en pièces | 1 | 1 | 0 | 1 | 0 |
| 15 | #485 | L'IA décide sur les prix | 1 | 1 | 0 | 1 | 0 |
| 16 | #486 | Le service et la photographie portent les prix, les trésors et les dettes | 1 | 1 | 0 | 1 | 0 |
| 17 | #487 | La carte des prix, le trésor et la dette dans Unity · pc | 1 | 1 | 0 | 1 | 0 |
| 18 | #488 | La preuve du jalon 8 | 1 | 1 | 0 | 1 | 0 |
|  | **total** | 18 lignes | 18 | **18** | 0 | 18 | 0 |

**J9 — Le premier siècle**

| ligne | issue | titre au CAP | nœuds | feuilles | livrées | ouvertes | fermées sans livre |
|--:|---|---|--:|--:|--:|--:|--:|
| 1 | #489 | La partie se sauvegarde et se recharge à l'identique | 1 | 1 | 0 | 1 | 0 |
| 2 | #490 | Le joueur sauve et reprend sa partie dans le jeu · pc | 1 | 1 | 0 | 1 | 0 |
| 3 | #491 | Les intendants gèrent ce qui se répète | 1 | 1 | 0 | 1 | 0 |
| 4 | #492 | Le joueur inféode des lieux à ses vassaux | 1 | 1 | 0 | 1 | 0 |
| 5 | #493 | Une loi remplace mille gestes | 1 | 1 | 0 | 1 | 0 |
| 6 | #494 | La chronique de la dynastie s'écrit seule | 1 | 1 | 0 | 1 | 0 |
| 7 | #495 | La carte de 1500 que la partie a faite | 1 | 1 | 0 | 1 | 0 |
| 8 | #496 | Le score de la dynastie | 1 | 1 | 0 | 1 | 0 |
| 9 | #497 | Le siècle tient le budget du tick | 1 | 1 | 0 | 1 | 0 |
| 10 | #498 | Les agrégations restent conservatives sur cent ans | 1 | 1 | 0 | 1 | 0 |
| 11 | #499 | Les gestes du joueur ne grandissent pas avec son royaume | 1 | 1 | 0 | 1 | 0 |
| 12 | #505 | Le jeu se lance sans l'atelier · pc | 1 | 1 | 0 | 1 | 0 |
| 13 | #506 | Un siècle se joue dans le jeu, du menu à la chronique · pc | 1 | 1 | 0 | 1 | 0 |
| 14 | #852 | Le siècle se lit dans une seule langue · pc | 1 | 1 | 0 | 1 | 0 |
| 15 | #507 | La preuve du jalon 9 | 1 | 1 | 0 | 1 | 0 |
|  | **total** | 15 lignes | 15 | **15** | 0 | 15 | 0 |

### Les issues de J4, J5 et J6 qui ne descendent d'aucune ligne du CAP

Toutes les issues dont le milestone **actuel** est J4, J5 ou J6, quel que soit leur état. « Descend d'une ligne » = c'est l'issue d'une ligne numérotée, ou un sous-lot (récursif) de l'une d'elles. Pour les autres, on remonte leur propre découpe jusqu'à sa racine : « citée au CAP » = la racine ou un intermédiaire est cité ailleurs dans CAP.md (listes « Déjà livré », « Passent à l'horizon », texte) ; « jamais citée » = ni elle ni ses ancêtres n'apparaissent dans CAP.md.

| milestone | issues | descendent d'une ligne | hors du cap | dont citées au CAP (livrées / ouvertes / fermées sans livre) | dont jamais citées (livrées / ouvertes / fermées sans livre) | hors du cap créées depuis le 07/10 |
|---|--:|--:|--:|--:|--:|--:|
| J4 | 192 | 147 | **45** | 32 (32 / 0 / 0) | 13 (2 / 0 / 11) | 9 |
| J5 | 34 | 29 | **5** | 4 (4 / 0 / 0) | 1 (0 / 0 / 1) | 0 |
| J6 | 41 | 41 | **0** | 0 (0 / 0 / 0) | 0 (0 / 0 / 0) | 0 |

Les 14 issues hors du cap et jamais citées, par racine de découpe :

| racine | titre de la racine | milestone | créée le | issues | livrées | ouvertes | fermées sans livre | issues |
|---|---|---|---|--:|--:|--:|--:|---|
| #250 | Découper le jalon J4 — La capitale | J4 | 2026-09-30 | 11 | 0 | 0 | 11 | #250 #252 #255 #258 #260 #261 #262 #264 #267 #346 #363 |
| #318 | Découper le jalon J5 — Les autres | J5 | 2026-10-04 | 1 | 0 | 0 | 1 | #318 |
| #634 | La garde des terres : on ne bâtit que dans un bourg qu'on tient | J4 | 2026-10-15 | 1 | 1 | 0 | 0 | #634 |
| #745 | Le tick de master regagne 10 ms sur son budget de 100 | J4 | 2026-10-20 | 1 | 1 | 0 | 0 | #745 |

Les 36 issues hors des lignes mais citées au CAP viennent de 2 racines : #250 (32), #318 (4).


## 6. Les lots « à créer » du CAP, sans issue

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_mesure.py --compact docs/mesures/2026-11-07-refonte/brut/chaine-github.json --section 6`

Lignes numérotées « n. *(lot à créer)* … » sous les « ## Jalon n » de CAP.md : **12** — J5 : 5, J6 : 4, J7 : 3.

| jalon | ligne | lot à créer | ligne de CAP.md |
|---|--:|---|--:|
| J5 | 5 | La soudure de 1400 : les greniers du 1er janvier portent la récolte de 1399 | 578 |
| J5 | 6 | L'Europe de 1400 tient dix ans sans joueur | 579 |
| J5 | 9 | Le monde dit ce qui arrive : le fil des nouvelles | 582 |
| J5 | 11 | Le jeu se lance en observateur, avec la pause et cinq vitesses · pc | 584 |
| J5 | 13 | Le siècle sans joueur, mesuré chaque semaine au journal | 586 |
| J6 | 1 | Le pays se lit d'un seul tenant : ses lieux, ses vassaux et son suzerain | 699 |
| J6 | 2 | Le joueur prend la tête de n'importe quel pays de 1400 | 700 |
| J6 | 3 | Le joueur pose un bâtiment dans une province, et le plan lui trouve sa parcelle | 701 |
| J6 | 4 | Le panneau du pays et ses alertes dans Unity · pc | 702 |
| J7 | 2 | Le joueur s'allie, et l'allié appelé pèse sa réponse | 818 |
| J7 | 10 | La bataille se calcule dans `sim/`, jour après jour | 826 |
| J7 | 16 | La bataille et le siège se suivent sur la carte · pc | 832 |

Autres lignes numérotées sans « #n » ni « à créer » sous un jalon : 0.

Issues ouvertes dont le titre partage au moins la moitié des mots longs (plus de 4 lettres) d'un lot à créer — à regarder : J6 ligne 1 ↔ #492 « Le joueur inféode des lieux à ses vassaux ».

Contre-vérification : `grep -c '(lot à créer)' CAP.md` compte aussi les mentions hors des listes numérotées (paragraphe « Les lots nouveaux … *à créer* » et descriptions « — *à créer* »).

Contre-vérification indépendante (commandes en lecture, lancées par `--verifier` à la mesure) :

- mentions « (lot à créer) » dans CAP.md : `grep -c '(lot à créer)' CAP.md` → **12**


## 8. Le temps de « pret » à la fusion

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_mesure.py --compact docs/mesures/2026-11-07-refonte/brut/chaine-github.json --section 7`

Pour chaque lot livré depuis le 1er octobre (fenêtre = `closedAt` de l'issue, comme en 1) : du **premier** événement `LabeledEvent` de l'étiquette `pret` dans la timeline de l'issue (`timelineItems(itemTypes:[LABELED_EVENT, …])`) au `mergedAt` de sa PR `lot/…`. En heures (jours entre parenthèses). Quartiles : interpolation linéaire.

| fenêtre | lots | n | Q1 | médiane | Q3 | max |
|---|--:|--:|--:|--:|--:|--:|
| F1 — depuis le 1er octobre 2026 | tous | 241 | 3,1 h (0,1 j) | **9,9 h (0,4 j)** | 54,3 h (2,3 j) | 505,4 h (21,1 j) — #425 |
| F1 | `pc` | 118 | 3,7 h (0,2 j) | **11,7 h (0,5 j)** | 28,4 h (1,2 j) | 178,1 h (7,4 j) — #788 |
| F1 | autres | 123 | 2,7 h (0,1 j) | **9,0 h (0,4 j)** | 64,5 h (2,7 j) | 505,4 h (21,1 j) — #425 |
| F2 — depuis le 28 octobre 2026 | tous | 70 | 6,0 h (0,2 j) | **16,1 h (0,7 j)** | 28,3 h (1,2 j) | 505,4 h (21,1 j) — #425 |
| F2 | `pc` | 42 | 6,0 h (0,3 j) | **14,6 h (0,6 j)** | 23,9 h (1,0 j) | 178,1 h (7,4 j) — #788 |
| F2 | autres | 28 | 5,7 h (0,2 j) | **20,8 h (0,9 j)** | 127,7 h (5,3 j) | 505,4 h (21,1 j) — #425 |

À part : **0** lot(s) livré(s) avec PR de lot mais sans événement `pret` ; **7** lot(s) livré(s) sans PR `lot/…` (mode direct, pas de `mergedAt` de lot : #388, #524, #549, #525, #526, #527, #393) ; aucune durée négative.

Lecture : 238 des 241 lots ont reçu `pret` dans la minute de leur création (les sous-lots du chef naissent `pret`) : la durée mesure donc surtout création → fusion, attente des dépendances comprise. 56 lots ont reçu `pret` plusieurs fois (blocage puis reprise) ; c'est le premier qui compte.

| fenêtre | < 6 h | 6–24 h | 1–3 j | 3–7 j | > 7 j |
|---|--:|--:|--:|--:|--:|
| F1 | 94 | 61 | 42 | 34 | 10 |
| F2 | 18 | 30 | 5 | 10 | 7 |


## Ce qui paraît douteux dans les données

- **Les timelines GraphQL se tronquent quand la requête est grosse.** Avec `timelineItems(itemTypes: …)` demandé dans `issues(first: 50)` (ou à 40-50 alias `issue(number:)` par requête), GitHub rend un `totalCount` faux pour une partie des issues, sans erreur : à la première collecte, 161 issues fermées n'avaient pas leur `ClosedEvent` et 91 issues `livre` pas leur événement `livre` (ex. #388 : 4 événements au lieu de 9). Mesuré sur les 50 issues #331 à #409 : justes à 1-30 alias, 11 fausses à 40. La collecte retenue lit **10 issues par requête**, recompte par 7, relit seule toute issue dont le compte diffère (relues : aucune) ; contrôles : toute issue fermée a son `ClosedEvent`, toute issue `livre` son événement `livre`. Une mesure « par lots de 50 issues » faite autrement serait à refaire.
- **7 lots livrés sans PR de lot** (#388, #524, #549, #525, #526, #527, #393) : faits en mode direct le 9-11 octobre (PR #559 `direct/carte-epreuve` pour #524-#527 et #549 ; #388 et #393 fermés par commit). Comptés en 1-3 (issue `livre`), absents de 4 et 7.
- **Jalon et `pc` sont lus aujourd'hui**, pas au jour de la livraison : 0 lot(s) livré(s) en F1 ont changé de milestone après leur fermeture, 0 ont gagné ou perdu `pc` après ; 0 ont été rouverts un jour.
- **« pret » n'est pas « prenable »** : les sous-lots du chef naissent `pret`, même quand ils attendent un autre lot (« Dépend de »). La section 7 mesure surtout création → fusion, file d'attente comprise.
- **Le classement de la section 3 est un classement de titres** : « La ville dense mesurée sur quatre vues » ou « Le banc du temps d'image » sont des mesures de performance, « La capture … », « La photo … » des preuves visuelles ; à l'inverse, un lot de preuve au titre muet échappe (voir la liste des titres voisins non classés).
- **Taille de PR** : seules les PR #91 et #113 (septembre, hors fenêtres) dépassent la limite de 3 000 fichiers de l'API ; dans les fenêtres, fichiers et sommes concordent avec la PR.

<!-- complement -->

# Compléments (chaine_github_complement.py)

## 3bis. Le même classement par les fichiers de la PR (contrôle de la section 3)

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_complement.py` (échantillon : `gh pr diff <n> --name-only`).

Règle des fichiers, par chemin, dans cet ordre : `brief` = `docs/briefs/` ; `doc` = autre `docs/` ou `*.md` (`docs/mesures/…` = rendus d'épreuve) ; `test` = dossier `tests/` ou `Tests/`, `test_*.py`, `*Test(s).cs` ; `epreuve` = `pc/…`, `Editor/Captures/`, `Editor/*Epreuve|Preuve|Capture|Relance*`, fichier nommé `epreuve*`/`preuve*` ; `produit` = tout le reste (`jeu/sim/*.py`, `3d/unity/Assets/…` hors tests et Editor-épreuve, `3d/local3d/…`, `jeu/data/…`). Une PR « hors produit » = aucun fichier `produit`.

| fenêtre | lots avec PR lot/ | PR sans fichier `produit` | titre classé strict | les deux | titre strict mais PR touche du produit | PR hors produit, titre muet |
|---|--:|--:|--:|--:|--:|--:|
| F1 — depuis le 1er octobre 2026 | 241 | 40 (16,6 %) | 41 (17,0 %) | 33 | 8 | 6 |
| F2 — depuis le 28 octobre 2026 | 70 | 20 (28,6 %) | 22 (31,4 %) | 18 | 4 | 2 |

### Échantillon de 15 lots (F1, graine `random.Random(20261107)`) : 10 titres stricts + 5 titres non classés

Fichiers relus par `gh pr diff <n> --name-only` et comparés à la collecte GraphQL (colonne « gh = collecte »).

| lot | PR | titre | intitulé | fichiers par catégorie | hors produit | gh = collecte |
|---|---|---|---|---|---|---|
| #386 | #467 | strict | Unity joue les gestes de la preuve et redessine la même ville | brief 1, epreuve 2, produit 1 | non | oui |
| #406 | #768 | strict | La preuve du jalon 3 | brief 1, epreuve 1, test 1 | oui | oui |
| #702 | #722 | strict | La session Unity de l'épreuve de la capitale | brief 1, doc 3, epreuve 3 | oui | oui |
| #733 | #769 | strict | Le verdict de l'épreuve de la transition | brief 1, doc 4, epreuve 1, test 1 | oui | oui |
| #740 | #770 | strict | Le verdict de l'épreuve de la ville de 1400 | brief 1, doc 4, epreuve 1, test 1 | oui | oui |
| #782 | #854 | strict | L’épreuve juge les signes de vie contre le monde | brief 1, doc 5, epreuve 1, test 1 | oui | oui |
| #928 | #930 | strict | Le juge de la carte lit la fiche en noms | brief 1, epreuve 1, test 1 | oui | oui |
| #944 | #948 | strict | L'épreuve, aucun identifiant à l'écran, et la photo | brief 1, epreuve 2 | oui | oui |
| #986 | #997 | strict | Le montage de l'IA passe sur celui du programme | brief 1, doc 1, test 1 | oui | oui |
| #988 | #1019 | strict | L'ancienne règle quitte les tests | brief 1, test 2 | oui | oui |
| #263 | #364 | non classé | Le panneau de la capitale montre les foyers, leur logement et le chantier | brief 1, epreuve 2, produit 2, test 2 | non | oui |
| #270 | #272 | non classé | La planche Unity des neuf étapes de chantier | brief 1, doc 1, produit 25 | non | oui |
| #343 | #384 | non classé | Chaque lieu meurt de sa dette et naît de son abondance | brief 1, doc 1, produit 3, test 10 | non | oui |
| #392 | #557 | non classé | Les lieux et leurs seigneurs portent un nom plausible | brief 1, doc 2, produit 4, test 8 | non | oui |
| #642 | #646 | non classé | /plan dit les bras du jour et le grain payé de chaque chantier | brief 1, doc 2, produit 3, test 2 | non | oui |

Lecture : sur les 10 titres stricts, 9 ont une PR sans fichier `produit` ; sur les 5 non classés, 5 touchent bien du produit. Écarts entre `gh pr diff` et la collecte : 0.

PR « hors produit » dont le titre n'a aucun mot de la liste (F1, 6) : #408 « On ne bâtit que sur ses terres » ; #651 « La session Unity du choix de la Morée » ; #682 « Jouer.cmd laisse le jeu lire la maison du joueur » ; #731 « Le jeu s'ouvre sur la carte à sa vitesse » ; #781 « Une session Unity relève la capitale nourrie puis affamée » ; #897 « Une session Unity relève les ouvriers au chantier puis le bourg vidé ».

Titres stricts dont la PR touche pourtant du produit (F1, 8) : #306 « La preuve du jalon 2 » ; #386 « Unity joue les gestes de la preuve et redessine la même ville » ; #604 « La photographie porte la maison du joueur et son suzerain, et la preuve rejoue » ; #777 « Un service d’épreuve peut vider le panier du bourg » ; #896 « Un service d'épreuve peut vider le bourg » ; #936 « Le service d'épreuve règle le travail de l'enceinte » ; #957 « Le service d'épreuve monte la ville dense de la mesure » ; #970 « La mesure de l'IA suit les trente derniers jours ».

## 5bis. Médiane et maximum de la découpe, par ligne du CAP

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_complement.py` (la table par ligne : `chaine_github_mesure.py --compact … --section 5`).

Par ligne numérotée (J3 à J9 ; J1 et J2 n'ont pas de ligne « #n »). **nœuds** = l'issue de la ligne + tous ses sous-lots, récursivement (parents découpés compris) ; **feuilles** = nœuds sans sous-lot (les lots réellement exécutés) ; livrées = feuilles `livre`. « issue elle-même plus ses sous-lots » = nœuds.

| jalon | lignes | médiane nœuds | max nœuds | médiane feuilles | max feuilles | nœuds (somme) | feuilles livrées | ligne la plus enflée |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| J3 | 19 | 1 | 14 | 1 | 11 | 74 | 58 | #403 |
| J4 | 30 | 2,5 | 22 | 2 | 15 | 147 | 108 | #856 |
| J5 | 9 | 1 | 21 | 1 | 16 | 29 | 16 | #426 |
| J6 | 19 | 1 | 21 | 1 | 17 | 41 | 12 | #431 |
| J7 | 14 | 1 | 1 | 1 | 1 | 14 | 0 | #449 |
| J8 | 18 | 1 | 1 | 1 | 1 | 18 | 0 | #471 |
| J9 | 15 | 1 | 1 | 1 | 1 | 15 | 0 | #489 |
| tous | 124 | 1 | 22 | 1 | 17 | 338 | 194 | #856 |

Lignes **terminées** (toutes leurs feuilles livrées) : 47 ; médiane 3 nœud(s) et 2 feuille(s) ; maximum 22 nœuds / 15 feuilles ; 24 sont découpées. Biais : une ligne ouverte (J6 à J9) n'est pas encore découpée, donc la médiane globale sous-estime ce qu'elle deviendra ; la médiane des lignes terminées sur-représente les jalons déjà travaillés.

## 6bis. Un « lot à créer » a-t-il déjà une issue ouverte au même titre ?

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_complement.py`.

Pour chaque ligne « à créer » : parmi toutes les issues **ouvertes** (hors journal), meilleur rapport `difflib.SequenceMatcher` sur le titre en minuscules sans accents, et meilleure part de mots de plus de 4 lettres communs. Seuil « à regarder » : rapport ≥ 0,6 ou ≥ 50 % des mots longs de la ligne.

| jalon | ligne | lot à créer | titre le plus proche (rapport) | plus de mots longs communs | verdict |
|---|---|---|---|---|---|
| J5 | 5 | La soudure de 1400 : les greniers du 1er janvier portent la récolte de 1399 | #487 La carte des prix, le trésor et la dette dans Unity (0.48) | #445 Le service et la photographie portent les dynasties (20%) | non |
| J5 | 6 | L'Europe de 1400 tient dix ans sans joueur | #475 La monnaie de 1400 est déjà dans les bourses (0.60) | #438 Le joueur propose un mariage, et l'autre maison le pèse (33%) | à regarder |
| J5 | 9 | Le monde dit ce qui arrive : le fil des nouvelles | #500 Le kit de pierre et de tuile des Balkans et de Morée (0.48) | #444 L'IA marie, éduque et choisit ses lois avec des raisons de monde (33%) | non |
| J5 | 11 | Le jeu se lance en observateur, avec la pause et cinq vitesses · pc | #860 Le jeu s'ouvre en pause et dit quoi faire (0.49) | #505 Le jeu se lance sans l'atelier (25%) | non |
| J5 | 13 | Le siècle sans joueur, mesuré chaque semaine au journal | #852 Le siècle se lit dans une seule langue (0.52) | #434 Chaque personne a ses traits et ses compétences (17%) | non |
| J6 | 1 | Le pays se lit d'un seul tenant : ses lieux, ses vassaux et son suzerain | #492 Le joueur inféode des lieux à ses vassaux (0.48) | #492 Le joueur inféode des lieux à ses vassaux (50%) | à regarder |
| J6 | 2 | Le joueur prend la tête de n'importe quel pays de 1400 | #490 Le joueur sauve et reprend sa partie dans le jeu (0.51) | #438 Le joueur propose un mariage, et l'autre maison le pèse (33%) | non |
| J6 | 3 | Le joueur pose un bâtiment dans une province, et le plan lui trouve sa parcelle | #438 Le joueur propose un mariage, et l'autre maison le pèse (0.51) | #438 Le joueur propose un mariage, et l'autre maison le pèse (20%) | non |
| J6 | 4 | Le panneau du pays et ses alertes dans Unity · pc | #446 L'arbre de la dynastie dans Unity (0.52) | #419 Le panneau de la capitale dit ce que coûte un chantier (33%) | non |
| J7 | 2 | Le joueur s'allie, et l'allié appelé pèse sa réponse | #438 Le joueur propose un mariage, et l'autre maison le pèse (0.60) | #438 Le joueur propose un mariage, et l'autre maison le pèse (25%) | non |
| J7 | 10 | La bataille se calcule dans `sim/`, jour après jour | #459 La bataille se joue sans image, à l'identique (0.58) | #456 Le contrat de bataille : le monde envoie ses armées et son terrain, et reçoit ses pertes (33%) | non |
| J7 | 16 | La bataille et le siège se suivent sur la carte · pc | #459 La bataille se joue sans image, à l'identique (0.61) | #141 Tutoriel carte-ville (25%) | à regarder |

12 lignes ; 3 à regarder ; aucune n'a d'issue ouverte de titre identique.

## 7. L'état courant

Commande : `py docs/mesures/2026-11-07-refonte/scripts/chaine_github_complement.py` ; contrôles : `gh issue list -R PLiagre/Forge --state open --limit 1000 --json number,labels,milestone` et `gh pr list -R PLiagre/Forge --state open --json number,title,headRefName,createdAt`.

Issues ouvertes par milestone et par étiquette d'état (`pc` = dont étiquette `pc`, comptée à part).

| milestone | état du milestone | pret | idee | en-cours | bloque | (sans état) | journal | dont `pc` | total ouvertes |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| J4 | open | 6 | · | · | 2 | · | · | 8 | **8** |
| J5 | open | 7 | · | · | 1 | · | · | 1 | **8** |
| J6 | open | 23 | · | · | 1 | · | · | 2 | **24** |
| J7 | open | 21 | · | · | · | · | · | 9 | **21** |
| J8 | open | 18 | · | · | · | · | · | 1 | **18** |
| J9 | open | 20 | · | · | · | · | · | 9 | **20** |
| Réserve | open | · | 19 | · | · | · | · | 13 | **19** |
| (aucun) | ? | · | · | · | · | 1 | 2 | · | **3** |
| **total** |  | **95** | **19** | **0** | **4** | **1** | **2** | **43** | **121** |

### PR ouvertes

| PR | branche | titre | issue | étiquettes de l'issue | ouverte le (Paris) | âge |
|---|---|---|---|---|---|---|
| #511 | lot/324-la-preuve-du-jalon-5 | Lot #324 — La preuve du jalon 5 | #324 | lot pret | 07/10/2026 13:59 | 30,8 j |

1 PR ouverte(s) en tout, dont 1 de branche `lot/`.
