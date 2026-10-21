"""Juge pur des deux essais de part #659 et son lanceur PC (#764) : 0 égalité, 1 écart, 2 impossible.

    py pc\\epreuve_part.py --sortie D [--part-forte P] [--part-faible P] [--unity CHEMIN]
"""
import argparse
import http.client
import importlib.util
import json
import math
import re
import sys
import time
import urllib.request
from pathlib import Path

_spec = importlib.util.spec_from_file_location("epreuve_capitale", Path(__file__).with_name("epreuve_capitale.py"))
CAPITALE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CAPITALE)
_fiche, _ecrire, TITRES = CAPITALE._fiche, CAPITALE._ecrire, CAPITALE.TITRES
EGALITE, ECART, IMPOSSIBLE = CAPITALE.EGALITE, CAPITALE.ECART, CAPITALE.IMPOSSIBLE
MOREE = "Despotat de Morée"
ENTIERS = "terre part_demandee_pct curseur_pct tick_avant tick_apres_choix tick_apres ticks_part maison_statut".split()
TEXTES = "maison intention_json message_ordre panneau maison_json defaut".split()
NOMBRE = r"[+-]?[0-9]+(?:,[0-9]+)?"

def _nombre(v):
    try: return type(v) in (int, float) and math.isfinite(v)
    except OverflowError: return False


def _proche(v, attendu, tolerance):
    return _nombre(v) and abs(v - attendu) <= tolerance


def _valider(r, corps, p):
    if not isinstance(r, dict) or not r: raise ValueError("rapport absent ou vide")
    for cle, genre in [(c, int) for c in ENTIERS] + [(c, str) for c in TEXTES] + [("choix", dict), ("ordre", dict)]:
        if cle not in r or type(r[cle]) is not genre: raise ValueError(f"champ absent ou illisible : {cle}")
    for cle in ("choix", "ordre"):
        for champ, genre in (("statut", int), ("tick", int), ("raison", str)):
            if type(r[cle].get(champ)) is not genre: raise ValueError(f"champ absent ou illisible : {cle}.{champ}")
    if r["defaut"]: raise ValueError(f"défaut : {r['defaut']}")
    if type(p) is not int or not 0 <= p <= 60 or not 0 <= r["part_demandee_pct"] <= 60: raise ValueError("pourcentage demandé hors de 0–60")
    try: m = json.loads(corps) if isinstance(corps, str) else None
    except (ValueError, TypeError): raise ValueError("corps relu non JSON") from None
    if not isinstance(m, dict): raise ValueError("corps relu non objet")
    if type(m.get("id")) is not str or type(m.get("tick")) is not int: raise ValueError("id ou tick relu absent ou illisible")
    if not _nombre(m.get("part")): raise ValueError("part relue absente ou non finie")
    if not isinstance(m.get("grenier"), dict) or any(not _nombre(v) or v < 0 for v in m["grenier"].values()):
        raise ValueError("grenier relu absent ou kilos invalides")
    return m


def _panneau(texte, m):
    tete = re.match(r"Prélèvement : (" + NOMBRE + r") % · tick ([0-9]+)(?:\n|$)", texte)
    part = bool(tete and (tete[2].lstrip("0") or "0") == str(m["tick"]) and _proche(float(tete[1].replace(",", ".")), 100 * m["part"], .005))
    lignes = re.findall(r"(?m)^Grenier : (.*)$", texte)
    if len(lignes) != 1: return part, False
    if not m["grenier"]: return part, lignes[0] == "vide"
    morceaux = [re.fullmatch(r"(.+) : (" + NOMBRE + r") kg", s) for s in lignes[0].split(" · ")]
    if not all(morceaux): return part, False
    cles = [s[1] for s in morceaux]
    return part, len(cles) == len(set(cles)) and set(cles) == set(m["grenier"]) and all(
        _proche(float(s[2].replace(",", ".")), m["grenier"][s[1]], .005) for s in morceaux)


