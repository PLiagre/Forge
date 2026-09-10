"""Point d'entrée : python3 -m atelier."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import sys
from pathlib import Path

import subprocess

from . import (backends, boite, couches, cycle, echange, etat, feuille, porte,
               projet, quota, reprise, verrou, worktree)
from .etat import FusionInterdite


ROLES = list(boite.ROLES)
ROLES_INVOCABLES = list(backends.ROLES_INVOCABLES)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atelier",
        description="Infrastructure d'agents pour exécuter des lots. Pas un agent de plus.",
    )
    sous = parser.add_subparsers(dest="commande", required=True)

    sous.add_parser("couches", help="afficher les sept couches et qui les occupe")

    doctor = sous.add_parser("doctor", help="vérifier le branchement d'un dépôt produit")
    doctor.add_argument("--projet", required=True)

    portes = sous.add_parser("portes", help="jouer la porte mécanique sur un brief")
    portes.add_argument("--brief", required=True)

    start = sous.add_parser("start", help="préparer un lot (aperçu, ou --run)")
    start.add_argument("brief")
    start.add_argument("--projet", required=True)
    start.add_argument("--run", action="store_true")

    status = sous.add_parser("status", help="lister les runs durables")
    status.add_argument("--projet", required=True)

    verrous = sous.add_parser("verrous", help="fichiers actuellement tenus")
    verrous.add_argument("--projet", required=True)

    sous.add_parser("fusionner", help="refuse toujours — le propriétaire fusionne")

    hop = sous.add_parser("hop", help="choisir un agent d'après des quotas connus")
    hop.add_argument(
        "mesure",
        nargs="+",
        help="paires agent=restant (restant=-1 si inconnu)",
    )

    prochain = sous.add_parser(
        "prochain",
        help="prochaine carte d'un rôle ; RIEN et code 0 si la boîte est vide",
    )
    prochain.add_argument("--projet", required=True)
    prochain.add_argument("--role", required=True, choices=ROLES)
    prochain.add_argument(
        "--champ",
        choices=["lot", "brief", "pr", "note"],
        help="n'imprimer qu'un champ (le shell n'a pas à lire du JSON)",
    )

    deposer = sous.add_parser("deposer", help="poser une carte dans une boîte")
    deposer.add_argument("--projet", required=True)
    deposer.add_argument("--etat", required=True)
    deposer.add_argument("--lot", required=True)
    deposer.add_argument("--brief", required=True)
    deposer.add_argument("--fichier", action="append", default=[])

    avancer = sous.add_parser("avancer", help="passer une carte au rôle suivant")
    avancer.add_argument("--projet", required=True)
    avancer.add_argument("--role", required=True, choices=ROLES)
    avancer.add_argument("--lot", required=True)
    avancer.add_argument("--pr", type=int)
    avancer.add_argument("--note")
    avancer.add_argument("--fichier", action="append", default=[])

    echouer = sous.add_parser("echouer", help="ranger une carte dans echec/")
    echouer.add_argument("--projet", required=True)
    echouer.add_argument("--role", required=True, choices=ROLES)
    echouer.add_argument("--lot", required=True)
    echouer.add_argument("--raison", required=True)
    echouer.add_argument(
        "--cause",
        choices=list(reprise.CAUSES),
        default=reprise.INCONNUE,
        help="le mot que la machine compare pour décider si ça se retente",
    )

    rappeler = sous.add_parser(
        "rappeler",
        help="remettre en circulation les cartes de echec/ qui se retentent",
    )
    rappeler.add_argument("--projet", required=True)
    rappeler.add_argument("--role", required=True, choices=ROLES)

    canal = sous.add_parser(
        "canal", help="ouvrir le canal d'échange d'un worktree, avec sa garde git"
    )
    canal.add_argument("--worktree", required=True)

    ranger = sous.add_parser(
        "ranger", help="enregistrer ce qui traîne dans un worktree, sans rien effacer"
    )
    ranger.add_argument("--worktree", required=True)
    ranger.add_argument("--message", default="atelier : ce que le tour précédent a laissé")

    invocation = sous.add_parser(
        "invocation", help="l'argv d'un rôle — imprimé, jamais lancé"
    )
    invocation.add_argument("--role", required=True, choices=ROLES_INVOCABLES)
    invocation.add_argument("--projet", required=True)
    invocation.add_argument("--lot")
    invocation.add_argument("--brief")
    invocation.add_argument("--pr", type=int, help="la PR à relire, si on la connaît")
    invocation.add_argument(
        "--decision",
        help="pour le pilote : la sortie de `atelier piloter`, transmise telle quelle",
    )
    invocation.add_argument(
        "--nul",
        action="store_true",
        help="séparer les arguments par NUL, pour un tableau shell",
    )

    feuille_p = sous.add_parser(
        "feuille", help="le registre des lots de la feuille de route du produit"
    )
    feuille_sous = feuille_p.add_subparsers(dest="action", required=True)
    valider = feuille_sous.add_parser(
        "valider", help="FAIL sur toute incohérence feuille / briefs / cartes ; 0 sinon"
    )
    valider.add_argument("--projet", required=True)
    valider.add_argument(
        "--base", help="révision git de référence : vérifie aussi les transitions"
    )
    valider.add_argument("--branche", help="la branche de la PR, pour reconnaître une PR de lot")
    valider.add_argument("--pr", type=int, help="le numéro de la PR, s'il est connu")
    etat_p = feuille_sous.add_parser("etat", help="chaque lot, son état écrit et son état dérivé")
    etat_p.add_argument("--projet", required=True)
    marquer = feuille_sous.add_parser("marquer", help="faire avancer la fiche d'un lot")
    marquer.add_argument("--projet", required=True)
    marquer.add_argument("--lot", required=True, help="le numéro (046) ou le slug du lot")
    marquer.add_argument("--etat", required=True, choices=list(feuille.ETATS))
    marquer.add_argument("--pr", type=int, action="append", default=[])

    piloter = sous.add_parser(
        "piloter",
        help="ce que la feuille de route commande de déposer ; --run dépose",
    )
    piloter.add_argument("--projet", required=True)
    piloter.add_argument("--run", action="store_true")

    reprendre = sous.add_parser(
        "reprendre",
        help="retirer la carte d'un lot de sa boîte pour que le pilote le redépose",
    )
    reprendre.add_argument("--projet", required=True)
    reprendre.add_argument("--lot", required=True)
    reprendre.add_argument(
        "--etat",
        help="la boîte d'où sortir la carte ; par défaut, celle où elle dort",
    )

    verrouiller = sous.add_parser(
        "verrouiller", help="tenir les fichiers d'une carte avant d'écrire"
    )
    verrouiller.add_argument("--projet", required=True)
    verrouiller.add_argument("--role", required=True, choices=ROLES)
    verrouiller.add_argument("--lot", required=True)

    lever = sous.add_parser("lever", help="rendre les fichiers d'un lot")
    lever.add_argument("--projet", required=True)
    lever.add_argument("--lot", required=True)

    fumee = sous.add_parser("fumee", help="la commande de fumée du dépôt produit")
    fumee.add_argument("--projet", required=True)

    poste = sous.add_parser(
        "poste", help="qui tient un rôle, d'après le branchement du produit"
    )
    poste.add_argument("--projet", required=True)
    poste.add_argument("--role", required=True, choices=ROLES_INVOCABLES)
    poste.add_argument(
        "--champ",
        choices=["backend", "binaire", "abo", "modele", "lecture_seule"],
        help="n'imprimer qu'un champ (le shell n'a pas à tenir de table)",
    )

    pret = sous.add_parser(
        "pret", help="tout est-il en place pour poser ATELIER_INVOQUER=1 ?"
    )
    pret.add_argument("--projet", required=True)

    branche = sous.add_parser(
        "branche",
        help="la branche du lot, dérivée de prefixe_branche ; --run l'extrait",
    )
    branche.add_argument("--projet", required=True)
    branche.add_argument("--lot", required=True)
    branche.add_argument(
        "--worktree",
        help="worktree du rôle ; obligatoire avec --run (jamais le clone du produit)",
    )
    branche.add_argument(
        "--run",
        action="store_true",
        help="créer ou extraire la branche dans le worktree ; sans --run, on imprime",
    )

    pr = sous.add_parser(
        "pr",
        help="lire un numéro de PR dans un fichier d'échange ; refuse tout autre format",
    )
    pr.add_argument("--fichier", required=True, help="chemin de atelier-echange/pr.txt")
    pr.add_argument(
        "--branche",
        help="si gh répond, la PR doit être sur cette branche ; sinon la sonde se tait",
    )
    pr.add_argument(
        "--worktree",
        help="dépôt depuis lequel sonder gh (remote origin) ; ignoré sans --branche",
    )
    return parser


def _cmd_couches() -> int:
    occupees = couches.couches_occupees()
    for couche in couches.Couche:
        modules = occupees[couche]
        if not modules:
            print(f"FAIL  {couche.value} — aucun module")
            return 1
        print(f"PASS  {couche.value} — {', '.join(modules)}")
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    try:
        produit = projet.charger(args.projet)
    except projet.ProjetIncomplet as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(f"PASS  projet={produit.nom}")
    print(f"      briefs={produit.briefs}")
    print(f"      tests={produit.tests}")
    print(f"      fumee={produit.fumee}")
    print(
        f"      roles=écrire:{produit.roles.ecriture} "
        f"exécuter:{produit.roles.execution} "
        f"relire:{produit.roles.controle}"
    )
    if not produit.briefs.is_dir():
        print(f"FAIL  dossier briefs introuvable : {produit.briefs}", file=sys.stderr)
        return 1
    return 0


def _cmd_portes(args: argparse.Namespace) -> int:
    print(porte.rendre(Path(args.brief)))
    return 0 if porte.passer(Path(args.brief)) else 1


def _cmd_start(args: argparse.Namespace) -> int:
    brief = Path(args.brief)
    try:
        apercu = cycle.preparer(brief, args.projet)
    except (cycle.CycleErreur, projet.ProjetIncomplet) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(f"lot        {apercu.lot}")
    print(f"branche    {apercu.branche}")
    print(f"worktree   {apercu.worktree}")
    print(f"fichiers   {', '.join(apercu.fichiers)}")
    print(f"écrire     {apercu.ecrivain}")
    print(f"exécuter   {apercu.executant} → {apercu.commande_executant}")
    print(f"relire     {apercu.relecteur} → {apercu.commande_relecteur}")
    print(f"isolation  {apercu.commande_worktree}")
    print()
    print(apercu.portes)
    print()
    print(apercu.note)
    if not args.run:
        print("poursuivre : relancer avec --run")
        return 0
    try:
        run = cycle.lancer(brief, args.projet)
    except (cycle.CycleErreur, verrou.Collision) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(f"RUN {run.id}  etape={run.etape.value}  auteur≠relecteur")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    runs = etat.lister(Path(args.projet))
    if not runs:
        print("aucun run")
        return 0
    for run in runs:
        print(f"{run.id}  {run.lot}  {run.etape.value}  {run.auteur_code}≠{run.relecteur}")
    return 0


def _cmd_verrous(args: argparse.Namespace) -> int:
    try:
        tableau = verrou.charger(Path(args.projet))
    except verrou.Collision as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    if not tableau.poses:
        print("aucun verrou")
        return 0
    for pose in tableau.poses:
        print(f"{pose.lot}  {', '.join(sorted(pose.fichiers))}")
    return 0


def _cmd_fusionner() -> int:
    try:
        etat.fusionner(None)  # type: ignore[arg-type]
    except FusionInterdite as exc:
        print(f"REFUS  {exc}", file=sys.stderr)
        return 2
    print("FAIL  fusionner n'a pas refusé", file=sys.stderr)
    return 1


def _cmd_hop(args: argparse.Namespace) -> int:
    mesures: list[quota.Quota] = []
    for piece in args.mesure:
        if "=" not in piece:
            print(f"FAIL  mesure mal formée : {piece} (attendu agent=restant)", file=sys.stderr)
            return 1
        agent, restant = piece.split("=", 1)
        try:
            mesures.append(quota.Quota(agent=agent, restant=int(restant)))
        except ValueError:
            print(f"FAIL  restant non entier : {restant}", file=sys.stderr)
            return 1
    try:
        choisi = quota.hop(mesures)
    except ValueError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(choisi.agent)
    return 0


def _declarer_file_bloquee(racine: Path, role: str) -> None:
    """Une file vide reste silencieuse. Une file tenue par un verrou parle."""
    try:
        cartes = boite.lister(racine, boite.BOITE_DU_ROLE[role])
        poses = verrou.charger(racine).poses
    except (boite.BoiteErreur, verrou.Collision):
        return
    if not cartes:
        return
    tenus = {fichier: pose.lot for pose in poses for fichier in pose.fichiers}
    for carte in cartes:
        for fichier in sorted(carte.fichiers):
            tenu_par = tenus.get(Path(fichier).as_posix())
            if tenu_par and tenu_par != carte.lot:
                print(
                    f"{carte.lot} attend : {fichier} est tenu par {tenu_par}",
                    file=sys.stderr,
                )
    print(
        "aucune carte libre — `atelier lever --lot <lot>` après ta fusion.",
        file=sys.stderr,
    )


def _cmd_prochain(args: argparse.Namespace) -> int:
    try:
        carte = boite.prochain(Path(args.projet), args.role)
    except (boite.BoiteErreur, verrou.Collision) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    if carte is None:
        if args.role == boite.ROLE_QUI_ECRIT:
            _declarer_file_bloquee(Path(args.projet), args.role)
        print("RIEN")
        return 0
    if args.champ:
        valeur = carte.vers_dict()[args.champ]
        print("" if valeur is None else valeur)
        return 0
    print(json.dumps(carte.vers_dict(), ensure_ascii=False))
    return 0


def _cmd_deposer(args: argparse.Namespace) -> int:
    try:
        cible = boite.deposer(
            Path(args.projet),
            args.etat,
            boite.Carte(lot=args.lot, brief=args.brief, fichiers=list(args.fichier)),
        )
    except boite.BoiteErreur as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(cible)
    return 0


def _fichiers_de_la_carte(racine: Path, carte: boite.Carte) -> list[str]:
    """Le périmètre d'une carte vient du brief, pas de la carte.

    Une carte déposée par le pilote peut ne rien nommer : le brief
    n'existait pas encore. Dès qu'il existe, sa section Périmètre fait
    foi — c'est la seule source d'instruction, verrou compris.
    """
    if carte.fichiers:
        return list(carte.fichiers)
    chemin = Path(carte.brief)
    if not chemin.is_absolute():
        chemin = Path(racine) / carte.brief
    if not chemin.is_file():
        return []
    # Le lecteur de périmètre vit dans `cycle` ; ce lot n'a pas le droit
    # d'écrire dans ce fichier, donc on l'appelle tel qu'il est plutôt
    # que d'en recopier une seconde version ici.
    return cycle._fichiers_du_perimetre(chemin)


def _cmd_avancer(args: argparse.Namespace) -> int:
    racine = Path(args.projet)
    champs: dict[str, object] = {}
    if args.pr is not None:
        champs["pr"] = args.pr
    if args.note:
        champs["note"] = args.note
    try:
        carte = boite.lire(racine, boite.BOITE_DU_ROLE[args.role], args.lot)
        if not carte.fichiers:
            deduits = list(args.fichier) or _fichiers_de_la_carte(racine, carte)
            if deduits:
                champs["fichiers"] = deduits
        cible = boite.avancer(racine, args.role, args.lot, **champs)
    except boite.BoiteErreur as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(cible)
    return 0


def _cmd_echouer(args: argparse.Namespace) -> int:
    try:
        cible = boite.echouer(
            Path(args.projet), args.role, args.lot, args.raison, args.cause
        )
    except boite.BoiteErreur as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(cible)
    return 0


def _cmd_rappeler(args: argparse.Namespace) -> int:
    """Ce qui revient seul de echec/. Le reste attend une personne, et on dit qui.

    Appelé par `crons/tour.sh` au début de chaque tour : le rôle se
    rattrape lui-même au réveil suivant, sans que le pilote arbitre et
    sans qu'une horloge de plus soit à lire — deux heures séparent déjà
    deux tours du coder.
    """
    racine = Path(args.projet)
    try:
        rappelees = boite.rappeler(racine, args.role)
        restantes = [
            c for c in boite.lister(racine, "echec")
            if c.role == args.role and c.lot not in {r.lot for r in rappelees}
        ]
    except (boite.BoiteErreur, verrou.Collision) as exc:
        # Un rappel qui échoue n'annule pas le tour : la carte reste où
        # elle est, et le rôle continue avec ce que sa file porte.
        print(f"rappel impossible : {exc}", file=sys.stderr)
        return 0
    for carte in rappelees:
        print(
            f"rappelé  {carte.lot} : echec → {boite.BOITE_DU_ROLE[args.role]} "
            f"(cause « {carte.cause} », essai {carte.essais + 1})"
        )
    for carte in restantes:
        print(
            f"reste    {carte.lot} : {reprise.raison_du_refus(carte.cause, carte.essais)}",
            file=sys.stderr,
        )
    return 0


def _cmd_canal(args: argparse.Namespace) -> int:
    """Le canal d'échange, avec sa garde `*`, dans le worktree du rôle.

    Sans elle, un agent qui fait `git add -A` — ils le font tous —
    enregistre `atelier-echange/pr.txt` ; `crons/tour.sh` le supprime
    ensuite, et le worktree reste sale. Le lot suivant butait alors sur
    `preparer_lot`. Le tour *nominal* empoisonnait le lot d'après :
    mesuré, puis fermé ici.
    """
    cible = Path(args.worktree)
    if not cible.is_dir():
        print(f"FAIL  worktree introuvable : {cible}", file=sys.stderr)
        return 1
    try:
        dossier = echange.ouvrir(cible)
    except OSError as exc:
        print(f"FAIL  canal impossible dans {cible} : {exc}", file=sys.stderr)
        return 1
    if not echange.git_ignore_le_canal(cible):
        print(f"FAIL  le canal {dossier} n'a pas sa garde git", file=sys.stderr)
        return 1
    print(dossier)
    return 0


def _cmd_ranger(args: argparse.Namespace) -> int:
    cible = Path(args.worktree)
    if not cible.is_dir():
        print(f"FAIL  worktree introuvable : {cible}", file=sys.stderr)
        return 1
    try:
        ranges = worktree.ranger(cible, args.message)
    except worktree.WorktreeErreur as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    if not ranges:
        print("worktree propre : rien à ranger")
        return 0
    print(f"rangé dans {worktree.courante(cible)} : {', '.join(ranges)}")
    return 0


def _roles_du_produit(chemin: str) -> dict[str, str]:
    """Qui tient quel poste. Une seule réponse, et elle est dans le produit."""
    return projet.charger(chemin).roles.vers_dict()


def _feuille_relative(produit: projet.Projet) -> str | None:
    """Le chemin de la feuille tel que le prompt le cite : relatif au produit."""
    if produit.feuille is None:
        return None
    try:
        return produit.feuille.relative_to(produit.racine).as_posix()
    except ValueError:
        return produit.feuille.as_posix()


def _cmd_invocation(args: argparse.Namespace) -> int:
    try:
        produit = projet.charger(args.projet)
        branche = produit.branche_du_lot(args.lot) if args.lot else None
        argv = backends.argv_du_role(
            args.role,
            roles=produit.roles.vers_dict(),
            projet=args.projet,
            lot=args.lot,
            brief=args.brief,
            pr=args.pr,
            branche=branche,
            feuille=_feuille_relative(produit),
            decision=args.decision,
        )
    except (backends.BackendErreur, projet.ProjetIncomplet, KeyError) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    if args.nul:
        sys.stdout.write("\0".join(argv) + "\0")
        sys.stdout.flush()
        return 0
    print(shlex.join(argv))
    return 0


def _cmd_verrouiller(args: argparse.Namespace) -> int:
    racine = Path(args.projet)
    try:
        carte = boite.lire(racine, boite.BOITE_DU_ROLE[args.role], args.lot)
    except boite.BoiteErreur as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    fichiers = _fichiers_de_la_carte(racine, carte)
    if not fichiers:
        print(
            f"FAIL  la carte {args.lot} ne nomme aucun fichier et son brief "
            f"({carte.brief}) n'en donne pas : l'atelier ne devine pas un périmètre",
            file=sys.stderr,
        )
        return 1
    try:
        pose = verrou.poser(racine, args.lot, fichiers)
    except verrou.Collision as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(" ".join(sorted(pose.fichiers)))
    return 0


def _cmd_lever(args: argparse.Namespace) -> int:
    verrou.lever(Path(args.projet), args.lot)
    print(f"verrou levé : {args.lot}")
    return 0


def _cmd_poste(args: argparse.Namespace) -> int:
    try:
        poste = backends.poste_du_role(args.role, _roles_du_produit(args.projet))
    except (backends.BackendErreur, projet.ProjetIncomplet, KeyError) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    champs = {
        "backend": poste.backend,
        "binaire": poste.binaire,
        "abo": poste.abo,
        "modele": poste.modele or "",
        "lecture_seule": poste.lecture_seule,
    }
    if args.champ:
        print(champs[args.champ])
        return 0
    print(f"role          {poste.role}")
    for nom, valeur in champs.items():
        print(f"{nom:<13} {valeur}")
    return 0


def _cmd_pret(args: argparse.Namespace) -> int:
    """Ce qu'on regarde avant de poser ATELIER_INVOQUER=1.

    On lit le PATH et le disque. On n'invoque personne : regarder n'est
    pas dépenser. Un inconnu se marque `?`, jamais `FAIL` — l'atelier ne
    compte pas ce qu'il n'a pas mesuré.
    """
    lignes: list[tuple[str, str]] = []

    def dire(marque: str, texte: str) -> None:
        lignes.append((marque, texte))

    try:
        produit = projet.charger(args.projet)
    except projet.ProjetIncomplet as exc:
        print(f"FAIL  branchement — {exc}")
        return 1
    dire("PASS", f"branchement — {produit.nom} ({produit.racine}/atelier.toml)")

    roles = produit.roles.vers_dict()
    tenus: dict[str, list[str]] = {}
    for role in backends.ROLES_INVOCABLES:
        try:
            poste = backends.poste_du_role(role, roles)
        except backends.BackendErreur as exc:
            dire("FAIL", f"rôle {role} — {exc}")
            continue
        tenus.setdefault(poste.binaire, []).append(role)
    for binaire, roles_tenus in sorted(tenus.items()):
        porte = ", ".join(roles_tenus)
        chemin = shutil.which(binaire)
        if chemin:
            dire("PASS", f"binaire {binaire} ({porte}) — {chemin}")
        else:
            dire("FAIL", f"binaire {binaire} ({porte}) — introuvable dans le PATH")

    try:
        garde = backends.poste_du_role("relire", roles).lecture_seule
    except backends.BackendErreur:
        garde = "non-tenue"
    if garde == "tenue":
        dire("PASS", "le relecteur n'a pas la main qui écrit")
    else:
        dire("?", "le relecteur garde la main qui écrit — garde non-tenue")

    for outil in ("flock", "timeout"):
        if shutil.which(outil):
            dire("PASS", f"{outil} — présent")
        else:
            dire("FAIL", f"{outil} — absent : le cron tournerait sans garde")

    # Regarder n'est pas créer : si le dossier n'existe pas encore, on
    # demande à son plus proche parent s'il accepterait qu'on l'y pose.
    verrous = Path(os.environ.get("ATELIER_VERROUS") or os.environ.get("TMPDIR") or "/tmp")
    ancetre = verrous
    while not ancetre.exists() and ancetre != ancetre.parent:
        ancetre = ancetre.parent
    if os.access(ancetre, os.W_OK):
        suffixe = "" if verrous.is_dir() else " (sera créé au premier tour)"
        dire("PASS", f"dossier des verrous — {verrous}{suffixe}")
    else:
        dire("FAIL", f"dossier des verrous — {verrous} : {ancetre} n'est pas inscriptible")

    if os.environ.get("ATELIER_QUOTA_CMD") or shutil.which("llmquota"):
        dire("PASS", "quota — lisible")
    else:
        dire("?", "quota — non lisible ; un inconnu ne se compte pas pour zéro")

    for role in boite.ROLES:
        nom = f"ATELIER_WORKDIR_{role}"
        chemin = os.environ.get(nom)
        if not chemin:
            continue
        if Path(chemin).is_dir():
            dire("PASS", f"{nom} — {chemin}")
        else:
            dire("FAIL", f"{nom} — {chemin} n'existe pas")

    boites = (
        "a-briefer", boite.SUIVANT["briefer"], "a-planifier", "a-coder", "a-relire",
        "faite", feuille.BOITE_FUSIONNEE, "echec",
    )
    for etat in boites:
        try:
            combien = len(boite.lister(produit.racine, etat))
        except boite.BoiteErreur as exc:
            dire("FAIL", f"boîte {etat} — {exc}")
            continue
        dire("PASS", f"boîte {etat} — {combien} carte(s)")

    # Le pilote décide d'après la feuille de route : sans elle, il n'a
    # rien à décider, et on le dit avant d'armer.
    if produit.feuille is None:
        dire("?", "feuille de route — [projet].feuille non nommé : le pilote ne déposera rien")
    else:
        try:
            f = feuille.lire(produit.feuille)
            erreurs = feuille.verifier(f, produit.racine, produit.briefs)
            erreurs += feuille.verifier_cartes(f, produit.racine)
        except feuille.FeuilleErreur as exc:
            dire("FAIL", f"feuille de route — {exc}")
        else:
            if erreurs:
                dire("FAIL", f"feuille de route — {len(erreurs)} incohérence(s) : `atelier feuille valider`")
            else:
                dire("PASS", f"feuille de route — {_feuille_relative(produit)}, {len(f.fiches)} lot(s), cohérente")

    if os.environ.get("ATELIER_INVOQUER") == "1":
        dire("PASS", "ATELIER_INVOQUER=1 — l'invocation est armée")
    else:
        dire("?", "ATELIER_INVOQUER n'est pas posé — mode à sec")

    for marque, texte in lignes:
        print(f"{marque:<5} {texte}")
    return 1 if any(m == "FAIL" for m, _ in lignes) else 0


def _cmd_branche(args: argparse.Namespace) -> int:
    """Sans --run : imprime le nom. Avec --run : l'extrait dans le worktree du rôle."""
    try:
        produit = projet.charger(args.projet)
        nom = produit.branche_du_lot(args.lot)
    except projet.ProjetIncomplet as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    if not args.run:
        print(nom)
        return 0
    if not args.worktree:
        print(
            "FAIL  --run exige --worktree : l'atelier ne bascule pas la branche "
            "du clone du produit",
            file=sys.stderr,
        )
        return 1
    cible = Path(args.worktree).resolve()
    if cible == produit.racine.resolve():
        print(
            "FAIL  le worktree du rôle ne peut pas être le clone du produit "
            f"({cible}) : pose ATELIER_WORKDIR_coder",
            file=sys.stderr,
        )
        return 1
    try:
        worktree.preparer_lot(cible, nom, produit.branche_base)
    except worktree.WorktreeErreur as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(nom)
    return 0


