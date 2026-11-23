"""`python3 -m atelier <commande>` : la chaîne de Forge, à la main ou par le cron.

    agents     la table des rôles : modèle, effort, délai
    veille     ce qui manque pour tourner (binaire, jeton, branchement)
    sonde      chaque rôle répond-il, sans écran, avec son modèle ?
    tour       un tour du pilote (--a-sec : lire et dire, sans rien faire ;
               --lot N : ne faire avancer que ce lot)
    journal    le journal du matin, dans sa propre issue « Journal du JJ/MM/AAAA »
    demo       la démo : le build figé de l'étape et la note du CTO, dès qu'elle n'a plus de lot ouvert
    couts      ce que le palier en cours a coûté, par rôle et par lot
    pc         un pas du meneur d'un lot « pc » (appelé par lot-pc.yml)
    marquer-attente
               la réponse d'un passage du PC tombé sans répondre (lot-pc.yml)
    testeur    le testeur joue le build figé de l'étape, dans la session ouverte du PC
               (appelé par la tâche planifiée « ForgeTesteur », que lance testeur-pc.yml)
    traces     ce qui fait rougir les contrôles d'une PR
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from . import agents as agents_mod
from . import journal, traces
from .depot import Depot
from .github import GitHub
from .projet import CHEF, DEVELOPPEUR, MACHINES, OUTILS, ROLES, ProjetIncomplet, charger, table_des_roles


def _racine(args: argparse.Namespace) -> Path:
    return Path(args.projet or os.environ.get("ATELIER_PROJET") or Path.cwd()).resolve()


def journal_local() -> Path:
    """Le journal de cette machine : un fait par ligne. Seules les commandes
    qui tournent pour de vrai le nomment ; le pilote n'en devine aucun."""
    return Path(os.environ.get("ATELIER_JOURNAL") or Path.home() / ".atelier" / "journal.jsonl")


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
    for outil in sorted({a.outil for a in projet.agents.values()}):
        binaire = OUTILS[outil]
        # Lancé comme la chaîne le lance : sous Windows, un .cmd passe par son
        # node.exe, jamais par cmd.exe (`agents.lancement`).
        try:
            commande, env = agents_mod.lancement([binaire, "--version"], dict(os.environ))
        except agents_mod.Introuvable as e:
            dire(False, f"{binaire} — {e}")
            continue
        try:
            version = subprocess.run(commande, env=env, capture_output=True, text=True, encoding="utf-8",
                                     errors="replace", timeout=60).stdout.strip()
            dire(bool(version), f"{binaire} — {version.splitlines()[0] if version else 'ne rend pas sa version'}")
        except (OSError, subprocess.TimeoutExpired) as e:
            dire(False, f"{binaire} — ne démarre pas : {e}")
    jeton = agents_mod.FICHIER_JETON_CLAUDE
    if jeton.is_file() and jeton.stat().st_size > 0:
        mode = jeton.stat().st_mode & 0o777
        dire(mode & 0o077 == 0 or sys.platform.startswith("win"),
             f"jeton Claude longue durée — {jeton} (mode {oct(mode)})")
    else:
        dire(None, f"jeton Claude longue durée absent ou vide ({jeton}) : la session de `claude` fait foi")
    fuites = [k for k in agents_mod.CLES_API if os.environ.get(k)]
    dire(None if fuites else True, "clés d'API dans l'environnement : "
         + (", ".join(fuites) + " (retirées avant chaque agent)" if fuites else "aucune"))
    dire(agents_mod.GARDE.is_file(), f"garde des commandes — {agents_mod.GARDE}")
    try:
        GitHub(projet.depot).json("repo", "view", projet.depot, "--json", "name")
        dire(True, f"gh — accès à {projet.depot}")
    except Exception as e:  # noqa: BLE001
        dire(False, f"gh — {e}")
    return 1 if fautes else 0


