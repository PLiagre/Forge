"""
Ce qui tient la commande de bout en bout.

La porte de la V1 n'est pas une somme de tests unitaires : c'est
« une commande simule et affiche ». Ce fichier protège ce que seul
l'assemblage peut casser :

  - les trois vues lisent **la même** photographie, pas trois mondes ;
  - la commande refuse ce qu'elle ne peut pas faire, au lieu de rendre
    une sortie muette ;
  - le compte rendu porte de quoi rejouer et de quoi douter.

L'horizon est court exprès. Ce fichier ne mesure pas le monde — c'est le
travail de `sim/tests/` — il mesure que la plomberie tient.
"""

import json
from pathlib import Path

import pytest

from forge.__main__ import main

TICKS_COURTS = 3


def _jouer(tmp_path: Path, *args: str) -> tuple[int, Path]:
    sortie = tmp_path / "sortie"
    code = main([
        "--ticks", str(TICKS_COURTS),
        "--seed", "0",
        "--pas", "2",
        "--largeur", "64",
        "--sortie", str(sortie),
        *args,
    ])
    return code, sortie


def test_une_commande_simule_et_affiche(tmp_path):
    """
    La porte de la V1, en un test.

    Si celui-ci rougit, « lancer une simulation et l'afficher » ne marche
    plus — quelle que soit la couleur des tests unitaires.
    """
    code, sortie = _jouer(tmp_path)
    assert code == 0

    for nom in ("monde.json", "formes.json", "carte.png", "tableau.svg", "planche.html", "resume.json"):
        chemin = sortie / nom
        assert chemin.is_file(), f"{nom} n'a pas été écrit"
        assert chemin.stat().st_size > 0, f"{nom} est vide"


def test_les_vues_lisent_la_meme_photographie(tmp_path):
    """
    Une seule simulation, trois regards. Le tick et la graine du compte rendu
    doivent être ceux du snapshot — sinon une vue montre un autre monde, et
    c'est précisément ce que « une seule source de vérité » interdit.
    """
    _code, sortie = _jouer(tmp_path)
    resume = json.loads((sortie / "resume.json").read_text(encoding="utf-8"))
    monde = json.loads((sortie / "monde.json").read_text(encoding="utf-8"))

    assert resume["carte"]["tick"] == monde["tick"] == TICKS_COURTS
    assert resume["carte"]["seed"] == monde["seed"] == 0
    assert resume["carte"]["cellules"] == monde["cell_count"]
    assert resume["simulation"]["cellules"] == monde["cell_count"]


def test_le_compte_rendu_porte_le_plafond_de_survie(tmp_path):
    """
    Ce que la V1 promet en un chiffre : le monde nourrit ceux qu'il amorce.

    Le compte rendu le publie à chaque exécution, pour qu'une régression se
    voie dans la sortie et pas seulement dans une suite de tests.
    """
    _code, sortie = _jouer(tmp_path)
    resume = json.loads((sortie / "resume.json").read_text(encoding="utf-8"))
    plafond = resume["simulation"]["plafond_de_survie_a_l_amorcage"]
    assert plafond >= 1.0, (
        f"plafond {plafond:.4f} < 1 : la commande affiche un monde condamné."
    )


def test_le_monde_ne_s_effondre_pas_sur_l_horizon_de_la_commande(tmp_path):
    """
    Garde grossière contre un monde qui s'effondre : il perdait jadis 86 %
    de ses habitants la première année. Sur trois
    ticks, une chute de plus d'un pour cent est déjà anormale.
    """
    _code, sortie = _jouer(tmp_path)
    part = json.loads((sortie / "resume.json").read_text(encoding="utf-8"))
    part = part["simulation"]["part_survivante"]
    assert part > 0.99, f"part survivante {part:.4f} : le monde s'effondre dès le départ."


def test_sans_chronique_saute_la_planche(tmp_path):
    """La planche rejoue le monde ; on doit pouvoir ne pas la payer."""
    code, sortie = _jouer(tmp_path, "--sans-chronique")
    assert code == 0
    assert not (sortie / "planche.html").exists()
    assert (sortie / "carte.png").is_file()


