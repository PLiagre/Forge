"""Ce que chaque rôle reçoit, et la forme de ce qu'il doit rendre.

Une consigne cite ses sources (la fiche, la revue, l'erreur de CI) ; elle ne
les paraphrase pas. Chaque rôle rend un objet dont le harnais vérifie la
forme (`--json-schema`) : rien ne se lit par expression régulière dans un
texte libre, et rien ne se perd de ce que l'agent a écrit.

Le meneur d'un lot (le chef, ou le développeur pour un lot simple) travaille
dans une seule session. Sa première consigne tient seule ; les suivantes sont
courtes, car la session se souvient : `suite_*`.
"""

from __future__ import annotations

import sys

from .lots import Lot, Question
from .projet import CHEF, DEVELOPPEUR, Projet

_FRONTIERE = ("Tu ne fais ni `git commit`, ni `git push`, ni aucune commande `gh` : le pilote de la chaîne "
              "enregistre, pousse et parle à GitHub.")


def _py() -> str:
    """`python3` ou `py`, celui qu'on tape sur cette machine."""
    return "py" if sys.platform.startswith("win") else "python3"


def _interdits(projet: Projet) -> str:
    return ", ".join(f"`{c}`" for c in projet.interdits)


def _chaine(texte: str = "") -> dict:
    return {"type": "string", "description": texte} if texte else {"type": "string"}


def _objet(proprietes: dict, obligatoires: tuple[str, ...]) -> dict:
    return {"type": "object", "properties": proprietes, "required": list(obligatoires)}


def _liste(element: dict) -> dict:
    return {"type": "array", "items": element}


_QUESTION = _objet({
    "texte": _chaine("la question, en une phrase"),
    "options": _liste(_objet({"lettre": _chaine("A, B, C ou D"), "reponse": _chaine(),
                              "cout": _chaine("ce que cette réponse coûte")}, ("lettre", "reponse"))),
    "recommandation": _objet({"lettre": _chaine(), "pourquoi": _chaine()}, ("lettre", "pourquoi")),
}, ("texte", "options", "recommandation"))
_TEST_CHANGE = _objet({"fichier": _chaine(), "pourquoi": _chaine("la règle du monde qui a changé")},
                      ("fichier", "pourquoi"))
_COMMANDE = _objet({"commande": _chaine(), "resultat": _chaine("ce qu'elle a rendu, en une ligne")},
                   ("commande", "resultat"))

SCHEMA_PLAN = _objet({
    "decision": {"type": "string", "enum": ["plan", "question", "refus"]},
    "resume": _chaine("ce que le lot fera, en deux ou trois phrases"),
    "etapes": _liste(_objet({
        "titre": _chaine(),
        "quoi": _chaine("ce que l'étape fait, et dans quels fichiers"),
        "qui": {"type": "string", "enum": ["chef", "developpeur"]},
        "tests": _chaine("les tests que l'étape joue avant de rendre la main"),
    }, ("titre", "quoi", "qui", "tests"))),
    "tests_a_changer": _liste(_TEST_CHANGE),
    "question": _QUESTION,
    "raison": _chaine("pourquoi le lot est refusé"),
}, ("decision",))

SCHEMA_PASSAGE = _objet({
    "etat": {"type": "string", "enum": ["faite", "a_poursuivre", "question", "conteste"]},
    "compte_rendu": _chaine("ce qui a été fait, en quelques phrases"),
    "tests_joues": _liste(_COMMANDE),
    "tests_changes": _liste(_TEST_CHANGE),
    "confie": _liste(_chaine("une tâche confiée au développeur")),
    "question": _QUESTION,
    "conteste": _liste(_objet({"constat": _chaine(), "pourquoi": _chaine()}, ("constat", "pourquoi"))),
    "capture": _chaine("lot `pc` : le groupe du scénario de capture qui montre le lot, si tu en as écrit un"),
}, ("etat", "compte_rendu"))

SCHEMA_RELECTURE = _objet({
    "verdict": {"type": "string", "enum": ["ACCEPTE", "CORRIGER"]},
    "resume": _chaine("ce que tu as vérifié et ce que tu en conclus"),
    "constats": _liste(_objet({
        "fichier": _chaine(), "ligne": {"type": "integer"},
        "gravite": {"type": "string", "enum": ["bloquant", "mineur"]},
        "quoi": _chaine("ce qui ne va pas, et ce qu'il faut à la place"),
    }, ("fichier", "gravite", "quoi"))),
    "promesse_joueur_tenue": {"type": "boolean"},
    "tests_changes_justifies": {"type": "boolean"},
    "tests_rejoues": _liste(_COMMANDE),
}, ("verdict", "resume", "constats", "promesse_joueur_tenue", "tests_changes_justifies"))

