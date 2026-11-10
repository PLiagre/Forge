# Lot #1046 — Affermir sa concorde ou asseoir son droit depuis le panneau
Jalon : J6 · Machine : pc · Taille prévue : 1400 lignes

## But
À côté du feuillet « Le pays », un panneau « Gestes des jauges » montre chaque geste du pays avec son prix en points, son effet et la raison de son refus servie par `/pays`. Le geste confirmé dépose `depenser_jauge` par `POST /intention`, et un refus du service s'affiche avec sa raison dans l'état « × Demande refusée » du socle.

## Le joueur
Le joueur ouvre « Le pays » par l'icône couronne. À droite du feuillet, il lit ses deux gestes :
- « Asseoir le droit » : 30 points de Sceau, pour +10 points de Droit ;
- « Affermir la concorde » : 50 points de Plume, pour +1 point de Concorde.

Chaque geste dit ce qu'il a en réserve et où en est la jauge. Si le geste ne se paie pas, le panneau le dit avant tout clic, avec la raison du monde : « Refusé d'avance : pas assez de points de Plume : 50 points demandés, 35 points disponibles ». Il choisit un geste, relit son prix, puis le confirme. Le reçu lui dit que le monde paie au jour suivant. S'il insiste le même jour sans avoir de quoi payer, le monde refuse, et le panneau le dit : « × Demande refusée », puis la raison en points.

Il sent le coût de chaque geste. Son Sceau payé aujourd'hui lui manquera demain. C'est la décision du jalon 6 (`CAP.md`) : « quand dépenser sa Plume pour affermir la concorde ». Et l'écran du jalon : la barre « lui montre ses quatre jauges […] qu'il dépense en gestes ». Le geste du panneau passe par le chemin de l'IA et de la main : il donne le même monde (décision 38).

## Règle du monde
Les règles ne changent pas. Seuls les mots changent : `jeu/sim/MODELE.md`, « Le pays et ses jauges », point « Les gestes ». Un geste coûte et fait ce que disent les données (`data/jauges.toml`, niveau 2, sans changement). Le dépôt refuse, avec sa raison, des points insuffisants (les gestes déjà déposés pour le tick comptés) ou une jauge déjà à sa borne.

Ce lot récrit ces deux raisons en points, au dixième, avec une virgule. `TexteDuMonde.SansUnite` refusait « 50 demandés, 0 disponibles », et le panneau aurait dû les taire :
- `pas assez de points de <Plume|Sceau|Épée> : <P(coût)> demandé(s), <P(reste)> disponible(s)` ;
- `<Concorde|Renom|Droit> déjà à sa borne : <P(valeur)>`.

`P(v)` écrit comme `TexteDuMonde.Points` :
- arrondi au dixième, la moitié loin de zéro ;
- virgule décimale, sans `,0` final, sans séparateur de milliers, et jamais `-0` ;
- `point` sous 2 en valeur absolue, `points` au-delà.

Le participe s'accorde de la même façon : `demandé`, `disponible` sous 2, puis `demandés`, `disponibles`. Exemples : `0 point disponible`, `1,5 point disponible`, `35 points disponibles`, `30 points demandés`. Les refus « maison inconnue » et « geste inconnu » ne changent pas.

Le point « Les gestes » de MODELE.md gagne une phrase : elle donne ces deux formes, avec un exemple chacune, et dit que le panneau du pays dépose ce même geste.

## Périmètre
jeu/sim/jauges.py
jeu/sim/MODELE.md
jeu/sim/tests/test_pays_et_jauges.py
3d/unity/Assets/ForgeLocal3D/Pont/ClientPays.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPaysTests.cs
3d/unity/Assets/Interface/GestesDesJauges.cs
3d/unity/Assets/Interface/GestesDesJauges.cs.meta
3d/unity/Assets/Interface/Feuillet.cs
3d/unity/Assets/Interface/DossierPays.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/LecturePartie.cs
3d/unity/Assets/Interface/Tests/GestesDesJaugesTests.cs
3d/unity/Assets/Interface/Tests/GestesDesJaugesTests.cs.meta
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/Interface/Tests/LecturePartieTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1046.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1046.cs.meta
docs/briefs/1046-affermir-sa-concorde-ou-asseoir-son-droit-depuis.md

