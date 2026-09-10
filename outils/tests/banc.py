"""Un banc pour les scripts des workflows : de faux `gh`, `git`, `python`.

Les décisions s'éprouvent en Python ; les **gestes** vivent dans du shell,
et un shell qui n'a jamais tourné est un shell qu'on croit connaître. Le
4 septembre 2026, `relecture.sh` — alors bloc de YAML — est mort sur le
`errexit` que GitHub pose par défaut, avant de poser l'état qu'il devait
poser. Le contrôle ne rougissait pas : il n'existait pas. Rien dans le
dépôt ne pouvait le voir, parce que rien ne jouait ce shell.

Le banc pose de faux exécutables en tête du `PATH` : un vrai `gh` n'est
pas *choisi de ne pas être appelé*, il est **hors de portée**. Chaque
appel s'écrit dans un journal, et c'est le journal qu'on affirme — pas
la sortie de l'écran, qui ne dit pas si le geste a eu lieu.

Un faux répond **selon ses arguments**, et peut répondre autre chose au
deuxième appel : c'est ce qu'il faut pour éprouver une attente — une
révision qui ne bouge qu'après le troisième coup d'œil, par exemple.

Ses variables portent toutes le préfixe `BANC_` : la première version
appelait la sienne `JOURNAL`, comme le script du palier, et le scénario
écrasait celle du banc sans un mot. Aucun appel n'était enregistré, et le
contrôle échouait en accusant le script.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import subprocess
import sys

RACINE = Path(__file__).resolve().parent.parent.parent
SCRIPTS = RACINE / ".github" / "scripts"

# Le séparateur d'unité : il ne peut pas apparaître dans un argument, donc
# les bornes des arguments survivent au journal. Un simple espace les
# perdait — « -f description=FAIL PR 225 » redevenait quatre mots, et un
# contrôle affirmait « FAIL » là où l'argument valait toute la phrase.
SEPARATEUR = "\x1f"

# Le faux nomme son interpréteur par son chemin, pas par `env`. Sinon il
# se cherche lui-même : le banc pose ses faux en tête du `PATH`, et un
# faux nommé `python3` deviendrait son propre interpréteur — le banc
# tournait alors en rond sans jamais rien journaliser. C'est ce qui
# interdisait jusqu'ici d'éprouver un script qui appelle `python3`, donc
# tout script qui respecte la règle 1.
_FAUX = '''#!''' + sys.executable + '''
"""Un faux exécutable du banc : il journalise, puis répond selon ses arguments."""
import json, os, sys

nom = os.path.basename(sys.argv[0])
argv = sys.argv[1:]
with open(os.environ["BANC_JOURNAL"], "a", encoding="utf-8") as journal:
    journal.write("\\x1f".join([nom, *argv]) + "\\n")

regles = json.loads(open(os.path.join(os.environ["BANC_REPONSES"], nom + ".json"),
                         encoding="utf-8").read())
ligne = " ".join(argv)
choisie = regles["defaut"]
for regle in regles["regles"]:
    if all(fragment in ligne for fragment in regle["si"]):
        choisie = regle
        break

# Un appel de plus rend la réponse suivante ; la dernière se répète. C'est
# ce qui permet d'éprouver une attente : la tête a bougé au troisième coup.
compte = os.path.join(os.environ["BANC_REPONSES"], nom + "." + choisie["cle"] + ".n")
rang = int(open(compte).read()) if os.path.exists(compte) else 0
open(compte, "w").write(str(rang + 1))
sorties = choisie["sorties"]
sys.stdout.write(sorties[min(rang, len(sorties) - 1)])
sys.exit(choisie["code"])
'''


@dataclass
class Banc:
    dossier: Path
    journal: Path = field(init=False)
    reponses: Path = field(init=False)
    bin: Path = field(init=False)

    def __post_init__(self) -> None:
        self.journal = self.dossier / "journal.txt"
        self.reponses = self.dossier / "reponses"
        self.bin = self.dossier / "bin"
        self.reponses.mkdir(parents=True, exist_ok=True)
        self.bin.mkdir(parents=True, exist_ok=True)
        self.journal.write_text("", encoding="utf-8")

    def poser(self, nom: str, sortie: str = "", code: int = 0, selon=None) -> None:
        """Un faux exécutable, sa réponse par défaut, et ses cas particuliers.

        `selon` : une liste de (fragments, sorties, code). Le premier cas
        dont tous les fragments sont dans la ligne de commande gagne ; ses
        sorties se consomment dans l'ordre, la dernière se répète.
        """
        chemin = self.bin / nom
        chemin.write_text(_FAUX, encoding="utf-8")
        chemin.chmod(0o755)
        regles = []
        for rang, cas in enumerate(selon or ()):
            fragments, sorties = cas[0], cas[1]
            regles.append({
                "cle": str(rang),
                "si": list(fragments),
                "sorties": list(sorties) if isinstance(sorties, (list, tuple)) else [sorties],
                "code": cas[2] if len(cas) > 2 else 0,
            })
        (self.reponses / f"{nom}.json").write_text(
            json.dumps({"regles": regles,
                        "defaut": {"cle": "defaut", "si": [], "sorties": [sortie], "code": code}}),
            encoding="utf-8",
        )

    def jouer(self, script: str, **env) -> subprocess.CompletedProcess:
        """Jouer un script des workflows, tel qu'il est sur le disque.

        `bash -e` reproduit ce que GitHub impose aux blocs `run:` — c'est
        la condition qui a manqué la première fois. Un script qui ne
        survit pas à cette ligne-là ne survivra pas non plus en ligne.
        """
        chemin = SCRIPTS / script
        assert chemin.is_file(), f"{chemin} n'existe pas"
        return subprocess.run(
            ["bash", "-e", str(chemin)],
            cwd=self.dossier,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                "BANC_JOURNAL": str(self.journal),
                "BANC_REPONSES": str(self.reponses),
                # L'attente du rejeu ne dort pas sur le banc : on éprouve
                # la boucle, pas la patience.
                "PAS_REJEU": "0",
                "ATTENTE_REJEU": "4",
                **{cle: str(valeur) for cle, valeur in env.items()},
            },
        )

    @property
    def brut(self) -> list[list[str]]:
        """Chaque appel, argument par argument."""
        return [
            ligne.split(SEPARATEUR)
            for ligne in self.journal.read_text(encoding="utf-8").splitlines()
            if ligne
        ]

    @property
    def appels(self) -> list[str]:
        """Chaque appel, lisible : les arguments joints par un espace."""
        return [" ".join(morceaux) for morceaux in self.brut]

    def appel(self, *fragments: str) -> list[str] | None:
        """Le premier appel qui porte tous ces fragments, argument par argument."""
        for morceaux, lisible in zip(self.brut, self.appels):
            if all(f in lisible for f in fragments):
                return morceaux
        return None

    @staticmethod
    def valeur(appel, drapeau: str) -> str | None:
        """La valeur passée à `cle=valeur` dans un appel journalisé."""
        for morceau in appel or ():
            if morceau.startswith(f"{drapeau}="):
                return morceau.split("=", 1)[1]
        return None