SCHEMA_RESUME_CI = _objet({
    "resume": _chaine("ce qui est rouge, en deux phrases"),
    "echecs": _liste(_objet({"travail": _chaine(), "test": _chaine(), "erreur": _chaine("citée telle quelle"),
                             "fichier": _chaine(), "ligne": {"type": "integer"}}, ("travail", "erreur"))),
}, ("resume", "echecs"))

SCHEMA_ARBITRAGE = _objet({
    "decision": {"type": "string", "enum": ["meneur", "relecteur"]},
    "pourquoi": _chaine(),
    "consigne": _chaine("ce que le meneur doit faire, si le relecteur a raison"),
}, ("decision", "pourquoi"))


def schema_fiche(projet: Projet) -> dict:
    return _objet({
        "titre": _chaine("court, en mots de joueur"),
        "piste": {"type": "string", "enum": list(projet.pistes)},
        "machine": {"type": "string", "enum": ["vps", "pc"]},
        "meneur": {"type": "string", "enum": ["chef", "developpeur"]},
        "joueur": _chaine("ce que je joue de plus : le geste, et ce qu'il décide"),
        "samedi": _chaine("ce que je vois samedi, en mots de joueur"),
        "regle": _chaine("la règle du monde, son niveau de fidélité, la section de MODELE.md ; « sans objet » "
                         "pour un écran"),
        "preuves": _liste(_chaine("une commande qui peut échouer, ou la capture qu'on regarde")),
        "hors_du_lot": _chaine("ce que ce lot ne fait pas"),
        "apres": _liste({"type": "integer", "description": "le rang, dans ta liste, d'une fiche qu'elle attend"}),
    }, ("titre", "piste", "machine", "meneur", "joueur", "samedi", "regle", "preuves"))


def schema_deblocage(projet: Projet) -> dict:
    return _objet({
        "decision": {"type": "string", "enum": ["relancer", "trancher", "redecouper", "reporter", "proprietaire"]},
        "pourquoi": _chaine("ce qui fonde la décision, vérifié dans le code ou les règles"),
        "consigne": _chaine("pour « relancer » : ce que le meneur et le relecteur doivent faire, et où"),
        "reponse": _chaine("pour « trancher » : la lettre choisie"),
        "bornes": _chaine("ce que la décision n'autorise pas"),
        "a_revoir_samedi": _chaine("une phrase pour le propriétaire, s'il doit revoir ce choix samedi"),
        "fiches": _liste(schema_fiche(projet)),
        "dependances_a_retirer": _liste({"type": "integer"}),
    }, ("decision", "pourquoi"))


def schema_palier(projet: Projet) -> dict:
    return _objet({
        "palier_atteint": {"type": "boolean", "description": "le propriétaire dit-il que le palier joué est atteint ?"},
        "titre": _chaine("le titre du palier suivant, en trois à cinq mots"),
        "but": _chaine("ce que le joueur saura faire à la fin de la semaine"),
        "fiches": _liste(schema_fiche(projet)),
        "note": _chaine("ce que tu as fait de chaque demande du propriétaire, et ce que tu reportes"),
    }, ("palier_atteint", "titre", "but", "fiches", "note"))


def sous_agents(projet: Projet) -> dict:
    """Le développeur, que le chef appelle dans sa session."""
    return {"developpeur": {
        "description": "Le développeur de Forge : fait une tâche bornée que le chef de lot lui confie (un fichier, "
                       "un test, un écran), dans le dossier du lot, et rend un compte rendu court.",
        "prompt": ("Tu es le développeur de Forge. Le chef de lot te confie une tâche bornée : fais-la, et elle "
                   "seule. Lis `AGENTS.md` et le `CLAUDE.md` de la zone où tu travailles. Joue les tests de ce que "
                   "tu touches (un fichier de test, `-k` pour un nom), jamais la suite entière. Tu ne décides "
                   "d'aucune règle du monde : si la tâche en demande une, arrête-toi et dis-le au chef. "
                   f"{_FRONTIERE} Écris en français. Termine par un compte rendu d'une à trois lignes : ce que tu "
                   "as fait, les tests joués et leur résultat."),
        "model": projet.agent(DEVELOPPEUR).modele,
    }}


