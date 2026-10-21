# Lot #659 — La session Unity de l'épreuve de la part
Jalon : J3 · Machine : pc · Taille prévue : 290 lignes

## But
Une session Unity choisit une terre, règle sa part au vrai curseur, fait passer trente jours au service et relève le panneau et `/maison` dans un rapport exploitable par l'épreuve de la part.

## Le joueur
Lot de fond découpé de #405 : il prépare la preuve du geste « fixer la part qu'il prend sur ses lieux » de J3, déjà visible dans #656. Le joueur doit pouvoir croire le panneau lorsqu'il prend davantage pour remplir son grenier, au risque de voir partir ses gens. Cette moitié Unity rejoue son geste et en conserve les observations ; le lot de jugement de l'épreuve de la part, autre morceau de #405, comparera ces observations au monde. La session seule ne certifie ni l'effet économique ni l'égalité des vues. Dépend de : #656.

## Règle du monde
Sans objet : outil d'épreuve, aucune règle modifiée. Contrats lus dans `jeu/sim/MODELE.md`, « Les intentions du joueur », « Le prélèvement », « Le grenier d'une maison » et « Les maisons servies, vue dérivée ». Le choix et la part s'appliquent au tick suivant ; le N du reçu est recopié tel quel, sans lui ajouter 1. Une part est une fraction dans l'intention, un pourcentage au curseur. Les kilos, les réserves et les flux viennent uniquement du service. Les trente ticks commencent après le dépôt de la part et incluent son tick d'application ; le tick préalable qui applique le choix est compté séparément.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/EpreuvePart.cs
3d/unity/Assets/ForgeLocal3D/Editor/EpreuvePart.cs.meta
docs/briefs/659-la-session-unity-de-l-epreuve-de-la-part.md

Tout autre chemin est interdit. Budget, brief compris : environ 210 lignes de session, 2 de `.meta`, 78 de brief ; moins de 300 lignes ajoutées et retirées. Rapports et journaux d'exécution vont dans un dossier temporaire, hors du dépôt. Réutiliser les aides internes d'`EpreuveChoix` (arguments, chemin de lancement, reçus), de `Lot690` (attentes, lectures, tick) et le parcours de `Lot656`, sans modifier ces fichiers.

La seule entrée neuve est `ForgeLocal3D.EpreuvePart.Jouer`, sur le modèle d'`EpreuveCapitale` : ouverture de `CarteBuilder.Chemin`, Play, état conservé dans `SessionState`, coroutine par `EditorApplication.update`, rapport écrit avant sortie du Play et terminaison bornée, y compris sans service. La session utilise un service externe déjà lancé en pause ; elle ne le lance ni ne l'arrête, ne change pas `/vitesse` et ne lance aucune simulation locale. Désactiver seulement dans cette session `PassageALaCapitale` avant le choix pour rester sur la carte, même au Zab ; aucun changement du comportement livré au joueur.

Arguments : `-forgeEpreuve <rapport.json>` et `-forgeTerre N` obligatoires, N entier positif recherché dans les fiches servies, jamais converti localement en identifiant de maison ; `-forgePart P` facultatif, 50 par défaut, entier de 0 à 60 inclus, en pourcentage, conformément au curseur de #656. Argument présent sans valeur, fraction, texte ou valeur hors bornes : code 2 avant toute intention et aucun rapport neuf. Résoudre le chemin comme `EpreuveChoix.DossierDeLancement()`, créer son dossier au besoin. Ne pas confondre une option absente avec une option mal formée.

Attendre le vrai cabinet et ses fiches ; sélectionner la maison de la fiche N avec son bouton puis « Choisir cette maison », relever le reçu, pousser un seul tick et attendre la maison publiée et les commandes disponibles. La maison utilisée ensuite vient de `/monde.maison_du_joueur`. Ouvrir « Prélèvement », déplacer le `Slider` actif à P, laisser son événement remplir la saisie, cliquer « Préparer », conserver le JSON réel de `Ordre.Brouillon`, puis « Confirmer l’ordre ». Ne pas remplir directement l'`InputField`, fabriquer le JSON ou remplacer le geste par un dépôt HTTP. Relever le reçu et `CommandesMaison.MessageAffiche`, sans exiger que la part servie égale P.

Après la fin de l'envoi, pousser exactement 30 ticks par le service, hors du fil principal, en comptant seulement les ticks dont la réponse confirme l'exécution. Relever les ticks publiés, pas un compteur présenté comme l'horloge. Attendre le rafraîchissement ordinaire des comptes pendant au plus deux périodes de 2 s, puis copier le vrai texte du relevé de `CommandesMaison` (part, tick, grenier), même s'il est périmé ou annonce une absence. Lire séparément `/maison?id=<maison publiée>` et conserver statut HTTP et corps intégral ; ne pas reconstituer ce corps depuis le panneau ni le panneau avec `Decrire`. Les attentes de réseau et de contrôles sont bornées à 30 s ; ne pas attendre une valeur économique attendue pour terminer.

