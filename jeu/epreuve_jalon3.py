"""Réunit les contrôles du jalon 3 et une capture neuve, hors du dépôt."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

CAS = {
    'sim/tests/test_lieux.py': ['surface_des_lieux_fait_la_cellule_exactement', 'identite_et_bourg_unique'],
    'sim/tests/test_maisons.py': ['maitre_monde', 'maitre_contre_epreuves'],
    'sim/tests/test_prelevement.py': ['jalon3_lieux', 'jalon3_destination_annuelle', 'conservation_sur_un_an',
                                   *[f'jalon3_lanceur[{n}-{code}]' for n, code in [('aucun', 0), ('vide', 1), ('absent', 1), ('ignore', 1), ('echec', 1), ('ancienne_image', 1), ('impossible', 2)]],
                                   'bar_paie_les_valois', 'deux_etages_et_pyramide_videe', 'departs_direction_et_contre_epreuves'],
    'sim/tests/test_distribution_interieure.py': ['sans_chemin', 'sans_chemin_part_locale_par_surface', 'conservation',
                                               *[f'consommation_par_lieu[{p}]' for p in ['0-plaine-populations0-paniers0-restes0-40', '10-plaine-populations1-paniers1-restes1-26', '10-montagne-populations2-paniers2-restes2-34', '10-plaine-populations3-paniers3-restes3-30']],
                                               'consommation_par_lieu_sans_repartage_inutile', 'bourg_miniers_ont_faim'],
    'forge/tests/test_forge.py': ['encart_assemblage[False]', 'encart_assemblage[True]', 'encart_refus'],
}


def main():
    class Arguments(argparse.ArgumentParser):
        def error(self, message):
            self.exit(2, f'Arguments invalides : {message}\n')
    arguments = Arguments(description=__doc__)
    arguments.add_argument('--sortie', required=True, type=Path)
    sortie = arguments.parse_args().sortie.resolve()
    jeu = Path(__file__).resolve().parent
    if sortie.is_relative_to(jeu.parent):
        arguments.error('la sortie doit être hors du dépôt')
    try:
        if importlib.util.find_spec('pytest') is None:
            raise OSError('pytest indisponible')
        sortie.mkdir(parents=True, exist_ok=True)
        with (sortie / 'preuve.txt').open('w', encoding='utf-8') as rapport:
            def executer(options):
                environnement = dict(os.environ, PYTEST_ADDOPTS='')
                resultat = subprocess.run([sys.executable, '-m', *options], cwd=jeu, env=environnement,
                                          stdout=rapport, stderr=subprocess.STDOUT)
                rapport.flush()
                if options[0] == 'forge' and resultat.returncode == 2:
                    raise OSError('forge ne peut pas produire la capture')
                if resultat.returncode:
                    raise AssertionError(f'commande {options[0]} refusée (code {resultat.returncode})')
            xml = sortie / 'controles.xml'
            xml.unlink(missing_ok=True)
            noeuds = [f'{fichier}::test_{nom}' for fichier, noms in CAS.items() for nom in noms]
            executer(['pytest', *noeuds, '-q', '-s', '-x', '-o', 'addopts=', f'--junitxml={xml}'])
            cas = ET.parse(xml).findall('.//testcase')
            executes = {(c.get('classname'), c.get('name')) for c in cas}
            attendus = {(f.removesuffix('.py').replace('/', '.'), f'test_{n}') for f, noms in CAS.items() for n in noms}
            if not cas or executes != attendus or any(c.find(tag) is not None for c in cas for tag in ('skipped', 'failure', 'error')):
                raise AssertionError('contrôle absent, ignoré ou en échec')
            capture = sortie / 'capture'
            capture.mkdir(exist_ok=True)
            fichiers = [capture / nom for nom in ('carte.png', 'monde.json', 'resume.json')]
            for fichier in fichiers:
                fichier.unlink(missing_ok=True)
            executer(['forge', '--ticks', '365', '--seed', '0', '--depart', '1', '--sans-chronique',
                      '--largeur', '900', '--sortie', str(capture)])
            if not all(f.is_file() and f.stat().st_size > 0 for f in fichiers):
                raise AssertionError('capture neuve absente ou vide')
            rapport.write('\nJ3 prouvé sur cette branche.\n' + '\n'.join(map(str, fichiers)) + '\n')
    except AssertionError as erreur:
        print(f'Preuve refusée : {erreur}', file=sys.stderr)
        return 1
    except (OSError, ET.ParseError) as erreur:
        print(f'Exécution impossible : {erreur}', file=sys.stderr)
        return 2
    print(f'J3 prouvé sur cette branche : {sortie / "preuve.txt"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
