# Les tests du jeu

## La règle d'admission

Un test existe s'il protège **l'une de ces trois choses**, et seulement :

1. un **invariant physique** — la masse se conserve, l'adjacence est
   symétrique, une dette ne se rembourse pas plus vite que le surplus ;
2. une **règle de jeu visible** — on ne mange pas deux fois, on a faim,
   puis on meurt ;
3. le **déterminisme** — même graine, même monde.

Un test qui protège une étape de processus, un compteur de coût, une
constante justifiée par un document, ou un mode d'automatisation n'a pas
sa place ici.

Corollaire : **ne pas ajouter un fichier de test par lot.** Un nouveau lot
ajoute ses cas dans le fichier qui porte déjà l'invariant concerné.

## Ce que porte chaque fichier

| fichier | ce qu'il protège |
|---|---|
| `test_survie.py` | faim, dette alimentaire, mortalité, direction du modèle de survie |
| `test_commerce.py` | conservation de la masse, un kg ne nourrit qu'une fois, pas de sur-livraison |
| `test_province.py` | la province est dérivée, jamais stockée |
| `test_determinisme.py` | même graine, même monde ; départage stable des égalités |
| `test_monde.py` | chargement de la carte, ligne de commande, schéma du snapshot |
| `test_no_hardcoded.py` | aucun nombre magique dans le moteur |
| `test_write_coverage.py` | tout champ du modèle est écrit quelque part et lu quelque part |

```bash
py -m pytest sim/tests/ -q
```
