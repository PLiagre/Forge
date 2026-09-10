"""Le tableau de pilotage : où en est le travail, et d'où on le débloque.

Une seule page, et une seule question à laquelle elle répond : *qu'est-ce
qui attend, et depuis quand ?* Le reste — l'avancement, l'histoire, le
registre — vient après, parce que ce qui va bien n'appelle personne.

Elle ne calcule aucun état et ne juge aucune proposition. Les états
viennent du registre, la cause qui retient une proposition vient de
`integration.examiner` — la même fonction que celle qui fusionne, mot
pour mot, jamais une paraphrase. Une page qui recalculerait pour son
affichage finirait par montrer autre chose que ce que la machine fait, et
c'est le mode de défaillance n°4 du dépôt.

Et elle ne fait rien. Elle est publiée sur GitHub Pages : statique, sans
jeton, sans appel réseau, sans une ligne de JavaScript. Ce qui s'actionne
depuis elle est un **lien** vers la page GitHub du geste, et un travail
qui le fait côté serveur (`outils/actions.py`). Un jeton publié est un
jeton perdu, et un dépôt public n'a pas de dos.

Ce module rend du texte. Il ne lit ni GitHub, ni le disque : il reçoit
des données déjà lues et déjà décidées. C'est cette coupure qui permet
d'éprouver la page hors ligne — et un contrôle qu'on ne peut pas jouer
hors ligne est un contrôle qu'on ne joue pas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import escape

from . import actions as actions_module
from . import attention, histoire, palier, sante as sante_module
from .mesure import INCONNU, NON_CALCULE, Lecture, Mesure, depuis, duree, instant

# Ce qu'une couche est, pour l'œil. Les noms vivent dans VISION.md ; ils
# sont repris ici parce qu'une page qui dirait « couche 4 » sans dire
# « armées » demanderait au lecteur d'aller chercher ailleurs. Si les deux
# divergent un jour, VISION.md a raison.
NOMS = {
    "1": "Monde vivant",
    "2": "Villes",
    "3": "États",
    "4": "Armées",
    "5": "Batailles tactiques",
}

# L'état d'une fiche, et le ton qui le porte. Un ton, pas une couleur :
# la couleur vit dans la feuille de style, où le thème sombre peut la
# reprendre. Une couleur écrite dans le corps de la page ne se rethème
# pas, et une page illisible la nuit est une page qu'on n'ouvre pas.
TONS = {
    "livre": "ok",
    "archive": "neutre",
    "pret": "froid",
    "a-briefer": "attente",
    "idee": "neutre",
    "abandonne": "du",
}

TONS_ACTION = {"fusionner": "ok", "rebaser": "attente"}

VIDE = "—"

# La feuille de style. Toutes les couleurs sont nommées dans `:root` ;
# le bloc sombre ne fait que les redéfinir. Une couleur qui n'existerait
# que dans le bloc sombre serait absente en thème clair — et personne ne
# regarde une page dans les deux thèmes avant de la publier.
STYLE = """
:root {
  color-scheme: light dark;
  --fond:#fbfaf8; --encre:#1b1a17; --gris:#6b6862; --trait:#e2ded6; --carte:#fff;
  --ok:#2f7d32; --attente:#a8620a; --du:#8a2b2b; --froid:#1d63b8; --neutre:#7a7a7a;
  --appel:#fdf1ef; --appel-trait:#e8c4bd; --barre:#2f7d32; --grille:#e2ded6;
}
@media (prefers-color-scheme:dark) { :root {
  --fond:#161513; --encre:#eceae6; --gris:#9b968d; --trait:#2c2a26; --carte:#1e1d1a;
  --ok:#7ec98a; --attente:#e0a35c; --du:#e78b84; --froid:#7fb4f0; --neutre:#9b968d;
  --appel:#2a1f1d; --appel-trait:#5b3a34; --barre:#7ec98a; --grille:#2c2a26;
} }
* { box-sizing:border-box }
body { margin:0; background:var(--fond); color:var(--encre);
  font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:60rem; margin:0 auto; padding:2.5rem 1.25rem 4rem }
