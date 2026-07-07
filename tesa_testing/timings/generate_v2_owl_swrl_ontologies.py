import os
from owlready2 import *


def generate_owl_swrl_programmatic(num_conflicts, output_file):
    # 1. Setup a fresh world and ontology
    default_world.ontologies.clear()
    iri = "http://www.semanticweb.org/owl_swrl_comparison#"
    onto = get_ontology(iri)

    with onto:
        # 2. Define Schema Programmatically
        class Machine(Thing): pass

        class Action(Thing): pass

        class ActiveState(Thing): pass

        class StoppedState(Thing): pass

        StoppedState.comment = ["State indicating stopped operation"]
        ActiveState.comment = ["State indicating active operation"]
        AllDisjoint([ActiveState, StoppedState])

        class affectsMachine(ObjectProperty):
            domain = [Action]
            range = [Machine]

        class actionType(DataProperty):
            domain = [Action]
            range = [str]

        class priorityValue(DataProperty):
            domain = [Action]
            range = [int]

        # 3. Define SWRL Rules
        # Rules are defined as strings but parsed into the formal RDF structure
        rule1 = Imp()
        rule1.set_as_rule("""Action(?a), actionType(?a, "START"), affectsMachine(?a, ?m) -> ActiveState(?m)""")

        rule2 = Imp()
        rule2.set_as_rule("""Action(?a), actionType(?a, "STOP"), affectsMachine(?a, ?m) -> StoppedState(?m)""")

        # 4. Generate Individuals
        for i in range(1, num_conflicts + 1):
            m = Machine(f"Machine_{i}")

            # Start Action
            a_start = Action(f"StartAction_{i}")
            a_start.actionType = ["START"]
            a_start.priorityValue = [20 + i]
            a_start.affectsMachine = [m]

            # Stop Action
            a_stop = Action(f"StopAction_{i}")
            a_stop.actionType = ["STOP"]
            a_stop.priorityValue = [50 + i]
            a_stop.affectsMachine = [m]

    # 5. Save the file (This produces the cleaned RDF/XML you saw)
    onto.save(file=output_file, format="rdfxml")
    print(f"✓ Programmatically generated {output_file} with {num_conflicts} conflicts.")


# Run for your configurations
if __name__ == "__main__":
    for count in [5, 10, 20, 30, 40,50]:
        generate_owl_swrl_programmatic(count, f"v2_owl_swrl_{count}c.owl")