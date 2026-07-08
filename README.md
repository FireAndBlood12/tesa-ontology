# TESA — Temporal Event-driven Scheduled Actions ontology

TESA is a small OWL ontology for describing *when* things should happen in a
cyber-physical system, and what to do when two scheduled things collide. It grew
out of our work on digital twins, where we kept running into the same problem:
OWL-Time is great at describing time itself, but the moment you need "run
maintenance every Friday at 22:00, unless production has a higher-priority job in
the same window", you end up writing ad-hoc SWRL rules that eventually contradict
each other and stall the reasoner.

TESA adds exactly four constructs on top of the [W3C OWL-Time
ontology](https://www.w3.org/TR/owl-time/):

| Construct | What it does |
|---|---|
| `tesa:TimeTrigger` | a time-based directive: "at this time pattern, within this validity interval, fire these actions" |
| `tesa:Action` | the thing being scheduled; carries the `executeIndicator` / `checkedIndicator` flags the rules operate on |
| `tesa:PriorityRelator` | assigns a numeric priority to an action (a UFO-style relator between conflicting actions) |
| `tesa:ConflictedActions` | groups actions that must not run at the same time |

The trick that keeps reasoners from halting: conflicts are stored as plain ABox
data (a `ConflictedActions` group), never as logically contradictory axioms. Rules
only *mark* candidate actions; picking the winner is a separate argmax over
priorities, done by a SQWRL query or by the host application. Losing actions get
skipped, not negated, so the knowledge base stays consistent no matter how many
conflicts pile up. The paper (below) has the formal semantics and the benchmarks —
short version: baseline OWL+SWRL conflict handling degrades exponentially with
conflict count, TESA stays near-linear.


## Repository layout

```
ontology/       the TESA core itself (RDF/XML). Start here if you just want the ontology.
examples/       car-factory.ttl — the test system from the paper: a car plant with
                6 hierarchy levels, 191 individuals, 20 triggers, 30 actions and
                6 conflict groups. Useful as a template for your own domain.
alignments/     bridge modules to the foundational ontologies: BFO, UFO (via gUFO),
                SUMO, DOLCE (via DUL). Purely additive subclass axioms — nothing
                in the upper ontologies gets redefined.
integrations/   interop with other time/scheduling vocabularies: OWL-Time usage
                patterns, PSL (ISO 18629), GTO, iCalendar (RFC 5545) export.
scripts/        verify_compatibility.py — parses everything, materializes the
                OWL RL closure, then re-checks with Pellet. One command, see below.
```

## Quick start

Open `ontology/tesa-ontology.rdf` in Protégé, or load it programmatically:

```python
from rdflib import Graph
g = Graph().parse("ontology/tesa-ontology.rdf")
g.parse("examples/car-factory.ttl", format="turtle")   # add the demo dataset
```

A minimal schedule looks like this:

```turtle
ex:FridayNight a time:GeneralDateTimeDescription ;
    time:dayOfWeek time:Friday ;
    time:hour "22"^^xsd:nonNegativeInteger .

ex:Maintenance a tesa:Action ;
    tesa:hasPriorityRelator ex:PR9 ;          # priority 9 of 10
    tesa:executeIndicator "false"^^xsd:boolean .

ex:WeeklyMaintenance a tesa:TimeTrigger ;
    tesa:hasTriggerTime ex:FridayNight ;
    tesa:hasAction ex:Maintenance .
```

## Checking the compatibility claims yourself

The paper states that TESA stays consistent when combined with BFO, UFO, SUMO and
DOLCE, and interoperates with OWL-Time, PSL, GTO and iCalendar. Don't take our
word for it:

```bash
pip install -r requirements.txt
python scripts/verify_compatibility.py
```

The script validates every file, merges the core + car-factory dataset with each
alignment module (and with all of them at once), runs an OWL 2 RL consistency
check, and finishes with a Pellet run — the same reasoner configuration used in
the paper. It should end with `RESULT: ALL CHECKS PASSED`. If it doesn't on your
machine, please open an issue and attach the output.

