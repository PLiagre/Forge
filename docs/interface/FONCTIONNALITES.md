# Écrans et gestes — périmètre proposé

La carte, la ville et la bataille vivent dans Unity. Priorité au premier siècle de CAP.md ; les images industrielles ne créent aucune fonctionnalité. « Disponible » désigne une donnée ou un chemin trouvé dans le code, pas une nouvelle interface livrée.

| Écran / geste | Ce que le joueur y gagne | Source ou attente ; lots UI |
|---|---|---|
| Menu et choix de départ | Choisir sa petite maison, connaître sa terre et reprendre une partie | `/departs`, `choisir_depart` ; reprise attend le contrat J9 ; 04, 05, 27 |
| Carte et calques | Comprendre ses lieux, voisins, relief et difficultés sans quitter le territoire | `/carte`, `/monde`, `/lieu`, `/maisons` ; 06, 07 |
| Fiche de lieu et maison | Savoir qui tient quoi, où vivent les gens, ce que contient leur panier | `/lieu?cell=X`, `/maison?id=X` ; 08, 09 |
| Grenier et prélèvement | Arbitrer entre ses projets et les besoins de ses habitants | `fixer_part`, `ouvrir_grenier`, reçus réels ; 10, 11 |
| Stocks, trajets et flux | Distinguer réserve, grain en voyage, pertes et arrivées | `flux_30j` et `absents` de `/maison`, flux de `/lieu` ; détail des routes à qualifier ; 12, 13 |
| Temps et passage carte/ville | Garder le contrôle du rythme sans perdre son lieu | `/horloge`, `/vitesse`, clients du pont ; politique de transition à vérifier ; 03, 15 |
| Capitale et autres bourgs | Bâtir sa capitale ; inspecter ses autres terres sans les bâtir à la main | Plan et droits servis ; kit disponible requis, ville étrangère reste sur la carte ; 15, 16 |
| Outils et dossier de chantier | Tracer, poser puis comprendre l’effort demandé | Intentions route/parcelle/bâtiment, plan ; enceinte et coûts selon contrat livré ; 17–19 |
| Voisins et raisons de leurs gestes | Comprendre un voisin et les mouvements de ses gens | `/ia` et maisons ; afficher uniquement les raisons publiées ; 14 |
| Personnage, famille, succession | Choisir mariage, éducation, loi ; voir l’héritier et les terres partagées | J6, export #445 et intentions correspondantes à vérifier ; 20–22 |
| Relations et diplomatie | Lire suzeraineté et interlocuteurs ; négocier quand le monde le permet | Registre disponible ; mariage J6, guerre/paix J7 ; aucun score diplomatique inventé ; 09, 22, 23 |
| Armée et ravitaillement | Lever et déplacer en voyant les hommes et vivres engagés | J7, contrat #468 et intentions ; 23, 24 |
| Bataille et siège | Mener ou déléguer, donner des ordres, connaître les pertes rendues au monde | Contrat #456, même moteur avec ou sans image ; 25, 26 |
| Trésor, prix et dette | Relier une décision financière aux lieux, pièces et échéances | J8, contrat #486 ; aucune pièce fictive dans le bandeau ; 28, 29 |
| Chronique et événements | Retrouver les faits, leurs acteurs et leurs lieux | J9 #494 ; ne pas reconstituer une causalité à partir d’écarts de stocks ; 30 |
| Décisions et alertes | Voir les arbitrages à prendre sans acquitter chaque lieu chaque jour | File sémantique et échéances à demander au moteur ; déconnexion déjà constatable ; 02, 31 |
| Délégation et lois | Confier ce qui se répète à l’échelle du domaine | J9 #491–493 ; actes groupés fournis par le monde ; 32 |
| Sauvegarde et retour au jeu | Reprendre exactement son monde et comprendre un échec de chargement | J9 #489–490, aucune sauvegarde économique locale dans Unity ; 27 |
| Réglages et aide | Lire, utiliser le clavier, réduire mouvement et son, retrouver un geste | Préférences de présentation locales uniquement ; 33, 34 |
| Fin de partie et bilan | Comprendre la perte des terres et relire le siècle | Défaite J6 #442, score J9 #496 ; ne jamais déduire une victoire localement ; 35 |

Un panneau numérique affiche son unité, son périmètre et le tick reçu ; zéro est une mesure, absence et lecture périmée sont des états distincts. Les champs réunis dans une décision doivent provenir d’un état cohérent ; une réponse ancienne ne remplace pas une réponse récente. Aucun nouveau `lieu_id` : le rang reste relatif à `cell_id`.
Chaque geste affiche « en attente », puis le reçu, puis son effet publié ; « accepté » ne veut pas dire « appliqué ». Refus et panne gardent la saisie. Pas de renvoi automatique d’un ordre non idempotent sans contrat le garantissant. L’UI ne calcule ni prix, ni rendement, ni délai de transport, ni issue de combat.
Les besoins non confirmés ci-dessus deviennent, avant leur lot, des entrées de `BESOINS-SIM.md` : nom, forme proposée, unité, tick/révision, nullabilité, raison et cas refusé. Ce fichier sera ajouté dès le premier adaptateur concerné ; aucun contrat proposé n’est présenté comme déjà implémenté. Une galerie distincte peut lire des données d’essai marquées « Démonstration », jamais la partie réelle.
Retirés : gestion manuelle de toutes les villes, fenêtre par événement mineur, jauges de bonus, conseil fondé sur un score caché, fonctionnalités de 1500–1900 avant le premier siècle. Les écrans avancés restent accessibles en galerie seulement tant que leur contrat manque.
