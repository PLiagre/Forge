"""pc/epreuve_capitale.py juge la session #702 contre le siège servi (lot #703).

`/departs` du pont est ramené au tick 0. Les maisons du pont, copiées au tick 1, ne sont pas un relevé PC. `avant` est au tick 0 sans joueur, `apres` au tick 1 avec la maison de l'essai.
"""
import copy
import importlib.util
import json
import os
import sys
import time
import urllib.error
from pathlib import Path

import pytest

JEU = Path(__file__).resolve().parents[2]
RACINE = JEU.parent
EPREUVE = RACINE / "pc" / "epreuve_capitale.py"
PONT = RACINE / "3d" / "unity" / "Assets" / "ForgeLocal3D" / "Pont" / "Tests"
RAPPORTS = RACINE / "docs" / "mesures" / "702-session-capitale"
AVANT = {"tick": 0}
if str(JEU) not in sys.path:
    sys.path.insert(0, str(JEU))


def _charger(nom, chemin):
    if not chemin.is_file():
        pytest.fail(f"fichier introuvable : {chemin}")
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def epreuve():
    return _charger("epreuve_capitale", EPREUVE)


@pytest.fixture
def base():
    departs = json.loads((PONT / "departs-graine0-tick3.json").read_text(encoding="utf-8"))
    departs["tick"] = 0

    def maison(nom):
        lu = json.loads((PONT / nom).read_text(encoding="utf-8"))
        lu["tick"] = 1
        return lu

    return {"departs": departs,
            "zab": json.loads((RAPPORTS / "rapport-zab.json").read_text(encoding="utf-8")),
            "bar": json.loads((RAPPORTS / "rapport-bar.json").read_text(encoding="utf-8")),
            "maison_zab": maison("maison-zab-graine0-tick0.json"), "maison_bar": maison("maison-bar-graine0-tick0.json")}


def _juge(epreuve, rapport, base, avec_kit, **kw):
    departs = kw.get("departs", base["departs"])
    nom = epreuve.ZAB if avec_kit else epreuve.BAR
    trouvees = [f for f in departs.get("departs", []) if isinstance(f, dict) and f.get("nom") == nom]
    retenue = kw.get("retenue", f"seigneurie-{trouvees[0]['id']}" if len(trouvees) == 1 else None)
    apres = kw.get("apres", {"tick": kw.get("tick_monde", 1), "maison_du_joueur": retenue})
    return epreuve.juger(rapport, departs, kw.get("maison", base["maison_zab" if avec_kit else "maison_bar"]),
                         kw.get("avant", AVANT), apres, avec_kit)


def _ecarts(lignes):
    return [ligne for ligne in lignes if ligne.endswith(" · ÉCART")]


def test_les_rapports_702_du_zab_et_de_bar_sont_egaux(epreuve, base):
    siege = base["maison_zab"]["siege"]["cell_id"]
    assert base["zab"]["panneau_lieu"] == f"Cellule {siege} · tick 1" and base["bar"]["cellule"] == base["bar"]["tick_ouverture"] == -1
    for avec, cle in ((True, "zab"), (False, "bar")):
        code, lignes = _juge(epreuve, base[cle], base, avec)
        assert code == 0 and len(lignes) == 11 and all(l.endswith(" · égal") for l in lignes), lignes


@pytest.mark.parametrize("champ,prefixe,valeur", [
    ("cellule", "cellule", 1175), ("scene_active", "scène", "ailleurs"), ("panneau_lieu", "panneau", "ailleurs"),
    ("tick_ouverture", "ouverture", 0), ("message_passage", "message", "x"), ("scene_active", "scène", ""),
])
def test_un_zab_ailleurs_ou_incomplet_est_un_ecart(epreuve, base, champ, prefixe, valeur):
    code, lignes = _juge(epreuve, copy.deepcopy(base["zab"]) | {champ: valeur}, base, True)
    assert code == 1 and len(_ecarts(lignes)) == 1 and _ecarts(lignes)[0].startswith(prefixe)


