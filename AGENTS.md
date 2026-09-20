# AGENTS.md — les règles, pour tous

Le seul fichier de règles du dépôt. Il ne paraphrase aucun autre document :
ce qui est ici n'est écrit qu'ici.

Les trois documents vivants : **[VISION.md](VISION.md) et [OBJECTIF.md](OBJECTIF.md)** (ce qu'on construit,
gelé) · **[ROADMAP.md](ROADMAP.md)** (où on en est) · **AGENTS.md** (ce
fichier). Le quatrième document, [`sim/MODELE.md`](sim/MODELE.md), dit
comment le monde fonctionne — c'est de lui que les lots sont découpés.

---

## Le projet en trois phrases

ForgeHistory est un moteur de simulation historique vivant (1400-1900) dont
le gameplay émerge. Le produit est `sim/` — `py -m sim`. Le monde lit une
carte figée, `data/world-1400.json`.

## Langue

Tout ce qui s'écrit ici est en **français clair** : messages de commit,
briefs, commentaires, documents. Phrases courtes, concrètes : ce qui a été
fait, pourquoi, ce qui reste. Un terme technique nécessaire s'explique en une
phrase la première fois.

---

## Le workflow

Le propriétaire donne une direction. Le reste avance sans lui.

1. Une fiche entre au registre de [ROADMAP.md](ROADMAP.md), état
   `a-briefer` — par le formulaire « Demander un lot », qui l'écrit et
   ouvre sa PR. Le registre ne s'édite plus à la main.
2. Le **briefer** écrit `briefs/NNN-slug.md` sur `brief/NNN-slug` et ouvre
   sa PR ; elle passe la fiche à `pret`.
3. Le **coder** exécute le brief sur `agent/NNN-slug` et ouvre sa PR ; elle
   passe la fiche à `livre` avec son numéro.
4. La **CI** joue les tests. Le **relecteur** — jamais l'auteur — approuve
   ou refuse, sur la révision courante de la PR.
5. L'**intégration** fusionne, une PR à la fois, rejouée sur le dernier
   `master`.
6. Quand une fusion finit une couche, un **palier** entre au registre.

Trois choses seulement restent au propriétaire : donner des directions,
reprendre ce qui est tombé, et fusionner ce qui n'est pas un lot — une
expérience, une branche à lui. Il ne fusionne pas les lots.

Il n'a pas non plus à aller chercher où en est le travail : la page
`tableau` est réécrite à chaque tour et dit, pour chaque lot son état, et
pour chaque PR ouverte ce qui la retient — avec les mots de l'intégration
elle-même, pas une paraphrase.

### Ce qui remplace son œil sur le bouton

**Celui qui a écrit le code ne dit pas s'il est recevable.** La phrase n'a
pas changé ; ce qui la tient a changé. Elle était une politesse tant que
personne ne la mesurait ; c'est maintenant une règle mécanique
(`outils/relecture.py`) : une approbation posée sur la **révision
courante**, par une connexion qui n'a écrit aucun des commits. Quatre
refus, et aucun feu vert par défaut : absente, périmée, de l'auteur, ou
changements demandés.

Cette règle est appliquée **deux fois, par le même module, depuis deux
endroits qui ne se valent pas**. Le travail `relecture` la joue sur la PR
et pose un état visible — c'est ce qui dit à un relecteur pourquoi la PR
attend. L'intégration la rejoue depuis le code de `master`, et c'est
celle-là qui ouvre la porte. La distinction n'est pas un scrupule : un
travail qui tourne sur le code de la PR juge avec du code que la PR peut
changer, et rien n'est plus facile à écrire qu'un juge complaisant.

**La fusion est mécanique.** Une PR entre dans `master` quand tous les
contrôles déclarés dans [`atelier.toml`](atelier.toml) § `[integration]`
sont verts sur sa révision courante **et** qu'un tiers l'a approuvée sur
cette même révision. À ces conditions, et à elles seules. Personne ne
fusionne sur un avis : l'intégration ne lit ni le brief, ni le diff, ni un
compte rendu. Un contrôle **absent** n'est pas un contrôle vert ; un état
de fusion **inconnu** retient au lieu de passer.

**L'intégration est séquentielle et rejouée.** Plusieurs lots s'écrivent en
même temps ; ils n'entrent jamais en même temps. Une PR en retard sur
`master` est d'abord rejouée dessus : ses contrôles n'ont pas vu ce qui a
été fusionné depuis. Deux PR vertes séparément ne sont pas une PR verte
ensemble.

