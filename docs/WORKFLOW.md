# Le workflow automatique — schéma et mode d'emploi

> Comment un besoin devient du code fusionné, sans que personne appuie sur un
> bouton. Ce fichier explique la chaîne ; les règles font foi dans
> [AGENTS.md](../AGENTS.md), et l'état des lots dans
> [ROADMAP.md](../ROADMAP.md).

---

## L'idée en une phrase

Le propriétaire donne une direction ; une fiche, un brief, un lot, une
relecture et une intégration font le reste, et **chaque étape peut rougir**.

## Le schéma général

```
   PROPRIÉTAIRE                     LA CHAÎNE                        master
        │                                                              │
        │  « je veux X »                                               │
        └──────────►┌───────────────┐                                  │
                    │  LA FICHE     │  une ligne au registre           │
                    │  ROADMAP.md   │  état : a-briefer                │
                    └───────┬───────┘                                  │
                            │                                          │
                            ▼                                          │
                    ┌───────────────┐  branche brief/NNN-slug          │
                    │  LE BRIEFER   │  écrit briefs/NNN-slug.md        │
                    │   (Claude)    │  cinq sections, un périmètre     │
                    └───────┬───────┘                                  │
                            │  PR ─────► contrôles ─► relecture ───────┤
                            │                                     fiche → pret
                            ▼                                          │
                    ┌───────────────┐  branche agent/NNN-slug          │
                    │   LE CODER    │  exécute le brief, et lui seul   │
                    │   (Cursor)    │  n'écrit que dans le périmètre   │
                    └───────┬───────┘                                  │
                            │  PR                                      │
                            ▼                                          │
                    ┌───────────────┐                                  │
                    │ LES CONTRÔLES │  sim · vues · forge · outils     │
                    │     (CI)      │  feuille · gitleaks              │
                    └───────┬───────┘                                  │
                            ▼                                          │
                    ┌───────────────┐  jamais l'auteur                 │
                    │ LA RELECTURE  │  sur la révision courante        │
                    │   (Claude)    │  quatre refus possibles          │
                    └───────┬───────┘                                  │
                            ▼                                          │
                    ┌───────────────┐  une PR à la fois                │
                    │ L'INTÉGRATION │  rejouée sur le dernier master   │
                    │  (GitHub)     │  ne lit ni brief ni diff         │
                    └───────┬───────┘                                  │
                            │  fusion ─────────────────────────────────►
                            ▼                                     fiche → livre
                    ┌───────────────┐
                    │   LE PALIER   │  quand une fusion finit une couche,
                    │               │  une fiche de stabilisation entre
                    └───────────────┘  en tête du registre
```

## Qui fait quoi, et ce qu'il ne fait pas

| acteur | fait | ne fait **jamais** |
|---|---|---|
| **propriétaire** | donne des directions, reprend ce qui tombe | fusionner un lot |
| **ForgeAtelier** | lit le registre, distribue les cartes, cadence, isole les worktrees | écrire du code, juger, fusionner |
| **le briefer** (Claude) | écrit le brief et ses critères ; relit en lecture seule | exécuter le lot, fusionner |
| **le coder** (Cursor) | planifie et exécute un lot dans `agent/*` | prononcer un verdict, fusionner |
| **la CI** | joue les contrôles déclarés | décider d'entrer |
| **le relecteur** | approuve ou refuse sur la révision courante, par une revue GitHub signée d'un second compte | relire son propre code |
| **l'intégration** | fusionne quand les conditions sont réunies | lire le brief, le diff ou un compte rendu |
| **le worker Unity** | joue l'EditMode sur le SHA exact, quand un lot touche `unity/` | fusionner, juger le PlayMode graphique |

## La coupure qui porte : décider ≠ faire

C'est la leçon la plus chère du dépôt, et elle est écrite dans l'arbre.

```
   outils/                          .github/scripts/
   ────────                         ────────────────
   DÉCIDE                           FAIT le geste
   ne touche jamais GitHub          appelle l'API
   rejouable hors ligne             rejouable sur un banc,
                                    avec de faux exécutables

                    ▲                       ▲
                    └───────────┬───────────┘
                                │
                        .github/workflows/
                        ne portent aucune logique :
                        ils appellent l'un, puis l'autre
```

Sans cette coupure, un travail de relecture qui tourne **sur le code de la PR**
juge avec du code que la PR peut changer — et rien n'est plus facile à écrire
qu'un juge complaisant. C'est pourquoi la règle de relecture est appliquée deux
fois, par le même module, depuis deux endroits qui ne se valent pas : la CI la
joue pour rendre la PR lisible ; **l'intégration la rejoue depuis le code de
`master`, et c'est celle-là qui ouvre la porte.**

## Les six états d'une fiche

L'état d'un lot ne s'écrit **qu'à un seul endroit** : sa fiche au registre.

| état | ce que ça veut dire | qui l'écrit |
|---|---|---|
| `idee` | recensé et placé dans l'ordre, sans brief | le propriétaire |
| `a-briefer` | on veut le brief maintenant | le propriétaire, ou l'intégration quand une couche s'achève |
| `pret` | le brief est sur `master` et passe la porte | la PR du brief |
| `livre` | la PR du lot est fusionnée ; la fiche porte son numéro | la PR du lot |
| `abandonne` | on n'y va pas, ou plus. La fiche reste, avec une note | le propriétaire |
| `archive` | livré avant le dégraissage ; le brief vit au tag | personne, plus jamais |

```
  —          → a-briefer     l'intégration, quand une fusion finit une couche
  idee       → a-briefer     le propriétaire
  idee       → pret          le propriétaire, s'il écrit le brief lui-même
  a-briefer  → pret          la PR du brief
  pret       → livre         la PR du lot
  pret       → a-briefer     le propriétaire, si le brief est à réécrire ;
                             l'ancien brief part dans la même PR
  *          → abandonne     le propriétaire (sauf livre et archive)
  abandonne  → idee          le propriétaire
```

