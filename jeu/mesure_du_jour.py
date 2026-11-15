"""Ce que coûte un jour du monde sur cette machine, phase par phase.

    cd jeu && py mesure_du_jour.py                  # 365 jours, graine 0, sans IA puis avec
    cd jeu && py mesure_du_jour.py --ticks 60 --ia non --sans-phases
    cd jeu && py mesure_du_jour.py --profil 10      # les dix fonctions les plus chères
    cd jeu && py mesure_du_jour.py --json avant.json
    cd jeu && py mesure_du_jour.py --temoin         # l'empreinte de tout ce que le service publie

Le jour se mesure là où le jeu le paie : `ServeurMonde.jouer_un_tick()` en entier, les jauges, l'IA,
le tick et la publication, sur le monde que le service charge, avec le réglage du ramasse-miettes de
son `main()`. L'horloge du service reste en pause : chaque jour est joué par un appel direct.

Chaque colonne (sans IA, avec IA) joue l'année deux fois, chaque fois dans un processus neuf :

- **le passage nu** donne les chiffres qui comptent : le jour entier, le tick avec l'IA
  (`duree_dernier_tick_ms`) et la publication (le jour moins le tick) ;
- **le passage instrumenté** donne la part de chaque phase. Chaque fonction de phase y est
  chronométrée, le temps d'une phase appelée par une autre étant retiré à celle qui l'appelle.
  Le chronomètre coûte : les millisecondes des phases sont donc leur part du passage instrumenté
  rapportée au jour du passage nu.

L'empreinte est le hachage du monde au dernier jour : deux mesures du même monde, de la même graine,
sur la même machine, donnent la même. Elle ne se compare pas d'une machine à l'autre (les derniers
bits de la trigonométrie diffèrent entre Windows et Linux).

Le témoin (`--temoin`) est l'empreinte de tout ce que le service publie, jour après jour : le monde,
chaque lieu, chaque plan, chaque occupation, chaque maison, les modificateurs, le relevé de l'IA, et
au dernier jour chaque pays. Une optimisation de la publication doit rendre le même. Il ne
chronomètre rien : lire tous les octets de chaque jour n'est pas ce que le jeu fait.

Bibliothèque standard seule.
"""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import platform
import pstats
import statistics
import subprocess
import sys
import time
from pathlib import Path

JEU = Path(__file__).resolve().parent
TICKS = 365
GRAINE = 0
MS = 1000.0
CENTILE = 95