Ce qui n'a pas de préfixe déclaré n'est pas intégré : une branche
d'expérience qui passe au vert n'est pas un lot, et elle attend le
propriétaire.

### Qui fait quoi, et où ça vit

L'**invocation** des agents — quel agent à quelle étape, quel prompt, sur
quelle machine, quelle carte dans quelle boîte — vit dans **l'atelier**
(`atelier/`, `python3 -m atelier`). Le branchement de ce dépôt est
[`atelier.toml`](atelier.toml).

Avant la fusion, l'atelier vivait sur une branche détachée d'un dépôt et en
copie vendorisée dans l'autre — deux chaînes qui divergeaient en silence, et
sept tests rouges du seul fait de son absence. Il vit maintenant dans l'arbre.
Un dépôt unique n'a pas à aller chercher son propre outil ailleurs.

L'**intégration** vit ici, parce que c'est ici qu'est `master` : elle
tourne sur GitHub, sans machine allumée chez personne, et elle ne sait rien
du jeu non plus. L'atelier ne fusionne pas — `atelier fusionner` refuse, et
continue de refuser.

Elle est coupée en deux, et la coupure porte : `outils/` **décide** et
n'écrit jamais sur GitHub — c'est ce qui permet de jouer chaque décision
hors ligne ; `.github/scripts/` **fait** le geste — et c'est ce qui permet
de le jouer sur un banc, avec de faux exécutables. Les workflows ne portent
aucune logique : ils appellent l'un, puis l'autre. La règle 13 dit ce que
cette coupure a coûté avant d'exister.

Ce fichier-ci dit les **règles du jeu** ; l'atelier dit **comment on
invoque**. Aucun des deux ne paraphrase l'autre, et celui-ci fait foi pour
le monde. Un rappel local tient dans
[`docs/WORKFLOW.md`](docs/WORKFLOW.md).

## Le brief

Un fichier, cinq sections. C'est la seule source d'instruction d'un lot :
aucun autre document ne le paraphrase.

```
# Brief NNN — titre

## But                    une phrase : ce que le monde saura faire après
## Règle du monde         comment ça marche, en termes de monde ;
                          cite la section de sim/MODELE.md dont ça découle
## Périmètre              les fichiers autorisés en écriture, rien d'autre
## Conditions de succès   SC1…SCn ; chacune nomme une commande qui peut échouer
## Hors périmètre         ce que ce lot ne fait pas
```

Six façons de rater un brief :

1. **Un lot = un changement.** Si deux parties pourraient être livrées et
   jugées séparément, ce sont deux briefs. Le test : « si la moitié marche et
   l'autre pas, est-ce que ça entre dans `master` ? » Si oui, couper.
2. **Chaque critère nomme une commande, un fichier ou une valeur
   observable**, et doit pouvoir échouer. « Le code est propre » n'est pas un
   critère.
3. **Tout compteur a un dénominateur dérivé des données.** Jamais un nombre
   attendu écrit en dur. Un échantillon vide **échoue**, il ne passe pas.
4. **Ne jamais demander de modifier un test existant.** Ajuster un contrôle
   après avoir vu une mesure est une calibration déguisée. Un lot **ajoute**
   ses cas au fichier qui porte déjà l'invariant concerné.
5. **Tout brief qui touche au monde dit son niveau de fidélité** (1, 2 ou 3).
6. **Le périmètre d'écriture n'autorise que ce que le travail décrit exige.**
 Tout autre chemin est interdit, nommément. Un périmètre large est une
 permission qu'on ne se souvient pas d'avoir donnée. Les fichiers
 autorisés dans leur phrase, les interdits dans la leur : l'atelier lit
 les premiers pour poser le verrou et écarte les seconds.

## Le palier

Un lot prouve sa règle. Il ne prouve pas que les lots tiennent ensemble.

Quand plus aucune fiche d'une couche n'attend quelque chose — le monde
vivant, les villes, les armées — la couche est finie, et personne n'a plus
de raison d'ouvrir le sujet. C'est là que dorment les défauts que les lots
ne pouvaient pas voir chacun de son côté : une grandeur que deux mécanismes
font bouger sans se connaître, une vue qui montre autre chose que ce que le
moteur joue, un déterminisme perdu à la jointure.