def test_contre_epreuve_ville_ailleurs(epreuve, base):
    """Copie en mémoire du rapport Zab #702 : cellule et panneau à 1175. Pas une mesure PC."""
    rapport = copy.deepcopy(base["zab"]) | {"cellule": 1175, "panneau_lieu": "Cellule 1175 · tick 1"}
    code, lignes = _juge(epreuve, rapport, base, True)
    print("transformation : rapport-zab.json copié en mémoire, cellule = 1175, panneau = « Cellule 1175 · tick 1 »")
    print(f"code du jugement : {code}")
    print("\n".join(lignes))
    ecarts = _ecarts(lignes)
    assert code == 1 and len(ecarts) == 2
    assert ecarts[0].startswith("cellule") and "10103" in ecarts[0] and "1175" in ecarts[0]
    assert ecarts[1].startswith("panneau") and "10103" in ecarts[1] and "1175" in ecarts[1]


@pytest.mark.parametrize("champ,valeur", [("scene_active", "ailleurs"), ("message_passage", ""), ("message_passage", "presque")])
def test_bar_sans_le_message_ou_hors_de_la_carte_est_un_ecart(epreuve, base, champ, valeur):
    assert _juge(epreuve, copy.deepcopy(base["bar"]) | {champ: valeur}, base, False)[0] == 1


def test_bar_qui_ouvre_une_ville_est_un_ecart(epreuve, base):
    rapport = copy.deepcopy(base["bar"]) | {"scene_active": epreuve.SCENE_VILLE, "cellule": base["zab"]["cellule"],
                                            "tick_ouverture": 1, "panneau_lieu": base["zab"]["panneau_lieu"]}
    code, lignes = _juge(epreuve, rapport, base, False)
    assert code == 1 and {l.split(" :", 1)[0] for l in _ecarts(lignes)} >= {"scène", "cellule", "ouverture", "panneau"}


@pytest.mark.parametrize("ou,valeur", [("rapport", 0), ("rapport", 2), ("monde", 0), ("maison", 2), ("recu", 409), ("retenue", "seigneurie-autre")])
def test_un_tick_un_recu_ou_une_maison_deplaces_sont_un_ecart(epreuve, base, ou, valeur):
    rapport, maison, kw = copy.deepcopy(base["zab"]), copy.deepcopy(base["maison_zab"]), {}
    if ou == "rapport":
        rapport["tick_apres"] = valeur
    elif ou == "monde":
        kw["tick_monde"] = valeur
    elif ou == "maison":
        maison["tick"] = valeur
    elif ou == "recu":
        rapport["choix"] = {"statut": valeur, "tick": 0, "raison": "refusé"}
    else:
        kw["retenue"] = valeur
    assert _juge(epreuve, rapport, base, True, maison=maison, **kw)[0] == 1


def test_le_siege_de_la_maison_est_l_attendu_quel_que_soit_l_ordre(epreuve, base):
    inverse = dict(base["departs"], departs=list(reversed(base["departs"]["departs"])))
    assert epreuve._fiche(base["departs"], epreuve.ZAB)[0]["id"] == epreuve._fiche(inverse, epreuve.ZAB)[0]["id"]
    assert _juge(epreuve, base["zab"], base, True, departs=inverse)[0] == 0
    assert next(f["cell_id"] for f in base["departs"]["departs"] if f["nom"] == epreuve.ZAB) == 10103
    maison = copy.deepcopy(base["maison_zab"])
    maison["siege"] = dict(maison["siege"], cell_id=99999)
    code, lignes = _juge(epreuve, base["zab"], base, True, maison=maison)
    assert code == 1 and any(l.startswith("cellule") and "99999" in l and l.endswith(" · ÉCART") for l in lignes)
    aligne = copy.deepcopy(base["zab"]) | {"cellule": 99999, "panneau_lieu": "Cellule 99999 · tick 1"}
    assert _juge(epreuve, aligne, base, True, maison=maison)[0] == 0