def juger(forte, faible, departs, relu_forte, relu_faible, part_forte, part_faible) -> tuple[int, list[str]]:
    """Confronte les rapports aux observations sans écrire ni modifier les entrées."""
    try:
        fiche, t = _fiche(departs, MOREE)
        if t != 0: raise ValueError("départ hors tick 0")
        maisons = [_valider(r, c, p) for r, c, p in ((forte, relu_forte, part_forte), (faible, relu_faible, part_faible))]
    except ValueError as exc:
        return IMPOSSIBLE, [str(exc)]
    lignes, egaux = [], []
    def ajouter(nom, vu, attendu, egal):
        lignes.append(f"{nom} : {vu} · attendu {attendu} · {'égal' if egal else 'ÉCART'}")
        egaux.append(egal)
    identite = f"seigneurie-{fiche['id']}"
    for cote, r, corps, m, p in zip(("forte", "faible"), (forte, faible), (relu_forte, relu_faible), maisons, (part_forte, part_faible)):
        def ligne(nom, vu, attendu, egal=None):
            ajouter(f"{cote} · {nom}", vu, attendu, vu == attendu if egal is None else egal)
        ligne("terre", r["terre"], fiche["id"])
        ligne("demande", (r["part_demandee_pct"], r["curseur_pct"]), (p, p))
        for cle, tick in (("choix", t), ("ordre", t + 1)):
            recu = r[cle]
            ligne(cle, f"{recu['statut']} au tick {recu['tick']} «{recu['raison']}»", f"200 au tick {tick} «»")
        ligne("ticks", tuple(r[c] for c in ("tick_avant", "tick_apres_choix", "tick_apres", "ticks_part")), (t, t + 1, t + 31, 30))
        try: intention = json.loads(r["intention_json"])
        except ValueError: intention = None
        valide = isinstance(intention, dict) and intention.get("type") == "fixer_part" and intention.get("maison") == identite and _proche(intention.get("part"), p / 100, 1e-9)
        ligne("intention", r["intention_json"], f"fixer_part {identite} {p / 100}", valide)
        ligne("maison", (r["maison"], m["id"], m["tick"]), (identite, identite, t + 31))
        ligne("part relue", m["part"], p / 100, _proche(m["part"], p / 100, 1e-9))
        ligne("corps", f"statut {r['maison_statut']}, longueurs {len(r['maison_json'])}/{len(corps)}", "statut 200, corps identiques", r["maison_statut"] == 200 and r["maison_json"] == corps)
        part, grenier = _panneau(r["panneau"], m)
        ligne("panneau part", r["panneau"].split("\n")[0], f"{100 * m['part']} % · tick {m['tick']}", part)
        ligne("panneau grenier", r["panneau"].split("\n")[1:], m["grenier"], grenier)
    a, b = (sum(m["grenier"].values()) for m in maisons)
    ajouter("grenier", f"forte {a:.2f} kg · faible {b:.2f} kg", "forte > faible", a > b)
    return (EGALITE if all(egaux) else ECART), lignes


# Le lanceur (#764) : un service neuf en pause par essai, forte puis faible ; Unity joue le curseur, la confirmation et
# le temps, Python ne fait que lire. Les aides de lancement, d'arrêt et de verdict sont celles de l'épreuve de la capitale.
CARTE, JALON1, JOUER = CAPITALE.CARTE, CAPITALE.JALON1, CAPITALE.JOUER
_lancer_service, _arreter = CAPITALE._lancer_service, CAPITALE._arreter
METHODE, GRAINE, ESSAIS = "ForgeLocal3D.EpreuvePart.Jouer", 0, ("forte", "faible")


def _lire(chemin: str) -> str:
    """Corps UTF-8 intégral d'une lecture bornée, exigée en HTTP 200 : jamais décodé en JSON puis réencodé."""
    url = f"http://{CAPITALE.SERVICE_HOST}:{CAPITALE.DEFAULT_SERVICE_PORT}{chemin}"
    with urllib.request.urlopen(url, timeout=CARTE.DELAI_REQUETE_S) as reponse:
        if reponse.status != 200: raise RuntimeError(f"{chemin} : HTTP {reponse.status}")
        return reponse.read().decode("utf-8")