h1 { font-size:1.55rem; margin:0 0 .2rem; letter-spacing:-.01em }
h2 { font-size:1.2rem; margin:2.2rem 0 .9rem; letter-spacing:-.01em }
h3 { font-size:1.02rem; margin:0 0 .6rem; display:flex; align-items:center;
  flex-wrap:wrap; gap:.6rem }
a { color:var(--froid) }
.chapeau { color:var(--gris); margin:0 0 1.4rem }
.carte { background:var(--carte); border:1px solid var(--trait);
  border-radius:10px; padding:1.1rem 1.2rem; margin-bottom:1rem }
.carte.appel { background:var(--appel); border-color:var(--appel-trait) }
.sous { color:var(--gris); font-size:.87rem; margin:.5rem 0 .8rem }
.jauge { height:5px; background:var(--trait); border-radius:3px; overflow:hidden }
.jauge i { display:block; height:100%; background:var(--ok) }
.defile { overflow-x:auto }
table { width:100%; border-collapse:collapse; font-size:.9rem }
td, th { padding:.34rem .5rem; border-top:1px solid var(--trait);
  vertical-align:top; text-align:left }
th { color:var(--gris); font-weight:600; font-size:.8rem; border-top:0 }
tr:first-child td { border-top:0 }
.num { font-variant-numeric:tabular-nums; color:var(--gris);
  white-space:nowrap; width:3.4rem }
.fin { color:var(--gris); white-space:nowrap; text-align:right }
.duree { font-variant-numeric:tabular-nums; white-space:nowrap; color:var(--gris) }
code { font-size:.85em }
.etat { font-weight:600; white-space:nowrap }
.badge { font-size:.74rem; font-weight:600; padding:.1rem .5rem; border-radius:99px;
  border:1px solid currentColor; white-space:nowrap }
.t-ok { color:var(--ok) } .t-attente { color:var(--attente) }
.t-du { color:var(--du) } .t-froid { color:var(--froid) }
.t-neutre { color:var(--neutre) } .t-inconnu { color:var(--gris) }
.compteur { font-size:3.2rem; line-height:1; font-weight:700;
  font-variant-numeric:tabular-nums }
.compteur.t-du { color:var(--du) }
.paire { display:flex; flex-wrap:wrap; gap:1.6rem; align-items:baseline }
.courbe { width:100%; height:auto; max-width:44rem; display:block }
.courbe .barre { fill:var(--barre) }
.courbe .socle { stroke:var(--grille); stroke-width:1 }
.courbe text { fill:var(--gris); font-size:9px }
ul.liste { margin:.2rem 0 0; padding-left:1.1rem }
ul.liste li { margin:.25rem 0 }
footer { color:var(--gris); font-size:.82rem; margin-top:2rem }
"""


# ---------------------------------------------------------- les données


@dataclass(frozen=True)
class LignePR:
    """Une proposition ouverte, et ce que l'intégration en dit."""

    numero: int
    branche: str
    action: str
    raison: str
    titre: str = ""
    ouverte: str = ""
    brouillon: bool = False


@dataclass(frozen=True)
class Etat:
    """Tout ce que la page montre en plus du registre.

    Chaque champ peut manquer, et son absence s'affiche : une page qui
    ferait disparaître un bloc qu'elle n'a pas pu lire laisserait croire
    que sa vue est complète (règle 10).
    """

    maintenant: datetime | None = None
    sante: sante_module.Sante | None = None
    alertes: tuple[attention.Alerte, ...] = ()
    journal: tuple[histoire.Proposition, ...] = ()
    velocite: tuple[histoire.Semaine, ...] = ()
    traversee: histoire.Traversee | None = None
    ages: dict = field(default_factory=dict)
    deductions: tuple[histoire.Deduction, ...] = ()
    actions: tuple[actions_module.Action, ...] = ()
    # Ce qui n'a pas pu être mesuré, et pourquoi. Une ligne par renoncement.
    refus: tuple[str, ...] = ()


# ------------------------------------------------------------- l'écriture


def _e(texte) -> str:
    """Tout ce qui vient de GitHub passe par ici. Titres, branches, noms."""
    return escape(str(texte), quote=True)


def _lien(url: str, texte: str) -> str:
    return f'<a href="{_e(url)}">{_e(texte)}</a>' if url else _e(texte)