def test_un_horizon_negatif_est_refuse(tmp_path):
    assert main(["--ticks", "-1", "--sortie", str(tmp_path / "x")]) == 2


def test_un_pas_nul_est_refuse(tmp_path):
    assert main(["--ticks", "1", "--pas", "0", "--sortie", str(tmp_path / "x")]) == 2


def test_une_lecture_inconnue_est_refusee_avant_de_simuler(tmp_path):
    """argparse refuse la lecture : on ne joue pas 365 ticks pour rien."""
    with pytest.raises(SystemExit):
        main(["--lecture", "prosperite", "--sortie", str(tmp_path / "x")])


def _terres_depart():
    from sim.seigneuries import charger_seigneuries

    table = charger_seigneuries()
    assert table, "échantillon vide : aucune terre de départ"
    return next(s.id for s in table if s.nom == "Duché de Bar"), max(s.id for s in table) + 1


def test_depart_et_photographie_ne_differe_que_par_la_terre(tmp_path):
    bar, _ = _terres_depart()
    code, avec = _jouer(tmp_path / "avec", "--depart", str(bar), "--sans-chronique")
    assert code == 0
    code, sans = _jouer(tmp_path / "sans", "--sans-chronique")
    assert code == 0
    assert json.loads((avec / "resume.json").read_text())["simulation"]["maison_du_joueur"] == f"seigneurie-{bar}"
    assert "maison_du_joueur" not in json.loads((sans / "resume.json").read_text())["simulation"]
    photographie = json.loads((avec / "monde.json").read_text())
    temoin = json.loads((sans / "monde.json").read_text())
    assert photographie.pop("terre_choisie")["id"] == bar
    assert temoin.pop("terre_choisie") is None
    assert "maisons_du_joueur" not in temoin
    with pytest.raises(AssertionError):
        assert photographie.copy() == temoin
    maisons = photographie.pop("maisons_du_joueur")
    assert maisons["maison"]["id"] == f"seigneurie-{bar}"
    from sim.world import World
    suzerain = next(m.suzerain for m in World.charger(0).maisons if m.id == maisons["maison"]["id"])
    assert suzerain is not None and maisons["suzerain"]["id"] == suzerain
    assert photographie == temoin
    import copy
    sonde = copy.deepcopy(photographie)
    assert sonde["cells"], "échantillon vide"
    sonde["cells"][0]["population"] += 1
    with pytest.raises(AssertionError):
        assert sonde == temoin
    print(f"photographies_comparées={len((photographie, temoin))}, cellules_vues={len(photographie['cells'])}")


def _verifier_refus_depart(tmp_path, arguments, message, capsys):
    code, sortie = _jouer(tmp_path, *arguments, "--sans-chronique")
    assert code == 2
    assert message in capsys.readouterr().err
    assert not (sortie / "resume.json").exists()
    assert not (sortie / "monde.json").exists()


@pytest.mark.parametrize("cas", ["inconnu", "double", "sans_tick"])
def test_depart_refuse_avant_simulation(tmp_path, cas, capsys, monkeypatch):
    bar, inconnu = _terres_depart()
    arguments, message = {
        "inconnu": (["--depart", str(inconnu)], "seigneurie inconnue"),
        "double": (["--depart", str(bar), "--depart", str(bar)], "départ déjà choisi"),
        "sans_tick": (["--depart", str(bar), "--ticks", "0"], "l'intention s'applique au tick suivant"),
    }[cas]
    monkeypatch.setattr("sim.engine.tick", lambda *a, **kw: pytest.fail("tick joué avant refus"))
    _verifier_refus_depart(tmp_path, arguments, message, capsys)
    print(f"cas={cas}, refus_observés=1, ticks_joués=0, résumés_écrits=0")


def test_depart_contre_epreuve_acceptation_trop_large(tmp_path, capsys, monkeypatch):
    _, inconnu = _terres_depart()
    arguments = ["--depart", str(inconnu)]
    with monkeypatch.context() as sonde:
        sonde.setattr("sim.intentions.deposer_intention", lambda *a, **kw: None)
        with pytest.raises(AssertionError):
            _verifier_refus_depart(tmp_path / "altere", arguments, "seigneurie inconnue", capsys)
    _verifier_refus_depart(tmp_path / "valide", arguments, "seigneurie inconnue", capsys)
    print("contre_épreuves_rouges=1, refus_observés=1")