# (module, nom dans ce module, phase). Le nom est celui par lequel l'appelant atteint la fonction :
# une fonction importée par son nom se remplace dans le module qui l'a importée.
PHASES_DU_TICK = (
    ("sim.service", "avant_le_tick", "jauges du mois"),
    ("sim.service", "jouer_ia", "IA"),
    ("sim.service", "toutes_les_maisons_de_l_ia", "IA"),
    ("sim.service", "tick", "tick : le reste"),
    ("sim.modificateurs", "expirer", "tick : modificateurs"),
    ("sim.modificateurs", "facteurs_du_monde", "tick : modificateurs"),
    ("sim.engine", "_appliquer_intentions", "tick : intentions"),
    ("sim.engine", "_appliquer_pertes_greniers", "tick : greniers"),
    ("sim.engine", "_avancer_chantiers", "tick : chantiers"),
    ("sim.engine", "_affecter_artisans", "tick : ateliers"),
    ("sim.batiments", "avancer", "tick : bâtiments de province"),
    ("sim.lieux", "repartir_sur_les_lieux", "tick : reprise des lieux"),
    ("sim.engine", "_apply_fabrication", "tick : fabrication"),
    ("sim.lieux", "accorder_fabrication", "tick : fabrication"),
    ("sim.engine", "_apply_extraction", "tick : extraction"),
    ("sim.engine", "_apply_production", "tick : production"),
    ("sim.engine", "_apply_production_saison_moyenne", "tick : production"),
    ("sim.prelevement", "prelever", "tick : prélèvement"),
    ("sim.routes_interieures", "facteurs_des_routes", "tick : chemins intérieurs"),
    ("sim.engine", "_remplir_chemins_interieurs", "tick : chemins intérieurs"),
    ("sim.engine", "_apply_commerce", "tick : commerce"),
    ("sim.engine", "_apply_consumption", "tick : consommation"),
    ("sim.engine", "_update_hunger", "tick : faim"),
    ("sim.engine", "_apply_mortality", "tick : mortalité"),
    ("sim.engine", "_apply_natalite", "tick : natalité"),
    ("sim.evenements", "poser_les_famines", "tick : famines et flux"),
    ("sim.flux", "noter_affames", "tick : famines et flux"),
    ("sim.engine", "_apply_migration", "tick : migration"),
    ("sim.departs", "appliquer_departs", "tick : départs"),
)
PHASES_DE_LA_PUBLICATION = (
    ("sim.service", "_bourg_du_lieu", "publication : bourgs"),
    ("sim.service", "_cellule_legere", "publication : cellules"),
    ("sim.service", "noms_depuis_monde", "publication : noms"),
    ("sim.service", "flux_des_lieux", "publication : flux"),
    ("sim.service", "logement_de", "publication : logement"),
    ("sim.service", "_foyers_du_lieu", "publication : foyers"),
    ("sim.service", "lieux_en_photographie", "publication : lieux"),
    ("sim.service", "_serialiser", "publication : octets"),
    ("sim.service", "portes_de_l_enceinte", "publication : portes"),
    ("sim.service", "controler_portes", "publication : portes"),
    ("sim.service", "aire_du_contour", "publication : occupations"),
    ("sim.service", "matiere_des_maisons", "publication : maisons"),
    ("sim.service", "document_des_modificateurs", "publication : modificateurs"),
)
# Des méthodes : (module, classe, méthode, phase).
METHODES = (
    ("sim.service", "ServeurMonde", "_construire_etat", "publication : le reste"),
    ("sim.service", "ServeurMonde", "_places_des_lieux", "publication : places"),
    ("sim.plan", "Plan", "to_dict", "publication : plans"),
)
RESTE_DU_JOUR = "jour : le reste"


class Chronometre:
    """Le temps propre de chaque phase : celui d'une phase appelée se retire à celle qui l'appelle."""

    def __init__(self):
        self.totaux: dict[str, float] = {}
        self._pile: list[float] = []

    def envelopper(self, fonction, phase):
        totaux, pile, horloge = self.totaux, self._pile, time.perf_counter

        def chronometree(*arguments, **options):
            pile.append(0.0)
            debut = horloge()
            try:
                return fonction(*arguments, **options)
            finally:
                duree = horloge() - debut
                totaux[phase] = totaux.get(phase, 0.0) + duree - pile.pop()
                if pile:
                    pile[-1] += duree

        return chronometree

    def poser(self):
        """Remplace chaque fonction de phase par sa version chronométrée ; une phase introuvable
        est une erreur, jamais une ligne absente du tableau."""
        import importlib

        for module, nom, phase in PHASES_DU_TICK + PHASES_DE_LA_PUBLICATION:
            porteur = importlib.import_module(module)
            setattr(porteur, nom, self.envelopper(getattr(porteur, nom), phase))
        for module, classe, nom, phase in METHODES:
            porteur = getattr(importlib.import_module(module), classe)
            setattr(porteur, nom, self.envelopper(getattr(porteur, nom), phase))


def _empreinte(monde) -> str:
    canonique = json.dumps(monde.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonique.encode("utf-8")).hexdigest()


