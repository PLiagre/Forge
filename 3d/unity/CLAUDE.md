# 3d/unity — la carte, l'interface et la ville

Un seul projet Unity. `Assets/Interface/` (assembly `Forge.Interface`) porte
les écrans de la carte ; `Assets/ForgeLocal3D/Pont/` (`Forge.Pont`) lit le
service du monde ; `Assets/ForgeLocal3D/` porte la ville du désert et ses
outils d'éditeur. Unity ne tourne que sur le PC.

## Les règles de la zone

- **Une vue lit, elle ne décide aucun nombre.** Ce qui s'affiche vient du
  service de `jeu/sim/` ; un geste envoie une intention et attend la réponse
  du monde.
- **La langue visuelle vit à un seul endroit** (`SocleInterface`,
  `MatieresCabinet` : jetons, matières, cadres, états, infobulle). Un écran
  la reçoit, il ne pose ni couleur ni police à lui. Sombre, gothique,
  médiévale : pierre, bois brûlé, métal patiné, rouge profond, cuivre, or
  vieilli. Les jetons et les interdits : `docs/interface/DA.md`.
- **Un écran se prouve par une capture du vrai écran**, branché au vrai
  service, regardée à l'œil ; et il se juge en jouant un build.
- **Jamais un pack de l'Asset Store dans git** : `Assets/Vendor/` est ignoré
  et relié par jonction vers `D:\Forge\3d\unity\Assets\Vendor`.

## Lancer Unity sans écran

- **Une seule instance à la fois** sur un projet, et une seule session Unity
  utile à la fois sur le PC.
- **Unity peut pendre à « Cleanup mono »** après avoir fini. Le lancer par
  `Start-Process -PassThru`, attendre avec une borne (`WaitForExit(ms)`), le
  tuer au-delà, et lire le résultat dans le XML ou le journal, pas dans le
  code de sortie.
- **`-assemblyNames` se sépare par « ; »**, entre guillemets sous
  PowerShell. Avec une virgule, Unity joue 0 cas et sort 0 : toujours lire
  `testcasecount` dans le XML.
- **Les chemins relatifs ne partent pas du même dossier** : `-testResults`
  et `-forgeCaptures` se résolvent depuis le projet, `-logFile` depuis le
  dossier courant. Donner des chemins absolus.
- **Unity vide `3d/unity/Temp` à chaque démarrage** : copier un journal hors
  du projet avant de lancer la session suivante.
- **Une session qui finit sans service pend** si elle quitte en Play :
  `ExitPlaymode()`, attendre 12 s, puis quitter. Un scénario de capture qui
  échoue peut donc ne pas rendre 1 : lire « CAPTURE : le scénario … a
  échoué » au journal.
- **« No valid Unity Editor license »** : la licence est liée à une carte
  réseau absente. C'est un geste du propriétaire (Unity Hub → Licences) ;
  ne jamais se connecter à sa place.

## Travailler dans un worktree

- **Une `Library` copiée d'un autre worktree perd les classes de
  `Forge.Pont`** (scripts « missing », `KitDesBatiments` introuvable, des
  dizaines de tests rouges qui n'accusent pas le code). Réimporter
  `Assets/ForgeLocal3D/Pont` et `Assets/ForgeLocal3D/Desert/Resources`
  (`ImportRecursive | ForceUpdate | ForceSynchronousImport`) par une méthode
  d'éditeur temporaire, jamais commitée, puis relancer une session neuve.
- **Jouer le build d'un worktree** : `ForgeLocal3D.Build.Nuit` avec
  `-forgeSortie`, puis `pc\jouer.py` du même worktree, pour que le service
  soit celui du même code. Ne jamais écraser `builds\dernier`.

## Les captures

- **Une capture se lance comme le lot l'écrit**, avec ses drapeaux
  `-forge…`. Sans `-forgeTicks`, le service part au tick 30 : un scénario lit
  le tick attendu au lieu de l'écrire en dur.
- **`--epreuve` n'arrive au service que par `-forgeServiceEpreuve`**, jamais
  par le code d'un scénario.
- **Un scénario a 60 s** (`DELAI_SCENARIO_S`). La ville dense sans
  optimisations le frôle : un dépassement se rejoue avant d'accuser le code.
- **Les textes du cabinet se notent après 2,5 s sans changement** : ils sont
  récrits une image après la lecture, et l'horloge a presque toujours une
  requête en vol.
- **Un scénario qui bâtit dépose d'abord `choisir_depart`**, puis laisse
  passer un tick ; sinon le monde refuse la route ou la parcelle.
- **Biskra n'a pas de nom sur la carte** (`villes-1400.json` ne la porte
  pas) : cadrer le siège par sa cellule (10103), `Centrer` après `Zoomer`.
- **À l'ouest de Biskra, le relief refuse une route** (pente de 40 % devant
  le mur) : une route de démonstration se trace ailleurs.
