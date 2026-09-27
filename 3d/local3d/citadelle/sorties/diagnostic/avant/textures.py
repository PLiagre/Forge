"""Palette froide, pierre stratifiée et ardoises, produites localement."""
from pathlib import Path
from local3d.atelier_v2.textures import save_material

PALETTE = {
    'basalte': ((.105,.126,.142),'stone'),
    'pierre_taille': ((.235,.245,.24),'stone'),
    'calcaire': ((.36,.35,.30),'stone'),
    'roche_noire': ((.125,.15,.17),'rock'),
    'roche_claire': ((.245,.28,.30),'rock'),
    'enduit': ((.31,.275,.22),'plaster'),
    'bois_noir': ((.075,.053,.035),'wood'),
    'bois_vieux': ((.20,.127,.071),'wood'),
    'ardoise': ((.075,.12,.155),'tiles'),
    'neige_givre': ((.67,.76,.81),'plaster'),
    'neige_ombre': ((.42,.52,.58),'plaster'),
    'aiguilles_sombres': ((.022,.068,.059),'leaf'),
    'fer_noir': ((.022,.028,.032),'plaster'),
    'cuivre': ((.31,.18,.07),'plaster'),
    'tissu_bordeaux': ((.14,.018,.027),'plaster'),
    'lumiere': ((1,.39,.055),'plaster'),
    'vitrail_ambre': ((.75,.255,.036),'plaster'),
    'vitrail_bleu': ((.075,.21,.26),'plaster'),
    'sol_pave': ((.18,.195,.20),'stone'),
}

def prepare(folder):
    for i,(name,(color,kind)) in enumerate(PALETTE.items()):
        save_material(Path(folder),name,color,kind,1100+i,.83 if name!='fer_noir' else .48)

if __name__=='__main__':
    prepare(Path(__file__).parent/'sorties/textures')