def _jouer(ticks: int, graine: int, ia: bool, instrumente: bool) -> dict:
    """Joue `ticks` jours par le service et rend les durées de chaque jour, en millisecondes."""
    chronometre = Chronometre() if instrumente else None
    if chronometre is not None:
        chronometre.poser()
    from sim import service

    serveur = service.ServeurMonde((service.SERVICE_HOST, 0), graine, 0.0, ia=ia)
    try:
        if chronometre is not None:
            serveur._signature_noms = chronometre.envelopper(serveur._signature_noms, "publication : noms")
            chronometre.totaux.clear()  # le premier état, construit au chargement, n'est pas un jour
        service.regler_le_ramasse_miettes()
        jours, ticks_seuls = [], []
        for _ in range(ticks):
            debut = time.perf_counter()
            etat = serveur.jouer_un_tick()
            jours.append((time.perf_counter() - debut) * MS)
            ticks_seuls.append(etat.duree_dernier_tick_ms)
        resultat = {"jours_ms": jours, "ticks_ms": ticks_seuls, "empreinte": _empreinte(serveur.world)}
        if chronometre is not None:
            phases = {phase: secondes * MS for phase, secondes in chronometre.totaux.items()}
            phases[RESTE_DU_JOUR] = sum(jours) - sum(phases.values())
            resultat["phases_ms"] = phases
        return resultat
    finally:
        serveur.server_close()


def _octets_publies(serveur, etat):
    """Tout ce qu'un lecteur peut demander de l'état publié, dans un ordre fixé."""
    from sim.ville1400 import BaseAbsente

    yield etat.monde
    yield etat.modificateurs
    yield etat.ia or b""
    for cell_id in sorted(etat.lieux):
        yield etat.lieux[cell_id]
        yield etat.lieux_avec_bourg[cell_id]
        for lecture in (serveur.octets_plan, serveur.octets_occupation):
            try:
                yield lecture(etat, cell_id)
            except BaseAbsente as refus:
                yield str(refus).encode("utf-8")
    yield serveur.octets_de_maison(etat)
    for maison in sorted(m.id for m in etat.maisons.registre):
        yield serveur.octets_de_maison(etat, maison)


def temoin(ticks: int, graine: int, ia: bool) -> dict:
    """L'empreinte de tout ce que le service publie pendant `ticks` jours, et celle du monde au dernier."""
    from sim import service

    serveur = service.ServeurMonde((service.SERVICE_HOST, 0), graine, 0.0, ia=ia)
    try:
        hachage = hashlib.sha256()
        octets = 0
        for _ in range(ticks):
            etat = serveur.jouer_un_tick()
            for morceau in _octets_publies(serveur, etat):
                hachage.update(morceau)
                octets += len(morceau)
        for maison in sorted(m.id for m in serveur.world.maisons):
            morceau = serveur.octets_du_pays(maison)
            hachage.update(morceau)
            octets += len(morceau)
        return {"ia": ia, "publication": hachage.hexdigest(), "octets": octets,
                "empreinte": _empreinte(serveur.world)}
    finally:
        serveur.server_close()


def _dans_un_processus_neuf(ticks: int, graine: int, ia: bool, instrumente: bool) -> dict:
    commande = [sys.executable, str(Path(__file__).resolve()), "--passage",
                "--ticks", str(ticks), "--seed", str(graine), "--ia", "oui" if ia else "non"]
    if instrumente:
        commande.append("--instrumente")
    sortie = subprocess.run(commande, cwd=JEU, capture_output=True, text=True, encoding="utf-8")
    if sortie.returncode != 0:
        raise SystemExit(f"le passage a échoué ({sortie.returncode}) :\n{sortie.stderr}")
    return json.loads(sortie.stdout)


