"""Reconstruit les six cartes du dépôt dans le dossier de livraison locale."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'fabrique'))
from generate_pbr_trim import build_maps, save_rgb, save_gray

recipe = json.loads((ROOT / 'fabrique/donnees/Recipes/texture_citylab_trim_v2.json').read_text(encoding='utf-8'))
output = ROOT / 'local3d/v1/textures'
output.mkdir(parents=True, exist_ok=True)
for name, array in build_maps(recipe).items():
    path = output / f'CityLabTrimV2_{name}.png'
    (save_rgb if array.ndim == 3 else save_gray)(path, array)
print(f'Six cartes PBR reconstruites : {output}')
