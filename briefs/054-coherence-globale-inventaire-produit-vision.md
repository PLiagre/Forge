# Brief 054 — Cohérence globale : inventaire du produit face à la vision

## But

Rendre lisible, dans un inventaire vérifiable, ce que le produit réalise,
réalise partiellement ou ne réalise pas encore de chaque promesse de
`VISION.md`, avec les commandes effectivement jouées et leurs limites.

Ce lot livre un constat, pas une déclaration de conformité globale. Une
fonction absente peut être un résultat correct de l'inventaire ; elle ne
devient pas présente parce que la suite de tests est verte. L'état des lots
reste exclusivement dans le registre de `ROADMAP.md`.

État de départ à mesurer :

```bash
git rev-parse HEAD
git status --short
rg -n '^## |^### ' VISION.md sim/MODELE.md ROADMAP.md
test -f docs/COHERENCE.md
```

La dernière commande échoue avant ce lot. Si un inventaire couvre déjà les
promesses, avec preuves rejouables sur la révision courante, le lot est
caduc. Un simple catalogue de fonctions ou des résultats d'une ancienne
révision ne le rendent pas caduc.

## Règle du monde

**Aucune règle nouvelle : ce lot ne change aucun nombre du monde.** Son
fondement est l'écart entre les promesses de `VISION.md` et le produit
observable. `sim/MODELE.md` § « Déclaration explicite » déclare notamment
l'amorçage paramétrique ; § « Ce que le moteur ne fait pas encore »,
§ « Le moteur sans état caché » et § « La province dérivée et ses centres »
fournissent des pistes à vérifier, jamais des preuves d'exécution.

Le modèle comporte encore des phrases périmées sur la mer, les mineurs et
le bourg. Pour dire ce qui tourne, l'inventaire vérifie le code et ses
effets. Pour dire ce qui est promis, il lit la vision. Il consigne les
contradictions documentaires sans réécrire l'un ou l'autre document.

**Fidélité : sans objet pour ce lot documentaire.** L'inventaire conserve
la distinction du produit entre le niveau 1, les proxies plausibles de
niveau 2 et ce qui n'est pas simulé. Il ne transforme pas une anomalie de
niveau 2 en défaut historique, ni une référence bibliographique citée dans
un commentaire en preuve d'amorçage historique.

### Une matrice de promesses, pas une liste de fichiers

Le livrable est `docs/COHERENCE.md`. Il indique la révision git mesurée,
la version de Python, les dépendances disponibles et les commandes de
rejeu depuis la racine du dépôt. Chaque section de niveau 2 de la vision
est représentée par une ligne littérale `source : <titre de section>`.
Sous cette source, chaque promesse distincte reçoit une ligne de matrice.
Les assertions liminaires de la vision sont examinées séparément, dont
l'amorçage historique et la note de statut sur le rendu.

Colonnes de la matrice :

- identifiant local stable de la promesse et citation courte, repérable
  dans la vision ;
- état : `mesure`, `partiel`, `absent` ou `non_verifie` ;
- chemin et symbole du code qui porte le comportement, ou recherche
  négative bornée s'il manque ;
- référence à une preuve exécutée : commande exacte, résultat, code de
  sortie et portée ;
- ce qui manque, ce que la preuve ne dit pas, et la contradiction éventuelle.

`mesure` exige une observation du comportement décrit, pas la présence d'un
nom. `partiel` nomme précisément la partie exercée et celle qui manque.
`absent` exige une inspection de l'implémentation et une recherche dont les
chemins et les motifs sont écrits ; un simple mot absent ne suffit pas.
`non_verifie` désigne une preuve non jouée ou impossible dans l'environnement,
avec la commande tentée et son erreur. Il ne signifie ni absent ni conforme.

Un test peut servir plusieurs promesses si sa portée le permet ; le rapport
le référence au lieu de recopier son résultat. Un résultat ne se cite pas
sans la révision où il a été mesuré. Aucun pourcentage de « produit fini »
n'est déduit d'un nombre de fichiers, de tests ou de lignes de matrice.

### Les jointures à examiner

L'inventaire doit pouvoir révéler au moins ces types d'écart, sans en
présupposer le verdict :