def _cmd_pr(args: argparse.Namespace) -> int:
    try:
        numero = echange.lire_numero_pr(Path(args.fichier))
        if args.branche:
            racine = Path(args.worktree) if args.worktree else Path(args.fichier).parent.parent
            echange.verifier_pr_branche_optionnel(numero, args.branche, racine)
    except echange.EchangeErreur as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(numero)
    return 0


def _charger_feuille(chemin_projet: str) -> tuple[projet.Projet, feuille.Feuille]:
    produit = projet.charger(chemin_projet)
    return produit, feuille.lire(produit.feuille_ou_refus())


def _feuille_de_base(produit: projet.Projet, base: str) -> feuille.Feuille:
    """La feuille telle que la révision `base` la porte, lue par git."""
    rel = _feuille_relative(produit)
    proc = subprocess.run(
        ["git", "-C", str(produit.racine), "show", f"{base}:{rel}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise feuille.FeuilleErreur(
            f"impossible de lire {rel} à la révision {base} : {proc.stderr.strip()}"
        )
    return feuille.lire_texte(proc.stdout, Path(f"{base}:{rel}"))


def _cmd_feuille_valider(args: argparse.Namespace) -> int:
    try:
        produit, apres = _charger_feuille(args.projet)
        erreurs = feuille.verifier(apres, produit.racine, produit.briefs)
        erreurs += feuille.verifier_cartes(apres, produit.racine)
        note_base = ""
        if args.base:
            try:
                avant = _feuille_de_base(produit, args.base)
            except feuille.FeuilleErreur as exc:
                if feuille.REPERE_DEBUT not in str(exc):
                    raise
                # La révision de base n'a pas encore de registre : c'est la
                # première feuille. On ne vérifie pas des transitions depuis
                # rien, et on le dit plutôt que de faire semblant.
                note_base = f" ; {args.base} sans registre : première feuille, transitions non vérifiées"
            else:
                erreurs += feuille.transitions(
                    avant, apres,
                    prefixe_branche=produit.prefixe_branche,
                    branche=args.branche,
                    pr=args.pr,
                )
    except (projet.ProjetIncomplet, feuille.FeuilleErreur) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    if not apres.fiches:
        # Un registre vide n'est pas un registre cohérent : c'est un
        # échantillon vide, et il échoue.
        erreurs.append(f"{apres.chemin} — le registre ne porte aucune fiche")
    for erreur in erreurs:
        print(f"FAIL  {erreur}", file=sys.stderr)
    if erreurs:
        return 1
    print(f"PASS  {_feuille_relative(produit)} — {len(apres.fiches)} lot(s), feuille cohérente{note_base}")
    return 0


def _cmd_feuille_etat(args: argparse.Namespace) -> int:
    try:
        produit, f = _charger_feuille(args.projet)
        lignes = [
            (fiche.lot, fiche.etat, feuille.etat_effectif(fiche, f, produit.racine))
            for fiche in f.fiches
        ]
    except (projet.ProjetIncomplet, feuille.FeuilleErreur, verrou.Collision) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    if not lignes:
        print("FAIL  le registre ne porte aucune fiche", file=sys.stderr)
        return 1
    largeur = max(len(lot) for lot, _, _ in lignes)
    for lot, ecrit, derive in lignes:
        print(f"{lot:<{largeur}}  {ecrit:<10} {derive}")
    return 0


def _cmd_feuille_marquer(args: argparse.Namespace) -> int:
    try:
        produit = projet.charger(args.projet)
        chemin = produit.feuille_ou_refus()
        texte = chemin.read_text(encoding="utf-8")
        nouveau = feuille.marquer(texte, args.lot, args.etat, tuple(args.pr), chemin)
    except (projet.ProjetIncomplet, feuille.FeuilleErreur, OSError) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    chemin.write_text(nouveau, encoding="utf-8")
    fiche = feuille.lire(chemin).fiche(args.lot)
    assert fiche is not None
    prs = ", ".join(map(str, fiche.prs)) or feuille.VIDE
    print(f"{fiche.lot}  état : {fiche.etat} · PR : {prs}")
    return 0


def _cmd_piloter(args: argparse.Namespace) -> int:
    """La décision du matin, calculée. Sans --run, rien n'est déposé."""
    try:
        produit, f = _charger_feuille(args.projet)
        racine = produit.racine
        lignes: list[str] = []
        for r in feuille.rapprochements(f, racine):
            if args.run:
                feuille.appliquer(racine, r)
            verbe = "rapproché " if args.run else "rapprocher"
            levee = " ; verrou levé" if r.lever_verrou and args.run else ""
            lignes.append(f"{verbe} {r.lot} : {r.source} → {r.destination} ({r.raison}){levee}")
        # Une carte qu'un rapprochement déplace n'est pas une incohérence :
        # `verifier_cartes` ne la compte pas, à sec comme sous --run.
        erreurs = feuille.verifier(f, racine, produit.briefs)
        erreurs += feuille.verifier_cartes(f, racine)
        if erreurs:
            for ligne in lignes:
                print(ligne)
            for erreur in erreurs:
                print(f"FAIL  {erreur}", file=sys.stderr)
            print("FAIL  feuille incohérente : aucune carte déposée", file=sys.stderr)
            return 1
        if not f.fiches:
            print(f"FAIL  {f.chemin} — le registre ne porte aucune fiche", file=sys.stderr)
            return 1
        for d in feuille.decider(f, racine):
            if args.run:
                feuille.deposer(racine, d)
            verbe = "déposé   " if args.run else "déposer  "
            fichiers = f"  ({', '.join(d.fichiers)})" if d.fichiers else ""
            lignes.append(f"{verbe} {d.boite:<10} {d.lot}  {d.brief}{fichiers}")
    except (projet.ProjetIncomplet, feuille.FeuilleErreur, boite.BoiteErreur, verrou.Collision) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    if not lignes:
        print("RIEN")
        return 0
    for ligne in lignes:
        print(ligne)
    if not args.run:
        print("sans --run : rien n'est déposé.")
    return 0


def _cmd_reprendre(args: argparse.Namespace) -> int:
    """Sortir une carte de sa boîte, quelle qu'elle soit.

    `reprendre` ne connaissait que `echec/`. Une carte coincée dans
    `faite/` — la PR fermée sans être fusionnée — ou dans `a-relire`
    n'avait aucune sortie : il fallait supprimer un fichier JSON à la
    main. Le verrou du lot tombe avec elle, sinon les fichiers qu'elle
    tenait resteraient tenus par un lot qui n'est plus nulle part.
    """
    racine = Path(args.projet)
    etat = args.etat or boite.ou_est(racine, args.lot)
    if etat is None:
        print(
            f"FAIL  aucune boîte ne porte la carte {args.lot} : rien à reprendre",
            file=sys.stderr,
        )
        return 1
    try:
        carte = boite.retirer(racine, etat, args.lot)
    except boite.BoiteErreur as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    verrou.lever(racine, args.lot)
    raison = carte.note or "aucune"
    print(
        f"{args.lot} retiré de {etat}/ (raison : {raison}) ; verrou levé "
        "— le pilote peut le redéposer."
    )
    return 0


def _cmd_fumee(args: argparse.Namespace) -> int:
    try:
        produit = projet.charger(args.projet)
    except projet.ProjetIncomplet as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(produit.fumee)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.commande == "couches":
        return _cmd_couches()
    if args.commande == "doctor":
        return _cmd_doctor(args)
    if args.commande == "portes":
        return _cmd_portes(args)
    if args.commande == "start":
        return _cmd_start(args)
    if args.commande == "status":
        return _cmd_status(args)
    if args.commande == "verrous":
        return _cmd_verrous(args)
    if args.commande == "fusionner":
        return _cmd_fusionner()
    if args.commande == "hop":
        return _cmd_hop(args)
    if args.commande == "prochain":
        return _cmd_prochain(args)
    if args.commande == "deposer":
        return _cmd_deposer(args)
    if args.commande == "avancer":
        return _cmd_avancer(args)
    if args.commande == "echouer":
        return _cmd_echouer(args)
    if args.commande == "rappeler":
        return _cmd_rappeler(args)
    if args.commande == "canal":
        return _cmd_canal(args)
    if args.commande == "ranger":
        return _cmd_ranger(args)
    if args.commande == "invocation":
        return _cmd_invocation(args)
    if args.commande == "verrouiller":
        return _cmd_verrouiller(args)
    if args.commande == "lever":
        return _cmd_lever(args)
    if args.commande == "fumee":
        return _cmd_fumee(args)
    if args.commande == "poste":
        return _cmd_poste(args)
    if args.commande == "pret":
        return _cmd_pret(args)
    if args.commande == "branche":
        return _cmd_branche(args)
    if args.commande == "pr":
        return _cmd_pr(args)
    if args.commande == "feuille":
        if args.action == "valider":
            return _cmd_feuille_valider(args)
        if args.action == "etat":
            return _cmd_feuille_etat(args)
        if args.action == "marquer":
            return _cmd_feuille_marquer(args)
    if args.commande == "piloter":
        return _cmd_piloter(args)
    if args.commande == "reprendre":
        return _cmd_reprendre(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