Toute autre transition est **refusée par la CI**. Un lot n'entre jamais dans le
registre déjà livré, et une fiche ne s'efface pas : elle passe à `abandonne`.

Tout ce qui est *entre* ces états — en file, en planification, en relecture, à
fusionner, bloqué, en échec — ne s'écrit pas : ça se **dérive** des cartes, des
verrous et des briefs.

## Ce qui ouvre la porte de `master`

Une PR entre quand **tous** les contrôles déclarés sont verts **sur sa révision
courante**, et qu'un tiers l'a approuvée **sur cette même révision**. À ces
conditions, et à elles seules.

```
contrôles déclarés :  sim · vues · forge · outils · atelier · feuille · gitleaks
branches intégrées :  agent/   brief/   feuille/
```

Trois pièges, chacun payé par un vrai défaut :

- **un contrôle absent n'est pas un contrôle vert** ; un état de fusion inconnu
  retient au lieu de passer ;
- **deux PR vertes séparément ne sont pas une PR verte ensemble** — une PR en
  retard sur `master` est d'abord rejouée dessus ;
- **ce qui n'a pas de préfixe déclaré n'est pas intégré** : une branche
  d'expérience qui passe au vert n'est pas un lot, et elle attend le
  propriétaire.

## Le brief : un fichier, cinq sections

C'est la **seule** source d'instruction d'un lot. Aucun autre document ne le
paraphrase — ni la fiche, ni la roadmap, ni une conversation.

```
# Brief NNN — titre

## But                  une phrase : ce que le monde saura faire après
## Règle du monde       comment ça marche, en termes de monde — jamais
                        en termes de gameplay
## Périmètre            les fichiers autorisés en écriture, rien d'autre
## Conditions de succès SC1…SCn ; chacune nomme une commande qui peut échouer
## Hors périmètre       ce que ce lot ne fait pas
```

Le périmètre n'est pas décoratif : l'atelier y lit les fichiers pour **poser un
verrou**. Deux lots ne se marchent jamais dessus.

## Le palier

Quand une fusion finit une couche, une fiche de stabilisation entre **en tête
du registre** — parce que l'ordre est la priorité, et qu'un palier passe avant
les lots qui attendent : c'est lui qui dit si ce qui vient d'être livré tient
debout. Son brief s'appelle `briefs/NNN-stabilisation-couche-N.md`, et c'est à
ce nom seul que la machine le reconnaît.

## Quand ça casse

| symptôme | ce que ça veut dire | le geste |
|---|---|---|
| carte dans `echec/` | un agent est tombé (code de retour, délai, brief introuvable) | lire la raison, corriger, `atelier reprendre` |
| lot immobile | dépendance non livrée, ou fichier tenu par un verrou | `feuille etat` dit par qui ; `atelier lever` après la fusion |
| PR fermée sans fusion | le lot est à décider | ranger la carte, rendre le verrou, choisir `pret` ou `abandonne` |
| carte dans `echec/`, cause `relecture` | le relecteur a demandé des changements sur la PR, ou n'a posé aucune revue | lire la revue sur la PR ; fermer la PR et `atelier reprendre`, ou repasser la fiche à `a-briefer` par le travail `etat-lot` |
| CI de feuille rouge | brief orphelin, fiche sans brief, dépendance fantôme | `atelier feuille valider` le nomme ; rien ne part tant que ce n'est pas réparé |
| tours à vide répétés | la chaîne est arrêtée et le dit dans son journal | la page de pilotage alerte au-delà de 10 tours |

**Rien ne se relance tout seul.** Un agent tombé reste tombé jusqu'à ce que
quelqu'un lise pourquoi.

## Les deux gestes qui ne sont pas du code

Ils se posent une fois, dans les options du dépôt, et la chaîne n'est pas
complète sans eux :

1. **la protection de `master`** — les contrôles déclarés obligatoires, et
   `enforce_admins`. Sans elle l'intégration reste correcte, mais rien
   n'empêche une main de fusionner du rouge. C'est déjà arrivé.
2. **Pages → Source : GitHub Actions** — pour que la page de pilotage soit
   publiée. Sans lui elle est réécrite à chaque tour et reste en pièce jointe.

## Le journal de ce qui a vraiment tourné

Un mécanisme joué sur un banc n'est pas un mécanisme qui a tourné. Ce qui
suit a été mesuré en ligne :

- **le tour à vide est juste** — l'intégration s'est réveillée, a lu les PR
  ouvertes, a écarté le brouillon et le hors-préfixe, et a dit `RIEN` ;
- **la chaîne peut s'arrêter en silence** — quarante réveils, quarante `RIEN`,
  trois bons de travail qui attendaient sans qu'aucun contrôle de relecture
  n'existe sur leur révision. Deux jours perdus. C'est ce que la page de
  pilotage existe pour montrer ;
- **quatre impasses n'ont été trouvées que par une relecture humaine**, parce
  qu'elles ne se voient qu'en ligne : un commit signé d'une adresse que GitHub
  ne relie à personne, un verdict calculé depuis le code de la PR jugée, des
  contrôles épinglés sur l'ancienne révision, une branche de palier restée
  d'une PR fermée qui bloquait sa couche pour toujours ;
- **jamais joué en ligne** : la fusion elle-même, le rejeu d'une PR en retard,
  le dépôt d'un palier. Le premier lot qui passera le cycle entier est ce qui
  les mesurera. C'est le lot 103, et c'est la dernière chose que la V1 doit
  encore à sa promesse « une chaîne verte de bout en bout ».
