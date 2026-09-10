"""Les outils du dépôt : ce que la CI décide, et rien d'autre.

Trois modules, trois décisions, aucune écriture. `relecture` dit si une
PR a été relue par quelqu'un qui ne l'a pas écrite ; `integration` dit
quelle PR entre dans `master` ; `palier` dit quand une couche finie
appelle son lot de stabilisation. Chacun reçoit un état déjà lu et rend
une décision : c'est le workflow qui parle à GitHub, jamais eux.

Cette séparation n'est pas une élégance. Une décision qui appelle le
réseau ne s'éprouve qu'en ligne, et un contrôle qu'on ne peut pas jouer
hors ligne est un contrôle qu'on ne joue pas.
"""
