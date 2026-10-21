#!/usr/bin/env python3

import argparse
import podio.root_io


parser = argparse.ArgumentParser()
parser.add_argument("input")
args = parser.parse_args()

reader = podio.root_io.Reader(args.input)

nevents = 0
events_with_hits = 0
total_hits = 0

collection_totals = {}
collection_events = {}

for frame in reader.get("events"):

    nevents += 1
    event_has_hits = False

    for name in frame.getAvailableCollections():

        if "Tracker" not in name:
            continue

        collection = frame.get(name)
        nhits = len(collection)

        collection_totals[name] = (
            collection_totals.get(name, 0) + nhits
        )

        if nhits > 0:
            collection_events[name] = (
                collection_events.get(name, 0) + 1
            )

            total_hits += nhits
            event_has_hits = True

    if event_has_hits:
        events_with_hits += 1


print()
print("=" * 70)
print("Tracker hit summary")
print("=" * 70)

print(f"Events:                  {nevents}")
print(f"Events with tracker hit: {events_with_hits}")
print(f"Total tracker hits:      {total_hits}")

if nevents:
    print(
        "Fraction with hits:       "
        f"{events_with_hits / nevents:.3f}"
    )

print()
print("Collections")
print("-" * 70)

for name in sorted(collection_totals):

    print(
        f"{name:35s} "
        f"events={collection_events.get(name, 0):5d} "
        f"hits={collection_totals[name]:7d}"
    )