def corps_de_fiche(fiche: dict, *, depend_de: list[int] = (), decoupe_de: int | None = None) -> str:
    """Le texte de l'issue d'un lot : la fiche du CTO."""
    preuves = "\n".join(f"- {p}" for p in fiche.get("preuves") or []) or "- (à écrire par le chef de lot)"
    morceaux = [
        "## Ce que je joue de plus", fiche.get("joueur", "").strip(), "",
        "## Ce que je vois samedi", fiche.get("samedi", "").strip(), "",
        "## La règle du monde", fiche.get("regle", "").strip() or "sans objet", "",
        "## Les preuves", preuves, "",
    ]
    if (fiche.get("hors_du_lot") or "").strip():
        morceaux += ["## Hors du lot", fiche["hors_du_lot"].strip(), ""]
    meneur = "le développeur seul" if fiche.get("meneur") == "developpeur" else "le chef de lot"
    morceaux.append(f"Piste : {fiche.get('piste', '')} · Machine : {fiche.get('machine', 'vps')} · Mené par : {meneur}")
    if decoupe_de is not None:
        morceaux.append(f"Découpé du lot #{decoupe_de} par le CTO.")
    if depend_de:
        morceaux.append("Dépend de : " + ", ".join(f"#{n}" for n in depend_de))
    return "\n".join(morceaux) + "\n"


def _decisions(decisions: tuple[str, ...]) -> str:
    """Ce qui a été décidé sur le lot : cela prime sur la fiche là où elle le contredit."""
    if not decisions:
        return ""
    return ("\n\nCE QUI A ÉTÉ DÉCIDÉ SUR CE LOT. Ces décisions valent consigne et priment sur la fiche là où elles "
            "la contredisent. Suis leurs raisons et reste dans leurs bornes.\n"
            + "".join(f"- {d.strip()[:3000]}\n" for d in decisions))


def _capture(lot: Lot) -> str:
    """Un lot `pc` se montre : le PC photographie ce que le meneur lui dit de jouer."""
    if lot.machine != "pc":
        return ""
    return ("- Ce lot se voit à l'écran : écris un scénario de capture qui pose ce que le lot ajoute ou joue son "
            "geste, et place la caméra pour qu'on le voie (`3d/unity/Assets/ForgeLocal3D/Editor/Captures/`, sur le "
            "modèle de `ScenarioExemple.cs` : `[ScenarioDeCapture(\"<groupe>\", \"<nom>\")]`, le groupe nommé "
            "d'après ce qu'il montre, jamais d'après un numéro). Rends son groupe dans `capture` : quand le plan "
            "est fini, le PC joue les tests EditMode, puis ce scénario, et joint ses images à la PR.\n")


def _regles_du_meneur(projet: Projet, lot: Lot) -> str:
    role = "le chef de lot" if lot.meneur == CHEF else "le développeur, et tu mènes seul ce lot simple"
    confier = ("- Tu codes le difficile toi-même. Tu confies au sous-agent `developpeur` les tâches bornées (un "
               "fichier, un test, un écran, une donnée), une à la fois, avec les fichiers et la règle à suivre ; "
               "tu relis ce qu'il rend avant de continuer.\n" if lot.meneur == CHEF else
               "- Tu ne décides d'aucune règle du monde : si le lot en demande une que la fiche ne donne pas, "
               "pose la question.\n")
    return f"""Tu es {role} de Forge. Tu mènes le lot #{lot.numero} « {lot.titre} » du plan à la fusion, dans cette session : elle sera reprise à chaque étape et à chaque correction, tu t'y souviendras de tout.

Lis d'abord `AGENTS.md`, `CAP.md` (le palier en cours), le `CLAUDE.md` de chaque zone que tu touches, et `jeu/sim/MODELE.md` si le lot touche le monde.

La fiche du lot (issue #{lot.numero}) :
-----
{lot.corps.strip() or "(vide)"}
-----

Tes règles :
{confier}- Joue les tests de ce que tu touches avant de rendre la main : un fichier de test, `-k` pour un nom (par exemple `{_py()} -m pytest jeu/sim/tests/test_lieux.py -q -k ouverture`), et les commandes des preuves de la fiche. Jamais la suite entière ni une simulation de plus de {projet.jours_max} jours : la chaîne les refuse, la CI joue la suite après la poussée et la nuit joue les longues preuves.
- Un changement du monde met à jour les tests qu'il touche, dans ce lot, aussi stricts, et tu dis pourquoi dans `tests_changes` : la règle qui a changé. Un test juge le monde livré : jamais un drapeau, une fixture ou un paramètre qui rejoue l'ancienne règle pour garder l'ancien test vert.
- Un changement du monde met à jour `jeu/sim/MODELE.md` dans ce lot.
- Jamais dans : {_interdits(projet)}. Le pilote retire ces changements.
- Un commentaire dit ce que le code fait et la contrainte qu'il respecte : ni date, ni numéro de lot, ni auteur.
- Si le lot exige une décision que tu n'as pas le droit de prendre (une règle du monde que la fiche ne donne pas, deux lectures de la fiche qui se valent), rends `question` : la question en une phrase, deux à quatre réponses avec ce que chacune coûte, et ta recommandation. Le CTO tranche, et le lot continue.
{_capture(lot)}- {_FRONTIERE}
- Écris en français : code, commentaires, compte rendu."""


