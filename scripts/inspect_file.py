#!/usr/bin/env python3

"""
Inspect the collections stored in an EDM4hep/podio ROOT file.

Usage:
    python3 scripts/inspect_file.py chargino_fcchh_SIM.root
"""

import argparse
import podio.root_io


def main():
    parser = argparse.ArgumentParser(
        description="Inspect EDM4hep collections in a podio ROOT file"
    )
    parser.add_argument("input", help="Input EDM4hep ROOT file")
    parser.add_argument(
        "-n",
        "--events",
        type=int,
        default=1,
        help="Number of events to inspect",
    )
    args = parser.parse_args()

    reader = podio.root_io.Reader(args.input)

    for ievt, frame in enumerate(reader.get("events")):

        print()
        print("=" * 80)
        print(f"Event {ievt}")
        print("=" * 80)

        collections = sorted(frame.getAvailableCollections())

        for name in collections:

            try:
                collection = frame.get(name)
                size = len(collection)

                if size > 0:
                    typename = type(collection[0]).__name__
                else:
                    typename = "<empty>"

                print(
                    f"{name:40s}"
                    f" n = {size:8d}"
                    f"   type = {typename}"
                )

            except Exception as exc:
                print(f"{name:40s} <could not read: {exc}>")

        if ievt + 1 >= args.events:
            break


if __name__ == "__main__":
    main()