def test_carte_de_1400_depart_lectures_et_refus(tmp_path, monkeypatch, capsys):
    bar, _ = _terres_depart()
    for nom, arguments, choix, lecture in (
        ("avec", ["--depart", str(bar)], bar, "densite"),
        ("sans", [], None, "densite"),
        ("faim", ["--lecture", "faim"], None, "faim"),
    ):
        code, sortie = _jouer(tmp_path / nom, *arguments, "--sans-chronique")
        assert code == 0
        assert (sortie / "carte.png").is_file()
        compte = json.loads((sortie / "resume.json").read_text())["carte"]
        assert compte["lecture"] == lecture
        assert compte["terre_choisie"] == choix
        if choix is not None:
            with pytest.raises(AssertionError):
                assert compte["terre_choisie"] is None
    from vues.relief.carte1400 import Carte1400Erreur

    def refuser(*args, **kwargs):
        raise Carte1400Erreur("photographie sonde incomplète")

    monkeypatch.setattr("vues.relief.carte1400.carte_de_1400", refuser)
    code, sortie = _jouer(tmp_path / "refus", "--sans-chronique")
    assert code == 2
    assert "carte : photographie sonde incomplète" in capsys.readouterr().err
    assert not (sortie / "resume.json").exists()
    print("cartes_vérifiées=3, refus=1, contre_épreuves_rouges=1")


def test_forge_ia_boucle(tmp_path, monkeypatch):
    import random
    from forge.__main__ import _simuler
    from sim import ia, engine, snapshot_export as photo
    from sim.world import World
    jouer, tick, exporter = ia.jouer_ia, engine.tick, photo.export_snapshot
    evenements, sorties = [], []
    def jouer_sonde(w, r, maisons=None):
        evenements.append(('ia', w, r)); jouer(w, r, maisons)
    def tick_sonde(w, rng, *a):
        if evenements and w is evenements[0][1]: evenements.append(('tick', w, evenements[0][2]))
        return tick(w, rng, *a)
    def export_sonde(w, *a, **kw):
        sorties.append(w.to_dict()); return exporter(w, *a, **kw)
    monkeypatch.setattr(ia, 'jouer_ia', jouer_sonde)
    monkeypatch.setattr(engine, 'tick', tick_sonde)
    monkeypatch.setattr(photo, 'export_snapshot', export_sonde)
    _simuler(31, 0, tmp_path / 'ia.json', ia=True)
    def ordre(e):
        assert [x[0] for x in e] == ['ia', 'tick'] * 31
        assert all(x[1] is e[0][1] and x[2] is e[0][2] for x in e)
    ordre(evenements)
    with pytest.raises(AssertionError): ordre(evenements[::-1])
    from sim.jauges import avant_le_tick
    temoin, releve, rng = World.charger(0), [], random.Random(0)
    # Le témoin est la boucle du jeu : le mois des jauges, l'IA, puis le tick (sim/jauges.py, avant_le_tick).
    for _ in range(31): avant_le_tick(temoin); jouer(temoin, releve); tick(temoin, rng)
    assert releve and evenements[0][2] == releve and sorties[-1] == temoin.to_dict() and temoin.jauges
    monkeypatch.setattr(ia, 'jouer_ia', lambda *a: None)
    _simuler(31, 0, tmp_path / 'muet.json', ia=True)
    with pytest.raises(AssertionError): assert sorties[-1] == temoin.to_dict()
    monkeypatch.setattr(ia, 'jouer_ia', lambda *a: pytest.fail('IA avant le premier tick'))
    _simuler(0, 0, tmp_path / 'zero.json', ia=True)