def plan(projet: Projet, lot: Lot, decisions: tuple[str, ...] = ()) -> str:
    """La première consigne du meneur : concevoir le lot et rendre son plan."""
    confie = (" et dit qui la fait (`chef` pour le difficile, `developpeur` pour une tâche bornée que tu lui "
              "confieras)" if lot.meneur == CHEF else " (`qui` vaut `developpeur` : c'est toi)")
    return _regles_du_meneur(projet, lot) + _decisions(decisions) + f"""

TA TÂCHE MAINTENANT : LE PLAN. Lis le code que le lot touche, puis rends ton plan en étapes. Tu n'écris aucun fichier à cette étape, et tu ne lances aucun test : tu lis.
- Chaque étape laisse le dépôt cohérent, se vérifie par les tests qu'elle nomme{confie}. Trois à sept étapes pour un gros lot, une ou deux pour un petit.
- La dernière étape joue les preuves de la fiche et vérifie que ce qu'elle promet au joueur est vrai.
- `tests_a_changer` : les tests existants que le lot rendra faux, avec la règle qui change. Cherche-les maintenant (ce qui compte, borne ou fige ce que le lot touche ; les empreintes épinglées).
- Si la fiche ne sert pas le palier ou se contredit, rends `refus` avec la raison. Si elle demande une décision qui n'est pas la tienne, rends `question`."""


def _etape(k: int, n: int, etape: dict) -> str:
    qui = ("Confie-la au sous-agent `developpeur`, puis vérifie ce qu'il rend."
           if etape.get("qui") == "developpeur" else "Elle est à toi.")
    return (f"ÉTAPE {k} SUR {n} : {etape.get('titre', '')}.\n{etape.get('quoi', '')}\nSes tests : "
            f"{etape.get('tests', '')}\n{qui}\n"
            "Rends `faite` quand elle est finie et que ses tests sont verts ; `a_poursuivre` si tu dois t'arrêter "
            "avant la fin (dis où tu en es) ; `question` si elle exige une décision qui n'est pas la tienne.")


def etape(projet: Projet, lot: Lot, k: int, etapes: list[dict], decisions: tuple[str, ...] = (),
          coupee: bool = False) -> tuple[str, str]:
    """La consigne d'une étape : (pour une session neuve, pour la session reprise)."""
    plan_ecrit = "\n".join(f"{i}. {'[faite] ' if i < k else ''}{e.get('titre', '')} — {e.get('quoi', '')}"
                           for i, e in enumerate(etapes, start=1))
    coupure = ("Ton passage précédent a été coupé par son délai : ce que tu avais écrit est gardé. Reprends où tu "
               "en étais, sans relancer ce qui t'a fait attendre.\n\n" if coupee else "")
    tache = coupure + _etape(k, len(etapes), etapes[k - 1])
    neuve = (_regles_du_meneur(projet, lot) + _decisions(decisions)
             + f"\n\nTon plan, déjà dans la PR (les étapes « faite » sont déjà sur la branche) :\n{plan_ecrit}\n\n" + tache)
    return neuve, tache + _decisions(decisions)


def correction_ci(resume: str) -> str:
    return ("C'EST UNE CORRECTION. La CI est rouge sur ta dernière révision. Ce qu'elle dit, résumé par le lecteur :\n"
            f"-----\n{resume.strip()[:8000] or '(journal illisible : rejoue toi-même les tests que tu as touchés)'}\n-----\n"
            "Corrige la cause. Si un test existant est rouge parce que la règle du monde a changé, mets-le à jour "
            "aussi strict et dis-le dans `tests_changes` ; s'il est rouge parce que le code est faux, corrige le "
            "code. Rends `faite` quand c'est corrigé.")