def _badge(mot: str, ton: str) -> str:
    return f'<span class="badge t-{_e(ton)}">{_e(mot)}</span>'


def _puce(etat: str) -> str:
    return f'<span class="etat t-{_e(TONS.get(etat, "neutre"))}">{_e(etat)}</span>'


def _table(entetes, lignes: str, vide: str) -> str:
    """Un tableau, ou la phrase qui dit pourquoi il n'y en a pas.

    `vide` est de la prose de ce module, pas du texte de GitHub : elle ne
    passe donc pas par l'échappement. Seul ce qui vient d'un tiers y
    passe — échapper le reste remplirait le source d'entités sans rien
    protéger, et brouillerait la seule distinction qui compte ici.
    """
    if not lignes:
        return f'<p class="sous">{vide}</p>'
    tete = "".join(f"<th>{_e(t)}</th>" for t in entetes)
    return f'<div class="defile"><table><tr>{tete}</tr>{lignes}</table></div>'


def _mesure(valeur: Mesure) -> str:
    """Une médiane et son échantillon, ou l'aveu qu'il n'y en a pas.

    Jamais un zéro tout seul : « 0 » et « rien n'a encore été mesuré » se
    ressemblent à l'écran et ne veulent pas dire la même chose.
    """
    if not valeur.connue:
        return '<span class="t-inconnu">pas encore mesurable</span>'
    return f'{_e(duree(valeur.valeur))} <span class="fin">({valeur.echantillon} lot(s))</span>'


def _lecture(valeur: Lecture, oui: str, non: str) -> str:
    if not valeur.connue:
        raison = f" — {valeur.raison}" if valeur.raison else ""
        return f'<span class="t-inconnu">{_e(INCONNU)}{_e(raison)}</span>'
    ton, mot = ("ok", oui) if valeur.valeur else ("du", non)
    return f'<span class="t-{ton}">{mot}</span>'


# --------------------------------- 1. ce qui demande une décision maintenant


def _decisions(etat: Etat) -> str:
    if etat.maintenant is None:
        return (
            '<section class="carte"><h2>Ce qui demande une décision maintenant</h2>'
            '<p class="sous">Non lu : cette page a été écrite sans lire GitHub.</p></section>'
        )
    if not etat.alertes:
        return (
            '<section class="carte"><h2>Ce qui demande une décision maintenant</h2>'
            '<p class="sous">Rien. Aucune proposition retenue, aucun palier dû, '
            "aucun contrôle rouge sur la base.</p></section>"
        )
    lignes = "".join(
        f"<tr><td>{_badge(a.quoi, 'du')}</td>"
        f"<td>{_lien(a.lien, a.texte) if a.lien else _e(a.texte)}</td>"
        f'<td class="duree">{_e(depuis(a.depuis, etat.maintenant))}</td></tr>'
        for a in etat.alertes
    )
    return f"""<section class="carte appel">
<h2>Ce qui demande une décision maintenant</h2>
<p class="sous">{len(etat.alertes)} chose(s) attendent quelqu'un. La cause est celle que
l'intégration rend, mot pour mot.</p>
{_table(("quoi", "quoi exactement", "depuis"), lignes, "")}
</section>"""


# ----------------------------------------------- 2. la santé de la chaîne