Tout autre chemin est interdit, en particulier :
- `jeu/sim/service.py`, `jeu/sim/intentions.py`, `jeu/sim/ia.py`, `jeu/data/jauges.toml`, et les autres tests Python ;
- `OrdreConfirme.cs`, `CommandesMaison.cs`, `EtatsLecture.cs`, `SocleInterface.cs`, `BarreDuPays.cs`, `TexteDuMonde.cs`, `ClientIntention.cs` ;
- les scénarios `Lot549`, `Lot690`, `Lot944`, `Lot1004`, `Lot1032`, `Lot1045`.

Chaque `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master 1c5cb709 (#1045 fusionné). Il ne dépend d'aucun lot ouvert.

**`jeu/sim/jauges.py`.** Deux fonctions privées neuves :
- `_points(valeur)` rend `P(v)` ;
- `_accord(valeur, mot)` rend `mot`, ou `mot + "s"` à partir de 2.

`verifier_geste` écrit avec elles les deux raisons de la section « Règle du monde ». Rien d'autre ne change : ni l'ordre des contrôles, ni les gestes engagés, ni `document_des_jauges`. Celui-ci sert `refus` par `verifier_geste`, donc dans les mêmes mots.

**`ClientPays.cs`** (espace `Forge.Pont`). `Lire`, `LireTerres`, `PaysLu`, `TerresDuPays` et le témoin `Temoin` ne changent pas. Deux classes neuves, en lecture seule :
- `GesteLu` :
  - `Id`, `Nom` ;
  - `Cout` (`IReadOnlyDictionary<string, double>`, réserve → points) ;
  - `Effet` (`IReadOnlyDictionary<string, double>`, jauge → écart) ;
  - `Refus` : un texte, ou nul ;
- `GestesDuPays` : `Pays` (`PaysLu`), `Gestes` (`IReadOnlyList<GesteLu>`, dans l'ordre servi), `MaisonId` et `Tick`, ceux de `Pays`.

`LireGestes(string id)` lit `GET /pays?maison=<id échappé>` par le même `ServiceLocal`. Il lit le pays comme `Lire`, par la même fonction, puis `jauges.gestes`. Une faute refuse toute la réponse, et l'absence nomme la clé fautive. Il refuse :
- `jauges.gestes` absent, qui n'est pas un objet, ou vide ;
- un geste qui n'est pas un objet ;
- un `nom` qui n'est pas un texte non vide ;
- un `cout` vide, dont une clé n'est pas une réserve de `jauges.points`, ou dont une valeur n'est pas finie et > 0 ;
- un `effet` vide, dont une clé n'est pas une jauge de `jauges.jauges`, ou dont une valeur n'est pas finie et non nulle ;
- une clé `refus` absente, ou qui n'est ni nulle ni un texte non vide.

**`LecturePartie.cs`** gagne :
- un 8ᵉ paramètre optionnel `Func<string, Lecture<GestesDuPays>> gestes = null`, et `Gestes { get; private set; }` ;
- la lecture des gestes au même passage, juste après les terres, seulement avec une maison du joueur. Elle est remise à nul avec elles dans le `catch` ;
- dans `Locale(port)` : `id => { using var c = new ClientPays(port, TimeSpan.FromSeconds(10)); return c.LireGestes(id); }`.

**`Feuillet.cs`** gagne `public RectTransform Cadre => cadre;`. **`DossierPays.cs`** gagne `public RectTransform Cadre => feuillet.Cadre;`. Rien d'autre ne change dans ces deux fichiers.

**`CabinetDeCarte.cs`**, juste après `DossierPays` (gardé dans une variable) :
`gameObject.AddComponent<GestesDesJauges>().Initialiser(pays.Cadre, () => Partie.Monde, () => Partie.Gestes, OrdreConfirme.Local(carte.port))`.

**`GestesDesJauges.cs`** (espace `Forge.Interface`) est un `MonoBehaviour`, dans le style de `CommandesMaison`.

Ses constantes : `TITRE = "Gestes des jauges"`, `CONFIRMER = "Confirmer le geste"`, `RETOUR = "Retour aux gestes"`.

`Initialiser(RectTransform cadre, Func<Lecture<MondeAvecMaisonLu>> monde, Func<Lecture<GestesDuPays>> gestes, OrdreConfirme ordre)` pose son panneau dans le cadre du feuillet, à sa droite : `SocleInterface.Panneau(cadre, TITRE, 764, 0, 500, 640)`. Il s'ouvre et se ferme donc avec le feuillet. Sur la toile de 1920 × 1080, il va de x 788 à 1288 et de y 124 à 764, sans toucher « Votre maison » (x 1312). Son contenu, en x 24, sur 452 de large :
- l'**état** en y 88 ;
- pour le i-ième geste servi (i = 0, 1) : son **texte** en y 124 + 172 i, de 116 de haut, et son **bouton** en y 240 + 172 i, de 452 × 44. Le bouton porte le nom du geste, et la phrase `<nom> : prépare ce geste sans le payer ; « Confirmer le geste » le paie.` ;
- le **message** en y 468, de 96 de haut ;
- `Retour aux gestes` en (24, 572) et `Confirmer le geste` en (256, 572), chacun de 220 × 44. `Confirmer le geste` porte `MatieresCabinet.Engagement`.

Les phrases de `Retour aux gestes` et `Confirmer le geste` disent ce que fait chaque bouton. Tous les `Text` ont `supportRichText = false`. Les gestes au-delà de deux, que les données n'ont pas, ne se montrent pas : le panneau l'écrit au journal. Un geste servi en moins cache sa ligne.

Ses accesseurs publics : `Panneau`, `Ordre`, `EtatAffiche`, `MessageAffiche`, `TexteDuGeste(string id)`, `BoutonDuGeste(string id)`, `BoutonConfirmer`, `BoutonRetour`. `LateUpdate` appelle `Pas()`, qui récrit tout à chaque image, dans l'ordre de `DossierPays.Decrire`. L'état :
1. **monde nul** : `Lecture des gestes…` ;
2. **monde absent** : `Gestes indisponibles : <TexteDuMonde.Absence(raison)>` ;
3. **pas de maison du joueur** : `Choisissez une maison pour dépenser ses points.` ;
4. **gestes nuls, ou d'une autre maison, ou d'un autre tick que le monde lu** : `Gestes en attente du monde` ;
5. **gestes absents** : `Gestes indisponibles : <TexteDuMonde.Absence(raison, id)>` ;
6. **sinon** : `<nom servi du pays> · relevé au <TexteDuMonde.Date(date)>`.

Dans les états 1 à 5, les textes des gestes sont vides et aucun bouton de geste n'est actif.

**Le texte d'un geste** : `public static string Geste(GesteLu g, PaysLu p)`, quatre lignes séparées par `\n` :

```
<nom>
Prix : <Points(coût)> de <nom des points> (en réserve : <Points(valeur des points)>)
Effet : +<Points(écart)> de <nom de la jauge> (aujourd'hui : <Points(valeur de la jauge)>)
Payable aujourd'hui
```

Quand le geste a plusieurs coûts ou plusieurs effets, ils se joignent par ` et `, dans l'ordre des clés. Un écart négatif s'écrit sans `+`. La quatrième ligne est `Refusé d'avance : <Raison(refus, maison)>` quand `Refus` n'est pas nul. `Points` est `TexteDuMonde.Points`.

`public static string Raison(string raison, string maison)` rend la raison telle quelle, si elle passe `TexteDuMonde.Interdit(raison, maison)` et `SansUnite`. Sinon, elle rend `raison illisible, gardée au journal`, et l'écrit au journal par `Debug.Log`.

**Le geste.** `public static string Intention(string maison, string geste)` rend `JsonUtility.ToJson` d'une classe `[Serializable]` qui déclare `type = "depenser_jauge"`, `maison` et `geste`, dans cet ordre. Pour Bar, cela donne exactement `{"type":"depenser_jauge","maison":"seigneurie-1","geste":"asseoir_le_droit"}`.

Le bouton d'un geste est actif seulement si quatre conditions tiennent :
- l'état est le 6 ;
- `Refus` est nul ;
- aucun brouillon ni reçu n'est en cours ;
- aucun envoi n'est en cours.

Son clic appelle `Ordre.Preparer(Intention(maison, id), résumé)`. Le résumé est `<nom> : <Points(coût)> de <points> pour +<Points(écart)> de <jauge>. Confirmez pour payer.`

`Confirmer le geste` n'est visible qu'avec un brouillon sans reçu. Il est actif hors envoi, à l'état 6, sur la maison du brouillon, et appelle `Ordre.Confirmer()`. `Retour aux gestes` est visible avec un brouillon ou un reçu, actif hors envoi, et appelle `Ordre.Recommencer()`.

**Le message** :
- **rien de préparé** : `Choisissez un geste : son prix se paie à la confirmation.` ;
- **brouillon** : le résumé ;
- **envoi en cours** : `Envoi en cours. Attendez le reçu.` ;
- **reçu accepté** : `<nom> : geste reçu au <date>. Le monde le paie au jour suivant.`. La date est celle des gestes lus, si leur tick égale `AppliqueeAuTick`. Sinon, la phrase s'écrit sans `au <date>`. Elle s'écrit une fois, à l'arrivée du reçu ;
- **reçu refusé** : `EtatsLecture.Afficher(message, EtatLecture.Refus, "<nom> : " + Raison(erreur, maison))`, soit `× Demande refusée`, puis la raison sur la ligne suivante, en couleur `alerte` ;
- **reçu absent** : `EtatsLecture.Afficher(message, EtatLecture.Panne, "Envoi non confirmé : " + TexteDuMonde.Absence(absence) + ". Vérifiez le monde avant tout nouveau geste.")`.

Hors de ces deux états, le message reprend la couleur `encre`.

**`Lot1046.cs`** est une `static class Lot1046`, dans le style de `Lot1045`. Ses deux scénarios se jouent dans l'ordre de leur nom, sur le même service. La première faute lève une `InvalidOperationException` qui la nomme.

Le scénario écrit lui-même le texte attendu de chaque geste, d'après le format ci-dessus, depuis sa propre lecture `new ClientPays(port, …).LireGestes(bar)`. Il n'appelle ni `GestesDesJauges.Geste` ni `Raison`. Il clique par `onClick.Invoke()`, et attend par `Lot690.Jusqua` :
- avant un jugement : `Partie.Gestes` présent, de Bar, au tick du monde lu ;
- après un clic sur `Confirmer le geste` : le reçu.

1. **`gestes-1-paye-puis-refuse`.**
   - Il ouvre la carte comme `Lot1045`. Le tick lu doit égaler `-forgeTicks` (210 dans les commandes de la photo).
   - Il choisit le départ dont le siège est « Bar-le-Duc », pousse un tick (211), attend la maison du joueur, puis clique sur l'icône `Le pays`. Le feuillet et le panneau `Gestes des jauges` doivent être actifs.
   - **Jugement R1**, dans une seule image :
     - le texte de chaque geste égale l'attendu ;
     - un bouton est actif si et seulement si son `refus` servi est nul ;
     - le Sceau servi vaut au moins 30, et le refus servi de `asseoir_le_droit` est nul. Sinon : `Bar ne peut pas asseoir son droit : <état servi>` ;
     - chaque texte du panneau passe `Interdit(t, bar)` et `SansUnite`.
   - **Le geste payé.** Il clique sur `Asseoir le droit`, puis sur `Confirmer le geste`. Le reçu doit être accepté, au tick du monde lu. Le message doit commencer par `Asseoir le droit : geste reçu au `.
   - **Le geste refusé.** Il clique sur `Retour aux gestes`. Avec `-forge1046Avance`, il pousse alors un tick et attend le panneau au tick neuf. Il clique de nouveau sur `Asseoir le droit`. Si le bouton est inactif, le scénario échoue : `le panneau refuse d'avance : <ligne 4 du texte>`. Puis il clique sur `Confirmer le geste`. Le reçu doit être refusé. Le message doit valoir exactement `× Demande refusée\nAsseoir le droit : pas assez de points de Sceau : 30 points demandés, <P(Sceau servi − 30)> disponible`, accordé comme dans « Règle du monde » (1,5 point attendu). Un seul tick a passé depuis le choix.
   - Il laisse passer 10 images.
2. **`gestes-2-jour-suivant`.** Il pousse un tick (212) et attend le panneau au tick neuf.
   - **Le même monde.** Le pays servi doit avoir un Sceau égal à celui de R1 moins 30, et un Droit égal à celui de R1 plus 10. Un seul geste a donc été payé, et le refus n'a rien pris.
   - **Le refus d'avance.** La ligne 4 de `Asseoir le droit` vaut `Refusé d'avance : ` suivi du refus servi, qui commence par `pas assez de points de Sceau : 30 points demandés, `. Son bouton est inactif.
   - Il laisse passer 10 images.

Chaque scénario écrit `CAPTURE_1046 <nom> Bar au tick T : Sceau <P>, Droit <P>, Plume <P>, reçus <acceptés>/<refusés>, message « <message sur une ligne> »`.

## Conditions de succès
On lance depuis la racine. Côté Python, depuis `jeu/`. Sur le PC, éditeur fermé, en PowerShell, `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Deux commandes de tests :
- `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot1046-interface.xml -logFile 3d/unity/Temp/lot1046-interface.log` ;
- `P` = la même avec `-assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot1046-pont.xml -logFile 3d/unity/Temp/lot1046-pont.log`.

Chacune sort 0, sans échec ni cas ignoré, et ses cas neufs réussissent.

**SC1 — Les raisons d'un geste s'écrivent en points (`python3 -m pytest -q sim/tests/test_pays_et_jauges.py`).** Cas neuf `test_les_raisons_d_un_geste_s_ecrivent_en_points`, sur Bar au mois (`_monde_au_mois`). `J.verifier_geste` rend exactement :
- avec Plume 10 : `pas assez de points de Plume : 50 points demandés, 10 points disponibles` ;
- avec Plume 1.5 : `…, 1,5 point disponible` ;
- avec Plume 0 : `…, 0 point disponible` ;
- avec Plume 35.04 : `…, 35 points disponibles` ;
- avec Sceau 31.5 et un `asseoir_le_droit` engagé : `pas assez de points de Sceau : 30 points demandés, 1,5 point disponible` ;
- avec Concorde 3 et Plume 500 : `Concorde déjà à sa borne : 3 points`.

Pour chacun, sauf le cas du geste engagé (que `/pays` ne compte pas), `J.document_des_jauges(monde, bar, regles)["gestes"][geste]["refus"]` donne le même texte. Chaque nombre du texte, pris en entier (`re.finditer(r"(?<![\d,])\d+(?:,\d+)?(?![\d,])", t)`), est suivi de ` point` ou de ` points`. `_points` rend aussi `-3 points` pour −3, `0,1 point` pour 0,05 et `0 point` pour −0,04.

`test_un_geste_depense_ses_points_ou_se_refuse` passe sans changer. Contre-épreuve : l'ancien `f"{cout} demandés, {valeurs[nom]:g} disponibles"` rougit le cas.

**SC2 — Le geste du panneau donne le même monde que la main (même commande).** Cas neuf `test_un_geste_du_panneau_donne_le_meme_monde_qu_a_la_main`, sur le modèle de `test_part_service` :
- deux `ServeurMonde(("127.0.0.1", 0), 0, 0)`, servis chacun par un fil `serve_forever`, et fermés dans un `finally` ;
- dans chacun, sous `verrou_tick`, Bar reçoit Sceau 31,5 : `J.etat(...) | {"sceau": 31.5}`, puis `J.poser_les_modificateurs` ;
- le premier reçoit en `POST /intention` les octets du panneau, `b'{"type":"depenser_jauge","maison":"seigneurie-1","geste":"asseoir_le_droit"}'`. Ce littéral est celui que SC5 fige pour `GestesDesJauges.Intention` ;
- le second reçoit la même intention écrite à la main : `json.dumps({"geste": "asseoir_le_droit", "maison": "seigneurie-1", "type": "depenser_jauge"}, indent=1)`, en octets.

Le cas vérifie :
- les deux reçus valent `{"acceptee": True, "appliquee_au_tick": 0}` ;
- un second dépôt des octets du panneau sur le premier serveur rend 400, avec l'erreur exacte `pas assez de points de Sceau : 30 points demandés, 1,5 point disponible`. `world.to_dict()` et `intentions_en_attente` ne bougent pas ;
- après `POST /tick?n=1` sur les deux, `json.dumps(world.to_dict(), sort_keys=True)` est égal sur les deux, et `GET /pays?maison=seigneurie-1` rend les mêmes octets ;
- Bar a Sceau 1,5 et Droit 60, et son `to_dict` d'avant le tick diffère de celui d'après.

Contre-épreuve : remplacer `asseoir_le_droit` par `affermir_la_concorde` dans les octets du panneau rougit le cas.

**SC3 — Les gestes se lisent en entier ou pas du tout (`ClientPaysTests.cs`, `P`).** Une constante neuve, `TemoinGestes` : `Temoin` où `"jauges":{"absents":{},` reçoit, juste après, deux gestes :
- `affermir_la_concorde` : nom `Affermir la concorde`, coût `{plume: 50}`, effet `{concorde: 1}`, refus `pas assez de points de Plume : 50 points demandés, 10 points disponibles` ;
- `asseoir_le_droit` : nom `Asseoir le droit`, coût `{sceau: 30}`, effet `{droit: 10}`, refus nul.

`Temoin` ne change pas. Les cas :
- `Les_gestes_se_lisent_avec_leur_prix_leur_effet_et_leur_refus` : chaque valeur, dans l'ordre servi, et `Pays` égal à ce que `Lire` rend sur le même document ;
- `Des_gestes_mal_servis_sont_refuses` : chaque refus de la section Périmètre est essayé un à un. Chacun donne une lecture absente qui nomme sa clé ;
- `Le_pays_sans_gestes_se_lit_toujours` : `LireGestes` sur `Temoin` est absent et nomme `jauges.gestes`, tandis que `Lire` sur `Temoin` reste présent.

Tous les cas existants passent sans changer. Contre-épreuve : un client qui accepte un coût sur une réserve non servie rougit `Des_gestes_…`.

**SC4 — La partie lit les gestes au même passage (`LecturePartieTests.cs`, `I`).** Cas `Les_gestes_se_lisent_avec_les_terres`, sur le modèle de `Les_terres_se_lisent_avec_le_pays` :
- monde sans maison : aucun appel au lecteur, et `Gestes` nul ;
- monde qui nomme `identifiant-servi` : un appel avec cet identifiant, après celui des terres ;
- une `LecturePartie` à sept paramètres laisse `Gestes` nul ;
- un lecteur de monde qui lève remet `Gestes` à nul.

Contre-épreuve : lire les gestes sans maison rougit le cas.

**SC5 — Le panneau dit prix, effet et refus, et dépose le geste (`GestesDesJaugesTests.cs`, `I`).** Le témoin : Bar au tick 211, date (1400, 212), Plume 35, Sceau 31,5, Concorde 0, Droit 50. Ses deux gestes sont ceux de SC3, sauf le refus de Concorde : `pas assez de points de Plume : 50 points demandés, 35 points disponibles`.

- `Chaque_geste_dit_son_prix_son_effet_et_son_refus` : `Geste` rend exactement :
  ```
  Asseoir le droit
  Prix : 30 points de Sceau (en réserve : 31,5 points)
  Effet : +10 points de Droit (aujourd'hui : 50 points)
  Payable aujourd'hui
  ```
  et :
  ```
  Affermir la concorde
  Prix : 50 points de Plume (en réserve : 35 points)
  Effet : +1 point de Concorde (aujourd'hui : 0 point)
  Refusé d'avance : pas assez de points de Plume : 50 points demandés, 35 points disponibles
  ```
  Les deux passent `Interdit(t, "seigneurie-1")` et `SansUnite`. `Raison("maison inconnue ou mal formée : 'seigneurie-1'", "seigneurie-1")` rend `raison illisible, gardée au journal` ;
- `Le_geste_confirme_depose_depenser_jauge` : un `GestesDesJauges` sur un `GameObject` témoin reçoit le monde et les gestes du témoin, et un `OrdreConfirme` dont l'envoi garde le texte reçu et rend `AccepteeAu(211)`. Après `Pas()`, `Asseoir le droit` est actif et `Affermir la concorde` inactif (son clic ne prépare rien). Le scénario du test suit ensuite cet ordre :
  - clic sur `Asseoir le droit` : le message vaut `Asseoir le droit : 30 points de Sceau pour +10 points de Droit. Confirmez pour payer.` ;
  - clic sur `Confirmer le geste` : le texte envoyé vaut exactement le littéral de SC2, et `Intention("seigneurie-1", "asseoir_le_droit")` aussi ;
  - le message vaut `Asseoir le droit : geste reçu au jour 212 de 1400. Le monde le paie au jour suivant.`, et les boutons de geste sont inactifs jusqu'à `Retour aux gestes` ;
- `Un_refus_du_service_s_affiche_dans_l_etat_du_socle` : l'envoi rend `Refusee(400, "pas assez de points de Sceau : 30 points demandés, 1,5 point disponible")`. Le message vaut `× Demande refusée\nAsseoir le droit : pas assez de points de Sceau : 30 points demandés, 1,5 point disponible`, en `SocleInterface.Couleur("alerte")`. Un refus `maison inconnue ou mal formée : 'seigneurie-1'` donne `raison illisible, gardée au journal`. Un reçu absent donne un message qui commence par `! Le monde ne répond pas\nEnvoi non confirmé : `. Après `Retour aux gestes`, le message revient en `encre` ;
- `Le_panneau_attend_le_meme_tick` : les états 1 à 5, chacun avec son texte exact. Avec les gestes au tick 210 ou 212, ou de `grande-3`, aucun texte de geste et aucun bouton actif.

Contre-épreuve :
- un bouton actif malgré un refus servi rougit `Le_geste_confirme_…` ;
- un panneau qui ne compare pas le tick rougit `Le_panneau_attend_…`.

**SC6 — Le panneau s'ouvre avec le feuillet du pays (`CabinetDeCarteTests.cs`, `I`).** Cas `Les_gestes_des_jauges_s_ouvrent_avec_le_feuillet_du_pays` :
- le cabinet porte un `GestesDesJauges` dont le `Panneau` est un enfant du cadre du feuillet `Le pays` ;
- le panneau est fermé d'avance, s'ouvre au premier clic sur l'icône `Le pays`, et se ferme au second ;
- ouvert, son rectangle, rapporté à la toile de 1920 × 1080, tient entre x 788 et 1288 et entre y 124 et 764, et ne recouvre ni « Votre maison », ni « Territoire conservé », ni le bandeau ;
- ses textes et ses boutons ne se recouvrent pas deux à deux ;
- après `Proposer()`, son état vaut `Choisissez une maison pour dépenser ses points.`, et aucun de ses boutons n'est actif.

`L_icone_du_pays_ouvre_son_feuillet_hors_des_dossiers`, `ChaqueCommandeDuCabinetDitCeQuElleFait`, `Aucun_dossier_ne_recouvre_la_barre` et `SansHorlogeRecueLesCommandesDuTempsRestentInactives` passent sans changer. Contre-épreuve : un panneau posé sur la toile, et non dans le cadre du feuillet, rougit le cas.

**SC7 — Sur le vrai service, la photo et sa contre-épreuve.** Les deux commandes de la section Photo.
- `PHOTO` sort 0. Elle laisse `*--gestes-1-paye-puis-refuse.png`, `*--gestes-2-jour-suivant.png` et deux traces `CAPTURE_1046` :
  - la première montre `reçus 1/1` et `× Demande refusée` ;
  - la seconde montre `Sceau 1,5 point` et `Droit 60 points`.
- `AVANCE` sort 1, sans image, et son journal dit `le panneau refuse d'avance`.

Le codeur ouvre chaque image lui-même et dit ce qu'il y voit.

**SC8 — Les scénarios qui lisent le cabinet et le pays restent verts.** Chacune de ces commandes sort 0 :
- `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 944 -forgeCaptures 3d/unity/Temp/lot1046-944 -logFile 3d/unity/Temp/lot1046-944.log` ;
- la même avec `-forgeLot 1004`, son dossier `lot1046-1004` et son journal ;
- la même avec `-forgeLot 1032`, son dossier `lot1046-1032` et son journal ;
- la même avec `-forgeLot 1045`, son dossier `lot1046-1045` et son journal. Le feuillet du pays, avec son panneau de gestes, garde son texte au tick de `/pays`.

**SC9 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `I`, `P` et `python3 -m pytest -q` (depuis `jeu/`) passent en entier.
- `git diff origin/master -- jeu/sim/tests 3d/unity/Assets/Interface/Tests 3d/unity/Assets/ForgeLocal3D/Pont/Tests` ne montre que des lignes ajoutées.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 1 500 lignes, brief compris.

## Hors périmètre
- Compter, dans `/pays`, les gestes déjà déposés pour le tick. `refus` reste celui du monde au tick publié. Un second geste le même jour se dit donc payable, et c'est le service qui le refuse : la photo le montre.
- Refuser, au service, un `depenser_jauge` d'une autre maison que celle du joueur (`/intention` ne le contrôle pas encore). Le panneau ne dépose que pour la maison du joueur.
- Les gestes d'un royaume ou de n'importe quel pays (#1037). Seul Bar, choisi pour de vrai, est photographié.
- Les alertes du panneau (« ce qui menace »), et l'IA qui joue ses jauges (#1035).
- Montrer, avant le paiement, ce que la jauge posera au pays (le Prélèvement du Droit) : la barre le dit au survol (#1032).
- Toute autre raison de refus : maison ou geste inconnus, et les refus des bâtiments.
- La langue du cabinet appliquée au panneau (#849, #850), et la définition du PNG : la chaîne l'écrit à 1600 × 900.

## Photo
Deux images, la carte et son cabinet en entier. Pour chacune :
- à gauche, le feuillet « Le pays » de Bar, ouvert ;
- à sa droite, le panneau « Gestes des jauges » ;
- au-dessus, le bandeau, avec la barre des jauges.

1. **Payé, puis refusé, au jour 212 de 1400 (tick 211).** Le panneau montre :
   - `Bar · relevé au jour 212 de 1400` ;
   - « Affermir la concorde », `Refusé d'avance : pas assez de points de Plume : 50 points demandés, 35 points disponibles` (attendu : 35 points), et son bouton éteint ;
   - « Asseoir le droit », `Prix : 30 points de Sceau (en réserve : 31,5 points)`, `Payable aujourd'hui` ;
   - en bas, en couleur d'alerte, `× Demande refusée`, puis `Asseoir le droit : pas assez de points de Sceau : 30 points demandés, 1,5 point disponible`. Le premier geste a été reçu ; le second, déposé le même jour, est refusé par le monde.
2. **Le jour suivant (tick 212).** Le Droit payé est là : la barre montre `Droit 60 points, en hausse` et `Sceau 1,5 point`. Dans le panneau, « Asseoir le droit » montre `Refusé d'avance : pas assez de points de Sceau : …`, avant tout clic, et son bouton est éteint.

Le scénario `Lot1046.cs` (Périmètre) joue ces étapes, et la chaîne écrit chaque image à la fin de son scénario.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1046 -forgeTicks 210 -forgeCaptures 3d/unity/Temp/lot1046-photo -logFile 3d/unity/Temp/lot1046-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1046 -forgeTicks 210 -forgeCaptures 3d/unity/Temp/lot1046-avance -forge1046Avance -logFile 3d/unity/Temp/lot1046-avance.log
```

Les deux sessions :
- **`PHOTO`**, la première, donne la photo : elle sort 0 avec ses deux images ;
- **`AVANCE`** est la contre-épreuve du même jour. Un tick passe entre le geste payé et le second. Le panneau refuse alors d'avance, et le refus du service n'est jamais atteint. Elle sort 1, sans image, et son journal est joint au compte rendu.

Les PNG restent hors du dépôt.
