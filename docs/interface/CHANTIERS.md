# Suivre les chantiers du bourg — UI-19a

Dans **Plan du bourg → Chantiers**, le joueur consulte rues, parcelles et bâtiments ajoutés au monde. Le dossier conserve le territoire et le tick reçus ; il indique l’effort fourni et requis en journées de travail, les foyers affectés, puis les ouvriers et le grain payé du jour lorsque le service les renseigne. Un ouvrage achevé reste identifiable. Les formes du plan de départ ne sont pas comptées comme des chantiers.

Les motifs d’arrêt viennent de `chantiers_du_jour` : parcelle inachevée, métiers non calculés, bras, payeur ou grain manquants. Une absence reste déclarée ; zéro reste une mesure. Aucun coût en pièces, date de fin ou effet de chantier n’est calculé par la vue. Mauvais territoire, doublon, compteur négatif, ouvrage incohérent ou relevé sans ouvrage refusent le bilan.

Preuve du code `b1c1b97e` : cinq contre-épreuves de données rouges, puis un test rouge reproduisant le bouton qui recouvrait « Puissances » sur la première capture. Après déplacement dans le plan : **102 tests verts**, dont 63 d’interface et 39 des contrats de capitale. [Rapports et parcours Unity](preuves/chantiers-b1c1b97e.zip).

Parcours réel aux ticks 69 et 70 : trois rues de Bar, paiement de 15 kg de grain pour cinq ouvriers chacune, avancement de la première de 30 à 35 journées fournies après un tick, passage à Milan et retour au dossier sans perdre la sélection. Le chantier achevé de Milan n’hérite pas du relevé de Bar.

Captures Unity regardées à 1920 × 1080 : [Bar](preuves/chantiers-bar-b1c1b97e.png), [accès depuis le plan](preuves/chantiers-acces-b1c1b97e.png), [autre territoire](preuves/chantiers-autre-terre-b1c1b97e.png). Papier, encre, filet et lecture simultanée suivent DA.md ; les calques restent accessibles. Le projet de vérification rassemble aussi le tracé de rue #708 et les formulaires #676.

Ce lot ne livre pas encore l’enceinte, les outils de parcelle et de bâtiment ni la finition typographique. L’aperçu Windows précédent doit être recompilé pour inclure ce dossier. La transition vers un kit 3D reste à vérifier dans le parcours complet.