def _sante(etat: Etat) -> str:
    if etat.sante is None:
        return (
            '<section class="carte"><h2>La santé de la chaîne</h2>'
            '<p class="sous">Non lue : cette page a été écrite sans lire '
            "l'historique des exécutions.</p></section>"
        )
    s = etat.sante
    ton = "du" if s.alerte else "ok"
    if s.alerte:
        phrase = (
            f"Au-delà de {s.seuil}, la chaîne tourne à vide : c'est ce qui est arrivé "
            "entre le 5 et le 7 septembre 2026, quarante tours et quarante « RIEN »."
        )
    else:
        phrase = f"Le seuil d'alerte est {s.seuil} tours ; il est déclaré dans atelier.toml."
    fusion = (
        "aucune fusion dans l'historique lu"
        if s.jamais_fusionne
        else f"dernière fusion il y a {depuis(s.derniere_fusion, etat.maintenant)}"
        if etat.maintenant
        else "dernière fusion connue"
    )
    reveil = (
        f'{_lien(s.dernier_reveil.lien, s.dernier_reveil.conclusion or INCONNU)} — '
        f"il y a {_e(depuis(s.dernier_reveil.moment, etat.maintenant))}"
        if s.dernier_reveil is not None and etat.maintenant is not None
        else f'<span class="t-inconnu">{_e(INCONNU)}</span>'
    )
    obligatoires = s.obligatoires
    if not obligatoires.connue:
        dit = (
            f'<span class="t-inconnu">{_e(INCONNU)}</span> — la lecture de la protection '
            f"a été refusée ({_e(obligatoires.raison)}). Une protection illisible n'est "
            "pas une protection absente."
        )
    else:
        poses = obligatoires.valeur or ()
        absents = [nom for nom in s.requis if nom not in set(poses)]
        dit = (
            f'<span class="t-ok">les {len(s.requis)} contrôles déclarés sont exigés par '
            "GitHub</span>"
            if not absents
            else f'<span class="t-du">GitHub n\'exige pas : {_e(", ".join(absents))}</span>'
        )
    rouges = "".join(
        f"<tr><td>{_e(r.travail)}</td>"
        f"<td>{_lien(r.lien, 'voir le journal')}</td>"
        f'<td class="duree">il y a {_e(depuis(r.moment, etat.maintenant))}</td></tr>'
        for r in s.rouges
    ) if etat.maintenant else ""
    return f"""<section class="carte">
<h2>La santé de la chaîne</h2>
<div class="paire">
  <div><div class="compteur t-{ton}">{s.tours_sans_fusion}</div>
  <p class="sous">tours d'intégration depuis la dernière fusion<br>{fusion}</p></div>
  <div><p class="sous">{phrase}</p></div>
</div>
<table>
<tr><td>Dernier réveil de l'intégration</td><td>{reveil}</td></tr>
<tr><td>Contrôles requis (atelier.toml)</td><td><code>{_e(", ".join(s.requis))}</code></td></tr>
<tr><td>Ce que GitHub exige vraiment</td><td>{dit}</td></tr>
<tr><td>La protection s'applique aux administrateurs</td>
    <td>{_lecture(s.admins_soumis, "oui", "non")}</td></tr>
<tr><td>La page est publiée par Actions</td>
    <td>{_lecture(s.pages, "oui", "non — elle est écrite, pas publiée")}</td></tr>
</table>
<h3>La dernière exécution rouge de chaque travail</h3>
{_table(("travail", "où", "quand"), rouges, "Aucun travail n'a d'exécution rouge dans l'historique lu.")}
</section>"""


# --------------------------------------------------------- 3. l'avancement


def _fiche(fiche, etat: Etat) -> str:
    deps = ", ".join(fiche.depend_de) or VIDE
    prs = ", ".join(str(p) for p in fiche.prs) or VIDE
    age = etat.ages.get(fiche.numero, NON_CALCULE)
    return (
        f'<tr><td class="num">{_e(fiche.numero)}</td>'
        f"<td>{_e(fiche.titre)}</td>"
        f"<td>{_puce(fiche.etat)}</td>"
        f'<td class="duree">{_e(duree(age))}</td>'
        f'<td class="fin">{_e(deps)}</td>'
        f'<td class="fin">{_e(prs)}</td></tr>'
    )


def _couche(etape, fiches, etat: Etat, depot: str) -> str:
    nom = NOMS.get(etape.couche, "")
    de_la_couche = [f for f in fiches if f.couche == etape.couche]
    finis = [f for f in de_la_couche if f.etat in palier.FINIS]
    part = round(100 * len(finis) / len(de_la_couche)) if de_la_couche else 0
    if etape.due:
        mot, ton = "palier dû", "du"
    elif etape.finie:
        mot, ton = "finie", "ok"
    else:
        mot, ton = f"{len(etape.en_cours)} lot(s) en cours", "attente"
    demande = (
        _lien(actions_module.lien_demande(depot, f"{etape.couche} — {nom}"),
              "demander un lot ici")
        if depot else ""
    )
    lignes = "".join(_fiche(f, etat) for f in de_la_couche)
    return f"""<section class="carte">
  <h3>Couche {_e(etape.couche)} — {_e(nom)} {_badge(mot, ton)} {demande}</h3>
  <div class="jauge"><i style="width:{part}%"></i></div>
  <p class="sous">{len(finis)} lot(s) sur {len(de_la_couche)} ne demandent plus rien.</p>
  {_table(("lot", "titre", "état", "dans cet état", "dépend de", "PR"), lignes, "Aucune fiche.")}
</section>"""


