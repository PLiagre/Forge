# La carte dans l’exécutable — 16 octobre 2026

Le premier aperçu Windows du cabinet affichait les dossiers, mais aucune terre : le matériau par défaut du pipeline URP est disponible dans l’éditeur et absent dans ce build. La carte déclarait cette absence au lieu de fabriquer un rendu.

`Resources/Forge/Carte.mat` embarque maintenant un matériau URP Lit sans texture externe. La carte le charge avant le matériau de secours du pipeline. Les couleurs restent celles des données servies ; aucun changement de simulation, de maillage ou de scène. Ce raccord exige deux fichiers hors de la zone d’interface : `ForgeLocal3D/Pont/CarteDessinee.cs` et son test existant. Sans lui, le cabinet de la PR #666 ne montre pas la carte dans l’exécutable.

Contre-épreuve : un nouveau test retire les pipelines de l’éditeur ; il échoue avec 0 cellule posée pour 596 attendues. Après correction, les 14 tests de carte et les 26 tests d’interface passent, sans assouplir les tests existants. [Rapports bruts et manifeste](preuves/materiau-dac2591c.zip).

Build Windows local avec Unity 6000.0.43f1 : réussi, zéro erreur. Lancement par `pc/jouer.py`, vrai service sur le port 8000, scène `Forge_Carte`, 596 cellules, maisons proposées, souris disponible. Fermeture du jeu : code 0 et arrêt du service confirmé. [Capture de l’exécutable regardée à 1920 × 1080](preuves/cabinet-executable-dac2591c.png), palette comparée au cabinet déjà validé et aux références papier/encre de DA.md.

Code éprouvé : correctif `dac2591c`, cabinet de `direct/interface-ecran` (`e0c6eae5`, code inchangé depuis la preuve `af3d6b28`). Le projet local de contrôle reprend la scène et le pont ; ce n’est pas une validation du build nocturne complet. L’exécutable n’inclut que la carte et le cabinet. Le parcours de choix, temps et souris reste documenté dans PARTIE.md de la PR #666.
