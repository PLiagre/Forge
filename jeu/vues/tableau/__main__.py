"""Regard mince : preuve SVG déterministe, ou serveur local stdlib."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vues.tableau.server import serve
from vues.tableau.snapshot_loader import SnapshotLoadError, load_snapshot
from vues.tableau.svg_proof import write_svg

EXIT_REFUS = 2
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Visualiseur mince d'un snapshot cellulaire ForgeHistory."
    )
    parser.add_argument("--snapshot", required=False, help="fichier snapshot v0a-1")
    parser.add_argument("--compare", required=False, help="second snapshot à comparer")
    parser.add_argument("--proof-svg", dest="proof_svg", default=None)
    parser.add_argument("--layer", default="population")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if not args.snapshot:
        print("refus : --snapshot est obligatoire", file=sys.stderr)
        return EXIT_REFUS
    try:
        document = load_snapshot(Path(args.snapshot))
        compare = load_snapshot(Path(args.compare)) if args.compare else None
    except SnapshotLoadError as exc:
        print(f"refus : {exc}", file=sys.stderr)
        return EXIT_REFUS
    if args.proof_svg:
        try:
            write_svg(
                document,
                Path(args.proof_svg),
                layer=args.layer,
                compare=compare,
            )
        except (OSError, KeyError, ValueError) as exc:
            print(f"refus : {exc}", file=sys.stderr)
            return EXIT_REFUS
        return 0
    try:
        snapshot_a = Path(args.snapshot).read_bytes()
        snapshot_b = Path(args.compare).read_bytes() if args.compare else None
        server = serve(args.host, args.port, snapshot_a, snapshot_b)
    except OSError as exc:
        print(f"refus : port {args.port} pris ({exc})", file=sys.stderr)
        return EXIT_REFUS
    print(f"regard local sur {args.host}:{args.port} — Ctrl+C pour quitter")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
