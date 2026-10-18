# Polices du cabinet

Noto Serif Regular pour les titres, Noto Sans Regular pour le corps, les
commandes et les chiffres. Fichiers statiques TTF embarqués : aucun recours
aux fontes installées sur le PC. Corps 18 px et commandes 44 px conservés.

Source : https://github.com/googlefonts/noto-fonts/tree/main/hinted/ttf
Licence SIL Open Font License 1.1 intégrale dans
`Assets/Interface/Resources/Forge/Polices/OFL.txt`, avec son copyright.
Les fichiers ne sont pas modifiés. Les glyphes français et les chiffres
sont éprouvés dans Unity, ainsi que la distinction entre titres et lecture.

Preuve : un test rouge sur LegacyRuntime, puis 63 tests verts dans le projet
de contrôle (dont les chantiers de la PR #713). Capture de choix de maison
regardée à 1920 × 1080 : titres et commandes lisibles, accents conservés.
[Capture](preuves/typographie-choix.png) · [Rapports](preuves/typographie-tests.zip).
