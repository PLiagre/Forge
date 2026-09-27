"""Copie les livrables Blender locaux dans la scène Unity demandée."""
import shutil
from pathlib import Path
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'local3d/v1'
DEST=ROOT/'unity/Assets/ForgeLocal3D'
for folder in ('Models','Textures'):
    (DEST/folder).mkdir(parents=True,exist_ok=True)
shutil.copy2(OUT/'exports/Forge_Village_V1.fbx',DEST/'Models/Forge_Village_V1.fbx')
shutil.copy2(OUT/'rapport.json',DEST/'rapport.json')
for path in (OUT/'textures').glob('*.png'):
    shutil.copy2(path,DEST/'Textures'/path.name)
metal=Image.open(OUT/'textures/CityLabTrimV2_Metallic.png').convert('L')
rough=Image.open(OUT/'textures/CityLabTrimV2_Roughness.png').convert('L')
Image.merge('RGBA',(metal,metal,metal,ImageOps.invert(rough))).save(DEST/'Textures/CityLabTrimV2_MetallicGloss.png')
print('Exports et cartes Unity préparés.')