def _svg_velocite(semaines) -> str:
    """Un histogramme, écrit à la main. Aucune bibliothèque : c'est du SVG.

    Les couleurs viennent des variables de la feuille de style, donc le
    thème sombre les reprend. Une barre peinte en dur serait invisible
    la nuit.
    """
    if not semaines:
        return '<p class="sous">Pas encore mesurable : aucun lot livré dans l\'échantillon.</p>'
    largeur, hauteur, marge = 320.0, 78.0, 14.0
    pas = largeur / len(semaines)
    haut = max(s.compte for s in semaines)
    barres = []
    for rang, semaine in enumerate(semaines):
        # Un maximum nul donnerait une division par zéro ; une semaine
        # sans livraison est une barre de hauteur nulle, pas une erreur.
        h = (semaine.compte / haut) * (hauteur - marge) if haut else 0.0
        x = rang * pas + pas * 0.18
        w = pas * 0.64
        y = hauteur - h
        barres.append(f'<rect class="barre" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/>')
        barres.append(
            f'<text x="{x + w / 2:.1f}" y="{y - 2:.1f}" text-anchor="middle">{semaine.compte}</text>'
        )
        barres.append(
            f'<text x="{x + w / 2:.1f}" y="{hauteur + 9:.1f}" text-anchor="middle">'
            f"{_e(semaine.debut.strftime('%d/%m'))}</text>"
        )
    total = sum(s.compte for s in semaines)
    return (
        # La boîte laisse la place au chiffre au-dessus de la barre (12 px)
        # et à la date en dessous (14 px) : une boîte trop juste les coupe
        # sans rien signaler, et la première version les avait perdues.
        f'<svg class="courbe" viewBox="0 -12 {largeur:.0f} {hauteur + 26:.0f}" '
        f'role="img" aria-label="{total} lot(s) livrés sur {len(semaines)} semaines">'
        + "".join(barres)
        + f'<line class="socle" x1="0" y1="{hauteur:.1f}" x2="{largeur:.0f}" y2="{hauteur:.1f}"/>'
        + "</svg>"
    )


def _traversee(traversee) -> str:
    if traversee is None or not traversee.mesurable:
        return '<p class="sous">Pas encore mesurable : aucun lot livré n\'a ses dates.</p>'
    lignes = "".join(
        f"<tr><td>{_e(libelle)}</td><td>{_mesure(getattr(traversee, nom))}</td></tr>"
        for nom, libelle in histoire.ETAPES
    )
    lente = traversee.plus_lente
    ou = (
        f'<p class="sous">La chaîne est la plus lente sur : {_e(lente[0])} '
        f"({_e(duree(lente[1].valeur))}).</p>"
        if lente is not None else ""
    )
    return f"""<table>
<tr><td><strong>de la demande à la fusion</strong></td><td>{_mesure(traversee.total)}</td></tr>
{lignes}
</table>{ou}"""


def _avancement(fiches, etat: Etat, depot: str) -> str:
    etapes = palier.etapes(fiches)
    corps = "".join(_couche(e, fiches, etat, depot) for e in etapes)
    hors_couche = [f for f in fiches if f.couche is None]
    if hors_couche:
        corps += (
            '<section class="carte"><h3>Hors couche</h3>'
            + _table(("lot", "titre", "état", "dans cet état", "dépend de", "PR"),
                     "".join(_fiche(f, etat) for f in hors_couche), "Aucune fiche.")
            + "</section>"
        )
    return f"""<h2>L'avancement</h2>
{corps}
<section class="carte">
  <h3>La vélocité — lots livrés par semaine</h3>
  {_svg_velocite(etat.velocite)}
  <p class="sous">Dérivée des dates de fusion des propositions <code>agent/</code>,
  pas d'un compteur tenu à la main.</p>
</section>
<section class="carte">
  <h3>Le temps de traversée — médianes</h3>
  {_traversee(etat.traversee)}
</section>"""


