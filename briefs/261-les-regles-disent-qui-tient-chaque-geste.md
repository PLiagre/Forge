# Brief 261 — Les règles disent qui tient chaque geste

## But

`AGENTS.md` § « Le workflow » et § « Le palier » disent, sans reprendre
aucun autre document, les gestes qui restent au propriétaire et ceux que la
chaîne tient désormais seule.

## Règle du monde

Ce lot porte sur l'atelier, sans changement du monde simulé. Il réalise la
demande #84, et dépend du lot 256 pour que sa propre PR — qui touche
`AGENTS.md` — passe elle aussi par le propriétaire.

Direction du propriétaire, validée le 22 septembre 2026 : ses seuls gestes
deviennent suivre la page de pilotage et proposer des idées par le
formulaire « Demander un lot ». Il fusionne en plus, lui seul, deux choses :
ce qui touche la zone protégée (lot 256) et ce qui n'est pas un lot — une
expérience, une branche à lui. § « Le workflow » dit ces deux gestes et ces
deux fusions ; toute formulation qui compte encore « trois choses » au
propriétaire disparaît.

Une fiche `idee` part au brief à son tour, dans l'ordre du registre, quand
ses dépendances sont livrées et que le nombre de lots en vol reste sous la
borne déclarée dans `atelier.toml` : l'ordre du registre est la manette du
propriétaire, pas une main qui choisit à chaque tour.

Un lot qui échoue deux fois n'est pas rendu seul à `abandonne` : il est
parqué, dans un état dérivé — jamais écrit à la fiche elle-même — et
affiché sur la page de pilotage, en attendant que le propriétaire le
reprenne ou l'abandonne.

§ « Le palier » gagne un second déclencheur, à côté de la couche finie :
une passe d'hygiène, sur des signaux mesurés dont les tolérances sont
déclarées dans `atelier.toml`. Un palier livré compte lui-même comme une
passe d'hygiène.

La liste des chemins protégés n'est, à aucun moment, recopiée en entier :
`AGENTS.md` renvoie à `atelier.toml` § `[integration]`, qui seul en fait
foi pour cette liste.

## Périmètre

En écriture : `AGENTS.md`, sections « Le workflow » et « Le palier »
seulement. La fiche 261 relève du périmètre implicite du lot.

Tout autre chemin est interdit, nommément : tout le code, `docs/`,
`atelier.toml`, `ROADMAP.md` hors de la fiche du lot, et — dans `AGENTS.md`
même — les sections « Les trois principes non négociables » et « Les
treize règles payées par un vrai défaut ».

## Conditions de succès

### SC1 — Les « trois choses » disparaissent de la prose

`grep -c "Trois choses seulement restent au propriétaire" AGENTS.md` rend
`0`.

### SC2 — La liste de la zone protégée n'est jamais recopiée en entier

`AGENTS.md` renvoie à `atelier.toml` § `[integration]` pour la zone
protégée : nommer un chemin isolé pour ce qu'il est (le fichier de
branchement, le module qui pose la revue…) reste possible, mais aucune
phrase de la section ne reproduit la liste complète — sinon la liste vit à
deux endroits, et l'un des deux mentira un jour. Preuve, jouée à la main :

```bash
python3 -c '
import tomllib
zone = tomllib.load(open("atelier.toml", "rb"))["integration"]["zone"]
assert zone, "zone vide : ne prouve rien"
texte = open("AGENTS.md", encoding="utf-8").read()
section = texte.split("## Le workflow", 1)[1].split("## Le brief", 1)[0]
assert not all(chemin in section for chemin in zone), "la liste zone est recopiée en entier"
print("ok")
'
```

Une liste `zone` vide fait échouer la commande ; elle ne passe jamais par
défaut.

### SC3 — Les sections gelées ne bougent pas

`git diff origin/master -- AGENTS.md` ne touche aucune ligne des sections
« Les trois principes non négociables » et « Les treize règles payées par
un vrai défaut ».

### SC4 — Le registre reste cohérent

`python3 -m atelier feuille valider --projet .` passe.

## Hors périmètre

Aucun code : ni `outils/`, ni `atelier/`, ni aucun test. `docs/WORKFLOW.md`
n'est pas touché ici — il change avec chaque lot qui change ce qu'il
décrit, pas avec celui qui l'annonce en premier. Ce lot n'implémente ni le
parcage après deux échecs, ni la borne de lots en vol, ni les tolérances
d'hygiène : ces mécanismes viennent des lots qui dépendent de celui-ci, une
fois la règle écrite.