def test_forge_ia_sorties(tmp_path, capsys, monkeypatch):
    import copy
    from sim.ia import maisons_actives_30j
    blocs, octets = [], []
    for n, ticks in enumerate((31, 31, 0)):
        code, sortie = _jouer(tmp_path / str(n), '--ticks', str(ticks), '--ia', '--sans-chronique')
        assert code == 0 and all((sortie / f).stat().st_size > 0 for f in ('monde.json', 'formes.json', 'resume.json', 'carte.png', 'tableau.svg'))
        photo = json.loads((sortie / 'monde.json').read_bytes())
        resume = json.loads((sortie / 'resume.json').read_bytes())
        affiche = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        bloc = photo['ia']; blocs.append(bloc); octets.append((sortie / 'monde.json').read_bytes())
        assert bloc == resume['simulation']['ia'] == affiche['simulation']['ia']
        gestes = [g for m in bloc['maisons'] for g in m['gestes']]
        assert bloc['maisons'] and bloc['maisons_actives_30j'] == maisons_actives_30j(ticks, gestes)
        if ticks:
            def activite(r): assert r and maisons_actives_30j(ticks, r) > 0
            activite(gestes)
            with pytest.raises(AssertionError): activite([])
            for champ in ('gestes', 'population'):
                faux = copy.deepcopy(bloc)
                maison = next(m for m in faux['maisons'] if m['gestes'])
                if champ == 'gestes': maison[champ].pop()
                else: maison[champ] += 1
                with pytest.raises(AssertionError): assert faux == resume['simulation']['ia']
        else: assert not gestes and bloc['maisons_actives_30j'] == -1
    assert octets[0] == octets[1] and blocs[0] == blocs[1]
    monkeypatch.setattr('forge.__main__._planche', lambda *a: {'code': 0})
    assert _jouer(tmp_path / 'planche', '--ticks', '0', '--ia')[0] == 0
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])['planche']['ia'] is False