**Un palier est le lot qui va les chercher** : stabilisation et QA sur la
couche entière. Il entre au registre tout seul, en tête, à la fusion qui
finit la couche, et il nomme dans sa fiche les lots qu'il couvre. Ces trois
règles tiennent :

1. **Une couche finie sans rien de livré n'est pas une couche finie.** Un
   échantillon vide échoue ; il ne passe pas.
2. **Un palier ne se déclenche qu'une fois par lot couvert.** La liste de
   ses dépendances est ce qui l'en empêche — pas un compteur tenu à la
   main. Un lot livré après lui appelle le palier suivant.
3. **Le palier appartient à sa couche.** Tant qu'il n'est pas livré, la
   couche n'est pas finie : c'est ce qui empêche d'en déposer deux.

Un palier passe par le cycle ordinaire — brief, code, relecture, CI,
intégration. Il n'a aucun privilège : ce qu'il trouve devient des lots, et
ces lots-là passent par le même chemin.

## La feuille de route

L'état d'un lot ne s'écrit qu'à **un** endroit : sa fiche dans le registre
de [ROADMAP.md](ROADMAP.md), qui décrit aussi les états, les transitions et
qui tient chaque geste. Trois règles tiennent ici :

1. **Un lot n'existe que s'il a une fiche.** Un brief sans fiche est un
 orphelin, une fiche `pret` sans brief est un mensonge : les deux
 rougissent.
2. **La fiche d'un lot fait partie du périmètre implicite de sa PR**, et
 rien d'autre de `ROADMAP.md`. La PR du brief la passe à `pret` ; la PR du
 lot la passe à `livre` avec son numéro. C'est ce qui fait que `master` ne
 dit « livré » qu'après la fusion, jamais avant.
3. **La machine ne lit pas la prose.** `python3 -m atelier feuille valider
 --projet .` est la seule lecture qui compte ; la CI la joue sur chaque
 PR, avec les transitions contre `master`.

---

## Les trois principes non négociables

1. **Une seule source de vérité.** Monde → Pays → Province → Ville →
   Quartier → Bâtiment → Famille → Personne. Les vues lisent cette
   hiérarchie ; elles ne deviennent jamais une base de données parallèle.

2. **Le moteur raisonne en termes de monde, jamais de gameplay.**
   Interdit : « si famine alors +20 % de criminalité ».
   Exigé : ils ont faim → ils cherchent → certains volent → la criminalité
   monte.

3. **L'économie est physique.** Rien ne se téléporte. Tout a une origine, un
   transport, un stockage, une destination.

## Vraisemblable, pas véridique

- **Niveau 1 — juste dans les grandes lignes. Obligatoire.** La Méditerranée
  est là où elle est ; les Alpes sont des montagnes ; Venise est grande en
  1400.
- **Niveau 2 — plausible, généré, jamais sourcé.** Rendements, gisements
  secondaires, population des villages, climat local. **Une anomalie de
  niveau 2 n'est pas un défaut** : elle n'ouvre ni correctif, ni lot.
- **Niveau 3 — pas simulé.** Ce qui a besoin d'une source pour exister
  n'entre pas dans le jeu.

Pas de nombre magique dans le code du moteur — la règle tient. Justifier
chaque constante par une source — abandonné ; « ordre de grandeur plausible »
en commentaire suffit.

## La règle d'admission des tests

Un test existe s'il protège **l'une de ces trois choses**, et seulement :

1. un **invariant physique** (la masse se conserve, l'adjacence est
   symétrique, une dette ne se rembourse pas plus vite que le surplus) ;
2. une **règle de jeu visible** (on ne mange pas deux fois, on a faim, on
   meurt) ;
3. le **déterminisme** (même graine, même monde).

Corollaire : **ne pas ajouter un fichier de test par lot.** Un lot ajoute ses
cas au fichier qui porte déjà l'invariant concerné.

Et la suite doit rester **jouable à la main avant chaque fusion**. Une suite
qu'on n'attend pas est une suite qu'on ne joue pas.

---

## Les treize règles payées par un vrai défaut

Chacune a coûté un défaut mesuré. Elles portent sur le code, pas sur le
processus : elles survivent à tout changement de workflow.

1. `py`, jamais `python` (sur la machine Windows du propriétaire, `python`
   est un faux alias du Microsoft Store). Sur Linux : `python3`. Tenu
   mécaniquement par `.claude/hooks/no_bare_python.py`.
2. Un contrôle **dérive** sa référence ; il n'est jamais nommé d'après sa
   cible. (Six récurrences historiques.)