Rapport JSON, champs stables : `terre`, `part_demandee_pct`, `curseur_pct`, `maison`, `tick_avant`, `tick_apres_choix`, `tick_apres`, `ticks_part`, `choix`, `ordre`, `intention_json`, `message_ordre`, `panneau`, `maison_statut`, `maison_json`, `defaut`. `choix` et `ordre` ont la forme d'`EpreuveChoix.Recu` : statut, tick, raison. Initialiser les nombres non relevés à -1 et les textes à "" ; `ticks_part` devient 0 au début de la boucle, puis mesure les ticks exécutés. Une réponse HTTP absente garde statut -1 et sa cause dans `defaut`, jamais un faux panier vide.

Code 0 : parcours et observations terminés, sans verdict économique, même si les chiffres divergent ou si le reçu de part est un refus ; conserver alors ce reçu et poursuivre les trente ticks. Code 1 : session impossible (choix refusé empêchant la suite, composant absent, délai, coupure, tick refusé, écriture impossible), avec rapport partiel et cause précise lorsque le chemin est accessible. Aucun champ `egal`, aucun seuil de grain, aucun verdict « ÉGALITÉ / ÉCART ». Ajouter `-forgePartSansConfirmation`, lu seulement dans ce fichier : il omet uniquement le clic final de part, relève l'absence de reçu, puis déroule les mêmes trente ticks et lectures, sans exception provoquée par le drapeau.

