"""Derouler la simulation, et en faire une planche.

    python3 -m chronique --ticks 180 --pas 4 --html /tmp/chronique.html
    python3 -m chronique --ticks 180 --pas 4 --json /tmp/chronique.json
    python3 -m chronique --chronique /tmp/chronique.json --html /tmp/planche.html

Les deux gestes sont separes exprer : derouler coute des secondes de
simulation, dessiner n'en coute aucune. Une chronique ecrite une fois se
redessine autant de fois qu'on veut, avec une autre direction
artistique, ou par un autre moteur de rendu.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from vues.chronique.atlas import AtlasError, lire_da, rendre
from vues.chronique.bobine import BobineError, filmer
from vues.chronique.capture import CaptureError, capturer

EXIT_REFUS = 2


def _avancement(acheve: int, total: int) -> None:
    if total and (acheve % 10 == 0 or acheve == total):
        print(f"  tick {acheve}/{total}", end="\r", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="La chronique : le monde qui avance, dessine."
    )
    parser.add_argument("--ticks", type=int, default=180)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--pas", type=int, default=4, help="un instant capture tous les N ticks"
    )
    parser.add_argument(
        "--chronique",
        default=None,
        help="relire une chronique deja ecrite au lieu de derouler la simulation",
    )
    parser.add_argument("--json", dest="sortie_json", default=None)
    parser.add_argument("--html", dest="sortie_html", default=None)
    parser.add_argument("--da", default=None, help="autre direction artistique")
    parser.add_argument(
        "--sans-reseau",
        action="store_true",
        help="page sans aucune requete exterieure (fontes du systeme)",
    )
    parser.add_argument("--cadence-ms", type=int, default=140)
    parser.add_argument(
        "--bobine",
        default=None,
        help="filmer la planche (demande Chromium et ffmpeg) ; exige --html",
    )
    parser.add_argument("--bobine-lecture", default="population")
    parser.add_argument("--bobine-ips", type=int, default=8)
    parser.add_argument("--chrome", default=None)
    parser.add_argument("--ffmpeg", default=None)
    args = parser.parse_args(argv)

    if not args.sortie_json and not args.sortie_html:
        print("refus : rien a ecrire (--json et/ou --html)", file=sys.stderr)
        return EXIT_REFUS
    if args.bobine and not args.sortie_html:
        print("refus : --bobine filme une planche, donc exige --html",
              file=sys.stderr)
        return EXIT_REFUS

    try:
        if args.chronique:
            chronique = json.loads(Path(args.chronique).read_text(encoding="utf-8"))
        else:
            debut = time.time()
            print(
                f"chronique : {args.ticks} ticks, graine {args.seed}, "
                f"un instant tous les {args.pas}",
                file=sys.stderr,
            )
            chronique = capturer(
                args.ticks, args.seed, args.pas, avancement=_avancement
            )
            print(
                f"\n  {len(chronique['images'])} images en "
                f"{time.time() - debut:.1f}s",
                file=sys.stderr,
            )
        if args.sortie_json:
            destination = Path(args.sortie_json)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(chronique, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            print(f"  ecrit {destination} "
                  f"({destination.stat().st_size / 1e6:.1f} Mo)", file=sys.stderr)
        if args.sortie_html:
            da = lire_da(Path(args.da)) if args.da else lire_da()
            page = rendre(
                chronique,
                da,
                sans_reseau=args.sans_reseau,
                cadence_ms=args.cadence_ms,
            )
            destination = Path(args.sortie_html)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(page, encoding="utf-8")
            print(f"  ecrit {destination} "
                  f"({destination.stat().st_size / 1e6:.1f} Mo)", file=sys.stderr)
            if args.bobine:
                nombre = len(chronique["images"])
                print(f"  bobine : {nombre} images", file=sys.stderr)
                film = filmer(
                    destination,
                    Path(args.bobine),
                    nombre,
                    lecture=args.bobine_lecture,
                    images_par_seconde=args.bobine_ips,
                    chrome=args.chrome,
                    ffmpeg=args.ffmpeg,
                )
                print(f"  ecrit {film} "
                      f"({film.stat().st_size / 1e6:.1f} Mo)", file=sys.stderr)
    except (AtlasError, BobineError, CaptureError, OSError, ValueError, KeyError) as exc:
        print(f"refus : {exc}", file=sys.stderr)
        return EXIT_REFUS
    return 0


if __name__ == "__main__":
    sys.exit(main())