- monde amorcé historiquement contre densité et stocks paramétriques ;
- hiérarchie conservatrice promise contre cellule agrégée, province et
  bourg dérivés, niveaux inférieurs présents ou absents ;
- économie physique : origine, transport, stockage et destination, avec
  le bassin maritime dans les mesures de masse ;
- déterminisme du monde complet, en sachant que `World.to_dict()` ne
  photographie pas actuellement `stocks_mer` ;
- date, jour saisonnier et régimes d'appel de `tick`, sans assimiler une
  année moyenne à une suite de jours datés ;
- données du monde, snapshot puis tableau de bord : ce qui est effectivement
  exporté, lu, absent ou non calculé, y compris le bourg ;
- causalité simulée contre raccourcis ou absences, puis chacun des piliers
  et domaines de la vision, sans oublier ceux des couches non commencées.

La photographie ne constitue pas une sauvegarde rechargeable si aucune
reprise du moteur n'est démontrée. Une vue dérivée n'est pas une ville avec
des habitants individuels. Un contrôle de rasterisation n'est pas la preuve
qu'une image a été rendue par un GPU : si ce dernier essai manque, le dire.

### Mesurer sans réparer

Réutiliser les tests et interfaces existants. Des sondes courtes en
bibliothèque standard peuvent être écrites dans les blocs exécutables du
rapport ; elles ne s'installent pas dans le moteur ou dans la CI. Elles
dérivent leur échantillon du monde chargé, le refusent vide, et rapportent
le dénominateur avec les écarts. Les essais annuels passent explicitement
le numéro de tick lorsque l'API courante le demande.

Pour chaque défaut réel découvert, le rapport donne une reproduction,
l'invariant concerné et le lot existant qui le couvre si le registre le
nomme. Sinon il indique « aucun lot recensé ». Il n'invente ni numéro de
lot, ni priorité, ni correction. Une recherche documentaire ou un test
impossible reste un constat borné, pas une promesse validée.

Ce lot n'attend pas les propositions de briefs ou de documentation en PR.
Il mesure `master` au démarrage et distingue explicitement les propositions
non fusionnées du produit disponible. Une livraison ultérieure pourra
mettre l'inventaire à jour dans un autre lot ; il ne prédit pas son résultat.

## Périmètre

En écriture : `docs/COHERENCE.md`, pour la matrice, les observations, les
commandes exécutables et leurs résultats rattachés à la révision mesurée.

Tout autre chemin est interdit, nommément : `VISION.md`, `AGENTS.md`,
`sim/MODELE.md`, `docs/WORKFLOW.md`, `atelier.toml`, tout `sim/`, `viewer/`,
`visualisateur/`, `outils/`, `.github/`, `data/`, et les autres briefs.
La fiche 054 est tenue par la commande du registre, dans le périmètre
implicite de la PR de lot ; aucun autre état ni aucune prose de la feuille
de route ne change. Aucun test existant n'est modifié et aucun nouveau
fichier de test n'est créé.

## Conditions de succès

### SC1 — L'inventaire couvre toutes les sections de la vision

Chaque promesse est mise en regard d'une ligne de matrice. Le contrôle
ci-dessous refuse déjà un document vide ou une section oubliée ; la
relecture confronte ensuite chaque phrase et chaque puce de la vision à
ses lignes, car couvrir les titres seuls ne prouve pas l'exhaustivité.

```bash
python3 - <<'PY'
from pathlib import Path
import re
vision = Path('VISION.md').read_text(encoding='utf-8')
rapport = Path('docs/COHERENCE.md').read_text(encoding='utf-8')
titres = re.findall(r'^## (.+)$', vision, re.M)
assert titres, 'vision vide : aucune section à examiner'
absents = [t for t in titres if f'source : {t}' not in rapport.splitlines()]
assert not absents, f'sections non examinées : {absents}'
print('sections couvertes', len(titres) - len(absents), '/', len(titres))
PY
```

Rouge d'abord sur la base sans rapport (`FileNotFoundError`), puis sur une
copie privée du livrable dont une ligne `source :` a été retirée. Aucun
document de référence n'est modifié pour faire passer ce contrôle.

