"""L'épreuve du choix de la terre (lot #652, épreuve #615) : la terre cliquée dans Unity est-elle celle que le monde retient ?

    py pc\\epreuve_moree.py --sortie D [--terre N] [--seed S] [--unity CHEMIN]

Le script lance le service de sim/ (graine S, en pause) et lit `/departs` : c'est la référence. La Morée s'y trouve par
son nom ; Unity clique la terre N (la Morée par défaut), puis aussitôt une seconde terre, par la session de #651
(`ForgeLocal3D.EpreuveChoix.Jouer`). Le script lit ensuite `/monde`, pousse un tick et relit `/monde`. Le verdict juge
contre le monde, jamais contre la terre demandée : le premier choix est accepté et attend le tick suivant, la maison
retenue après le tick est la seigneurie de la Morée, le second choix est refusé pour la raison affichée, mot pour mot.
`--terre 6` fait cliquer le Zab (contre-épreuve). Sortie : 0 égalité, 1 écart, 2 épreuve impossible.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import urllib.error
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# L'épreuve de la carte (#527) sait lancer et arrêter le service, l'interroger et dire l'impossible ; elle charge
# pc/jouer.py (qui met jeu/ sur le chemin d'import) et l'épreuve du jalon 1 (qui sait trouver et lancer Unity).
CARTE = _charger("epreuve_carte", RACINE / "pc" / "epreuve_carte.py")
JOUER, JALON1 = CARTE.JOUER, CARTE.JALON1
_lancer_service, _arreter, _requete, _impossible = CARTE._lancer_service, CARTE._arreter, CARTE._requete, CARTE._impossible
from sim.service import DEFAULT_SERVICE_PORT, SERVICE_HOST  # noqa: E402

PROJET_UNITY = RACINE / "3d" / "unity"
METHODE = "ForgeLocal3D.EpreuveChoix.Jouer"
GRAINE_PAR_DEFAUT = 0
EGALITE, ECART, IMPOSSIBLE = 0, 1, 2
MOREE = "Despotat de Morée"
ACCEPTE, CONFLIT = 200, 409
# Les libellés de ReperesDeDepart.DireLeChoix et de deposer_intention (sim/intentions.py), tels quels.
TERRE_CHOISIE = "Terre choisie : "
APPLIQUE = "\nLe monde l'applique au tick suivant (après le tick "
FIN_APPLIQUE = ")."
CHOIX_REFUSE = "Choix refusé pour "
SUITE_REFUS = " :\n"
DEJA_CHOISI = "départ déjà choisi : "


def terres(departs: dict, terre: int | None) -> tuple[dict, dict, dict]:
    """(Morée, terre cliquée, seconde terre) : trois fiches de `/departs`. La Morée se trouve par son nom, jamais par
    son id ; la terre cliquée est `terre` si elle est donnée, la Morée sinon ; la seconde, la première fiche servie
    d'un autre id. Une fiche absente lève ValueError."""
    fiches = departs["departs"]
    moree = next((f for f in fiches if f["nom"] == MOREE), None)
    if moree is None:
        raise ValueError(f"{MOREE!r} absent de /departs")
    cliquee = moree if terre is None else next((f for f in fiches if f["id"] == terre), None)
    if cliquee is None:
        raise ValueError(f"terre {terre} absente de /departs")
    seconde = next((f for f in fiches if f["id"] != cliquee["id"]), None)
    if seconde is None:
        raise ValueError(f"/departs ne sert aucune terre autre que {cliquee['id']}")
    return moree, cliquee, seconde


def _ligne(texte: str, egal: bool) -> str:
    return f"{texte} · {'égal' if egal else 'ÉCART'}"


