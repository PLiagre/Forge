"""`python3 -m atelier.fabrique <commande>` : les outils locaux de l'usine d'assets.

    decouper-planche  découpe une planche RxC générée par `agy` en icônes PNG détourées
    detourer          détoure et normalise une icône ou un blason (alpha strict 0/255)
    pbr               rend une texture raccordable et génère albedo/height/normal/roughness/ao
    enregistrer       inscrit un asset dans `assets/manifeste.json`
    controler         vérifie tous les assets du manifeste (code 1 au moindre défaut)
    procede           affiche le procédé optimal retenu pour un type d'asset
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .controle import controler_manifeste
from .icones import decouper_planche, detourer_fichier, lire_grille
from .manifeste import CHEMIN_MANIFESTE, enregistrer_asset
from .procedes import TYPES_ASSETS, procede_pour
from .textures import erreur_couture, generer_pbr


def _cmd_decouper(args: argparse.Namespace) -> int:
    noms = [n.strip() for n in args.noms.split(",") if n.strip()]
    sorties = decouper_planche(
        args.planche, args.sortie, grille=lire_grille(args.grille), noms=noms,
        taille=args.taille, marge=args.marge, mode=args.detourer, seuil=args.seuil,
    )
    for chemin in sorties:
        print(chemin.as_posix())
    return 0


def _cmd_detourer(args: argparse.Namespace) -> int:
    cible = detourer_fichier(
        args.entree, args.sortie, taille=args.taille, marge=args.marge, mode=args.detourer, seuil=args.seuil,
    )
    print(cible.as_posix())
    return 0


def _cmd_pbr(args: argparse.Namespace) -> int:
    chemins = generer_pbr(
        args.albedo, args.sortie, nom=args.nom, taille=args.taille, raccorder=args.raccorder,
        force_normale=args.force_normale,
    )
    from PIL import Image
    with Image.open(chemins["albedo"]) as im:
        couture = erreur_couture(im)
    for cle, chemin in chemins.items():
        print(f"{cle:10} {chemin.as_posix()}")
    print(f"couture    {couture:.4f}")
    return 0


def _cmd_enregistrer(args: argparse.Namespace) -> int:
    entree = enregistrer_asset(
        args.manifeste, asset_id=args.id, type_asset=args.type, fichiers=args.fichiers,
        dimensions=args.dimensions,
        transparent=None if args.transparent is None else (args.transparent == "oui"),
        raccordable=None if args.raccordable is None else (args.raccordable == "oui"),
        lot=args.lot, demande_par=args.demande_par, references_da=args.references_da or None,
    )
    print(f"enregistré : {entree['id']} ({len(entree['fichiers'])} fichier(s))")
    return 0


def _cmd_controler(args: argparse.Namespace) -> int:
    defauts = controler_manifeste(args.racine, args.manifeste, exiger_non_vide=args.strict)
    if defauts:
        for d in defauts:
            print(f"FAIL  [{d.asset_id}] {d.fichier} — {d.raison}", file=sys.stderr)
        return 1
    print("PASS  contrôle des assets visuels vert")
    return 0


def _cmd_procede(args: argparse.Namespace) -> int:
    print(procede_pour(args.type).consigne())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m atelier.fabrique")
    sous = parser.add_subparsers(dest="commande", required=True)

    p_dec = sous.add_parser("decouper-planche", help="découper une planche d'icônes en PNG détourés")
    p_dec.add_argument("planche", type=Path)
    p_dec.add_argument("--grille", required=True, help="ex. 3x3 ou 4x4")
    p_dec.add_argument("--noms", required=True, help="noms séparés par des virgules")
    p_dec.add_argument("--sortie", type=Path, required=True)
    p_dec.add_argument("--taille", type=int, default=128)
    p_dec.add_argument("--marge", type=float, default=0.08)
    p_dec.add_argument("--detourer", choices=("auto", "fond", "aucun"), default="auto")
    p_dec.add_argument("--seuil", type=float, default=28.0)
    p_dec.set_defaults(func=_cmd_decouper)

    p_det = sous.add_parser("detourer", help="détourer et normaliser une image (alpha strict 0/255)")
    p_det.add_argument("entree", type=Path)
    p_det.add_argument("sortie", type=Path)
    p_det.add_argument("--taille", type=int, default=None)
    p_det.add_argument("--marge", type=float, default=0.08)
    p_det.add_argument("--detourer", choices=("auto", "fond", "aucun"), default="auto")
    p_det.add_argument("--seuil", type=float, default=28.0)
    p_det.set_defaults(func=_cmd_detourer)

    p_pbr = sous.add_parser("pbr", help="rendre raccordable et générer les cartes PBR")
    p_pbr.add_argument("albedo", type=Path)
    p_pbr.add_argument("sortie", type=Path)
    p_pbr.add_argument("--nom", required=True)
    p_pbr.add_argument("--taille", type=int, default=None)
    p_pbr.add_argument("--raccorder", action="store_true", default=False)
    p_pbr.add_argument("--force-normale", type=float, default=3.0)
    p_pbr.set_defaults(func=_cmd_pbr)

    p_enr = sous.add_parser("enregistrer", help="inscrire un asset dans assets/manifeste.json")
    p_enr.add_argument("--manifeste", type=Path, default=CHEMIN_MANIFESTE)
    p_enr.add_argument("--id", required=True)
    p_enr.add_argument("--type", choices=TYPES_ASSETS, required=True)
    p_enr.add_argument("--fichiers", nargs="+", required=True)
    p_enr.add_argument("--dimensions", default="")
    p_enr.add_argument("--transparent", choices=("oui", "non"), default=None)
    p_enr.add_argument("--raccordable", choices=("oui", "non"), default=None)
    p_enr.add_argument("--lot", type=int, default=None)
    p_enr.add_argument("--demande-par", type=int, default=None)
    p_enr.add_argument("--references-da", nargs="*", default=[])
    p_enr.set_defaults(func=_cmd_enregistrer)

    p_ctl = sous.add_parser("controler", help="contrôler tous les assets du manifeste")
    p_ctl.add_argument("--racine", type=Path, default=Path("."))
    p_ctl.add_argument("--manifeste", type=Path, default=CHEMIN_MANIFESTE)
    p_ctl.add_argument("--strict", action="store_true", default=False)
    p_ctl.set_defaults(func=_cmd_controler)

    p_pro = sous.add_parser("procede", help="afficher le procédé optimal d'un type d'asset")
    p_pro.add_argument("type", choices=TYPES_ASSETS)
    p_pro.set_defaults(func=_cmd_procede)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