## Conditions de succès
Sur le PC, éditeur fermé, depuis la racine, PowerShell : `$u = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `SESSION` désigne `& $u -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.EpreuvePart.Jouer`, sans `-quit` ni `-nographics`. Dans un second terminal placé dans `jeu/`, `py -m sim.service --seed 0 --jours-par-seconde 0` lance le service au port 8000 ; l'arrêter et le relancer entre essais. Supprimer chaque ancien rapport avant l'essai. Le codeur joint commandes, codes et relevés au rendu du pilote.

SC1 — Rouge d'abord, puis parcours normal. Commande : `SESSION -forgeEpreuve "$env:TEMP\lot659-normal.json" -forgeTerre 3 -logFile "$env:TEMP\lot659-normal.log"`. Avant implémentation, constater l'échec faute de méthode et de rapport neuf ; ensuite obtenir code 0 et un rapport non vide : terre 3, demande et curseur 50, ticks 0 / 1 / 31, trente ticks de part, choix accepté au tick 0, part acceptée au tick 1, maison identique à celle servie. Le reçu affiché nomme « après le tick 1 ». Contre-épreuve : SC3 doit faire échouer le contrôle ci-dessous par les observations, tout en laissant la session terminer.

SC2 — Le rapport se contrôle contre le service. Commande : définir puis appeler `Controler "$env:TEMP\lot659-normal.json" 50` avec cette fonction PowerShell ; toute assertion fausse lève une erreur :
```powershell
function Controler($f, $p) {
  $r = Get-Content -Raw -Encoding UTF8 $f | ConvertFrom-Json
  $m = $r.maison_json | ConvertFrom-Json; $i = $r.intention_json | ConvertFrom-Json
  $w = Invoke-RestMethod 'http://127.0.0.1:8000/monde'
  $d = @((Invoke-RestMethod 'http://127.0.0.1:8000/departs').departs | Where-Object { $_.id -eq $r.terre })
  $s = (Invoke-WebRequest -UseBasicParsing ('http://127.0.0.1:8000/maison?id=' + $r.maison)).Content
  if ($r.defaut -ne '' -or $r.tick_avant -ne 0 -or $r.tick_apres_choix -ne 1 -or $r.tick_apres -ne 31 -or $r.ticks_part -ne 30 -or $w.tick -ne 31) { throw 'ticks ou défaut' }
  if ($r.choix.statut -ne 200 -or $r.choix.tick -ne 0 -or $r.ordre.statut -ne 200 -or $r.ordre.tick -ne 1 -or !$r.message_ordre.Contains('après le tick 1')) { throw 'reçus' }
  if ($r.part_demandee_pct -ne $p -or $r.curseur_pct -ne $p -or $i.type -ne 'fixer_part' -or $i.maison -ne $r.maison -or [math]::Abs($i.part - $p/100.0) -gt 1e-7) { throw 'ordre' }
  if ($r.maison_statut -ne 200 -or $r.maison -ne $w.maison_du_joueur -or $m.id -ne $r.maison -or $m.tick -ne 31 -or $r.maison_json -cne $s -or [math]::Abs($m.part - $p/100.0) -gt 1e-7) { throw 'maison indépendante' }
  if ($d.Count -ne 1 -or $m.siege.nom -ne $d[0].siege.nom) { throw 'terre choisie' }
  if (!$r.panneau.Contains("Prélèvement : $p %") -or !$r.panneau.Contains('tick 31') -or !$r.panneau.Contains('Grenier :')) { throw 'panneau' }
}
```
Contre-épreuve : sur une copie temporaire, changer `tick_apres` en 30 ou retirer `maison_json` ; le même appel doit échouer. Le contrôle appartient à la vérification du lot, jamais à la session livrée.

SC3 — Sans confirmation, le monde garde sa part. Commandes : sur service neuf, `SESSION -forgeEpreuve "$env:TEMP\lot659-sans-confirmation.json" -forgeTerre 3 -forgePartSansConfirmation -logFile "$env:TEMP\lot659-sans-confirmation.log"`, puis `Controler "$env:TEMP\lot659-sans-confirmation.json" 50`. La session sort 0 avec trente ticks observés, reçu de part non relevé (-1), part coutumière dans `/maison`, texte effectivement affiché ; le contrôle échoue. Contre-épreuve : un envoi caché, un panneau fabriqué à 50 % ou une exception déclenchée par le seul drapeau refuse la livraison.

SC4 — La valeur demandée et la terre sont réellement jouées. Commandes : service neuf à chaque fois, reprendre SC1 avec `-forgePart 25`, puis avec `-forgeTerre 6 -forgePart 0`, vers des rapports distincts ; appeler `Controler <rapport> 25`, puis `Controler <rapport> 0`. Les deux sessions et contrôles passent ; le Zab reste sur la carte dans l'outil, sans scène substituée. Contre-épreuve : appeler le contrôle à 50 sur le rapport à 25 doit échouer ; une valeur demandée à zéro ne devient pas le défaut 50.

SC5 — Les impossibilités restent explicites. Commandes : SC1 sans service, puis avec service neuf mais `-forgeTerre 999999` ; chaque session sort 1 en temps borné avec rapport partiel et `defaut` non vide, sans inventer reçu, tick ni maison. Commandes d'arguments : SC1 sans `-forgeTerre`, puis avec `-forgePart 61`, `-forgePart 25.5` et `-forgePart` sans valeur, chacun vers un chemin neuf : code 2, aucun rapport et monde encore au tick 0 sans choix en attente. Contre-épreuve : un rapport normal conservé d'un ancien essai, un nombre absent à zéro ou une valeur corrigée silencieusement refuse ces vérifications.

SC6 — Les contrats actuels restent verts. Commandes : `& $u -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -testResults "$env:TEMP\lot659-tests.xml" -logFile "$env:TEMP\lot659-tests.log"` et `py -m pytest jeu/sim/tests/test_intentions.py jeu/sim/tests/test_maisons_servies.py -q`. XML non vide sans échec ; les cas existants de `CommandesMaisonTests`, `OrdreConfirmeTests`, `DossierMaisonTests` et `ClientMaisonTests` sont exécutés et inchangés. Contre-épreuve : zéro cas exécuté ou un test retiré ne vaut pas vert ; les contre-épreuves existantes doivent rester exécutées.

SC7 — Le diff reste borné. Commandes : `git diff --check`, `git diff --name-only origin/master`, `git diff --numstat origin/master`, `git ls-files --others --exclude-standard`. Compter les fichiers neufs et le brief : seulement les trois chemins du périmètre, moins de 300 lignes ajoutées et retirées. Contre-épreuve : un quatrième chemin, un test existant changé ou un total de 300 lignes refuse la livraison.

## Hors périmètre
Le juge et son lanceur Python, la preuve complète de J3 (#406), toute règle ou constante de simulation, les formats du service, les clients du pont, les scènes, le cabinet et ses contrôles ; aucune ouverture du grenier, aucune exigence de départs ou de flux positifs après trente jours. Aucun changement ni assouplissement de test existant. Aucun nouveau panneau, décoration ou graphique. Le rapport reste un relevé, pas une seconde simulation.

## Photo
sans objet : outil de session sans changement de ce que le joueur voit à l'écran. Le geste et le reçu sont déjà photographiés par `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot656.cs` ; ce lot ajoute uniquement leur collecte et un rapport, sans nouvelle capture ni modification de celle de #656.