def juger(rapport: dict, departs: dict, avant: dict, apres: dict) -> tuple[bool, list[str]]:
    """(égalité, lignes du verdict). L'attendu vient de la Morée servie et du monde, jamais de la terre demandée ni de
    `rapport["terre"]` : une session qui clique une autre terre doit rougir par le monde."""
    if rapport.get("defaut"):
        return False, [f"défaut : {rapport['defaut']}"]
    t = departs["tick"]
    moree, _, bar = terres(departs, None)
    attendue = f"seigneurie-{moree['id']}"
    refus = DEJA_CHOISI + attendue
    premier, second = rapport["premier"], rapport["second"]
    texte_premier = f"{TERRE_CHOISIE}{moree['nom']}{APPLIQUE}{t}{FIN_APPLIQUE}"
    texte_second = f"{CHOIX_REFUSE}{bar['nom']}{SUITE_REFUS}{refus}"
    maison_avant, maison_apres = avant.get("maison_du_joueur"), apres.get("maison_du_joueur")
    comparees = [
        (f"tick de la session : avant {rapport['tick_avant']} · après {rapport['tick_apres']} · /departs {t}",
         rapport["tick_avant"] == t and rapport["tick_apres"] == t),
        (f"maison avant le tick : /monde {maison_avant!r} · attendu None", maison_avant is None),
        (f"premier reçu : {premier['statut']} au tick {premier['tick']} « {premier['raison']} » · attendu {ACCEPTE} au tick {t} « »",
         (premier["statut"], premier["tick"], premier["raison"]) == (ACCEPTE, t, "")),
        (f"second reçu : {second['statut']} « {second['raison']} » · attendu {CONFLIT} « {refus} »",
         (second["statut"], second["raison"]) == (CONFLIT, refus)),
        (f"tick après la poussée : /monde {apres['tick']} · attendu {t + 1}", apres["tick"] == t + 1),
        (f"maison après le tick : /monde {maison_apres!r} · attendu {attendue!r}", maison_apres == attendue),
        (f"premier texte : {rapport['premier_texte']!r} · attendu {texte_premier!r}", rapport["premier_texte"] == texte_premier),
        (f"second texte : {rapport['second_texte']!r} · attendu {texte_second!r}", rapport["second_texte"] == texte_second),
    ]
    return all(egal for _, egal in comparees), [_ligne(texte, egal) for texte, egal in comparees]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="La terre cliquée dans Unity est-elle celle que le monde retient ?")
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--terre", type=JALON1._entier_positif)
    parser.add_argument("--seed", type=JALON1._entier_positif, default=GRAINE_PAR_DEFAUT)
    parser.add_argument("--unity", type=Path)
    args = parser.parse_args(argv)
    sortie = args.sortie.resolve()
    try:
        unity = args.unity or JALON1._unity_par_defaut()
    except (OSError, ValueError) as exc:
        return _impossible(f"version d'Unity illisible : {exc}")
    if not unity.is_file():
        return _impossible(f"Unity introuvable : {unity}")
    if JOUER._repond(DEFAULT_SERVICE_PORT):
        return _impossible(f"le port {SERVICE_HOST}:{DEFAULT_SERVICE_PORT} répond déjà")
    sortie.mkdir(parents=True, exist_ok=True)
    rapport, verdict, journal = sortie / "rapport.json", sortie / "verdict.txt", sortie / "unity.log"
    for ancien in (rapport, verdict):
        if ancien.is_file():
            ancien.unlink()

    service = None
    try:
        try:
            service = _lancer_service(args.seed)
            departs = _requete("GET", "/departs")
            moree, cliquee, seconde = terres(departs, args.terre)
        except (RuntimeError, OSError, ValueError, KeyError, urllib.error.URLError) as exc:
            return _impossible(f"la référence n'a pas pu être lue au service : {exc}")
        commande = [str(unity), "-batchmode", "-projectPath", str(PROJET_UNITY), "-executeMethod", METHODE,
                    "-logFile", str(journal), "-forgeEpreuve", str(rapport),
                    "-forgeTerre", str(cliquee["id"]), "-forgeSecondeTerre", str(seconde["id"])]
        debut = time.time()
        try:
            code = JALON1._unity(commande)
        except OSError as exc:
            return _impossible(f"Unity n'a pas démarré : {exc}")
        if code != 0:
            fin = journal.read_text(encoding="utf-8", errors="replace").splitlines() if journal.is_file() else []
            return _impossible(f"Unity a rendu {code} ; fin du journal :\n" + "\n".join(fin[-JALON1.LIGNES_JOURNAL_CITEES:]))
        if not rapport.is_file() or rapport.stat().st_mtime + JALON1.MARGE_HORODATAGE_S < debut:
            return _impossible(f"rapport absent ou antérieur à cet essai : {rapport}")
        lu = json.loads(rapport.read_text(encoding="utf-8"))
        try:
            avant = _requete("GET", "/monde")
            _requete("POST", "/tick?n=1")
            apres = _requete("GET", "/monde")
        except (RuntimeError, OSError, ValueError, urllib.error.URLError) as exc:
            return _impossible(f"le monde n'a pas pu être lu après la session : {exc}")
    finally:
        _arreter(service)

    entete = [f"graine {args.seed}", f"Morée servie : id {moree['id']} ({moree['nom']})",
              f"terre cliquée par Unity : id {cliquee['id']} ({cliquee['nom']})",
              f"seconde terre : id {seconde['id']} ({seconde['nom']})"]
    egal, corps = juger(lu, departs, avant, apres)
    texte = ["ÉGALITÉ" if egal else "ÉCART", *entete, *corps]
    verdict.write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return EGALITE if egal else ECART


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
