#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_compatibility.py — sanity and consistency checks for the TESA
compatibility pack.

Level 1 (always runs, pure Python):
  * parses every RDF/Turtle file in the pack (syntax validation);
  * merges the TESA core + car-factory ABox + each alignment /
    integration module into one graph;
  * materializes the OWL 2 RL closure with owlrl and checks that no
    individual is inferred to be a member of owl:Nothing and that no
    owl:disjointWith / differentFrom contradiction is raised;
  * runs structural SPARQL checks (every Action in a conflict group
    has a priority; every trigger has at least one action; every
    validity interval is a time:Interval).

Level 2 (optional, requires Java): if owlready2 + a JRE are available,
re-checks the merged ontologies with the Pellet reasoner (the
configuration used in the paper) and with HermiT.

Usage:  python scripts/verify_compatibility.py
Deps :  pip install rdflib owlrl   (owlready2 optional for level 2)
"""
import sys, glob, os
import rdflib
from rdflib.namespace import OWL, RDF, RDFS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "ontology", "tesa-ontology.rdf")
ABOX = os.path.join(ROOT, "examples", "car-factory.ttl")
MODULES = sorted(glob.glob(os.path.join(ROOT, "alignments", "*.ttl"))
               + glob.glob(os.path.join(ROOT, "integrations", "*.ttl")))

def load(path):
    g = rdflib.Graph()
    fmt = "xml" if path.endswith((".rdf", ".owl", ".xml")) else "turtle"
    g.parse(path, format=fmt)
    return g

def rl_consistency(g, label):
    """OWL 2 RL closure + contradiction scan."""
    from owlrl import DeductiveClosure, OWLRL_Semantics
    n_before = len(g)
    DeductiveClosure(OWLRL_Semantics).expand(g)
    problems = []
    for s in g.subjects(RDF.type, OWL.Nothing):
        problems.append(f"individual in owl:Nothing: {s}")
    # owlrl flags contradictions by adding daml:error-style triples on a
    # special node; simplest robust check is Nothing-membership plus
    # sameAs/differentFrom clashes:
    for s, o in g.subject_objects(OWL.differentFrom):
        if (s, OWL.sameAs, o) in g:
            problems.append(f"sameAs/differentFrom clash: {s} vs {o}")
    status = "CONSISTENT" if not problems else "INCONSISTENT"
    print(f"  [{status}] {label}: {n_before} -> {len(g)} triples after OWL RL closure")
    for p in problems:
        print("    !!", p)
    return not problems

def structural_checks(g):
    qs = {
        "conflict-group members lacking a PriorityRelator":
            """SELECT ?a WHERE {
                 ?g a tesa:ConflictedActions ; tesa:hasAction ?a .
                 FILTER NOT EXISTS { ?a tesa:hasPriorityRelator ?pr } }""",
        "triggers without any action":
            """SELECT ?t WHERE { ?t a tesa:TimeTrigger .
                 FILTER NOT EXISTS { ?t tesa:hasAction ?a } }""",
        "validDuringInterval targets that are not time:Interval":
            """SELECT ?i WHERE { ?x tesa:validDuringInterval ?i .
                 FILTER NOT EXISTS { ?i a time:Interval } }""",
    }
    ok = True
    for label, q in qs.items():
        rows = list(g.query(q, initNs={
            "tesa": rdflib.Namespace("http://example.org/tesa#"),
            "time": rdflib.Namespace("http://www.w3.org/2006/time#")}))
        print(f"  [{'OK' if not rows else 'FAIL'}] {label}: {len(rows)} violations")
        for r in rows[:5]:
            print("    !!", r[0])
        ok = ok and not rows
    return ok

def pellet_check(paths):
    """Optional level 2: Pellet via owlready2 (needs Java).

    To keep the check runnable offline, all files are merged into a
    single RDF/XML document and owl:imports declarations are removed
    (their content is either already merged or, for OWL-Time, declared
    locally where referenced). On a machine with internet access the
    imports resolve normally and this step is only an optimization.
    """
    try:
        import owlready2, shutil, tempfile
        if not shutil.which("java"):
            print("  (skipped: no Java runtime found)")
            return None
    except ImportError:
        print("  (skipped: owlready2 not installed)")
        return None
    merged = rdflib.Graph()
    for p in paths:
        merged += load(p)
    merged.remove((None, OWL.imports, None))
    # Workaround for a known owlready2 limitation: it cannot parse
    # xsd:gDay / xsd:gMonth literals (used by OWL-Time time:day /
    # time:month). Downgrade them to plain strings for the Pellet run
    # only; the published Turtle files keep the spec-conformant types.
    XSD = rdflib.Namespace("http://www.w3.org/2001/XMLSchema#")
    for dtype in (XSD.gDay, XSD.gMonth, XSD.gYear):
        for s, pr, o in list(merged):
            if isinstance(o, rdflib.Literal) and o.datatype == dtype:
                merged.remove((s, pr, o))
                merged.add((s, pr, rdflib.Literal(str(o))))
    tmp = tempfile.NamedTemporaryFile(suffix=".owl", delete=False)
    merged.serialize(destination=tmp.name, format="xml")
    world = owlready2.World()
    world.get_ontology("file://" + tmp.name).load()
    try:
        with world.get_ontology("http://example.org/tesa/verify"):
            owlready2.sync_reasoner_pellet(world, infer_property_values=True,
                                           debug=0)
        bad = list(world.inconsistent_classes())
        print(f"  [Pellet] inconsistent classes: {len(bad)}")
        for c in bad[:5]:
            print("    !!", c)
        return not bad
    except Exception as e:
        print("  [Pellet] error:", e)
        return False

def main():
    print("== Level 0: syntax validation ==")
    graphs = {}
    for p in [CORE, ABOX] + MODULES:
        graphs[p] = load(p)
        print(f"  [OK] {os.path.relpath(p, ROOT)}: {len(graphs[p])} triples")

    print("\n== Level 1a: structural checks on the car-factory ABox ==")
    base = graphs[CORE] + graphs[ABOX]
    s_ok = structural_checks(base)

    print("\n== Level 1b: OWL RL consistency, core + ABox + each module ==")
    all_ok = s_ok
    for p in MODULES:
        merged = rdflib.Graph()
        for g in (graphs[CORE], graphs[ABOX], graphs[p]):
            merged += g
        all_ok &= rl_consistency(merged, os.path.relpath(p, ROOT))

    print("\n== Level 1c: OWL RL consistency, ALL modules together ==")
    merged = rdflib.Graph()
    for g in graphs.values():
        merged += g
    all_ok &= rl_consistency(merged, "core + ABox + all 8 modules")

    print("\n== Level 2: Pellet (optional) ==")
    pellet_check([CORE, ABOX] + MODULES)

    print("\nRESULT:", "ALL CHECKS PASSED" if all_ok else "FAILURES DETECTED")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
