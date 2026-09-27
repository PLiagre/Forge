# Images QA perdues

Ces 34 images de contrôle de la fabrique ont été committées le 10 septembre 2026
(fusion `1ebc6d2`) comme pointeurs LFS, sans que leurs objets soient jamais
téléversés. Le dépôt d'origine (VictoriaCityLab) n'existe plus sur GitHub, et
aucune copie n'a été retrouvée le 27 septembre 2026 : ni sur le VPS (dépôts,
archive d'avant l'unification), ni dans les dossiers du PC (caches LFS compris).

Les pointeurs ont été retirés : ils faisaient échouer tout `git clone`. Ce sont
des rendus de contrôle, refaits par la fabrique Blender quand on la relance.

| fichier | oid sha256 |
|---|---|
| `fabrique/donnees/Reports/QA/Clay/building_sawmill_frontier_01_a_clay_dessus.png` | `148e8c4523c6cb231113e15d6b4da37cafaf20752d9b550dd9a3dc0473328e6f` |
| `fabrique/donnees/Reports/QA/Clay/building_sawmill_frontier_01_a_clay_profil.png` | `1e4e4358cd21bfca76630b78394273334b11f8ec3f16796b1cfd92254eaea02d` |
| `fabrique/donnees/Reports/QA/Clay/building_sawmill_frontier_01_a_clay_rts.png` | `d09c3c3be69bc853c85491d178e3c0e70f3a2cf8a893591022847f5d99bcd2a8` |
| `fabrique/donnees/Reports/QA/Clay/building_sawmill_frontier_01_b_clay_dessus.png` | `547063b895f8c2a91be643573ad3e2c0be22cea7e6908d8b99bede8b7c268a58` |
| `fabrique/donnees/Reports/QA/Clay/building_sawmill_frontier_01_b_clay_profil.png` | `3d30c11cbfebfedab0e019daf63386d6e9b82f72ba1cea8278b7df929de61dd1` |
| `fabrique/donnees/Reports/QA/Clay/building_sawmill_frontier_01_b_clay_rts.png` | `836c0c4b3edc36c632b3a51b734be0a0c3e578f37c4f87faf376192099732ca9` |
| `fabrique/donnees/Reports/QA/Clay/building_sawmill_frontier_01_c_clay_dessus.png` | `9ffd696212b286d58aa0f0a0df954205114522453a96cfc16682fab256fd34ec` |
| `fabrique/donnees/Reports/QA/Clay/building_sawmill_frontier_01_c_clay_profil.png` | `eba3b0331a8b3625d26d3f23b8033077e162fd5860f358bfaa504c42c83931fd` |
| `fabrique/donnees/Reports/QA/Clay/building_sawmill_frontier_01_c_clay_rts.png` | `5cfbfd0c565b0fadbf8a1207a9fdd72dca951c363af5aa1465cd4db531b2c756` |
| `fabrique/donnees/Reports/QA/Scenes/village_place.png` | `2547d1293a4ad389290dbc0f0d7c87b1f0007480b791b385095ddd27e53d02c2` |
| `fabrique/donnees/Reports/QA/Scenes/village_revue.png` | `f0a89862d9a5857acd374550c6302888153dae664909816569ff8a7618e04510` |
| `fabrique/donnees/Reports/QA/Scenes/village_rue.png` | `cdb5c17bffed54dba312f8b65e3a4757246f789b442b49b8638198efdace20a8` |
| `fabrique/donnees/Reports/QA/building_barn_frontier_01_c_construction_board.png` | `a51e4b79304f4b34bad8f572f8a7707957d61bcc78a1844616528d3e05245a46` |
| `fabrique/donnees/Reports/QA/building_barn_frontier_01_contact_96px.png` | `58e43ffa17f83cf4adeca071b642e3cc85886d003e522153cabae7c61bd36f9e` |
| `fabrique/donnees/Reports/QA/building_blacksmith_frontier_01_c_construction_board.png` | `376a88e89d7ff6c8bf68090c86c44d071aab691e0331a18ec2a1da45fb7fcdcd` |
| `fabrique/donnees/Reports/QA/building_blacksmith_frontier_01_contact_96px.png` | `56ef69abd4588242df89a951b5485569058140cf03ab465219f3941425eb89cb` |
| `fabrique/donnees/Reports/QA/building_chapel_frontier_01_c_construction_board.png` | `19169c123b7cec8c1f1e05aa0c2a6d8d380fafa794530f59e2b3d30a57103b39` |
| `fabrique/donnees/Reports/QA/building_chapel_frontier_01_contact_96px.png` | `7e0f0a779c46851ebd05cc1acc310af36bac6b81cf4a79f43768fa3be8d0eb80` |
| `fabrique/donnees/Reports/QA/building_granary_frontier_01_c_construction_board.png` | `da606cc78057cb0f8e6e58389b6a034a44aa3dd56553ee9adb00647feac350be` |
| `fabrique/donnees/Reports/QA/building_granary_frontier_01_contact_96px.png` | `aa425f271ff33c144ec0678368a3fe1d1f79c4fcf188339e2f753d50c306a637` |
| `fabrique/donnees/Reports/QA/building_market_frontier_01_c_construction_board.png` | `50007d0a03cb7236b3a2d7c37a0fb77a7fa27978f7fda27d654d64a08f12b815` |
| `fabrique/donnees/Reports/QA/building_market_frontier_01_contact_96px.png` | `933da89ae4ec6f5f59e53f42c6ecfa6877a44543d2a5ff93e33fef76eee1603c` |
| `fabrique/donnees/Reports/QA/building_residence_frontier_01_a_construction_board.png` | `56043ca1953f0210962e6f162ed27b29896dbb5337df0d6f8139d39eb17b4385` |
| `fabrique/donnees/Reports/QA/building_residence_frontier_01_b_construction_board.png` | `b2b332751c4b1241a02536ee0b293ae0ee904b2a47e6571dbea0990baf93c481` |
| `fabrique/donnees/Reports/QA/building_residence_frontier_01_c_construction_board.png` | `608e7cc059f336bd6f9d1276cddc7ee87f3ea6080a34577f48d62022f3585cf7` |
| `fabrique/donnees/Reports/QA/building_residence_frontier_01_contact_96px.png` | `2a6cc6bc4187126dc119f1e27260f98bc3c31c10b9d4742329762f93b2775b6e` |
| `fabrique/donnees/Reports/QA/building_residence_frontier_01_pitch_96px.png` | `f2e3a0296ad5d3d7f27a3949ff881aa32aa360c62c2379e5aac4a044cf046c8a` |
| `fabrique/donnees/Reports/QA/building_residence_frontier_01_schemes_640px.png` | `0376fc44d284b07c9992c7986830c0de81b8e831f6beaabfcb6104dc90fa603e` |
| `fabrique/donnees/Reports/QA/building_sawmill_frontier_01_c_construction_board.png` | `9ba166606c451371d880d256c6398bb044b8675243adfbeffe4481241a631b23` |
| `fabrique/donnees/Reports/QA/building_sawmill_frontier_01_contact_96px.png` | `af3637723cd71090133c4dcc4495cab7ec142607e3b13f7ed04e6abac33ec08b` |
| `fabrique/donnees/Reports/QA/building_warehouse_frontier_01_c_construction_board.png` | `3cc6668c6170bfd6e2e5d4dc8da939e565f23704fbf1a871366efe3db1f74773` |
| `fabrique/donnees/Reports/QA/building_warehouse_frontier_01_contact_96px.png` | `d92e5eb783c18398be55ffb0d74a1b4d1dbee82e76e0f4088340f22e54d83931` |
| `fabrique/donnees/Reports/QA/factory_review_board.png` | `89594d132315611a35add50a254d40e8d75e4dde34bf0003d27962d3d8d66552` |
| `fabrique/donnees/Reports/QA/village_plan_map.png` | `5a0a23fdfda6661b43eefb32b73d9ecdcc638f2f7c990447776da89c2700ba5c` |