def _essai(unity: Path, sortie: Path, cote: str, part: int):
    """(départs, fiche, rapport, monde, corps de /maison) d'une session ; le service possédé est toujours arrêté."""
    service, rapport, journal = None, sortie / f"rapport-{cote}.json", sortie / f"unity-{cote}.log"
    try:
        service = _lancer_service(GRAINE)
        departs = json.loads(_lire("/departs"))
        fiche, _t = _fiche(departs, MOREE)
        debut = time.time()
        code = JALON1._unity([str(unity), "-batchmode", "-projectPath", str(CAPITALE.PROJET), "-executeMethod", METHODE,
                              "-forgeEpreuve", str(rapport), "-forgeTerre", str(fiche["id"]), "-forgePart", str(part), "-logFile", str(journal)])
        if code != 0: raise RuntimeError(f"Unity a rendu {code}")
        if not rapport.is_file(): raise RuntimeError(f"rapport absent : {rapport.name}")
        if rapport.stat().st_mtime + JALON1.MARGE_HORODATAGE_S < debut: raise RuntimeError(f"rapport antérieur à cet essai : {rapport.name}")
        try: lu = json.loads(rapport.read_text(encoding="utf-8"))
        except ValueError as exc: raise RuntimeError(f"rapport illisible : {exc}") from None
        if not isinstance(lu, dict) or not lu: raise RuntimeError(f"rapport vide ou non objet : {rapport.name}")
        monde, corps = json.loads(_lire("/monde")), _lire(f"/maison?id=seigneurie-{fiche['id']}")
        if not isinstance(monde, dict) or type(monde.get("tick")) is not int: raise ValueError("/monde : tick absent ou non entier")
        if type(monde.get("maison_du_joueur")) is not str: raise ValueError("/monde : maison_du_joueur absente ou non texte")
        _valider(lu, corps, part)  # une donnée requise absente est impossible ici, où le côté est connu
        return departs, fiche, lu, monde, corps
    finally:
        _arreter(service)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prendre davantage remplit-il davantage le grenier que le panneau affiche ?")
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--part-forte", default="50")
    parser.add_argument("--part-faible", default="10")
    parser.add_argument("--unity", type=Path)
    args = parser.parse_args(argv)
    sortie = args.sortie.resolve()
    sortie.mkdir(parents=True, exist_ok=True)
    for nom in ("verdict.txt", *(f"rapport-{cote}.json" for cote in ESSAIS)):
        (sortie / nom).unlink(missing_ok=True)
    parts = {}
    for cote in ESSAIS:
        brut = getattr(args, f"part_{cote}")
        if not (brut.isascii() and brut.isdigit() and int(brut) <= 60):
            return _ecrire(sortie, IMPOSSIBLE, [f"part {cote} illisible : {brut!r}, attendu un entier de 0 à 60"])
        parts[cote] = int(brut)
    entete = [f"graine {GRAINE} · part forte {parts['forte']} % · part faible {parts['faible']} %"]
    try:
        unity = args.unity or JALON1._unity_par_defaut()
    except (OSError, ValueError) as exc:
        return _ecrire(sortie, IMPOSSIBLE, entete + [f"Unity illisible : {exc}"])
    if not unity.is_file():
        return _ecrire(sortie, IMPOSSIBLE, entete + [f"Unity absent : {unity}"])
    if JOUER._repond(CAPITALE.DEFAULT_SERVICE_PORT):
        return _ecrire(sortie, IMPOSSIBLE, entete + [f"le port {CAPITALE.SERVICE_HOST}:{CAPITALE.DEFAULT_SERVICE_PORT} répond déjà"])
    essais = {}
    for cote in ESSAIS:
        try:
            essais[cote] = _essai(unity, sortie, cote, parts[cote])
        except (RuntimeError, OSError, ValueError, http.client.HTTPException) as exc:  # IncompleteRead n'est pas une OSError
            return _ecrire(sortie, IMPOSSIBLE, entete + [f"essai {cote} : {exc}"])
    (departs, fiche, *_), seconde = essais["forte"], essais["faible"]
    lignes = [f"départs faible : Morée id {seconde[1]['id']} · attendu id {fiche['id']}, départs identiques · {'égal' if seconde[0] == departs else 'ÉCART'}"]
    for cote, (_d, _f, rapport, monde, _c) in essais.items():
        vu, attendu = (monde["tick"], monde["maison_du_joueur"]), (rapport.get("tick_apres"), f"seigneurie-{fiche['id']}")
        lignes.append(f"{cote} · monde : tick {vu[0]}, {vu[1]} · attendu tick {attendu[0]}, {attendu[1]} · {'égal' if vu == attendu else 'ÉCART'}")
    code, juges = juger(essais["forte"][2], essais["faible"][2], departs, essais["forte"][4], essais["faible"][4], parts["forte"], parts["faible"])
    if code == IMPOSSIBLE:
        return _ecrire(sortie, IMPOSSIBLE, entete + juges)
    egal = code == EGALITE and all(ligne.endswith(" · égal") for ligne in lignes)
    return _ecrire(sortie, EGALITE if egal else ECART, entete + lignes + juges)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