def _cmd_sonde(args: argparse.Namespace) -> int:
    """Chaque rôle, appelé comme la chaîne l'appelle ; un rôle qui écrit doit
    vraiment écrire (`agents.sonder`). Deux rôles du même modèle se sondent une fois."""
    projet = charger(_racine(args))
    vus = set()
    fautes = 0
    for role in ([args.role] if args.role else ROLES):
        agent = projet.agent(role)
        ecrit = role in (CHEF, DEVELOPPEUR)
        if (str(agent), ecrit) in vus:
            continue
        vus.add((str(agent), ecrit))
        ok, detail = agents_mod.sonder(agent, role, lecture_seule=not ecrit)
        fautes += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {role:12} {str(agent):34} {'écriture' if ecrit else 'lecture seule':14} {detail}")
    return 1 if fautes else 0


def _pilote(args: argparse.Namespace):
    from .pilote import Pilote
    from .verrous import Verrous
    projet = charger(_racine(args))
    gh = GitHub(projet.depot)
    if getattr(args, "a_sec", False):
        from .asec import GitHubASec, DepotASec, executeur_a_sec
        # À sec, rien ne s'écrit : ni le journal local, ni une trace d'appel.
        return Pilote(projet, GitHubASec(projet.depot), DepotASec(projet.racine, projet.branche_base),
                      executeur_agents=executeur_a_sec, journal=Path(os.devnull), garder_les_traces=False,
                      seul=getattr(args, "lot", None))
    # Plusieurs tours tournent en même temps : ils partagent leurs verrous.
    verrous = Verrous()
    return Pilote(projet, gh, Depot(projet.racine, projet.branche_base, verrous=verrous), verrous=verrous,
                  journal=journal_local(), seul=getattr(args, "lot", None))


def _cmd_tour(args: argparse.Namespace) -> int:
    pilote = _pilote(args)
    # Assez de places pour chaque lot que les machines tiennent, plus deux
    # tours qui rangent ; au-delà, un tour passe : si GitHub ne répond plus,
    # les tours ne s'empilent pas toutes les deux minutes.
    places = sum(pilote.projet.capacite(m) for m in MACHINES) + 2
    with pilote.verrous.place("tour", places) as libre:
        if not libre:
            print(f"RIEN — {places} tours tournent déjà")
            return 0
        for ligne in pilote.tour():
            print(ligne)
    return 0


def _cmd_journal(args: argparse.Namespace) -> int:
    projet = charger(_racine(args))
    print(journal.ecrire(GitHub(projet.depot), projet, publication=not args.sans_publier))
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    from . import palier
    poser = palier.demo if args.maintenant else palier.demo_si_videe
    print(poser(_pilote(args), publication=not args.sans_publier))
    return 0


def _cmd_couts(args: argparse.Namespace) -> int:
    projet = charger(_racine(args))
    gh = GitHub(projet.depot)
    if args.lot:
        print(journal.table_des_couts(journal.mesures_des_lots(gh, projet, args.lot)))
    else:
        print(journal.couts_du_palier(gh, projet))
    return 0


def _cmd_pc(args: argparse.Namespace) -> int:
    from . import pc
    from .verrous import Verrous
    projet = charger(_racine(args))
    # Deux passages peuvent tourner ensemble sur le PC, chacun dans son
    # chantier : ils se partagent le dépôt, la branche des captures et les
    # places des agents.
    verrous = Verrous()
    lignes = pc.travailler(projet, GitHub(projet.depot),
                           Depot(Path(args.depot_local).resolve(), projet.branche_base, verrous=verrous),
                           issue=args.issue, journal=journal_local(), chantier=args.chantier, verrous=verrous,
                           vendor=Path(args.vendor) if args.vendor else None)
    for ligne in lignes:
        print(ligne)
    return 0


def _cmd_marquer_attente(args: argparse.Namespace) -> int:
    from . import pc
    projet = charger(_racine(args))
    print(pc.repondre_au_silence(projet, GitHub(projet.depot), Depot(projet.racine, projet.branche_base),
                                 issue=args.issue, raison=args.raison, journal=journal_local()))
    return 0