@pytest.mark.parametrize('ticks,empreinte', [(0, '383debd038d289ebad6d7d83c2826be4dfdbbbdcee9f78bd14be4933c9bb33eb'), (30, 'b1486b210ad18b2af9ed3d6d14fb34ebcb97825d7d442a5a8ffcf10eca6abe9a')])
def test_forge_ia_sans(tmp_path, monkeypatch, ticks, empreinte):
    monkeypatch.setattr("sim.constants.PART_COUTUMIERE", 0)
    # Les empreintes historiques de la photographie, couche après couche : le
    # monde amorcé comme avant la soudure (sim/tests/amorcage_d_avant.py).
    # Les frontières de 1400 changent chaque couche, et rien d'autre : la puissance et la maison
    # des cellules que la table décide, le maître des lieux (cellules partagées, capitales neuves),
    # les noms qui suivent le pays, et la place des lieux dont le bourg passe au siège d'une capitale
    # neuve. Population et flux sont inchangés. Les frontières de l'Empire, du Nord et de l'Est changent les
    # mêmes couches et elles seules : au 30e jour, la puissance de 131 cellules, la maison de 129, les noms de
    # 122, le maître de 915 lieux, le nom de 1 222 et le point de 190 (bourgs au siège d'une capitale neuve).
    # Celles des Balkans, de l'Orient et du Maghreb changent encore les mêmes couches et elles seules, sans le
    # point d'aucun lieu : au 30e jour (comme au jour 0), la puissance de 80 cellules, la maison de 71, les noms
    # de 49, le maître de 100 lieux et le nom de 187.
    # Le nom de chaque terre d'après sa vraie ville de 1400 ne change que les noms (celui des lieux et le bloc
    # `noms`) : sans eux, la photographie est celle d'avant, au jour 0 comme au 30e jour.
    from sim.tests.amorcage_d_avant import amorcer_comme_avant_la_soudure
    amorcer_comme_avant_la_soudure(monkeypatch)
    import hashlib
    from forge.__main__ import _simuler
    from sim.snapshot_export import serialize_snapshot
    monkeypatch.setattr('sim.ia.jouer_ia', lambda *a: pytest.fail('IA sans option'))
    ancienne = {0: '631b9a44b2383644d8e54a38d64d552dbc16f9ced57279e00fecbdf9a0dd9b89', 30: '90be61b50acb283b63f0546232a80d71fa778a67ca9ece4b5f957a710426926f'}[ticks]
    if ticks == 30:
        # Toutes les empreintes se prennent sur le même témoin.
        with monkeypatch.context() as ctx:
            ctx.setattr('sim.foyers.facteur_bras', lambda *a: 1.0)
            chemin, mesures = _simuler(ticks, 0, tmp_path / 'sans.json')
    else:
        chemin, mesures = _simuler(ticks, 0, tmp_path / 'sans.json')
    assert 'ia' not in mesures and 'ia' not in json.loads(chemin.read_bytes())
    # Chaque lieu porte son point ; sans lui, c'est exactement la photographie d'avant.
    assert hashlib.sha256(chemin.read_bytes()).hexdigest() == {0: 'da8f76cb781c804aa100ef46d7f436a2b6fd7f75346e885c77b2fc48cab42b56', 30: 'dbfc48021b3b5ce39e8a66685e42f7fa68b222cfb7bb4fd5a346def43c5ff39e'}[ticks]
    photo_noms = json.loads(chemin.read_bytes())
    faux_flux = json.loads(chemin.read_bytes()); faux_flux['cells'][0]['lieux'][0]['flux_30j']['preleve_kg'] += 1
    with pytest.raises(AssertionError): assert hashlib.sha256(serialize_snapshot(faux_flux)).hexdigest() == hashlib.sha256(chemin.read_bytes()).hexdigest()
    for cellule in photo_noms['cells']:
        for lieu in cellule['lieux']: lieu.pop('nom'); lieu.pop('flux_30j')
    assert hashlib.sha256(serialize_snapshot(photo_noms)).hexdigest() == {0: '65def16797e1799025d49b17af443e03a8ad84abcba9019fc13be09aee28fa0d', 30: 'c87b26a603e06e1b04ffa110480feaee85aa922ad3068732118e6988a8db66b2'}[ticks]
    points = [lieu.pop('point') for c in photo_noms['cells'] for lieu in c['lieux']]
    assert points and all(set(p) == {'x_m', 'y_m', 'latitude', 'longitude'} for p in points)
    assert hashlib.sha256(serialize_snapshot(photo_noms)).hexdigest() == {0: 'c5e0cf3ac4ec041417bb7b38c4197bb1ec160ac8d5a36819d08a3729238ee9c5', 30: '34e64ec213094f5e68a77d3a32910ce466f5f7d94823feaa5efb1d50abe0ef4f'}[ticks]
    assert all(c.pop('noms') for c in photo_noms['cells']); assert hashlib.sha256(serialize_snapshot(photo_noms)).hexdigest() == empreinte
    faux = dict(photo_noms, ia=[])
    with pytest.raises(AssertionError): assert hashlib.sha256(serialize_snapshot(faux)).hexdigest() == empreinte
    import copy
    from sim.world import World
    photo = photo_noms; prive = copy.deepcopy(photo)
    assert prive['cells'] and all(c['lieux'] for c in prive['cells'])
    for cellule in prive['cells']:
        for lieu in cellule['lieux']: assert lieu.pop('maitre') is not None
    assert hashlib.sha256(serialize_snapshot(prive)).hexdigest() == ancienne
    for champ in ('ia', 'population'):
        faux = copy.deepcopy(prive)
        if champ == 'ia': faux['ia'] = []
        else: faux['cells'][0]['lieux'][0]['population'] += 1
        with pytest.raises(AssertionError): assert hashlib.sha256(serialize_snapshot(faux)).hexdigest() == ancienne
    autre = next(m.id for m in World.charger(0).maisons if m.id != photo['cells'][0]['lieux'][0]['maitre'])
    photo['cells'][0]['lieux'][0]['maitre'] = autre
    with pytest.raises(AssertionError): assert hashlib.sha256(serialize_snapshot(photo)).hexdigest() == empreinte
    if ticks == 30:
        normal, _ = _simuler(ticks, 0, tmp_path / 'normal.json')
        def controler(octets):
            assert hashlib.sha256(octets).hexdigest() == '56ad347a039b3bc7ad66a14a48b1dfb26264befe4a3765ed252f9eea76b2413b'
        controler(normal.read_bytes())
        with pytest.raises(AssertionError):
            controler(normal.read_bytes() + b' ')


