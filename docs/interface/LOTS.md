# Lots d’interface — UI-01 en cours

Validation de DA.md requise avant UI-01. Chaque ligne = une branche `direct/interface-<sujet>` depuis `origin/master`, une PR de moins de 300 lignes ajoutées + supprimées, tests, métadonnées et suivi inclus. Les tailles sont des budgets prévisionnels ; découper davantage avant de dépasser, jamais comprimer le code pour tenir. Les dépendances Jn désignent les contrats effectivement livrés de CAP.md, pas seulement leur numéro de jalon.
Zone : `3d/unity/Assets/Interface/` et `docs/interface/`. Réutiliser `ForgeLocal3D/Pont` par adaptation ; tout raccord indispensable hors zone doit être précisément justifié dans sa PR. Aucun changement de `jeu/sim/`. UI-01 reste une galerie isolée ; aucun remplacement silencieux des scènes existantes.
Preuve commune : test rouge avant implémentation ; fixture non vide, capture Unity regardée et comparée aux références de DA.md, puis test vert. Les captures et rapports portent le SHA et sont liés dans la PR ; une capture conceptuelle n’est pas une preuve Unity. La colonne « échec » indique la contre-épreuve à provoquer. États : `à faire`, `en cours`, `livré` ; livré signifie preuve réussie et PR fusionnée.