@pytest.mark.parametrize("cas", ["vide", "manquant", "defaut", "fiche", "ambigu", "siege"])
def test_un_rapport_illisible_une_fiche_absente_ou_un_siege_nul_est_impossible(epreuve, base, cas):
    rapport, departs, maison = copy.deepcopy(base["zab"]), base["departs"], base["maison_zab"]
    if cas == "vide":
        rapport = {}
    elif cas == "manquant":
        del rapport["cellule"]
    elif cas == "defaut":
        rapport["defaut"] = "session interrompue"
    elif cas == "fiche":
        departs = dict(departs, departs=[f for f in departs["departs"] if f["nom"] != epreuve.ZAB])
    elif cas == "ambigu":
        departs = dict(departs, departs=[*departs["departs"], dict(departs["departs"][-1], nom=epreuve.ZAB)])
    else:
        maison = copy.deepcopy(maison)
        maison["siege"] = None
    code, lignes = _juge(epreuve, rapport, base, True, departs=departs, maison=maison)
    assert code == 2 and lignes and not any(l.endswith(" · égal") for l in lignes)
    attendu = {"defaut": "session interrompue", "siege": "siège nul", "manquant": "cellule"}.get(cas)
    assert attendu is None or attendu in lignes[0]


def test_une_sentinelle_absente_ne_remplace_pas_le_champ(epreuve, base):
    rapport = copy.deepcopy(base["bar"])
    del rapport["cellule"]
    code, lignes = _juge(epreuve, rapport, base, False)
    assert code == 2 and any("cellule" in l for l in lignes)


def test_le_script_ne_prend_pas_la_cellule_ni_le_tick_pour_reference():
    source = EPREUVE.read_text(encoding="utf-8")
    for interdit in ("10103", "POST", "/tick", "/vitesse", "-quit", "-nographics"):
        assert interdit not in source, interdit


def _harnais(monkeypatch, epreuve, tmp_path, base, plan):
    zab = next(f["id"] for f in base["departs"]["departs"] if f["nom"] == epreuve.ZAB)
    bar = next(f["id"] for f in base["departs"]["departs"] if f["nom"] == epreuve.BAR)
    brut = {cle: (RAPPORTS / f"rapport-{cle}.json").read_text(encoding="utf-8") for cle in ("zab", "bar")}
    etat = {"services": [], "arrets": [], "unity": [], "http": [], "seeds": [], "zab": zab, "bar": bar}

    def lancer(seed):
        etat["seeds"].append(seed)
        etat["services"].append(len(etat["services"]))
        etat["session"] = False
        return etat["services"][-1]

    def requete(methode, chemin):
        etat["http"].append((methode, chemin))
        if plan[etat["services"][-1]].get("http"):
            raise urllib.error.URLError(plan[etat["services"][-1]]["http"])
        if methode != "GET":
            raise AssertionError(methode)
        if chemin == "/departs":
            departs = copy.deepcopy(base["departs"])
            departs["departs"].reverse()
            return departs
        if chemin == "/monde":
            return {"tick": 0} if not etat.get("session") else {"tick": 1, "maison_du_joueur": f"seigneurie-{etat['terre']}"}
        if chemin in (f"/maison?id=seigneurie-{zab}", f"/maison?id=seigneurie-{bar}"):
            return copy.deepcopy(base["maison_zab" if chemin.endswith(f"-{zab}") else "maison_bar"])
        raise RuntimeError(chemin)

    def unity(commande):
        etat["unity"].append(list(commande))
        courant, etat["terre"], etat["session"] = plan[etat["services"][-1]], int(commande[commande.index("-forgeTerre") + 1]), True
        if courant.get("ecrire", courant.get("code", 0) == 0) and not courant.get("http"):
            texte = courant.get("corps")
            if texte is None and courant.get("rapport"):
                lu = json.loads(brut[courant["rapport"]])
                lu["cellule"] = courant.get("cellule", lu["cellule"])
                texte = json.dumps(lu)
            if texte is not None:
                chemin = Path(commande[commande.index("-forgeEpreuve") + 1])
                chemin.write_text(texte, encoding="utf-8")
                if courant.get("vieux"):
                    os.utime(chemin, (time.time() - 3600, time.time() - 3600))
        return courant.get("code", 0)

    exe = tmp_path / "Unity.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(epreuve, "_lancer_service", lancer)
    monkeypatch.setattr(epreuve, "_arreter", lambda svc: etat["arrets"].append(svc) if svc is not None else None)
    monkeypatch.setattr(epreuve, "_requete", requete)
    monkeypatch.setattr(epreuve.JOUER, "_repond", lambda _port: False)
    monkeypatch.setattr(epreuve.JALON1, "_unity", unity)
    etat["exe"] = exe
    return etat


