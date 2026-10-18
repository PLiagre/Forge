"""L'épreuve de la capitale (lot #703, épreuve #684).

    py pc\\epreuve_capitale.py --sortie D [--seed S] [--unity CHEMIN]

Deux services neufs (graine S, en pause). Le Zab puis Bar se trouvent par leur nom. Unity joue la session #702, qui pousse seule le tick. Le siège attendu est celui de `/maison`. 0 égalité, 1 écart, 2 impossible.
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


CARTE = _charger("epreuve_carte", RACINE / "pc" / "epreuve_carte.py")
JOUER, JALON1 = CARTE.JOUER, CARTE.JALON1
_lancer_service, _arreter, _requete = CARTE._lancer_service, CARTE._arreter, CARTE._requete
from sim.service import DEFAULT_SERVICE_PORT, SERVICE_HOST  # noqa: E402

PROJET = RACINE / "3d" / "unity"
METHODE = "ForgeLocal3D.EpreuveCapitale.Jouer"
EGALITE, ECART, IMPOSSIBLE = 0, 1, 2
ZAB, BAR = "Émirat du Zab", "Duché de Bar"
SCENE_VILLE, SCENE_CARTE = "Forge_Desert_Ville_ksar_des_sept_puits", "Forge_Carte"
MESSAGE, ACCEPTE = "Pas encore de kit pour cette terre", 200
ESSAIS = (("zab", ZAB, True), ("bar", BAR, False))
ENTIERS = ("terre", "tick_avant", "tick_apres", "cellule", "tick_ouverture")
TEXTES = ("scene_active", "panneau_lieu", "message_passage", "defaut")
TITRES = {EGALITE: "ÉGALITÉ", ECART: "ÉCART", IMPOSSIBLE: "ÉPREUVE IMPOSSIBLE"}


def _fiche(departs: dict, nom: str) -> tuple[dict, int]:
    if not isinstance(departs, dict) or type(departs.get("tick")) is not int or not isinstance(departs.get("departs"), list):
        raise ValueError("départs illisibles")
    trouvees = [f for f in departs["departs"] if isinstance(f, dict) and f.get("nom") == nom]
    if len(trouvees) != 1 or type(trouvees[0].get("id")) is not int:
        raise ValueError(f"fiche {nom!r} : {len(trouvees)} trouvée(s)")
    return trouvees[0], departs["tick"]


def _valider(rapport: dict) -> None:
    if not isinstance(rapport, dict):
        raise ValueError("rapport illisible")
    if not rapport:
        raise ValueError("rapport vide")
    for cle in (*ENTIERS, *TEXTES, "choix"):
        if cle not in rapport:
            raise ValueError(f"champ requis manquant : {cle}")
    if any(type(rapport[c]) is not int for c in ENTIERS) or any(type(rapport[c]) is not str for c in TEXTES):
        raise ValueError("champ illisible")
    choix = rapport["choix"]
    if not isinstance(choix, dict) or any(c not in choix for c in ("statut", "tick", "raison")):
        raise ValueError("champ requis manquant : choix")
    if type(choix["statut"]) is not int or type(choix["tick"]) is not int or type(choix["raison"]) is not str:
        raise ValueError("champ illisible : choix")


def _siege(maison: dict, fiche: dict) -> int:
    if not isinstance(maison, dict) or maison.get("id") != f"seigneurie-{fiche['id']}" or maison.get("nom") != fiche.get("maison"):
        raise ValueError("identité illisible")
    siege = maison.get("siege")
    if siege is None or (isinstance(siege, dict) and "cell_id" in siege and siege["cell_id"] is None):
        raise ValueError("siège nul")
    if not isinstance(siege, dict) or type(siege.get("cell_id")) is not int or type(maison.get("tick")) is not int:
        raise ValueError("siège absent")
    return siege["cell_id"]


def juger(rapport, departs, maison, avant, apres, avec_kit: bool) -> tuple[int, list[str]]:
    """Code 0, 1 ou 2, et les lignes. La fiche se retrouve par son nom ; le siège vient de `/maison`."""
    try:
        _valider(rapport)
        if rapport["defaut"]:
            return IMPOSSIBLE, [f"défaut : {rapport['defaut']}"]
        fiche, t = _fiche(departs, ZAB if avec_kit else BAR)
        cellule = _siege(maison, fiche)
        if not isinstance(avant, dict) or type(avant.get("tick")) is not int or not isinstance(apres, dict) or type(apres.get("tick")) is not int:
            raise ValueError("tick du monde illisible")
    except ValueError as exc:
        return IMPOSSIBLE, [str(exc)]
    choix, suiv = rapport["choix"], t + 1
    scene, panneau = (SCENE_VILLE, f"Cellule {cellule} · tick {suiv}") if avec_kit else (SCENE_CARTE, "")
    attendus = (
        ("terre", rapport["terre"], fiche["id"]),
        ("tick avant", f"monde {avant['tick']} · session {rapport['tick_avant']} · choix {choix['tick']}", f"monde {t} · session {t} · choix {t}"),
        ("maison avant", avant.get("maison_du_joueur"), None),
        ("reçu", f"{choix['statut']} au tick {choix['tick']} «{choix['raison']}»", f"{ACCEPTE} au tick {t} «»"),
        ("tick après", f"session {rapport['tick_apres']} · monde {apres['tick']} · maison {maison['tick']}", f"session {suiv} · monde {suiv} · maison {suiv}"),
        ("maison retenue", apres.get("maison_du_joueur"), f"seigneurie-{fiche['id']}"),
        ("scène", rapport["scene_active"], scene),
        ("cellule", rapport["cellule"], cellule if avec_kit else -1),
        ("ouverture", rapport["tick_ouverture"], suiv if avec_kit else -1),
        ("panneau", rapport["panneau_lieu"], panneau),
        ("message", rapport["message_passage"], "" if avec_kit else MESSAGE),
    )
    lignes = [f"{e} : {v!r} · attendu {a!r} · {'égal' if v == a else 'ÉCART'}" for e, v, a in attendus]
    return (EGALITE if all(v == a for _, v, a in attendus) else ECART), lignes


def _ecrire(sortie: Path, code: int, lignes: list[str]) -> int:
    texte = [TITRES[code], f"code {code}", *lignes]
    (sortie / "verdict.txt").write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return code


def _entete(fiche: dict, maison: dict) -> list[str]:
    siege = maison.get("siege") if isinstance(maison, dict) else None
    cellule = siege.get("cell_id") if isinstance(siege, dict) else None
    lieu = f" ({siege.get('nom')})" if isinstance(siege, dict) and siege.get("nom") else ""
    return [f"{fiche['nom']} : id {fiche['id']}",
            f"maison seigneurie-{fiche['id']} · siège {cellule}{lieu} au tick {maison.get('tick') if isinstance(maison, dict) else None}"]


def _essai(unity: Path, sortie: Path, slug: str, nom: str, avec_kit: bool, seed: int):
    service = info = None
    rapport, journal = sortie / f"rapport-{slug}.json", sortie / f"unity-{slug}.log"
    try:
        try:
            service = _lancer_service(seed)
            departs, avant = _requete("GET", "/departs"), _requete("GET", "/monde")
            fiche, _t = _fiche(departs, nom)
            debut = time.time()
            code_unity = JALON1._unity([str(unity), "-batchmode", "-projectPath", str(PROJET), "-executeMethod", METHODE,
                                        "-logFile", str(journal), "-forgeEpreuve", str(rapport), "-forgeTerre", str(fiche["id"])])
            if code_unity != 0:
                raise RuntimeError(f"Unity a rendu {code_unity}")
            if not rapport.is_file():
                raise RuntimeError(f"rapport absent : {rapport.name}")
            if rapport.stat().st_mtime + JALON1.MARGE_HORODATAGE_S < debut:
                raise RuntimeError(f"rapport antérieur à cet essai : {rapport.name}")
            try:
                lu = json.loads(rapport.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"rapport invalide : {exc}") from None
            apres = _requete("GET", "/monde")
            maison = _requete("GET", f"/maison?id=seigneurie-{fiche['id']}")
            info = (fiche, maison)
        except (RuntimeError, OSError, ValueError, urllib.error.URLError) as exc:
            return IMPOSSIBLE, [f"{nom} : {exc}"], info
        code, lignes = juger(lu, departs, maison, avant, apres, avec_kit)
        return code, lignes, info
    finally:
        _arreter(service)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Le passage à la capitale ouvre-t-il le siège que le monde sert ?")
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--seed", type=JALON1._entier_positif, default=0)
    parser.add_argument("--unity", type=Path)
    args = parser.parse_args(argv)
    sortie = args.sortie.resolve()
    sortie.mkdir(parents=True, exist_ok=True)
    for nom in ("verdict.txt", *(f"rapport-{slug}.json" for slug, *_ in ESSAIS)):
        if (sortie / nom).is_file():
            (sortie / nom).unlink()
    graine = [f"graine {args.seed}"]
    try:
        unity = args.unity or JALON1._unity_par_defaut()
    except (OSError, ValueError) as exc:
        return _ecrire(sortie, IMPOSSIBLE, graine + [f"Unity illisible : {exc}"])
    if not unity.is_file():
        return _ecrire(sortie, IMPOSSIBLE, graine + [f"Unity introuvable : {unity}"])
    if JOUER._repond(DEFAULT_SERVICE_PORT):
        return _ecrire(sortie, IMPOSSIBLE, graine + [f"le port {SERVICE_HOST}:{DEFAULT_SERVICE_PORT} répond déjà"])
    morceaux, codes = list(graine), []
    for slug, nom, avec_kit in ESSAIS:
        code, lignes, info = _essai(unity, sortie, slug, nom, avec_kit, args.seed)
        if info:
            morceaux.extend(_entete(*info))
        morceaux.extend(lignes)
        codes.append(code)
        if code == IMPOSSIBLE:
            break
    resultat = IMPOSSIBLE if IMPOSSIBLE in codes else ECART if ECART in codes else EGALITE
    return _ecrire(sortie, resultat, morceaux)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
