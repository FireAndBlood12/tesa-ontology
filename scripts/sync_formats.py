#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_formats.py — keeps the dual serializations (.ttl / .rdf) of every
ontology in this repository in sync.

For each ontology base name found in ontology/, examples/, alignments/,
integrations/:

  * if only one serialization exists      -> the missing twin is generated;
  * if both exist and are isomorphic      -> nothing to do;
  * if both exist and differ              -> the OLDER file (by mtime) is
                                             regenerated from the NEWER one,
                                             i.e. "the file you last edited
                                             wins". Override with --from-ttl
                                             or --from-rdf to force direction.

Run this after editing any .ttl or .rdf file, then re-run
scripts/verify_compatibility.py. Typical workflow:

    $ nano alignments/tesa-bfo.ttl        # e.g. uncomment owl:imports
    $ python scripts/sync_formats.py
    regenerated: alignments/tesa-bfo.rdf (from newer .ttl)
    $ python scripts/verify_compatibility.py
"""
import argparse, glob, os, sys
import rdflib
from rdflib.compare import to_isomorphic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = ["ontology", "examples", "alignments", "integrations"]

def load(path):
    fmt = "turtle" if path.endswith(".ttl") else "xml"
    return rdflib.Graph().parse(path, format=fmt)

def save(graph, path):
    if path.endswith(".ttl"):
        graph.serialize(destination=path, format="turtle")
    else:
        graph.serialize(destination=path, format="pretty-xml")

def main():
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--from-ttl", action="store_true",
                     help="always treat .ttl as the source of truth")
    grp.add_argument("--from-rdf", action="store_true",
                     help="always treat .rdf as the source of truth")
    args = ap.parse_args()

    bases = set()
    for d in DIRS:
        for p in glob.glob(os.path.join(ROOT, d, "*.ttl")) + \
                 glob.glob(os.path.join(ROOT, d, "*.rdf")):
            bases.add(p[:-4])

    changed, ok = 0, 0
    for base in sorted(bases):
        ttl, rdf = base + ".ttl", base + ".rdf"
        rel = os.path.relpath(base, ROOT)
        has_ttl, has_rdf = os.path.exists(ttl), os.path.exists(rdf)

        if has_ttl and not has_rdf:
            save(load(ttl), rdf)
            print(f"created:     {rel}.rdf (twin was missing)")
            changed += 1
            continue
        if has_rdf and not has_ttl:
            save(load(rdf), ttl)
            print(f"created:     {rel}.ttl (twin was missing)")
            changed += 1
            continue

        g_ttl, g_rdf = load(ttl), load(rdf)
        if to_isomorphic(g_ttl) == to_isomorphic(g_rdf):
            ok += 1
            continue

        if args.from_ttl:
            src, dst, g = ttl, rdf, g_ttl
        elif args.from_rdf:
            src, dst, g = rdf, ttl, g_rdf
        elif os.path.getmtime(ttl) >= os.path.getmtime(rdf):
            src, dst, g = ttl, rdf, g_ttl
        else:
            src, dst, g = rdf, ttl, g_rdf
        save(g, dst)
        print(f"regenerated: {os.path.relpath(dst, ROOT)} "
              f"(from newer {os.path.basename(src)})")
        changed += 1

    print(f"\n{ok} pair(s) already in sync, {changed} file(s) written.")
    if changed:
        print("Now re-run: python scripts/verify_compatibility.py")

if __name__ == "__main__":
    main()
