"""`python3 -m atelier <commande>` : la chaîne de Forge, à la main ou par le cron.

    agents     la table des rôles : outil/modèle et secours
    veille     ce qui manque pour tourner (binaires, jetons, branchement)
    sonde      chaque agent répond-il, en non interactif, avec son modèle ?
    tour       un tour du pilote (--a-sec : lire et dire, sans rien faire)
    journal    le journal du matin, dans l'issue « Journal de Forge »
    boussole   la comparaison de la semaine avec CAP.md
    pc         le côté PC d'un lot « machine : pc » (appelé par lot-pc.yml)
    traces     ce qui fait rougir les contrôles d'une PR
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from . import agents as agents_mod
from . import journal, traces
from .depot import Depot
from .github import GitHub
from .projet import ProjetIncomplet, charger, table_des_roles


def _racine(args: argparse.Namespace) -> Path:
    return Path(args.projet or os.environ.get("ATELIER_PROJET") or Path.cwd()).resolve()


def _cmd_agents(args: argparse.Namespace) -> int:
    print(table_des_roles(charger(_racine(args))))
    return 0


def _cmd_veille(args: argparse.Namespace) -> int:
    fautes = 0

    def dire(ok: bool | None, quoi: str) -> None:
        nonlocal fautes
        etiquette = {True: "PASS", False: "FAIL", None: "?   "}[ok]
        fautes += ok is False
        print(f"{etiquette}  {quoi}")

    try:
        projet = charger(_racine(args))
        dire(True, f"branchement — {projet.racine / 'atelier.toml'}")
    except ProjetIncomplet as e:
        dire(False, f"branchement — {e}")
        return 1
    for outil in sorted({a.outil for p in projet.postes.values() for a in p.agents}):
        binaire = {"claude": "claude", "codex": "codex", "cursor": "cursor-agent"}[outil]
        chemin = shutil.which(binaire)
        if not chemin:
            dire(False, f"{binaire} — absent du PATH")
            continue
        try:
            version = subprocess.run([chemin, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
            dire(bool(version), f"{binaire} — {version.splitlines()[0] if version else 'ne rend pas sa version'}")
        except (OSError, subprocess.TimeoutExpired) as e:
            dire(False, f"{binaire} — ne démarre pas : {e}")
    jeton = agents_mod.FICHIER_JETON_CLAUDE
    if jeton.is_file():
        mode = jeton.stat().st_mode & 0o777
        dire(mode & 0o077 == 0 or sys.platform.startswith("win"),
             f"jeton Claude longue durée — {jeton} (mode {oct(mode)})")
    else:
        dire(None, f"jeton Claude longue durée absent ({jeton}) : la session de `claude` fait foi")
    fuites = [k for k in agents_mod.CLES_API if os.environ.get(k)]
    dire(None if fuites else True, "clés d'API dans l'environnement : " + (", ".join(fuites) + " (retirées avant chaque agent)" if fuites else "aucune"))
    try:
        GitHub(projet.depot).json("repo", "view", projet.depot, "--json", "name")
        dire(True, f"gh — accès à {projet.depot}")
    except Exception as e:  # noqa: BLE001
        dire(False, f"gh — {e}")
    return 1 if fautes else 0


def _cmd_sonde(args: argparse.Namespace) -> int:
    """Chaque agent distinct de [agents], appelé comme la chaîne l'appelle."""
    projet = charger(_racine(args))
    vus = set()
    fautes = 0
    for poste in projet.postes.values():
        for agent in poste.agents:
            cle = (str(agent), poste.lecture_seule)
            if cle in vus or (args.outil and agent.outil != args.outil):
                continue
            vus.add(cle)
            unique = type(poste)(role=poste.role, agents=(agent,))
            res = agents_mod.invoquer(unique, "Réponds exactement par le mot : OK", projet.racine, 300)
            ok = res.reussi and "OK" in res.texte
            fautes += not ok
            detail = res.texte.strip().splitlines()[-1][:80] if res.texte.strip() else "; ".join(res.essais)
            print(f"{'PASS' if ok else 'FAIL'}  {str(agent):34} {'lecture seule' if poste.lecture_seule else 'écriture':14} {detail}")
    return 1 if fautes else 0