# --------------------------------------------------- 4. le journal des fusions


def _entree_journal(p: histoire.Proposition, maintenant) -> str:
    """Une ligne du journal. Six colonnes, pas huit : au-delà, la
    dernière sort de l'écran et personne ne la lit."""
    if p.fusionnee is not None:
        sortie = _badge("fusionnée", "ok") + '<br><span class="duree">' \
            + _e(p.fusionnee.strftime("%d/%m %Hh%M")) + "</span>"
        mise = duree(p.duree) if p.duree != NON_CALCULE else INCONNU
    else:
        quand = p.fermee.strftime("%d/%m %Hh%M") if p.fermee else INCONNU
        pourquoi = p.mot_de_la_fin or "aucun commentaire ne dit pourquoi"
        sortie = (
            _badge("fermée sans fusion", "du")
            + '<br><span class="duree">' + _e(quand) + "</span>"
            + '<br><span class="sous">' + _e(pourquoi) + "</span>"
        )
        mise = VIDE
    auteurs = ", ".join(p.auteurs) or INCONNU
    relecteurs = ", ".join(p.relecteurs) or "personne"
    if p.relue_par_un_tiers:
        mains = f'{_e(auteurs)} → <span class="t-ok">{_e(relecteurs)}</span>'
    else:
        # Court, parce que la colonne est étroite ; la phrase entière est
        # dans le chapeau du bloc, une fois, où elle se lit.
        mains = f'{_e(auteurs)} → <span class="t-du">{_e(relecteurs)} (pas un tiers)</span>'
    # Le compte d'abord, les exceptions ensuite : « 6/7 verts » se lit
    # d'un coup d'œil, la liste entière déborde de la colonne et ne se lit
    # donc jamais. Ce qui n'est pas vert est nommé avec le mot de GitHub,
    # parce que c'est ça qu'on cherche quand on ouvre le journal.
    if not p.controles:
        controles = VIDE
    else:
        controles = f"{len(p.verts)}/{len(p.controles)} verts"
        if p.non_verts:
            controles += " — " + ", ".join(f"{nom} : {mot}" for nom, mot in p.non_verts)
    lot = f'<span class="badge t-neutre">lot {_e(p.lot)}</span> ' if p.lot else ""
    return (
        f'<tr><td class="num">{_lien(p.lien, "#" + str(p.numero))}</td>'
        f"<td>{lot}{_e(p.titre)}<br><code>{_e(p.branche)}</code></td>"
        f"<td>{mains}</td>"
        f"<td>{sortie}</td>"
        f'<td class="duree">{_e(mise)}</td>'
        f'<td class="sous">{_e(controles)}</td></tr>'
    )


def _journal(etat: Etat) -> str:
    lignes = "".join(_entree_journal(p, etat.maintenant) for p in etat.journal)
    return f"""<h2>Le journal des fusions</h2>
<section class="carte">
<p class="sous">Les {len(etat.journal)} dernières propositions fermées, fusionnées ou non.
« Relu par » doit être une connexion différente de celles qui ont écrit les commits :
celui qui écrit le code ne dit pas s'il est recevable. Quand ce n'est pas le cas, la
ligne porte « pas un tiers ».</p>
{_table(("n°", "titre et branche", "écrit par → relu par", "sortie", "durée", "contrôles"),
        lignes, "Aucune proposition fermée n'a été lue.")}
</section>"""


# ------------------------------------------------------------- les actions


def _actions(etat: Etat) -> str:
    if not etat.actions:
        return ""
    lignes = "".join(
        f"<tr><td>{_lien(a.lien, a.titre) if a.lien else _e(a.titre)}</td>"
        f"<td>{_e(a.quoi)}</td>"
        f"<td><code>{_e(a.entree)}</code></td></tr>"
        if a.entree else
        f"<tr><td>{_lien(a.lien, a.titre) if a.lien else _e(a.titre)}</td>"
        f"<td>{_e(a.quoi)}</td><td>{VIDE}</td></tr>"
        for a in etat.actions
    )
    return f"""<h2>Ce qu'on peut déclencher d'ici</h2>
<section class="carte">
<p class="sous">Cette page ne fait rien : elle emmène. Chaque lien ouvre la page GitHub
du geste ; c'est un travail qui l'exécute, avec le jeton d'Actions. Un geste déclenché
deux fois ne se fait pas deux fois — le travail relit l'état et sort en disant
« déjà fait ».</p>
{_table(("action", "ce qu'elle fait", "ce qu'il faut taper"), lignes, "")}
</section>"""