| Lot | Titre et gain joueur | Dépend de | Capture + test pouvant échouer | Budget | État |
|---|---|---|---|---|---|
| UI-01 | Socle : préparer une lecture cohérente ; thème, texte, bouton, panneaux simultanés et galerie minimale | DA validée | Galerie des trois composants et états normal/focus/inactif ; jeton absent ou focus invisible échoue | 285 | en cours |
| UI-02 | États de lecture : reconnaître attente, absence, refus et panne | 01 | Quatre états distincts ; `null` affiché comme zéro échoue | 180 | à faire |
| UI-03 | Horloge : suspendre et reprendre le monde | 02 | Pause/vitesse reçues ; réponse retardée ne doit pas inverser l’état | 240 | à faire |
| UI-04 | Menu : entrer et revenir sans perdre le contexte | 01 | Navigation clavier et retour ; double ouverture échoue | 210 | à faire |
| UI-05 | Départ : lire une terre et confirmer sa maison | 02, 04 | Fiche servie puis attente/application ; double dépôt échoue | 270 | à faire |
| UI-06 | Cadre de carte : lire le territoire sans le masquer | 01, 03, 05 | Sélection et légende à 1080p ; clic à travers panneau échoue | 260 | à faire |
| UI-07 | Calques : distinguer relief, maîtres et habitants | 06 | Légende liée aux données ; cellule absente ou liste vide échoue | 260 | à faire |
| UI-08 | Lieu : reconnaître habitants, stocks et maître | 02, 06 | Deux rangs d’une même cellule ; mélange de rangs/ticks échoue | 250 | à faire |
| UI-09 | Maison : situer siège, terres et suzerain | 08 | Maison sur/hors carte ; siège inventé ou absence masquée échoue | 240 | à faire |
| UI-10 | Prélèvement : régler la part avec un reçu | 09 | Saisie puis reçu puis état ; effet optimiste avant tick échoue | 240 | à faire |
| UI-11 | Secours : ouvrir son grenier en connaissance du stock | 09 | Quantité, refus et attente ; deux clics ne doublent pas l’ordre | 240 | à faire |
| UI-12 | Flux : lire prélevé, reçu, pertes et période | 09 | Données 30 jours et manque explicite ; unité/personnes confondue échoue | 230 | à faire |
| UI-13 | Trajets : relier une charge à sa destination | 07, 12, contrat routes | Trajet fourni et absence ; trajet inventé ou quantité locale échoue | 260 | à faire |
| UI-14 | Voisins : lire leurs gestes et raisons | 09, `/ia` | Fil daté avec refus ; raison inventée ou doublon échoue | 240 | à faire |
| UI-15 | Passage en ville : retrouver sa capitale et revenir | 06, contrat transition J4 | Carte/ville/retour ; sélection perdue ou horloge locale échoue | 270 | à faire |
| UI-16 | Dossier du bourg : inspecter sans construire ailleurs | 08, 15 | Capitale, autre terre, kit absent ; outil actif sans droit échoue | 220 | à faire |
| UI-17 | Route : tracer et annuler une intention | 16 | Aperçu visuel et reçu ; annulation qui envoie un ordre échoue | 260 | à faire |
| UI-18 | Parcelle et atelier : préparer la construction | 17 | Outil choisi, cible, refus ; double intention sur un clic échoue | 275 | à faire |
| UI-19 | Chantier : lire effort, coût et enceinte | 16, J4 coûts/enceinte | Fiche reçue ; coût absent transformé en gratuit échoue | 250 | à faire |
| UI-20 | Personnage : reconnaître chef, traits et ambitions | 09, J6 personnes | Portrait et identité reçue ; trait absent inventé échoue | 250 | à faire |
| UI-21 | Famille : lire parenté et héritier désigné | 20, J6 succession | Arbre et partage fourni ; héritier choisi localement échoue | 275 | à faire |
| UI-22 | Choix dynastiques : proposer mariage, éducation, loi | 20, 21, intentions J6 | Formulaire commun et reçus ; option non autorisée échoue | 280 | à faire |
| UI-23 | Diplomatie : lire revendication, guerre et paix | 09, contrats J7 | Proposition et refus ; territoire cédé avant application échoue | 270 | à faire |
| UI-24 | Armée : lire levée, marche et ravitaillement | 07, 23, contrats J7 | Colonne et dossier ; effectif/vivres différents du contrat échouent | 280 | à faire |
| UI-25 | Entrée en bataille : mener ou déléguer | 24, contrat bataille | Choix et transition ; deuxième bataille ou monde non arrêté échoue | 250 | à faire |
| UI-26 | Commandement : transmettre un ordre et lire le bilan | 25, moteur bataille | Sélection, ordre, pertes reçues ; issue recalculée dans l’UI échoue | 280 | à faire |
| UI-27 | Sauvegarde : enregistrer et reprendre par le service | 04, contrat J9 | Liste et échec de reprise ; succès affiché sans reçu échoue | 275 | à faire |
| UI-28 | Argent : lire trésor, prix et dettes par lieu | 09, contrats J8 | Fiche avec unités ; monnaie absente remplacée par zéro échoue | 260 | à faire |
| UI-29 | Engagement financier : confirmer quantité et contrepartie | 28, intentions J8 | Formulaire/récapitulatif/reçu ; échéance fabriquée localement échoue | 275 | à faire |
| UI-30 | Chronique : retrouver faits, personnes et lieux | 08, 20, contrat J9 | Fil et retour au lieu ; événement dupliqué ou date inventée échoue | 250 | à faire |
| UI-31 | Décisions : lire les arbitrages groupés et leurs échéances | 02, contrat file | Vide/urgence/file longue ; un acquittement requis par lieu échoue | 260 | à faire |
| UI-32 | Délégation : donner une consigne durable | 09, 31, contrats J9 | Domaine et consigne ; écriture directe du monde échoue | 260 | à faire |
| UI-33 | Lisibilité : agrandir, réduire le mouvement, naviguer au clavier | 01, 06 | 720p/1080p à 100/150 % ; texte coupé ou focus perdu échoue | 260 | à faire |
| UI-34 | Aide et son : comprendre les gestes, régler le volume | 04, 33 | Aide contextuelle et silence ; information uniquement sonore échoue | 210 | à faire |
| UI-35 | Bilan : comprendre défaite, héritage et siècle | 21, 30, contrats J6/J9 | Fin reçue et chronique ; défaite déduite d’une panne échoue | 250 | à faire |
| UI-36 | Parcours complet : garder une interface cohérente du départ au bilan | 01–35 | Captures du parcours réel ; fixture vide, service absent ou reçu ignoré échoue | 280 | à faire |

Avant chaque PR : consulter les PR `head:lot/` et leurs fichiers ; prévenir seulement d’un chevauchement ; actualiser `origin/master`, rebaser avant poussée, puis `gh pr merge --auto --squash`. Contrôler les objets LFS sur le serveur après poussée. Mettre ETAT.md à jour ; ne pas confondre plan livré et capacité jouable.