def correction_relecture(revue: str, arbitrage: str = "") -> str:
    tranche = (f"\nLe CTO a tranché ton désaccord avec le relecteur :\n-----\n{arbitrage.strip()[:3000]}\n-----\n"
               if arbitrage.strip() else "")
    return ("C'EST UNE CORRECTION. Le relecteur demande des changements. Sa revue :\n"
            f"-----\n{revue.strip()[:10000]}\n-----\n{tranche}"
            "Traite chaque constat et rends `faite`. Si tu contestes un constat, ne change rien pour lui, rends "
            "`conteste` avec le constat et ta raison : le CTO tranchera.")


def conflit(branche: str, base: str, fichiers: list[str]) -> str:
    liste = "\n".join(f"- `{f}`" for f in fichiers)
    return (f"LA BRANCHE `{branche}` EST EN CONFLIT AVEC `{base}`. Une fusion de `origin/{base}` est en cours "
            f"dans ce dossier. Les fichiers en conflit :\n{liste}\n"
            "Résous chaque conflit en gardant l'intention des deux côtés, ton lot et la base. Retire tous les "
            "marqueurs `<<<<<<<`, `=======`, `>>>>>>>`. Joue les tests qui couvrent ces fichiers. Rends `faite`.")


def suite_neuve(projet: Projet, lot: Lot, etapes: list[dict], tache: str, decisions: tuple[str, ...] = ()) -> str:
    """Une correction, pour une session qu'il a fallu rouvrir : tout le lot, puis la tâche."""
    plan_ecrit = "\n".join(f"{i}. {e.get('titre', '')} — {e.get('quoi', '')}" for i, e in enumerate(etapes, start=1))
    return (_regles_du_meneur(projet, lot) + _decisions(decisions)
            + f"\n\nTon plan, déjà réalisé sur la branche (`git diff origin/{projet.branche_base}...HEAD`) :\n"
              f"{plan_ecrit}\n\n" + tache)


def relecteur(projet: Projet, lot: Lot, *, url: str, sha: str, plan_ecrit: str, tests_declares: str,
              tests_non_declares: tuple[str, ...] = (), rapports: str = "", lfs_lisibles: tuple[str, ...] = (),
              lfs_illisibles: tuple[str, ...] = (), decisions: tuple[str, ...] = (), cto: bool = False) -> str:
    qui = ("le CTO de Forge, et tu relis ce lot parce qu'il touche le cœur du moteur" if cto
           else "le relecteur de Forge")
    non_declares = (f"\nCes fichiers de test sont modifiés sans qu'une raison soit donnée : "
                    + ", ".join(f"`{f}`" for f in tests_non_declares)
                    + ". Juge chacun dans le diff : sans règle du monde qui le justifie, c'est un constat bloquant.\n"
                    if tests_non_declares else "")
    lfs = ""
    if lfs_lisibles:
        lfs += ("\nCes fichiers du lot sont en LFS : à leur place, ce dossier n'a que leur pointeur. Leur contenu "
                "réel est dans `.atelier/lfs/`, au même chemin :\n" + "".join(f"- `.atelier/lfs/{f}`\n" for f in lfs_lisibles))
    if lfs_illisibles:
        lfs += ("\nCes fichiers du lot sont en LFS et n'ont pas pu être téléchargés : "
                + ", ".join(f"`{f}`" for f in lfs_illisibles) + ". Juge-les sur les captures de la PR.\n")
    comptes = (f"\nCe que le meneur dit avoir fait (des affirmations à vérifier, pas des preuves) :\n-----\n"
               f"{rapports.strip()[:8000]}\n-----\n" if rapports.strip() else "")
    return f"""Tu es {qui}. Tu n'as pas écrit ce code et tu ne le modifies pas.

Relis le lot #{lot.numero} « {lot.titre} » : la PR {url}, révision {sha[:7]}. Ce dossier est cette révision. Lis `AGENTS.md` et le `CLAUDE.md` des zones touchées. Lis d'abord la fiche et le diff (`git diff origin/{projet.branche_base}...HEAD`), ensuite seulement ce que le meneur en dit.

La fiche du lot :
-----
{lot.corps.strip() or "(vide)"}
-----
Son plan :
-----
{plan_ecrit.strip() or "(aucun)"}
-----
Les tests changés, et la raison donnée pour chacun :
-----
{tests_declares.strip() or "(aucun test existant n'est déclaré changé)"}
-----
{non_declares}{comptes}{lfs}
La CI est verte : elle a joué la suite. Tu peux rejouer un fichier de test (`{_py()} -m pytest <fichier> -q -k <nom>`) pour vérifier une affirmation, jamais la suite entière.

Vérifie, du plus grave au plus léger :
1. Rien ne touche {_interdits(projet)}, et le diff fait ce que la fiche demande, pas autre chose.
2. Les principes du jeu d'`AGENTS.md` : une seule simulation (une vue ne décide aucun nombre), un modificateur change un taux et ne crée ni kilo ni pièce, ses chiffres sont dans `jeu/data/`, tout geste est une intention que l'IA peut déposer, déterminisme tenu.
3. Chaque preuve de la fiche est mesurée par un test ou une commande qui peut échouer.
4. Les tests changés : chacun l'est parce qu'une règle du monde a changé, il reste aussi strict, et il juge le monde livré. Un test basculé sur un « monde d'avant » (un drapeau, une fixture, un paramètre qui rejoue l'ancienne règle) est un constat bloquant. Un test retiré sans remplaçant aussi strict l'est aussi.
5. Ce que le lot prétend est vrai : lis le code, pas seulement le compte rendu.
6. La promesse au joueur : ce que la fiche dit que je joue de plus et que je vois samedi, le diff le donne. Pour un lot `pc`, le compte rendu du PC dit si Unity compile et joint les captures : regarde-les.

Rends ton verdict. `CORRIGER` seulement pour un constat bloquant : chacun avec son fichier, sa ligne et ce qu'il faut à la place. Un constat mineur n'empêche pas `ACCEPTE`. Ne demande au meneur que ce qu'il peut faire dans son lot. Écris en français. {_FRONTIERE}""" + _decisions(decisions)