3. Un compteur dérive aussi.
4. **Prouver le rouge d'abord.** Un contrôle qui ne peut pas rougir ne
   prouve rien.
5. Une garde placée après l'effet qu'elle doit empêcher ne protège rien.
6. Un contrôle trop grossier coûte aussi cher qu'un contrôle laxiste.
7. La présence n'est pas la fonction.
8. Un zéro peut être une vraie mesure — sentinelle `-1`, jamais `0`, pour
   « non calculé ».
9. Une impossibilité se teste avant d'être invoquée : une commande et un
   message d'erreur, sinon ce n'est pas un constat mais une abdication.
10. Quand une donnée manque, l'agent l'invente en silence par défaut —
    l'absence doit donc être **déclarable**, et le code doit refuser de
    deviner.
11. **Regarder les captures soi-même.** Quatre défauts majeurs ont été vus à
    l'œil que des suites 100 % vertes n'ont jamais attrapés.
12. Une empreinte de parité se cite par **nom**, jamais par valeur : elle
    sera rebasée un jour, et le document qui porte la constante morte piège
    tous les lots suivants.
13. **Un bloc de shell écrit dans un YAML ne se joue nulle part.** GitHub
    exécute `run:` avec `bash -e` ; un `set` qui n'éteint pas `errexit`
    laisse la première commande en échec tuer l'étape avant sa fin. Le
    4 septembre 2026, `relecture` est mort sur le verdict « pas encore
    relue » — code 1, attendu — et n'a jamais posé son état : le contrôle
    ne rougissait pas, il n'existait pas. Un geste vit donc dans un
    fichier de `.github/scripts/`, et un fichier se joue sur un banc
    (`outils/tests/banc.py`), avec de faux exécutables en tête du `PATH`.
    Le seul moyen de lire un `$?` sous `errexit` est `cmd || code=$?` :
    la ligne d'après n'est jamais atteinte.

## Les six modes de défaillance diagnostiqués

| # | mode de défaillance | contre-mesure structurelle |
|---|---|---|
| 1 | double clé primaire | UNE clé spatiale : `cell_id`, décidée avant tout code |
| 2 | champ déclaré que personne n'écrit | `sim/tests/test_write_coverage.py` : chaque champ a un site d'écriture et un site de lecture, rouge sinon |
| 3 | variable terminale (calculée, lue par personne) | avant d'ouvrir un levier, vérifier que sa conséquence atteint quelque chose de mesurable hors de son module |
| 4 | la présentation réimplémente la simulation | la présentation LIT, elle ne décide jamais |
| 5 | compteur codé en dur | un compteur dérive des données, ou il n'existe pas |
| 6 | contrôle qui nomme sa propre référence | référence DÉRIVÉE de la mesure ; un échantillon vide doit ÉCHOUER, jamais passer |

---

## Où vit quoi