@pytest.mark.parametrize("plan,attendu,cause", [
    ([{"rapport": "zab"}, {"rapport": "bar"}], 0, "ÉGALITÉ"),
    ([{"rapport": "zab", "cellule": 1175}, {"rapport": "bar"}], 1, "ÉCART"),
    ([{"rapport": "zab"}, {"code": 4}], 2, "rendu 4"),
    ([{"code": 7}], 2, "rendu 7"),
    ([{"corps": "pas du json"}], 2, "invalide"),
    ([{"ecrire": False}], 2, "absent"),
    ([{"rapport": "zab", "vieux": True}], 2, "antérieur"),
    ([{"http": "lecture HTTP impossible"}], 2, "lecture HTTP impossible"),
])
def test_main_orchestre_deux_services_et_nomme_la_panne(epreuve, base, tmp_path, monkeypatch, capsys, plan, attendu, cause):
    etat = _harnais(monkeypatch, epreuve, tmp_path, base, plan)
    sortie = tmp_path / "sortie"
    assert epreuve.main(["--sortie", str(sortie), "--unity", str(etat["exe"]), "--seed", "0"]) == attendu
    vu = capsys.readouterr().out
    assert cause in vu and etat["arrets"] == etat["services"]
    assert all(m == "GET" and "/tick" not in c and "/vitesse" not in c for m, c in etat["http"])
    assert all("-quit" not in c and "-nographics" not in c for c in etat["unity"])
    if attendu == 0:
        assert etat["seeds"] == [0, 0] and vu.startswith("ÉGALITÉ")
        assert [c[c.index("-forgeTerre") + 1] for c in etat["unity"]] == [str(etat["zab"]), str(etat["bar"])]
        assert (sortie / "rapport-zab.json").is_file() and (sortie / "rapport-bar.json").is_file()
    if attendu == 1:
        assert vu.startswith("ÉCART") and "ÉPREUVE IMPOSSIBLE" not in vu
    if cause == "rendu 4":
        assert len(etat["services"]) == 2


@pytest.mark.parametrize("cas", ["unity", "port"])
def test_unity_absent_ou_port_pris_sort_a_2_avant_toute_session(epreuve, tmp_path, monkeypatch, cas):
    sortie = tmp_path / cas
    sortie.mkdir()
    (sortie / "verdict.txt").write_text("ÉGALITÉ\nancien verdict\n", encoding="utf-8")
    exe = tmp_path / "Unity.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(epreuve, "_lancer_service", lambda *_a, **_k: pytest.fail("service"))
    monkeypatch.setattr(epreuve.JALON1, "_unity", lambda *_a, **_k: pytest.fail("unity"))
    if cas == "port":
        monkeypatch.setattr(epreuve.JOUER, "_repond", lambda _port: True)
        args, cause = ["--sortie", str(sortie), "--unity", str(exe)], "répond déjà"
    else:
        args, cause = ["--sortie", str(sortie), "--unity", str(tmp_path / "absent.exe")], "introuvable"
    assert epreuve.main(args) == 2
    texte = (sortie / "verdict.txt").read_text(encoding="utf-8")
    assert texte.startswith("ÉPREUVE IMPOSSIBLE") and cause in texte and "ancien" not in texte