def _cmd_testeur(args: argparse.Namespace) -> int:
    from . import testeur
    from .verrous import Verrous
    projet = charger(_racine(args))
    gh = GitHub(projet.depot)
    if args.attente:
        print(testeur.repondre_au_silence(gh, raison=args.attente))
        return 0
    local = Path(args.depot_local or projet.racine).resolve()
    builds = Path(args.builds).resolve() if args.builds else local / "builds"
    if args.sonde:
        # Le bureau seul, sans rien lancer : la preuve que ce processus tourne dans une session qui a un écran.
        libre, dit = testeur.Bureau(build=builds / "sonde", sortie=Path.home() / ".atelier" / "testeur" / "sonde").sonde()
        print(dit)
        return 0 if libre else 4
    verrous = Verrous()
    lignes = testeur.jouer(projet, gh, Depot(local, projet.branche_base, verrous=verrous), journal=journal_local(),
                           builds=builds, palier=args.palier, build=args.build,
                           force=args.maintenant or args.palier is not None, publication=not args.sans_publier,
                           verrous=verrous, **({"attente": 0} if args.sans_attendre else {}))
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
    sonde = sous.add_parser("sonde", help="chaque rôle répond-il avec son modèle ?")
    sonde.add_argument("--role", choices=ROLES, help="ce seul rôle")
    sonde.set_defaults(f=_cmd_sonde)
    tour = sous.add_parser("tour", help="un tour du pilote")
    tour.add_argument("--a-sec", action="store_true", help="lire et dire, sans rien écrire ni invoquer")
    tour.add_argument("--lot", type=int, help="ne faire avancer que ce lot, quel que soit son palier")
    tour.set_defaults(f=_cmd_tour)
    for nom, f in (("journal", _cmd_journal), ("demo", _cmd_demo)):
        p = sous.add_parser(nom)
        p.add_argument("--sans-publier", action="store_true")
        p.set_defaults(f=f)
        if nom == "demo":
            p.add_argument("--maintenant", action="store_true",
                           help="figer et noter tout de suite, même si l'étape a encore des lots ouverts")
    couts = sous.add_parser("couts", help="ce que la chaîne a coûté, par rôle et par lot")
    couts.add_argument("--lot", type=int, action="append", help="ces lots seulement (répétable)")
    couts.set_defaults(f=_cmd_couts)
    pc = sous.add_parser("pc", help="un pas du meneur d'un lot « pc »")
    pc.add_argument("--depot-local", required=True, help="le dépôt du PC (D:\\Forge)")
    pc.add_argument("--issue", type=int, required=True)
    pc.add_argument("--chantier", default="pc", help="le chantier du PC où vit le lot (pc, pc-2…)")
    pc.add_argument("--vendor", help="les packs de l'Asset Store à relier (D:\\Forge\\3d\\unity\\Assets\\Vendor)")
    pc.set_defaults(f=_cmd_pc)
    attente = sous.add_parser("marquer-attente", help="la réponse d'un passage du PC tombé sans répondre")
    attente.add_argument("--issue", type=int, required=True)
    attente.add_argument("--raison", required=True)
    attente.set_defaults(f=_cmd_marquer_attente)
    joueur = sous.add_parser("testeur", help="le testeur joue le build figé de l'étape (sur le PC, session ouverte)")
    joueur.add_argument("--depot-local", help="le dépôt du PC (D:\\Forge) : ses builds, sa branche des captures")
    joueur.add_argument("--builds", help="le dossier des builds (défaut : <dépôt du PC>\\builds)")
    joueur.add_argument("--palier", type=int, help="jouer ce palier, même fermé, sans attendre l'envoi du pilote")
    joueur.add_argument("--build", help="le nom du build à jouer (défaut : palier-<n>)")
    joueur.add_argument("--maintenant", action="store_true", help="jouer sans attendre l'envoi du pilote")
    joueur.add_argument("--sans-publier", action="store_true", help="ne rien écrire sur GitHub : le rapport s'affiche ici")
    joueur.add_argument("--sans-attendre", action="store_true",
                        help="si le bureau est occupé, répondre tout de suite au lieu d'attendre qu'il se libère")
    joueur.add_argument("--sonde", action="store_true", help="dire seulement si le bureau est libre, sans rien lancer")
    joueur.add_argument("--attente", metavar="RAISON",
                        help="répondre par une attente à l'envoi du pilote : le passage n'a pas pu partir")
    joueur.set_defaults(f=_cmd_testeur)
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