### SC2 — Chaque constat se rejoue sur la révision annoncée

```bash
git rev-parse HEAD
python3 --version
python3 -m pytest sim/tests/ viewer/tests/ -q
python3 -m sim --ticks 0 --seed 0 --json
python3 -m sim --ticks 365 --seed 0 --json
```

Le rapport contient les commandes, leurs sorties utiles et codes de
retour réels. Chaque preuve de la matrice renvoie à une de ces exécutions
ou à une sonde supplémentaire intégralement reproductible. Une suite
verte n'est attribuée qu'aux invariants que ses assertions exercent.
Une erreur est conservée et les promesses concernées restent `non_verifie`.
Si la base avance, rejouer les preuves sur la nouvelle base avant livraison.

### SC3 — Les vues sont comparées à ce qu'elles lisent

```bash
python3 -m pytest sim/tests/test_province.py viewer/tests/test_viewer_v0b.py -q
python3 -m sim --ticks 20 --seed 0 --snapshot-json /tmp/fh-coherence.json
```

Une sonde publiée dans le rapport compare sur ce snapshot les totaux
effectivement lus par `viewer.snapshot_loader.agregats_monde` aux sommes
dérivées des cellules exportées, en nommant les champs comparés. Elle
vérifie que le document contient des cellules et que chaque champ annoncé
mesuré a des contributeurs. Un champ absent est rapporté absent, jamais
mis à zéro. Une copie privée sans cellules doit lever `EchantillonVide`.
Le constat précise quels états du moteur ne sont pas exportés, sans
compléter artificiellement le snapshot pour faire réussir la comparaison.

### SC4 — Le déterminisme ne perd pas la mer de vue

```bash
python3 -m pytest sim/tests/test_determinisme.py -q
```

Le rapport distingue l'empreinte des cellules de la preuve du bassin.
Deux courses de même graine et même suite de numéros de tick sont comparées
sur les cellules **et** `stocks_mer`, avec les ticks effectivement joués
pour dénominateur. Le bassin doit avoir porté une marchandise dans au moins
une observation ; sinon la preuve maritime est vide et échoue. Les
empreintes sont désignées par leur nom, jamais élevées au rang de constante.

### SC5 — Les absences et limites restent visibles

```bash
rg -n '^## |source :|mesure|partiel|absent|non_verifie' docs/COHERENCE.md
rg -n 'class |def |stocks_mer|numero_tick' sim/ viewer/ visualisateur/
```

La relecture rejoue les recherches négatives exactes indiquées pour les
promesses absentes et vérifie les symboles cités pour les autres. Chaque
promesse sans preuve positive conserve sa limite. L'amorçage, les niveaux
sous la cellule, les stocks en mer et les différences entre date et saison
ont chacun un constat explicite. Les observations ne déclarent pas livrés
les changements encore en PR. La source figée de la carte n'est ni
régénérée ni remplacée pour satisfaire une promesse historique.

### SC6 — Le lot n'a fait qu'inventorier

```bash
git diff --name-only origin/master
git diff --exit-code origin/master -- sim/ viewer/ visualisateur/ outils/ data/ VISION.md AGENTS.md sim/MODELE.md atelier.toml .github/
python3 -m atelier feuille valider --projet . --base origin/master
```

La première commande ne nomme que le rapport et la fiche 054 du registre.
La deuxième est vide et retourne zéro. La troisième passe, avec l'atelier
sur le `PYTHONPATH`. Le rapport peut constater des défauts ; sa réussite
signifie qu'ils sont établis et lisibles, pas qu'ils ont été réparés.

## Hors périmètre

- corriger le moteur, les données, les tests, la CI ou la documentation du
  modèle ; l'inventaire dit où est l'écart et comment le reproduire ;
- modifier la vision, décider d'un nouveau mécanisme ou de sa priorité ;
- exécuter les lots 049 à 053, ou recopier leurs promesses comme preuves ;
- bâtir un nouveau harnais, un tableau de bord de conformité ou une suite
  de tests par promesse ;
- produire une recherche historique, calibrer un proxy de niveau 2 ou
  garantir que toutes les couches du jeu sont achevées.