def resume_ci(journal: str) -> str:
    return f"""Tu es le lecteur de Forge. Voici ce que dit une CI rouge. Dis ce qui est rouge, sans juger ni proposer de correction : pour chaque échec, le travail, le test, l'erreur citée telle quelle, le fichier et la ligne quand le journal les donne. N'invente rien : ce qui n'est pas dans le journal n'existe pas.

-----
{journal.strip()[:40000] or "(journal vide)"}
-----"""


def _contexte_cto(projet: Projet) -> str:
    return ("Tu es le CTO de Forge. Tu es appelé à ce moment précis, tu ne surveilles pas, et tu ne codes pas : tu "
            "ne modifies aucun fichier. Lis d'abord `AGENTS.md`, `CAP.md` et `docs/VISION.md` (ses décisions "
            "numérotées font foi, les plus récentes priment). Vérifie dans le code ce qu'on t'affirme.")


def deblocage(projet: Projet, lot: Lot, *, raison: str, question: Question | None, issue: str, pr: str,
              erreur_ci: str, relances: int, boucle: tuple[int, ...] = ()) -> str:
    """Le CTO, devant un lot bloqué : une question du meneur, des essais épuisés, une boucle."""
    if question is not None:
        quoi = f"Le meneur pose une question :\n-----\n{question.en_clair()}\n-----"
    elif boucle:
        quoi = ("Ce lot est pris dans une boucle de dépendances : " + " → ".join(f"#{n}" for n in (*boucle, boucle[0]))
                + ". Aucun de ces lots ne peut partir. Retire la dépendance de trop (`dependances_a_retirer`, sur ce "
                  "lot-ci) et relance.")
    else:
        quoi = f"Le pilote l'a bloqué : {raison}"
    deja = (f"\nTu as déjà relancé ce lot {relances} fois sur {projet.deblocages_max}"
            + (" : ne le relance plus, redécoupe-le ou reporte-le." if relances >= projet.deblocages_max
               else " : relance encore seulement pour une cause nouvelle.") if relances else "")
    ci = f"\nCe que dit la CI rouge :\n-----\n{erreur_ci.strip()[:6000]}\n-----\n" if erreur_ci.strip() else ""
    return f"""{_contexte_cto(projet)}

Le lot #{lot.numero} « {lot.titre} » est arrêté. {quoi}{deja}

Ce dossier est la branche du lot (ou la base, s'il n'a pas de PR). Tu peux lire le code, `git log`, `git diff origin/{projet.branche_base}...HEAD`, et rejouer un test rouge (`{_py()} -m pytest <fichier> -q -k <nom>`).

La fiche (issue #{lot.numero}) :
-----
{lot.corps.strip()[:6000] or "(vide)"}
-----
Ce qui s'est dit sur l'issue :
-----
{issue.strip()[-8000:] or "(rien)"}
-----
Ce qui s'est dit sur la PR, du plus ancien au plus récent :
-----
{pr.strip()[-16000:] or "(pas de PR)"}
-----
{ci}
Pendant la semaine, aucune question n'attend le propriétaire. Décide :
- `trancher` : pour une question. Choisis une des lettres proposées (`reponse`) quand `docs/VISION.md`, `CAP.md` ou une décision déjà écrite la donnent, ou quand le choix est réversible (un seuil, une durée, une donnée de `jeu/data/`, un ordre, une formulation). Dis pourquoi, et pose les bornes : ce que ta réponse n'autorise pas. Si le propriétaire doit revoir ce choix, écris-le en une phrase dans `a_revoir_samedi`.
- `relancer` : le lot repart, avec ta `consigne` au meneur et au relecteur : le fichier, la fonction, ce qu'il faut changer et pourquoi ; et ses `bornes`.
- `redecouper` : le lot est trop gros ou mal posé. Écris les fiches qui le remplacent (`fiches`), chacune jouable et prouvée seule ; le pilote ferme ce lot et sa PR, et ouvre les tiennes.
- `reporter` : le lot ne peut pas aboutir cette semaine. Il reste arrêté jusqu'à samedi ; dis pourquoi dans `a_revoir_samedi`.
- `proprietaire` : seulement pour l'irréversible, l'argent et les droits (une dépense, une licence, un secret, un réglage de GitHub ou d'une machine, une donnée figée qu'on ne retrouverait pas). Le propriétaire est prévenu tout de suite.
Jamais une décision qui touche {_interdits(projet)}, ni qui fait dire à un test le contraire de ce que le monde livré fait. {_FRONTIERE}"""