def _centile(valeurs: list[float], centile: int) -> float:
    rangees = sorted(valeurs)
    return rangees[min(len(rangees) - 1, (len(rangees) * centile) // 100)]


def mesurer(ticks: int, graine: int, ia: bool, phases: bool) -> dict:
    """Une colonne du tableau : le passage nu, puis le passage instrumenté rapporté au premier."""
    nu = _dans_un_processus_neuf(ticks, graine, ia, instrumente=False)
    jours, ticks_seuls = nu["jours_ms"], nu["ticks_ms"]
    colonne = {
        "ia": ia,
        "jour_ms": statistics.fmean(jours),
        "jour_mediane_ms": statistics.median(jours),
        "jour_centile_ms": _centile(jours, CENTILE),
        "jour_max_ms": max(jours),
        "tick_ms": statistics.fmean(ticks_seuls),
        "tick_mediane_ms": statistics.median(ticks_seuls),
        "publication_ms": statistics.fmean(jours) - statistics.fmean(ticks_seuls),
        "annee_s": sum(jours) / MS,
        "empreinte": nu["empreinte"],
        "jours_ms": jours,
    }
    if phases:
        instrumente = _dans_un_processus_neuf(ticks, graine, ia, instrumente=True)
        if instrumente["empreinte"] != nu["empreinte"]:
            raise SystemExit("le passage instrumenté n'a pas joué le même monde que le passage nu")
        total = sum(instrumente["phases_ms"].values())
        colonne["jour_instrumente_ms"] = statistics.fmean(instrumente["jours_ms"])
        colonne["phases_ms"] = {phase: colonne["jour_ms"] * duree / total
                                for phase, duree in instrumente["phases_ms"].items()}
    return colonne


def _ordre_des_phases() -> list[str]:
    ordre = []
    for *_, phase in PHASES_DU_TICK + PHASES_DE_LA_PUBLICATION + METHODES:
        if phase not in ordre:
            ordre.append(phase)
    # Le reste de la publication se lit après ses phases.
    ordre.remove("publication : le reste")
    return ordre + ["publication : le reste", RESTE_DU_JOUR]


def tableau(colonnes: list[dict], ticks: int, graine: int) -> str:
    titres = ["avec IA" if c["ia"] else "sans IA" for c in colonnes]
    lignes = [
        f"Le jour du monde — {ticks} jours, graine {graine}, Python {platform.python_version()}, "
        f"{platform.system()} {platform.machine()}",
        "",
        f"{'':34}" + "".join(f"{titre:>16}" for titre in titres),
    ]

    def ligne(libelle, cle, unite="ms"):
        lignes.append(f"{libelle:34}" + "".join(f"{c[cle]:>13.1f} {unite:2}" for c in colonnes))

    ligne("le jour entier, moyenne", "jour_ms")
    ligne("  médiane", "jour_mediane_ms")
    ligne(f"  {CENTILE}e centile", "jour_centile_ms")
    ligne("  le pire jour", "jour_max_ms")
    ligne("le tick avec l'IA, moyenne", "tick_ms")
    ligne("  médiane", "tick_mediane_ms")
    ligne("la publication, moyenne", "publication_ms")
    ligne(f"les {ticks} jours", "annee_s", "s")
    if all("phases_ms" in c for c in colonnes):
        lignes += ["", f"{'phase (ms par jour, part du jour)':34}" + "".join(f"{titre:>16}" for titre in titres)]
        for phase in _ordre_des_phases():
            if not any(phase in c["phases_ms"] for c in colonnes):
                continue
            cases = ""
            for c in colonnes:
                duree = c["phases_ms"].get(phase, 0.0)
                cases += f"{duree:>9.2f} {100 * duree / c['jour_ms']:>4.1f} %"
            lignes.append(f"  {phase:32}" + cases)
        lignes.append(f"{'le jour du passage instrumenté':34}"
                      + "".join(f"{c['jour_instrumente_ms']:>13.1f} ms" for c in colonnes))
    lignes.append("")
    for titre, c in zip(titres, colonnes):
        lignes.append(f"empreinte du monde au jour {ticks}, {titre} : {c['empreinte']}")
    return "\n".join(lignes)


def profil(ticks: int, graine: int, ia: bool, combien: int) -> str:
    """Les fonctions du jeu les plus chères, par temps propre puis par temps cumulé."""
    profileur = cProfile.Profile()
    profileur.enable()
    _jouer(ticks, graine, ia, instrumente=False)
    profileur.disable()
    stats = pstats.Stats(profileur).stats
    total = sum(propre for (_, _, propre, _, _) in stats.values())
    du_jeu = [(fichier, numero, nom, appels, propre, cumule)
              for (fichier, numero, nom), (_, appels, propre, cumule, _) in stats.items()
              if Path(fichier).is_relative_to(JEU)]
    lignes = [f"Profil — {ticks} jours, graine {graine}, {'avec' if ia else 'sans'} IA ; "
              f"{total:.1f} s sous le profileur, qui ralentit tout"]
    for titre, rang in (("par temps propre", 4), ("par temps cumulé", 5)):
        lignes += ["", f"{titre:42}{'appels/jour':>12}{'propre':>10}{'cumulé':>10}"]
        for fichier, numero, nom, appels, propre, cumule in sorted(du_jeu, key=lambda f: -f[rang])[:combien]:
            ou = f"{Path(fichier).relative_to(JEU).as_posix()}:{numero} {nom}"
            lignes.append(f"  {ou[:60]:60}{appels / ticks:>10.0f}{100 * propre / total:>8.1f} %"
                          f"{100 * cumule / total:>8.1f} %")
    return "\n".join(lignes)


def main(argv: list[str] | None = None) -> int:
    lecteur = argparse.ArgumentParser(description="Ce que coûte un jour du monde, phase par phase.")
    lecteur.add_argument("--ticks", type=int, default=TICKS)
    lecteur.add_argument("--seed", type=int, default=GRAINE)
    lecteur.add_argument("--ia", choices=("non", "oui", "les-deux"), default="les-deux")
    lecteur.add_argument("--sans-phases", action="store_true", help="le passage nu seul")
    lecteur.add_argument("--profil", type=int, metavar="N", help="les N fonctions les plus chères, au lieu du tableau")
    lecteur.add_argument("--temoin", action="store_true",
                         help="l'empreinte de tout ce que le service publie, au lieu du tableau")
    lecteur.add_argument("--json", type=Path, help="écrit aussi les mesures dans ce fichier")
    lecteur.add_argument("--passage", action="store_true", help=argparse.SUPPRESS)
    lecteur.add_argument("--instrumente", action="store_true", help=argparse.SUPPRESS)
    arguments = lecteur.parse_args(argv)
    if arguments.ticks < 1:
        lecteur.error("--ticks doit être ≥ 1")
    if arguments.passage:
        json.dump(_jouer(arguments.ticks, arguments.seed, arguments.ia == "oui", arguments.instrumente), sys.stdout)
        return 0
    avec_ia = {"non": [False], "oui": [True], "les-deux": [False, True]}[arguments.ia]
    if arguments.profil is not None:
        for ia in avec_ia:
            print(profil(arguments.ticks, arguments.seed, ia, arguments.profil), end="\n\n")
        return 0
    if arguments.temoin:
        for ia in avec_ia:
            rendu = temoin(arguments.ticks, arguments.seed, ia)
            titre = "avec IA" if ia else "sans IA"
            print(f"témoin de la publication sur {arguments.ticks} jours, {titre} : {rendu['publication']} "
                  f"({rendu['octets']} octets)")
            print(f"empreinte du monde au jour {arguments.ticks}, {titre} : {rendu['empreinte']}")
        return 0
    colonnes = [mesurer(arguments.ticks, arguments.seed, ia, not arguments.sans_phases) for ia in avec_ia]
    print(tableau(colonnes, arguments.ticks, arguments.seed))
    if arguments.json is not None:
        arguments.json.write_text(json.dumps(
            {"ticks": arguments.ticks, "graine": arguments.seed, "python": platform.python_version(),
             "machine": f"{platform.system()} {platform.machine()}", "colonnes": colonnes},
            ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