# ------------------------------------------- ce que la page ne peut pas savoir


def _angle_mort(etat: Etat) -> str:
    deductions = "".join(
        "<li>" + _e(d.texte)
        + ' <span class="fin">déduction, sur : ' + _e(d.sur_quoi) + "</span></li>"
        for d in etat.deductions
    )
    aucune = "<li>Aucune branche de code sans proposition ouverte.</li>"
    refus = "".join(f"<li>{_e(r)}</li>" for r in etat.refus)
    non_lu = (
        '<p class="sous">Et ce qui n\'a pas pu être lu du tout :</p>'
        f'<ul class="liste">{refus}</ul>'
        if refus else ""
    )
    return f"""<h2>Ce que cette page ne sait pas</h2>
<section class="carte">
<p class="sous">Les cartes de l'atelier (<code>.atelier/</code>) vivent sur le serveur du
propriétaire et ne sont pas dans le dépôt. <strong>Cette page ne sait donc pas si un agent
travaille en ce moment, ni si une carte est tombée.</strong> Ce qui suit est déduit, pas
mesuré : une branche n'est pas un agent au travail, c'est une branche.</p>
<ul class="liste">{deductions or aucune}</ul>
{non_lu}
</section>"""


# ------------------------------------------------------------- 5. le registre


def _registre(fiches, lignes_pr, etat: Etat, depot: str) -> str:
    travaux = "".join(
        f'<tr><td class="num">'
        f'{_lien(actions_module.lien_proposition(depot, l.numero) if depot else "", "#" + str(l.numero))}'
        f"</td>"
        f"<td><code>{_e(l.branche)}</code></td>"
        f"<td>{_badge(l.action, TONS_ACTION.get(l.action, 'du'))}</td>"
        f"<td>{_e(l.raison)}</td>"
        f'<td class="duree">{_e(depuis(instant(l.ouverte), etat.maintenant) if etat.maintenant else INCONNU)}</td>'
        f"</tr>"
        for l in lignes_pr
    )
    fiches_html = "".join(_fiche(f, etat) for f in fiches)
    return f"""<h2>Le registre complet</h2>
<section class="carte">
  <h3>Ce qui attend d'entrer</h3>
  {_table(("n°", "branche", "décision", "pourquoi", "ouverte depuis"), travaux,
          "Aucune proposition ouverte.")}
</section>
<section class="carte">
  <h3>Chaque lot, son état, ses dépendances</h3>
  {_table(("lot", "titre", "état", "dans cet état", "dépend de", "PR"), fiches_html,
          "Aucune fiche.")}
</section>"""


# ------------------------------------------------------------------ la page


def rendre(fiches, lignes_pr, moment: str, depot: str = "", etat: Etat | None = None) -> str:
    """La page entière. Un registre vide est une erreur, pas une page vide."""
    if not fiches:
        raise ValueError("registre sans fiche : il n'y a rien à montrer")
    etat = etat if etat is not None else Etat()
    lien = (
        _lien(actions_module.lien_demande(depot), "Demander un nouveau lot")
        if depot else ""
    )
    return f"""<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ForgeHistory — où en est le travail</title>
<style>{STYLE}</style></head><body><main>
<h1>Où en est le travail</h1>
<p class="chapeau">Réécrite à chaque tour de l'intégration. Elle ne décide rien et
n'appelle rien : tout ce qui s'affiche a été calculé à la génération, et tout ce qui
s'actionne est un lien vers GitHub. {lien}</p>
{_decisions(etat)}
{_sante(etat)}
{_avancement(fiches, etat, depot)}
{_journal(etat)}
{_registre(fiches, lignes_pr, etat, depot)}
{_actions(etat)}
{_angle_mort(etat)}
<footer>Écrite le {_e(moment)}. Si elle contredit le registre, c'est le registre qui a
raison — l'état d'un lot ne s'écrit que dans sa fiche.</footer>
</main></body></html>"""