def arbitrage(projet: Projet, lot: Lot, *, revue: str, contestation: str) -> str:
    return f"""{_contexte_cto(projet)}

Le meneur du lot #{lot.numero} « {lot.titre} » conteste la relecture. Ce dossier est la branche du lot. Lis le code en cause, puis tranche.

La fiche :
-----
{lot.corps.strip()[:4000] or "(vide)"}
-----
La revue du relecteur :
-----
{revue.strip()[:8000]}
-----
Ce que le meneur conteste, et pourquoi :
-----
{contestation.strip()[:6000]}
-----
Rends `meneur` s'il a raison sur tous les constats bloquants qu'il conteste : le lot est alors accepté tel quel. Rends `relecteur` sinon, avec ta `consigne` : ce que le meneur doit faire. Dis pourquoi, en citant la règle ou le code. {_FRONTIERE}"""


def palier(projet: Projet, *, numero: int, note_du_proprietaire: str, etat_du_palier: str, a_revoir: str,
           proposition: str = "", remarques: str = "") -> str:
    """Le CTO, le samedi : tirer les lots du palier suivant de ce que le propriétaire a dit."""
    reprise = (f"\nTa proposition précédente :\n-----\n{proposition.strip()[:8000]}\n-----\n"
               f"Ce que le propriétaire en a dit :\n-----\n{remarques.strip()[:4000]}\n-----\nRefais-la en en tenant compte.\n"
               if proposition.strip() else "")
    return f"""{_contexte_cto(projet)}

C'est samedi. Le propriétaire a joué la démo du palier {numero} et a écrit ce qu'il veut. Tire de sa note le palier {numero + 1} : les lots de la semaine.

Ce que le propriétaire a écrit :
-----
{note_du_proprietaire.strip()[:8000] or "(rien)"}
-----
Où en est le palier {numero} (lots livrés, en cours, arrêtés) :
-----
{etat_du_palier.strip()[:8000] or "(rien)"}
-----
Ce que tu avais décidé seul pendant la semaine, « à revoir samedi » :
-----
{a_revoir.strip()[:4000] or "(rien)"}
-----
{reprise}
La règle d'un palier et d'un lot est dans `CAP.md`. Regarde le code avant d'écrire : une fiche promet ce que le jeu peut vraiment recevoir en une semaine.
- Un lot par piste au moins ({", ".join(projet.pistes)}), et pas plus de lots que la semaine n'en porte. Un lot est l'avancée d'une piste pour le palier, sans plafond de taille : ne le coupe pas en morceaux invisibles.
- Chaque fiche dit ce que je joue de plus, ce que je vois samedi, la règle du monde (son niveau de fidélité, la section de `jeu/sim/MODELE.md`), les preuves, la piste, la machine (`pc` pour Unity ou Blender) et qui le mène (`chef`, ou `developpeur` pour un lot simple de données ou d'écran courant).
- `apres` : les rangs, dans ta liste, des fiches qu'une fiche attend vraiment (l'écran attend la règle). Jamais de boucle.
- Ce qui reste du palier {numero} et que le propriétaire veut encore, reprends-le dans une fiche ; ce qu'il écarte, laisse-le.
- `palier_atteint` : vrai seulement s'il le dit. `note` : ce que tu as fait de chacune de ses demandes, et ce que tu reportes. {_FRONTIERE}"""


