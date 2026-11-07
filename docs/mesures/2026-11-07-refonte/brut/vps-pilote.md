# La chaîne d'agents vue du journal du pilote (VPS) — 7 novembre 2026

Lecture seule : `ssh hermes-boost 'cat …'` (journal.jsonl, logs/pilote.log) et `gh` en lecture (liste des issues `lot` + timelines GraphQL par 20 issues, aucune tronquée).
Scripts : `scripts/vps_pilote_collecte.py` (rapatriement) et `scripts/vps_pilote.py` (tous les chiffres ; sortie complète dans `brut/vps-pilote-rapport.txt`, chiffres structurés dans `brut/vps-pilote.json`).
Historique : `pilote.log` remonte au 15 sept. 2026 (6,7 Mo, aucune rotation : pas de `.1` ni `.gz`) ; `journal.jsonl` au 27 sept. (23 656 entrées). Les deux fenêtres demandées sont donc entières : depuis le 1er oct (241 lots fusionnés) et depuis le 28 oct (70 lots).

## Ce que le journal contient, et ne contient pas
- Une entrée par évènement (`brief écrit`, `codeur : code`, `relecture ACCEPTE/CORRIGER`, `livré`, `bloqué`, `secours`, `attente`, `attendre_ci`, `attendre_pc`…), datée, avec le modèle quand un agent a répondu. **Aucune durée d'appel, aucune date de passage à `pret`.**
- `pilote.log` : un en-tête par tour (toutes les 2 min, 720 par jour) ; les lignes du tour sont écrites à sa fin. Les tours se chevauchent (un appel d'agent dure bien plus de 2 min) : les lignes d'un tour long apparaissent sous les en-têtes suivants.
- Date de `pret` = évènement « étiquette `pret` posée » de la timeline GitHub ; `en-cours` = étiquette posée à l'écriture du brief ; fusion = fermeture de l'issue.

## 1. De `pret` à la fusion (241 lots depuis le 1er oct ; 70 depuis le 28 oct)
Heures (script, section 1).

| | Q1 | médiane | Q3 | p90 | max |
|---|---|---|---|---|---|
| depuis 1er oct, `pret` → fusion | 3,1 | **9,9** | 54,3 | 124,6 | 505 |
| depuis 28 oct, `pret` → fusion | 6,0 | **16,1** | 28,3 | 159,2 | 505 |
| depuis 1er oct, `pret` « effectif » (dépendances `Dépend de #…` fermées) → fusion | 1,4 | **3,4** | 16,7 | 38,8 | 260 |
| depuis 28 oct, `pret` effectif → fusion | 1,9 | **5,4** | 18,4 | 79,7 | 255 |
| depuis 1er oct, `en-cours` (brief écrit) → fusion | 1,0 | **1,37** | 3,2 | 16,7 | 256 |
| depuis 28 oct, `en-cours` → fusion | 0,9 | **1,15** | 3,4 | 14,8 | 166 |

- Lots VPS / PC (depuis 1er oct) : `en-cours` → fusion médiane 1,43 h / 1,34 h.
- Une fois le brief écrit, un lot se fusionne en un peu plus d'une heure. **L'essentiel du délai est avant le chef** : médiane `pret` effectif → brief 0,29 h (Q3 4,2 h, p90 21 h), 1,9 h depuis le 28 oct. Ce délai mêle file (capacité de la machine, fenêtre de jalons, `reserve`), quota du chef et exécution du chef. Attente de quota du chef seule : 25 h cumulées sur 241 lots (21 h depuis le 28 oct) ; le chef lui-même dure ≈ 5 min (section 2). Le reste, ≈ 2 095 h cumulées (50 % de la somme des durées), est de la file que le journal ne détaille pas.
- Décomposition cumulée `pret` effectif → fusion, 241 lots : avant le chef ≈ 2 120 h (50 %) ; lots bloqués, en attente du propriétaire ou du dépanneur, 1 017 h (24 %) pour seulement 39 lots (médiane 9,9 h, max 201 h) ; relecture (de l'étape précédente au verdict) 271 h d'agent+latence, 202 h de CI (`attendre_ci` × 2 min), 181 h de quota/session, 181 h où le travail est sur le PC (`attendre_pc`) ; codeur 62 h ; corrections 26 h + 13 h de CI ; fusion après ACCEPTE : médiane 1 min.
- Par lot qui traverse la phase (depuis 1er oct) : codeur médiane 0,43 h (Q3 0,71) ; correction 1,15 h (n=26) ; relecture, CI et travail du PC compris, 1,0 h (Q3 1,9 ; p90 4,5).
- Depuis le 28 oct, le quota/session pèse plus dans la relecture : 175 h cumulées sur 70 lots (150 min par lot), presque autant que sur les 241 lots depuis le 1er oct (181 h).

## 2. Appels d'agents par rôle et par modèle (journalisés)
1 071 appels depuis le 1er oct, 266 depuis le 28 oct. Durée = heure de l'évènement − début du tour qui l'a porté (voir doutes), plafonnée à 4 h : la médiane est robuste, le total est indicatif. Détail complet dans `vps-pilote.json` (`appels`, `appels_par_semaine`).

| rôle · modèle (depuis 1er oct) | appels (échecs/vides) | durée médiane | total estimé |
|---|---|---|---|
| chef · claude opus-5-5 | 194 (36) | 5,7 min | 27 h |
| chef · codex gpt-6.1-sol | 74 (0) | 4,5 min | 7 h |
| chef (découpe) · opus-5-5 | 61 | 3,8 min | 5 h |
| codeur · codex gpt-6.1-sol | 167 (47) | 14,2 min | 54 h |
| codeur · cursor grok-4.7 | 35 (8) | 16,2 min | 13 h |
| codeur · claude sonnet-5-5 | 22 (0) | 9,7 min | 4,3 h |
| renfort (3 modèles) | 12 | 12 à 14 min | 3,8 h |
| relecteur · claude opus-5-5 | 126 (11) | 4,2 min | 20 h |
| relecteur · codex gpt-6.1-sol | 129 (0) | 2,7 min | 10 h |
| relecteur · cursor grok-4.7 | 104 (7) | 11,0 min | 19 h |
| relecteur · cursor gpt-5.6-sol | 29 (12) | 3,0 min | 2,5 h |
| dépanneur (4 modèles) | 31 (4) | 1 à 5 min | 3,8 h |
| mécanicien (master rouge, 3 modèles) | 41 (19) | 3 à 42 min | 12 h |
| résolveur de conflits | 17 | 4,5 à 12,6 min | 2,6 h |

- Depuis le 28 oct : chef opus 65 appels (5,2 min), codeur sonnet 22 (9,7 min), codeur grok 14, relecteur opus 26, grok 43, cursor gpt-5.6-sol 29 (12 échecs), composer 10 ; aucun appel codex.
- Par semaine (lundi) : 28/9 120 appels ; 5/10 282 ; 12/10 209 ; 19/10 190 ; 26/10 212 ; 2/11 58 (semaine en cours). Heures d'agent estimées : 35, 60, 35, 23, 26, 8,5, soit ≈ 187 h au total, hors PC.
- Le codeur 3D du PC est presque absent du journal (14 `codeur_3d` pour 119 lots passés par `attendre_pc`) : voir doutes.
- Chroniqueur et boussole ne passent pas par ce journal (`journal.log`, `boussole.log`) : non mesurés ici.

## 3. Attentes
Unité : un « tour » dure 2 min ; heures = tours distincts × 2 min (les lots simultanés d'un même tour ne comptent qu'une fois). Une attente = aucun agent possible pour le rôle.
**Depuis le 1er oct : 7 453 entrées, 6 514 tours ≈ 217 h. Depuis le 28 oct : 3 344 entrées, 2 408 tours ≈ 80 h.**

| cause (depuis 1er oct) | tours | heures |
|---|---|---|
| claude opus-5-5 · session expirée ou absente | 4 119 | 137,3 |
| claude opus-5-5 · quota épuisé (limite des 5 h) | 1 405 | 46,8 |
| cursor gpt-5.6-sol · quota épuisé | 1 116 | 37,2 |
| codex gpt-6.1-sol · quota épuisé | 374 | 12,5 |
| claude sonnet-5-5 · quota épuisé | 113 | 3,8 |
| codex « occupé », grok « ne démarre pas », autres | moins de 40 | ≈ 1 |

- Rôles bloqués : relecteur 5 659 tours, chef 913, dépanneur 51.
- **La plus grosse panne : session Claude expirée du 22/10 vers 21 h 53 au 28/10 vers 10 h 45, soit ≈ 145 h d'un seul tenant** (`claude.token` renouvelé le 28/10 à 09:50 ; le journal ne la coupe en deux qu'à la limite de la fenêtre du 28 oct). Lots fusionnés ces jours-là : 22/10 21, 23/10 0, 24/10 0, 25/10 0, 26/10 3, 27/10 0 ; ailleurs 10 à 20 par jour.
- Quota Claude depuis le 28 oct : 14 épisodes, 70 h cumulées, médiane 3,4 h ; les plus longs : 15,6 h le 29/10 dès 02 h 57, 15,4 h le 29/10 dès 18 h 53, 6,7 h le 28/10 dès 19 h 59, 3,8 h le 06/11, 3,5 h le 06/11. Heures de tours sans agent possible, par jour : 28/10 4 h de quota (+ 10,8 h de session), 29/10 23 h, 30/10 10,3 h, 1/11 4,6 h, 2/11 5,4 h, 5/11 8,5 h, 6/11 13,7 h.
- Quota cursor gpt-5.6-sol : 1 116 tours (37 h), tous depuis le 28 oct, comme relecteur de secours. Quota codex : 374 tours, aucun depuis le 28 oct.
- Attentes qui ne sont pas des pannes : `attendre_ci` 5 306 tours distincts (≈ 177 h, 244 lots), `attendre_pc` 6 061 tours (≈ 202 h, 119 lots ; 1 650 tours et 43 lots depuis le 28 oct), `attendre_fusion` 10. **« PC en pause » : 0 mention** dans le journal ; « outil plein » (`occupé`) : 28 tours codex, ≈ 1 h en tout.

## 4. Ce qui frappe en plus
1. **Relecture : 33 % de CORRIGER depuis le 1er oct** (119 CORRIGER contre 247 ACCEPTE), 23 % depuis le 28 oct (21 sur 92). 172 lots sur 241 sont fusionnés sans CORRIGER ; 45 après un, 13 après deux, 8 après trois, 3 après 4, 5 ou 8. Chaque CORRIGER ajoute ≈ 1,15 h (correction, CI, nouvelle relecture).
2. **Les blocages coûtent le plus de temps par lot** : 131 entrées `bloqué` sur 81 lots ; raisons : 22 CI rouge après N corrections, 18 CORRIGER après N corrections, 13 chef échoué, 8 relecteur échoué deux fois sur la même révision, 7 codeur échoué 3 fois. Les 39 lots fusionnés après un blocage ont attendu 9,9 h (médiane), 32 h (Q3), 201 h (max) avant la reprise.
3. **Délais d'appel** : 63 appels coupés (code 124) depuis le 1er oct : chef 30, codeur 25, relecteur 4, mécanicien 2, dépanneur 2 ; 7 depuis le 28 oct, tous des chefs opus. Chef opus en échec : 36 fois sur 194 appels (19 %). Codeur codex : 47 échecs ou vides sur 167 appels (28 %, dont 28 « sans changement »). Mécanicien cursor composer : 8 échecs sur 9 appels, jusqu'à 60 min chacun.
4. **Tours vides et rebonds** : sur 26 938 tours depuis le 1er oct, 33 % `RIEN` et 4 % avec un appel d'agent ; depuis le 28 oct 44 % `RIEN`. 279 `secours` (le premier agent du rôle a refusé : quota, session) sur 133 lots. 639 tours à code de sortie non nul depuis le 1er oct (dont la panne `git worktree` du 15 oct), 20 depuis le 28 oct.
5. Découpes : 69 lots découpés par le chef (61 par opus), soit plus d'un lot sur quatre. Les sous-lots forment des chaînes de dépendances : c'est ce qui rend le `pret` brut trompeur (médiane 9,9 h) face au `pret` effectif (3,4 h).

## Ce qui reste douteux
- Les durées d'appel sont **estimées** (heure de l'évènement − début du tour). Le log est écrit à la fin du tour et les tours se chevauchent : j'ai relié chaque bloc de sortie à un en-tête par une heuristique (appel d'agent : plus ancien tour encore ouvert). Contrôle indépendant : brief → `codeur : code` sur 96 lots VPS sans attente intercalée = médiane 13 min (sonnet) et 21 min (codex), soit quelques minutes de plus que l'appel estimé (9,7 et 14,2 min : latence jusqu'au tour suivant, git).
- Le travail du codeur 3D sur le PC n'est pas journalisé comme appel : son temps apparaît sous « relecture / PC au travail ». Aucune durée de l'agent du PC n'est écrite côté VPS.
- `pret` = première pose de l'étiquette ; une remise à `pret` après blocage n'est pas retenue (le lot compte alors dans « bloqué »). `pret` effectif ne tient compte que des lignes « Dépend de #… » du corps de l'issue ; capacité de machine, fenêtre de jalons et `reserve` ne sont pas séparées du chef (« file + chef » est un reste).
- Les heures d'attente sont des tours de 2 min comptés, bornes à 2 min près. Une raison d'attente liste chaque candidat ; j'attribue l'attente à tout candidat non « écarté », donc quand claude et cursor sont en quota ensemble les deux sont comptés (les heures par modèle ne s'additionnent pas).
- Un appel qui n'a produit aucune entrée (agent tué, tour mort) n'est pas vu : les taux de succès sont optimistes.