@pytest.mark.parametrize('cas', ['inconnu', 'double', 'sans_tick', 'donnee', 'position', 'intention', 'export', 'export_io'])
def test_forge_ia_refus(tmp_path, capsys, monkeypatch, cas):
    from sim.intentions import IntentionRefusee
    from sim.snapshot_export import SnapshotExportError
    from sim.aggregation import PositionCelluleInconnue
    bar, inconnu = _terres_depart()
    arguments = {'inconnu': ['--depart', str(inconnu)], 'double': ['--depart', str(bar), '--depart', str(bar)], 'sans_tick': ['--depart', str(bar), '--ticks', '0']}
    if cas in arguments:
        monkeypatch.setattr('sim.ia.jouer_ia', lambda *a: pytest.fail('IA avant validation'))
        message = {'inconnu': 'seigneurie inconnue', 'double': 'départ déjà choisi', 'sans_tick': "l'intention s'applique au tick suivant"}[cas]
    else:
        message = 'maison sonde : bourg absent'
        def refuser(*a, **kw): raise {'donnee': ValueError, 'position': PositionCelluleInconnue, 'intention': IntentionRefusee, 'export': SnapshotExportError, 'export_io': OSError}[cas](message)
        monkeypatch.setattr('sim.snapshot_export.export_snapshot' if cas in ('export', 'export_io') else 'sim.ia.jouer_ia', refuser)
    _verifier_refus_depart(tmp_path, [*arguments.get(cas, []), '--ia'], message, capsys)
    if cas in ('inconnu', 'donnee'):
        monkeypatch.setattr('sim.ia.jouer_ia', lambda *a: None)
        if cas == 'inconnu': monkeypatch.setattr('sim.intentions.deposer_intention', lambda *a: None)
        with pytest.raises(AssertionError):
            _verifier_refus_depart(tmp_path / 'ignore', [*arguments.get(cas, []), '--ia'], message, capsys)

@pytest.mark.parametrize('depart', [False, True])
def test_encart_assemblage(tmp_path, depart):
    import numpy as np
    from PIL import Image
    from vues.relief.carte1400 import carte_de_1400, COULEUR_CHOIX
    from vues.relief.encart import dessiner_encart
    largeur = 900 if depart else 64
    bar, _ = _terres_depart(); code, sortie = _jouer(tmp_path, *(['--depart',str(bar)] if depart else []), '--sans-chronique', '--largeur', str(largeur))
    assert code == 0; d = json.loads((sortie/'monde.json').read_text()); r = json.loads((sortie/'resume.json').read_text())
    formes = json.loads((sortie/'formes.json').read_text(encoding='utf-8'))
    haut, c = carte_de_1400(d, lecture='densite', largeur=largeur, formes=formes); bas, e = dessiner_encart(d, largeur=largeur, formes=formes); image = np.array(Image.open(sortie/'carte.png'))
    if depart: assert np.any(np.all(haut[..., :3] == COULEUR_CHOIX[:3],axis=2))
    def controle(i, resume):
        assert np.array_equal(i, np.concatenate((haut,bas))) and resume['carte'] == c and resume['encart'] == e
        assert np.array_equal(np.all(i[..., :3] == COULEUR_CHOIX[:3],axis=2), np.pad(np.all(haut[..., :3] == COULEUR_CHOIX[:3],axis=2), ((0,len(bas)),(0,0))))
    controle(image,r)
    for faux in (haut, np.roll(image,1,axis=0), image.copy()):
        if faux.shape == image.shape and np.array_equal(faux,image): faux[0,0] = 0
        with pytest.raises(AssertionError): controle(faux,r)
    r['encart']['fleches_dessinees'] += 1
    with pytest.raises(AssertionError): controle(image,r)

def test_encart_refus(tmp_path, monkeypatch):
    from vues.relief.encart import EncartErreur
    def refuser(*a, **kw): raise EncartErreur('sonde de rendu')
    monkeypatch.setattr('vues.relief.encart.dessiner_encart', refuser)
    code, sortie = _jouer(tmp_path, '--sans-chronique'); assert code == 2 and not (sortie/'resume.json').exists()