def note_de_demo(projet: Projet, *, numero: int, titre: str, faits: str) -> str:
    """Le CTO, le vendredi soir : la note d'une page qui accompagne le build figé."""
    return f"""{_contexte_cto(projet)}

C'est vendredi soir. Le build du palier {numero} « {titre} » est figé. Écris la note d'une page que le propriétaire lira avant de jouer samedi. Tu réponds de cette démo : n'écris que ce qui est vrai sur master, vérifie dans le code ce dont tu doutes.

Les faits, relevés par le pilote sur GitHub :
-----
{faits.strip()[:20000]}
-----

Écris en français simple, en mots de joueur, sans jargon de code ni de chaîne, exactement ces parties :

## Quoi essayer
Les gestes à faire, dans l'ordre, pour voir le palier : où cliquer, quoi attendre.

## Ce qui marche
Ce que chaque piste a vraiment livré cette semaine.

## Ce qui manque
Ce qui était promis et n'y est pas, et pourquoi, sans l'adoucir.

## À revoir samedi
Les choix que tu as pris seul pendant la semaine, chacun en une ligne, avec ce qu'il faudrait changer s'il ne convient pas.

## Ce que la semaine a coûté
Le tableau des coûts des faits, tel quel.

Rien d'autre que ces parties."""


def reparation_de_master(projet: Projet, *, url: str, resume: str) -> str:
    return f"""{_contexte_cto(projet)}

La CI de `{projet.branche_base}` est rouge ({url}) : tous les lots attendent. Écris la fiche du lot de réparation, qui passera avant tout autre. Ce dossier est une copie de `{projet.branche_base}`. Ce que dit la CI, résumé par le lecteur :
-----
{resume.strip()[:8000] or "(journal illisible)"}
-----
Trouve la cause dans le code. La fiche dit : dans `joueur`, ce que la panne empêche ; dans `samedi`, « master est vert » ; dans `regle`, la cause, avec le fichier et la ligne ; dans `preuves`, le test rouge qui doit redevenir vert. Choisis la piste et la machine du code en cause, et `chef` pour le mener. Une réparation corrige la cause : elle ne retire pas un test. Si la cause est dans {_interdits(projet)}, dis-le dans `regle` : le lot sera laissé au propriétaire. {_FRONTIERE}"""


def journal(*, faits: str) -> str:
    return f"""Tu es le lecteur de Forge, un jeu de grande stratégie sur l'Europe de 1400. Écris le journal du matin du propriétaire : il le lit sur son téléphone en deux minutes. Tu ne juges rien et tu n'inventes rien : ni lot, ni numéro, ni nombre, ni cause hors des faits.

Les faits, relevés par le pilote sur GitHub :
-----
{faits.strip()[:30000]}
-----

Écris en français simple, au présent, en mots de joueur, exactement ces parties :

> **Avancé** : une phrase, la nouveauté la plus forte depuis hier.
> **Arrêté** : une phrase, ce qui est arrêté et ce que le joueur en attend ; « rien » sinon.
> **Pour toi** : seulement ce que le propriétaire doit faire lui-même (l'irréversible, l'argent, les droits) ; « rien » sinon.

### Ce qui a changé dans le jeu
Pour chaque lot livré : son titre en gras avec le lien de sa PR, puis deux phrases sur ce que le joueur peut faire ou voir de neuf.

### En route
Une ligne par lot en cours : où il en est.

### À revoir samedi
Les choix que le CTO a pris seul, un par ligne, tels que les faits les donnent.

Interdits : les noms de fichiers et de fonctions, les mots de la chaîne (PR ouverte, session, marque, verdict), les noms de modèles. Le pilote ajoute lui-même les coûts : ne les écris pas. Rien d'autre que ces parties."""