| chemin | quoi |
|---|---|
| `sim/` | **le produit** — `py -m sim`. Voir `sim/README.md` et `sim/MODELE.md`. |
| `data/` | la carte figée `data/world-1400.json` et les centres de province. La seule entrée géographique du jeu. |
| `vues/tableau/` | un regard mince sur une photographie. Jamais une seconde simulation. |
| `briefs/` | un fichier par lot. |
| `outils/` | ce que la CI **décide** : qui a relu, quelle PR entre dans `master`, quand une couche finie appelle son palier, ce que la page de pilotage montre et ce que chacune de ses actions vérifie avant d'agir. Il ne parle jamais au jeu, et il n'écrit jamais sur GitHub. |
| `.github/scripts/` | ce que la CI **fait** : poser un état, fusionner, rejouer, déposer une fiche. Du shell dans des fichiers, joués sur un banc. |
| `.github/ISSUE_TEMPLATE/` | le formulaire par lequel une demande de lot entre au registre. Ses intitulés sont lus par `outils/saisie.py` : les changer d'un côté seulement fait rougir. |
| `.github/workflows/` | les neuf travaux : `tests`, `security`, `relecture`, `integration`, `lot`, `tableau`, plus les trois que la page de pilotage déclenche — `controles`, `brouillon`, `etat-lot`. Ils appellent les deux ci-dessus ; ils ne portent pas de logique. |
| `ROADMAP.md` | où on en est, et le registre des lots — la seule représentation de l'état d'un lot. |
| `atelier_meta/crons/` | **la machine** : l'horloge de la chaîne. Le reste du dépôt décide ; ces scripts réveillent un rôle, rangent sa carte, et s'arrêtent. C'est la seule pièce qui a besoin d'une machine allumée, et c'est donc la seule qu'on installe sur le VPS. Voir [`atelier_meta/crons/README.md`](atelier_meta/crons/README.md). |
| `atelier.toml` | comment ce dépôt se branche sur ForgeAtelier, la liste des contrôles requis pour entrer dans `master`, et les seuils de la page de pilotage (§ `[tableau]`) — un seuil qui ne vit que dans le code est un réglage que personne ne change. |
| `docs/WORKFLOW.md` | rappel local : les trois postes de *ce* produit, la conduite de la chaîne, et le lien vers l'atelier. |
| la page de pilotage | écrite par `tableau`, publiée sur GitHub Pages. Elle est **statique** : aucun jeton, aucun appel réseau, aucune bibliothèque. Ce qui s'affiche est calculé à la génération ; ce qui s'actionne est un lien vers GitHub et un travail qui fait le geste. |
| hors arbre : [forge3d](https://github.com/PLiagre/forge3d) | moteur de rendu terrain récupéré (Rust/WebGPU, API Python). Dépôt séparé. Il photographie un relief ; il ne simule pas. Il n'entre ni dans `sim/` ni dans `vues/tableau/`. |
| `vues/relief/` | le regard 3D. Lit une photographie, la donne à forge3d, rend une image. Il ne décide aucun nombre. **Le seul dossier du dépôt qui demande des bibliothèques extérieures** — elles sont déclarées dans son `requirements.txt`, et lui seul les exige. |

## Les archives

L'outil qui fabrique la carte, les quarante lots déjà faits avec leurs
preuves, l'ancien pilote et l'ancien harnais sont sortis de l'arbre de
travail au dégraissage V1. Ils vivent dans l'historique git, au tag
**`v0-avant-degraissage`** :

```bash
git show v0-avant-degraissage:<chemin>        # relire un fichier
git checkout v0-avant-degraissage -- tools/   # récupérer l'outil carte
git ls-tree --name-only v0-avant-degraissage  # voir ce qu'il y avait
```

La carte est figée : on ne refait pas `data/world-1400.json`. Le jour où il
faudrait, l'outil se récupère par la commande ci-dessus.

## Les commandes

`py` sur la machine Windows du propriétaire, `python3` sur Linux — jamais
`python` nu (règle 1).

```bash
py -m sim                                # le produit
py -m sim --ticks 0 --json               # fumée : le monde s'amorce
py -m pytest sim/tests/ -q               # les tests du jeu
py -m pytest vues/ -q                     # les trois vues
py -m pytest outils/tests/ -q            # ce que la CI décide, et ce qu'elle fait
py -m pytest forge/tests/ -q             # la commande de bout en bout

# ce que la CI décide, joué à la main (lecture seule, rien n'est écrit)
py -m outils palier --projet .           # une couche finie attend-elle son palier ?
py -m outils integration --depot PLiagre/Forge --projet .
py -m outils relecture --depot PLiagre/Forge --pr N
py -m outils tableau --depot PLiagre/Forge --projet . --sortie /tmp/etat.html
py -m outils saisie --projet . --corps demande.md

# la feuille de route : cohérente ? où en est chaque lot ?
# (l'atelier sur le PYTHONPATH — voir docs/WORKFLOW.md)
py -m atelier feuille valider --projet .
py -m atelier feuille etat --projet .

# regarder le monde : photographier, puis ouvrir
py -m sim --ticks 0 --seed 0 --snapshot-json /tmp/monde.json
py -m vues.tableau --snapshot /tmp/monde.json
```

Le moteur, le regard mince et les outils sont en bibliothèque standard
seule, et ça ne se négocie pas : c'est ce qui fait qu'ils tournent partout,
sans rien installer. `vues/relief/` est l'exception, et elle est bornée —
il parle à un moteur de rendu écrit en Rust, il ne pouvait pas ne rien
demander. Rien d'autre ne dépend de lui, et le jeu tourne sans lui.

Les tests demandent `pytest` ; ceux d'`outils/` demandent en plus l'atelier
sur le `PYTHONPATH` — c'est lui qui lit le registre, et il n'y a qu'un
lecteur ; ceux du `vues/relief/` demandent son `requirements.txt`.

Il n'y a pas de linter : les garde-fous du dépôt sont les tests, la
relecture et l'œil du propriétaire sur les captures.
