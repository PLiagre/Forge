"""Viewer mince : refus, classification, SVG déterministe, sources locales."""



from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from sim.snapshot_export import build_snapshot_document, export_snapshot
from sim.world import World
from vues.tableau.classify import (
    ABSENT,
    INCOMPARABLE,
    NON_CALCULE,
    ZERO,
    classify,
    diff_status,
    numeric_diff,
)
from vues.tableau.snapshot_loader import SnapshotLoadError, load_snapshot
from vues.tableau.snapshot_loader import proposed_layers
from vues.tableau.svg_proof import render_compare_svg, render_svg

_REPO = Path(__file__).resolve().parents[3]
_VIEWER = _REPO / "vues" / "tableau"


def test_classify_trois_etats():
    assert classify(0) == ZERO
    assert classify(0.0) == ZERO
    assert classify(None) == ABSENT
    assert classify(-1) == NON_CALCULE
    assert classify(-1.0) == NON_CALCULE
    assert diff_status(-1, 4) == INCOMPARABLE
    assert numeric_diff(-1, 4) is None
    assert numeric_diff(None, 4) is None
    assert numeric_diff(2, 5) == 3.0


def test_schema_inconnu(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version":"v0a-999","cells":[]}\n', encoding="utf-8")
    try:
        load_snapshot(path)
        raise AssertionError("schema inconnu doit lever")
    except SnapshotLoadError as exc:
        assert "inconnu" in str(exc)
    proc = subprocess.run(
        [sys.executable, "-m", "vues.tableau", "--snapshot", str(path), "--proof-svg", str(tmp_path / "x.svg")],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2


def test_svg_deterministe_et_legend(tmp_path: Path):
    world = World.charger(0)
    snap = tmp_path / "a.json"
    export_snapshot(world, 0, 0, snap)
    document = load_snapshot(snap)
    first = render_svg(document, layer="population")
    second = render_svg(document, layer="population")
    assert first == second
    assert first.count("<g id=\"cell-") == document["cell_count"]
    assert all(
        f'id="cell-{int(cell["cell_id"])}"' in first for cell in document["cells"]
    )
    assert "zéro mesuré" in first
    assert "absent" in first
    assert "non calculé" in first
    assert hashlib.sha256(first.encode("utf-8")).hexdigest()
    dest = tmp_path / "carte.svg"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "vues.tableau",
            "--snapshot",
            str(snap),
            "--proof-svg",
            str(dest),
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert dest.is_file()
    missing = subprocess.run(
        [sys.executable, "-m", "vues.tableau", "--proof-svg", str(dest)],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert missing.returncode == 2


def test_comparaison_incomparable_pas_numerisee(tmp_path: Path):
    world = World.charger(0)
    snap_a = tmp_path / "a.json"
    snap_b = tmp_path / "b.json"
    export_snapshot(world, 0, 0, snap_a)
    world_b = World.charger(0)
    from sim.engine import tick
    import random
    rng = random.Random(0)
    for _ in range(5):
        tick(world_b, rng)
    export_snapshot(world_b, 0, 5, snap_b)
    svg_a = render_svg(load_snapshot(snap_a))
    svg_cmp = render_compare_svg(load_snapshot(snap_a), load_snapshot(snap_b))
    assert svg_a != svg_cmp
    assert "incomparable" in svg_cmp
    dest = tmp_path / "cmp.svg"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "vues.tableau",
            "--snapshot",
            str(snap_a),
            "--compare",
            str(snap_b),
            "--proof-svg",
            str(dest),
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0


def test_sources_sans_pipeline_ni_url():
    hits = []
    for path in _VIEWER.rglob("*"):
        if path.suffix not in {".py", ".js", ".html", ".css"}:
            continue
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix in {".html", ".js", ".css"}:
            if "http://" in text or "https://" in text:
                hits.append(str(path))
        if path.suffix in {".py", ".js"} and "tools/map" in text:
            hits.append(str(path))
    assert hits == []


def test_null_reste_absent():
    assert classify(None) == ABSENT
    forged_zero = 0
    assert classify(forged_zero) == ZERO
    assert classify(None) != classify(forged_zero)


def test_les_couches_climat_rendent_des_nombres():
    """
    Le viewer lisait autrefois la couche climat avec un repli silencieux :
    quand la clé changeait, la carte devenait vide sans qu'aucun test ne
    rougisse. Ici, une couche climat qui ne rend plus de nombres est un échec.
    """
    from vues.tableau.svg_proof import cell_value

    world = World.charger(0)
    document = build_snapshot_document(world, 0, 0)

    for couche in ("insolation", "dist_sea"):
        valeurs = [cell_value(cell, couche) for cell in document["cells"]]
        nombres = [v for v in valeurs if isinstance(v, (int, float))]
        print(f"{couche} : {len(nombres)} valeurs numériques sur {len(valeurs)} cellules")
        assert len(nombres) == len(valeurs), (
            f"La couche « {couche} » ne rend plus de nombres : "
            "le snapshot et le viewer ne parlent plus la même langue."
        )

def test_couches_derivees_du_document(tmp_path: Path):
    world = World.charger(0)
    snap = tmp_path / "layers.json"
    export_snapshot(world, 0, 0, snap)
    document = load_snapshot(snap)
    couches = proposed_layers(document)
    assert couches[0] == "population"
    interdites = {"food_deficit_kg", "hunger_ticks", "insolation", "dist_sea"}
    assert interdites.isdisjoint(couches)
    marchandises = set()
    for cell in document["cells"]:
        marchandises.update(cell.get("stocks", {}).keys())
    assert set(couches[1:]) == marchandises


def test_trois_etats_visuels_panier(tmp_path: Path):
    world = World.charger(0)
    doc = build_snapshot_document(world, 0, 0)
    cell = doc["cells"][0]
    cle = next(iter(cell["stocks"]))
    absent = dict(cell)
    absent["stocks"] = {}
    zero = dict(cell)
    zero["stocks"] = {cle: 0.0}
    sentinelle = dict(cell)
    sentinelle["stocks"] = {cle: -1.0}
    base = {k: v for k, v in doc.items() if k != "cells"}
    rendus = {
        render_svg({**base, "cells": [absent], "cell_count": 1}, layer=cle),
        render_svg({**base, "cells": [zero], "cell_count": 1}, layer=cle),
        render_svg({**base, "cells": [sentinelle], "cell_count": 1}, layer=cle),
    }
    assert len(rendus) == 3
    assert len(set(rendus)) == 3


def test_schema_inconnu_nomme_attendu(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version":"v0a-999","cells":[]}\n', encoding="utf-8")
    with pytest.raises(SnapshotLoadError) as exc:
        load_snapshot(path)
    msg = str(exc.value)
    assert "inconnu" in msg
    assert "attendu" in msg


# --- Brief 048 : le dashboard lit, il n'invente pas ---


def test_agregats_echantillon_vide_echoue():
    from vues.tableau.snapshot_loader import EchantillonVide, agregats_monde

    with pytest.raises(EchantillonVide):
        agregats_monde({"cells": []})
    with pytest.raises(EchantillonVide):
        agregats_monde({})


def test_agregats_monde_derivent_du_snapshot():
    from vues.tableau.snapshot_loader import agregats_monde
    from sim.constants import MARCHANDISE_NOURRITURE

    world = World.charger(0)
    document = build_snapshot_document(world, 0, 0)
    cellules = document["cells"]
    assert cellules, "échantillon vide : le monde chargé n'a aucune cellule"

    pop_attendue = sum(int(c["population"]) for c in cellules)
    affamees_attendues = sum(
        1
        for c in cellules
        if classify(c.get("hunger_ticks")) not in {ABSENT, NON_CALCULE}
        and c["hunger_ticks"] > 0
    )
    stocks_lus = [
        float(c["stocks"][MARCHANDISE_NOURRITURE])
        for c in cellules
        if isinstance(c.get("stocks"), dict)
        and MARCHANDISE_NOURRITURE in c["stocks"]
        and classify(c["stocks"][MARCHANDISE_NOURRITURE]) not in {ABSENT, NON_CALCULE}
    ]
    assert stocks_lus, "échantillon vide : aucune cellule n'a de nourriture mesurée"

    kpis = agregats_monde(document)
    assert kpis["cellules"]["etat"] == "mesure"
    assert kpis["cellules"]["valeur"] == len(cellules)
    assert kpis["population"]["etat"] == "mesure"
    assert kpis["population"]["valeur"] == pop_attendue
    assert kpis["population"]["cellules_lues"] == len(cellules)
    assert kpis["cellules_affamees"]["etat"] == "mesure"
    assert kpis["cellules_affamees"]["valeur"] == affamees_attendues
    assert kpis["stock_nourriture_kg"]["etat"] == "mesure"
    assert kpis["stock_nourriture_kg"]["valeur"] == pytest.approx(sum(stocks_lus))
    assert kpis["stock_nourriture_kg"]["cellules_lues"] == len(stocks_lus)


def test_absence_declaree_pas_inventee():
    from vues.tableau.snapshot_loader import agregats_couche, agregats_monde

    document = {
        "tick": 3,
        "cells": [
            {
                "cell_id": 1,
                "population": 10,
                "stocks": {"nourriture": -1.0},
                "hunger_ticks": -1,
            },
            {
                "cell_id": 2,
                "population": 4,
                "stocks": {},
            },
        ],
    }
    assert "kg_transportes" not in document
    kpis = agregats_monde(document)
    assert kpis["kg_transportes"]["etat"] == "absent"
    assert "valeur" not in kpis["kg_transportes"]
    assert kpis["stock_nourriture_kg"]["etat"] == "absent"
    assert kpis["jour_de_tick"]["etat"] == "absent"
    couche = agregats_couche(document, "population")
    assert couche["provinces"]["etat"] == "absent"


def test_tick_et_jour_sont_distincts():
    from vues.tableau.snapshot_loader import agregats_monde

    world = World.charger(0)
    document = build_snapshot_document(world, 0, 365)
    assert document["cells"], "échantillon vide"
    kpis = agregats_monde(document)
    assert kpis["tick"]["etat"] == "mesure"
    assert kpis["tick"]["valeur"] == 365
    assert kpis["tick"]["valeur"] != kpis["jour_de_tick"].get("valeur")
    assert kpis["jour_de_tick"]["etat"] == "mesure"
    assert kpis["jour_de_tick"]["valeur"] == document["jour_de_tick"]
    sans_jour = dict(document)
    del sans_jour["jour_de_tick"]
    kpis_sans = agregats_monde(sans_jour)
    assert kpis_sans["tick"]["valeur"] == 365
    assert kpis_sans["jour_de_tick"]["etat"] == "absent"


def test_dashboard_html_porte_les_kpis():
    html = (_VIEWER / "static" / "index.html").read_text(encoding="utf-8")
    for identifiant in (
        "kpis",
        "kpi-tick",
        "kpi-jour",
        "kpi-population",
        "kpi-cellules",
        "kpi-affamees",
        "kpi-stock",
        "kpi-transport",
        "layer-min",
        "layer-max",
        "histogram",
        "provinces",
    ):
        assert f'id="{identifiant}"' in html, f"identifiant manquant : {identifiant}"
    assert "id=\"panel\"" in html
    assert "id=\"map\"" in html


def test_agregats_couche_derivent_du_snapshot():
    from vues.tableau.snapshot_loader import agregats_couche

    world = World.charger(0)
    document = build_snapshot_document(world, 0, 0)
    cellules = document["cells"]
    assert cellules, "échantillon vide"
    populations = [int(c["population"]) for c in cellules]
    couche = agregats_couche(document, "population")
    assert couche["min"]["etat"] == "mesure"
    assert couche["max"]["etat"] == "mesure"
    assert couche["min"]["valeur"] == min(populations)
    assert couche["max"]["valeur"] == max(populations)
    assert couche["histogramme"]["etat"] == "mesure"
    effectifs = couche["histogramme"]["effectifs"]
    assert effectifs, "échantillon vide : histogramme sans barre"
    assert sum(effectifs) == len(populations)
    noms = {
        c["province"]["name"]
        for c in cellules
        if isinstance(c.get("province"), dict) and c["province"].get("name")
    }
    assert noms, "échantillon vide : aucune province dans le snapshot"
    assert couche["provinces"]["etat"] == "mesure"
    assert {p["nom"] for p in couche["provinces"]["lignes"]} == noms
    pop_par_nom = {}
    for cell in cellules:
        nom = cell["province"]["name"]
        pop_par_nom[nom] = pop_par_nom.get(nom, 0) + int(cell["population"])
    lu = {p["nom"]: p["somme"] for p in couche["provinces"]["lignes"]}
    assert lu == pop_par_nom

    vide = agregats_couche(
        {"cells": [{"cell_id": 1, "stocks": {}}]},
        "nourriture",
    )
    assert vide["histogramme"]["etat"] == "absent"
    assert vide["min"]["etat"] == "absent"


def test_dashboard_json_sert_les_agregats(tmp_path: Path):
    import threading
    from urllib.request import urlopen

    from vues.tableau.server import serve
    from vues.tableau.snapshot_loader import construire_dashboard, serialize_dashboard

    world = World.charger(0)
    snap = tmp_path / "a.json"
    export_snapshot(world, 0, 0, snap)
    document = load_snapshot(snap)
    attendu = serialize_dashboard(construire_dashboard(document))
    payload = snap.read_bytes()
    server = serve("127.0.0.1", 0, payload, None)
    fil = threading.Thread(target=server.serve_forever, daemon=True)
    fil.start()
    host, port = server.server_address[:2]
    try:
        with urlopen(f"http://{host}:{port}/dashboard.json") as reponse:
            obtenu = reponse.read()
    finally:
        server.shutdown()
        server.server_close()
    assert obtenu == attendu


def test_zero_mesure_n_est_pas_absent_dans_les_agregats():
    """Un zéro photographié est une mesure : le bandeau ne le déguise pas en absence."""
    from vues.tableau.snapshot_loader import agregats_couche, agregats_monde

    document = {
        "tick": 0,
        "jour_de_tick": 0,
        "kg_transportes": 0.0,
        "cells": [
            {
                "cell_id": 1,
                "population": 0,
                "stocks": {"nourriture": 0.0},
                "hunger_ticks": 0,
            },
            {
                "cell_id": 2,
                "population": 0,
                "stocks": {"nourriture": 0.0},
                "hunger_ticks": 0,
            },
        ],
    }
    kpis = agregats_monde(document)
    assert kpis["population"]["etat"] == "mesure"
    assert kpis["population"]["valeur"] == 0
    assert kpis["population"]["cellules_lues"] == 2
    assert kpis["stock_nourriture_kg"]["etat"] == "mesure"
    assert kpis["stock_nourriture_kg"]["valeur"] == 0.0
    assert kpis["stock_nourriture_kg"]["cellules_lues"] == 2
    assert kpis["cellules_affamees"]["etat"] == "mesure"
    assert kpis["cellules_affamees"]["valeur"] == 0
    assert kpis["tick"]["etat"] == "mesure"
    assert kpis["tick"]["valeur"] == 0
    assert kpis["jour_de_tick"]["etat"] == "mesure"
    assert kpis["jour_de_tick"]["valeur"] == 0
    assert kpis["kg_transportes"]["etat"] == "mesure"
    assert kpis["kg_transportes"]["valeur"] == 0.0

    couche = agregats_couche(document, "population")
    assert couche["min"]["etat"] == "mesure"
    assert couche["min"]["valeur"] == 0
    assert couche["max"]["valeur"] == 0
    assert couche["histogramme"]["etat"] == "mesure"
    assert couche["histogramme"]["effectifs"] == [2]
    assert couche["n_zeros"] == 2
    assert couche["n_valeurs"] == 0

    tete_nulle = dict(document)
    tete_nulle["kg_transportes"] = None
    assert agregats_monde(tete_nulle)["kg_transportes"]["etat"] == "absent"
    tete_sentinelle = dict(document)
    tete_sentinelle["kg_transportes"] = -1
    assert agregats_monde(tete_sentinelle)["kg_transportes"]["etat"] == "non_calcule"
    assert "valeur" not in agregats_monde(tete_sentinelle)["kg_transportes"]


def test_agregats_melangent_mesure_sentinelle_et_absence():
    """La sentinelle et la clé absente sortent des sommes ; le zéro y reste."""
    from vues.tableau.snapshot_loader import agregats_couche, agregats_monde

    document = {
        "cells": [
            {
                "cell_id": 1,
                "population": 0,
                "stocks": {"nourriture": 0.0},
                "hunger_ticks": 0,
                "province": {"name": "Bourg"},
            },
            {
                "cell_id": 2,
                "population": -1,
                "stocks": {"nourriture": -1.0},
                "hunger_ticks": -1,
                "province": {"name": "Bourg"},
            },
            {
                "cell_id": 3,
                "population": 8,
                "stocks": {},
                "hunger_ticks": 2,
            },
            {
                "cell_id": 4,
                "population": 5,
                "stocks": {"nourriture": 3.0},
                "province": {"name": "Ville"},
            },
        ],
    }
    kpis = agregats_monde(document)
    assert kpis["population"]["etat"] == "mesure"
    assert kpis["population"]["valeur"] == 13
    assert kpis["population"]["cellules_lues"] == 3
    assert kpis["cellules_affamees"]["etat"] == "mesure"
    assert kpis["cellules_affamees"]["valeur"] == 1
    assert kpis["cellules_affamees"]["cellules_lues"] == 2
    assert kpis["stock_nourriture_kg"]["etat"] == "mesure"
    assert kpis["stock_nourriture_kg"]["valeur"] == pytest.approx(3.0)
    assert kpis["stock_nourriture_kg"]["cellules_lues"] == 2

    couche = agregats_couche(document, "population")
    assert couche["n_zeros"] == 1
    assert couche["n_non_calcules"] == 1
    assert couche["n_sans_province"] == 1
    assert couche["provinces"]["etat"] == "mesure"
    lu = {ligne["nom"]: ligne["somme"] for ligne in couche["provinces"]["lignes"]}
    assert lu == {"Bourg": 0.0, "Ville": 5.0}
    effectifs = couche["histogramme"]["effectifs"]
    assert effectifs
    assert sum(effectifs) == 3


def test_dashboard_echantillon_vide_rend_409():
    import threading
    from urllib.error import HTTPError
    from urllib.request import urlopen

    from vues.tableau.server import serve

    server = serve("127.0.0.1", 0, b'{"cells":[]}\n', None)
    fil = threading.Thread(target=server.serve_forever, daemon=True)
    fil.start()
    host, port = server.server_address[:2]
    try:
        try:
            urlopen(f"http://{host}:{port}/dashboard.json")
        except HTTPError as exc:
            assert exc.code == 409
            assert "échantillon vide" in exc.read().decode("utf-8")
        else:
            raise AssertionError("un snapshot sans cellule doit rendre 409, pas 200")
    finally:
        server.shutdown()
        server.server_close()


def test_snapshot_refuse_fichier_absent_illisible_ou_sans_cellules(tmp_path: Path):
    from sim.constants import SNAPSHOT_SCHEMA_VERSION

    with pytest.raises(SnapshotLoadError) as absent:
        load_snapshot(tmp_path / "manquant.json")
    assert "absent" in str(absent.value)

    illisible = tmp_path / "casse.json"
    illisible.write_text("{pas du json", encoding="utf-8")
    with pytest.raises(SnapshotLoadError) as lu:
        load_snapshot(illisible)
    assert "illisible" in str(lu.value)

    sans_cellules = tmp_path / "sans-cells.json"
    sans_cellules.write_text(
        json.dumps({"schema_version": SNAPSHOT_SCHEMA_VERSION}),
        encoding="utf-8",
    )
    with pytest.raises(SnapshotLoadError) as cellules:
        load_snapshot(sans_cellules)
    assert "cells absentes" in str(cellules.value)


def _ouvrir_serveur(snapshot_a: bytes, snapshot_b: bytes | None = None):
    import threading

    from vues.tableau.server import serve

    server = serve("127.0.0.1", 0, snapshot_a, snapshot_b)
    fil = threading.Thread(target=server.serve_forever, daemon=True)
    fil.start()
    return server


def _fermer_serveur(server) -> None:
    server.shutdown()
    server.server_close()


def _get(host: str, port: int, chemin: str):
    """GET brut : urllib normalise `/../x`, ce qui raterait la traversée."""
    import http.client

    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request("GET", chemin)
        reponse = conn.getresponse()
        return reponse.status, reponse.read()
    finally:
        conn.close()


def test_compare_json_absent_rend_404_et_meta_le_dit():
    """Sans second snapshot, compare.json est absent ; meta.json le dit, il n'invente pas."""
    payload = b'{"cells":[{"cell_id":1,"population":1}]}\n'
    server = _ouvrir_serveur(payload, None)
    host, port = server.server_address[:2]
    try:
        statut_cmp, corps_cmp = _get(host, port, "/compare.json")
        assert statut_cmp == 404, f"sans B, compare.json doit rendre 404, pas {statut_cmp}"
        assert corps_cmp == b"absent\n"

        statut_meta, corps_meta = _get(host, port, "/meta.json")
        assert statut_meta == 200
        meta = json.loads(corps_meta.decode("utf-8"))
        assert meta == {"has_compare": False}

        statut_snap, corps_snap = _get(host, port, "/snapshot.json")
        assert statut_snap == 200
        assert corps_snap == payload
    finally:
        _fermer_serveur(server)


def test_compare_json_present_et_meta_has_compare(tmp_path: Path):
    """Avec un second snapshot, compare.json le sert tel quel ; meta.json le signale."""
    world = World.charger(0)
    snap_a = tmp_path / "a.json"
    snap_b = tmp_path / "b.json"
    export_snapshot(world, 0, 0, snap_a)
    world_b = World.charger(0)
    from sim.engine import tick
    import random

    rng = random.Random(0)
    tick(world_b, rng, 0)
    export_snapshot(world_b, 0, 1, snap_b)
    payload_a = snap_a.read_bytes()
    payload_b = snap_b.read_bytes()
    assert payload_a != payload_b, "échantillon vide : A et B sont identiques"

    server = _ouvrir_serveur(payload_a, payload_b)
    host, port = server.server_address[:2]
    try:
        statut_cmp, corps_cmp = _get(host, port, "/compare.json")
        assert statut_cmp == 200
        assert corps_cmp == payload_b

        statut_meta, corps_meta = _get(host, port, "/meta.json")
        assert statut_meta == 200
        assert json.loads(corps_meta.decode("utf-8")) == {"has_compare": True}

        statut_snap, corps_snap = _get(host, port, "/snapshot.json")
        assert statut_snap == 200
        assert corps_snap == payload_a
    finally:
        _fermer_serveur(server)


def test_serveur_refuse_la_traversee_de_chemin():
    """Un `..` ne sort pas de static/ : le source du serveur n'est pas servi."""
    from vues.tableau.server import _STATIC

    hors_static = (_STATIC.parent / "server.py").read_bytes()
    assert hors_static, "échantillon vide : viewer/server.py introuvable"

    server = _ouvrir_serveur(b'{"cells":[{"cell_id":1}]}\n', None)
    host, port = server.server_address[:2]
    try:
        for chemin in ("/../server.py", "/static/../server.py", "/foo/../../server.py"):
            statut, corps = _get(host, port, chemin)
            assert statut == 404, f"{chemin} doit rendre 404, pas {statut}"
            assert corps == b"refus\n", f"{chemin} doit dire refus, pas fuiter le source"
            assert corps != hors_static
        statut_ok, corps_ok = _get(host, port, "/")
        assert statut_ok == 200
        assert b'id="kpis"' in corps_ok
        statut_manquant, corps_manquant = _get(host, port, "/nexiste-pas.js")
        assert statut_manquant == 404
        assert corps_manquant == b"absent\n"
    finally:
        _fermer_serveur(server)


def test_comparaison_cellule_absente_de_b_est_incomparable():
    """Une cellule de A qui n'est plus dans B n'est pas numérisée : gris incomparable."""
    geom = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }
    cellule_commune = {
        "cell_id": 1,
        "population": 10,
        "geometry": geom,
    }
    cellule_disparue = {
        "cell_id": 2,
        "population": 4,
        "geometry": geom,
    }
    doc_a = {
        "tick": 0,
        "seed": 0,
        "cells": [cellule_commune, cellule_disparue],
    }
    doc_b = {
        "tick": 1,
        "seed": 0,
        "cells": [dict(cellule_commune, population=12)],
    }
    svg = render_compare_svg(doc_a, doc_b)
    assert "incomparable" in svg
    groupe_disparu = svg.split('id="cell-2"')[1].split("</g>")[0]
    assert "#bdbdbd" in groupe_disparu
    groupe_commun = svg.split('id="cell-1"')[1].split("</g>")[0]
    assert "#bdbdbd" not in groupe_commun


def test_deux_zeros_mesures_restent_comparables():
    """Un zéro photographié est une mesure : B−A = 0, pas un gris incomparable."""
    from vues.tableau.classify import VALEUR, numeric_or_none

    assert diff_status(0, 0) == VALEUR
    assert numeric_diff(0, 0) == 0.0
    assert numeric_diff(0, 4) == 4.0
    assert numeric_or_none(0) == 0.0
    assert numeric_or_none(0.0) == 0.0
    assert numeric_or_none(-1) is None


def test_le_serveur_sert_le_regard_et_le_snapshot_a(tmp_path: Path):
    """Sans B, /snapshot.json reste A ; / et /app.js s'ouvrent. La présence
    des fichiers n'est pas la fonction : le serveur doit les servir."""
    import threading
    from urllib.request import urlopen

    from vues.tableau.server import serve

    world = World.charger(0)
    snap = tmp_path / "a.json"
    export_snapshot(world, 0, 0, snap)
    payload = snap.read_bytes()
    server = serve("127.0.0.1", 0, payload, None)
    fil = threading.Thread(target=server.serve_forever, daemon=True)
    fil.start()
    host, port = server.server_address[:2]
    try:
        with urlopen(f"http://{host}:{port}/") as reponse:
            html = reponse.read()
            assert reponse.status == 200
            assert b'id="map"' in html
            assert b'id="kpis"' in html
        with urlopen(f"http://{host}:{port}/app.js") as reponse:
            js = reponse.read()
            assert reponse.status == 200
            assert b"deriveLayers" in js
        with urlopen(f"http://{host}:{port}/snapshot.json") as reponse:
            assert reponse.read() == payload
    finally:
        server.shutdown()
        server.server_close()