def _pilote(args: argparse.Namespace):
    from .pilote import Pilote
    projet = charger(_racine(args))
    gh = GitHub(projet.depot)
    depot = Depot(projet.racine, projet.branche_base)
    if getattr(args, "a_sec", False):
        from .asec import GitHubASec, DepotASec, executeur_a_sec
        # À sec, rien ne s'écrit : pas même le journal local, que le
        # chroniqueur et la veille lisent comme ce qui a vraiment eu lieu.
        return Pilote(projet, GitHubASec(projet.depot), DepotASec(projet.racine, projet.branche_base),
                      executeur_agents=executeur_a_sec, journal=Path(os.devnull))
    return Pilote(projet, gh, depot)


def _cmd_tour(args: argparse.Namespace) -> int:
    for ligne in _pilote(args).tour():
        print(ligne)
    return 0


def _cmd_journal(args: argparse.Namespace) -> int:
    projet = charger(_racine(args))
    print(journal.ecrire(GitHub(projet.depot), projet, publier=not args.sans_publier))
    return 0


def _cmd_boussole(args: argparse.Namespace) -> int:
    projet = charger(_racine(args))
    print(journal.boussole(GitHub(projet.depot), projet, publier=not args.sans_publier))
    return 0


def _cmd_pc(args: argparse.Namespace) -> int:
    from . import pc
    racine = Path(args.depot_local).resolve()
    projet = charger(_racine(args))
    lignes = pc.travailler(projet, GitHub(projet.depot), Depot(racine, projet.branche_base),
                           issue=args.issue, branche=args.branche, pr=args.pr, essai=args.essai,
                           action=args.action, vendor=Path(args.vendor) if args.vendor else None)
    for ligne in lignes:
        print(ligne)
    return 0


def _cmd_traces(args: argparse.Namespace) -> int:
    code, texte = traces.rapport(args.pr, args.lignes, args.depot)
    print(texte)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atelier", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--projet", help="racine du dépôt (défaut : ATELIER_PROJET, sinon le dossier courant)")
    sous = parser.add_subparsers(dest="commande", required=True)
    sous.add_parser("agents", help="la table des rôles").set_defaults(f=_cmd_agents)
    sous.add_parser("veille", help="ce qui manque pour tourner").set_defaults(f=_cmd_veille)
    sonde = sous.add_parser("sonde", help="chaque agent répond-il avec son modèle ?")
    sonde.add_argument("--outil", choices=["claude", "codex", "cursor"])
    sonde.set_defaults(f=_cmd_sonde)
    tour = sous.add_parser("tour", help="un tour du pilote")
    tour.add_argument("--a-sec", action="store_true", help="lire et dire, sans rien écrire ni invoquer")
    tour.set_defaults(f=_cmd_tour)
    for nom, f in (("journal", _cmd_journal), ("boussole", _cmd_boussole)):
        p = sous.add_parser(nom)
        p.add_argument("--sans-publier", action="store_true")
        p.set_defaults(f=f)
    pc = sous.add_parser("pc", help="le côté PC d'un lot « machine : pc »")
    pc.add_argument("--depot-local", required=True, help="le dépôt du PC (D:\\Forge)")
    pc.add_argument("--issue", type=int, required=True)
    pc.add_argument("--branche", required=True)
    pc.add_argument("--pr", type=int, required=True)
    pc.add_argument("--essai", type=int, default=0)
    pc.add_argument("--action", default="coder")
    pc.add_argument("--vendor", help="les packs de l'Asset Store à relier (D:\\Forge\\3d\\unity\\Assets\\Vendor)")
    pc.set_defaults(f=_cmd_pc)
    tr = sous.add_parser("traces", help="ce qui fait rougir les contrôles d'une PR")
    tr.add_argument("--pr", type=int, required=True)
    tr.add_argument("--lignes", type=int, default=60)
    tr.add_argument("--depot")
    tr.set_defaults(f=_cmd_traces)
    args = parser.parse_args(argv)
    try:
        return args.f(args)
    except ProjetIncomplet as e:
        print(f"FAIL  {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
