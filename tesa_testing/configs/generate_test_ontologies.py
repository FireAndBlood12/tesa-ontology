#!/usr/bin/env python3
"""
Generate OWL ontology files for TESA performance testing.
Creates two test suites:
1. Fixed Conflicts (10), Variable Actions per Conflict
2. Fixed Actions (10), Variable Conflicts
"""

def generate_ontology(num_conflicts, actions_per_conflict, output_file):
    """
    Generate an OWL ontology file with the specified configuration.
    
    Args:
        num_conflicts: Number of ConflictedActions instances
        actions_per_conflict: Number of Action instances per conflict
        output_file: Output filename
    """
    
    ontology_header = """<?xml version="1.0"?>
<rdf:RDF xmlns="http://www.semanticweb.org/factory_tesa#"
     xml:base="http://www.semanticweb.org/factory_tesa"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
     xmlns:swrl="http://www.w3.org/2003/11/swrl#"
     xmlns:tesa="http://www.semanticweb.org/tesa#">

    <owl:Ontology rdf:about="http://www.semanticweb.org/factory_tesa"/>

    <swrl:Variable rdf:about="urn:swrl#a"/>

    <owl:Class rdf:about="http://www.semanticweb.org/tesa#Action"/>
    <owl:Class rdf:about="http://www.semanticweb.org/tesa#ConflictedActions"/>
    <owl:ObjectProperty rdf:about="http://www.semanticweb.org/tesa#hasAction"/>

    <owl:DatatypeProperty rdf:about="http://www.semanticweb.org/tesa#priorityValue">
        <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#integer"/>
    </owl:DatatypeProperty>

    <owl:DatatypeProperty rdf:about="http://www.semanticweb.org/tesa#executeIndicator">
        <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#boolean"/>
    </owl:DatatypeProperty>

    <swrl:Imp>
        <swrl:body rdf:parseType="Collection">
            <swrl:ClassAtom>
                <swrl:classPredicate rdf:resource="http://www.semanticweb.org/tesa#Action"/>
                <swrl:argument1 rdf:resource="urn:swrl#a"/>
            </swrl:ClassAtom>
        </swrl:body>
        <swrl:head rdf:parseType="Collection">
            <swrl:DatavaluedPropertyAtom>
                <swrl:propertyPredicate rdf:resource="http://www.semanticweb.org/tesa#executeIndicator"/>
                <swrl:argument1 rdf:resource="urn:swrl#a"/>
                <swrl:argument2 rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">true</swrl:argument2>
            </swrl:DatavaluedPropertyAtom>
        </swrl:head>
    </swrl:Imp>

"""

    ontology_footer = """</rdf:RDF>"""
    
    # Generate the action and conflict instances
    instances = []
    action_counter = 1
    
    for conflict_num in range(1, num_conflicts + 1):
        # Create actions for this conflict
        action_refs = []
        
        for action_num in range(1, actions_per_conflict + 1):
            # Alternate between different action types for variety
            action_types = ["Boost", "Maintenance", "Calibration", "Inspection", "Adjustment"]
            action_type = action_types[(action_counter - 1) % len(action_types)]
            
            # Generate semi-random but deterministic priorities
            # Ensure diversity and avoid too many ties
            priority = ((action_counter * 17) % 90) + 10  # Range: 10-99
            
            action_id = f"{action_type}_{action_counter}"
            action_refs.append(action_id)
            
            action_xml = f"""    <tesa:Action rdf:about="#{action_id}">
        <tesa:priorityValue rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">{priority}</tesa:priorityValue>
    </tesa:Action>
"""
            instances.append(action_xml)
            action_counter += 1
        
        # Create the ConflictedActions instance
        conflict_xml = f"""    <tesa:ConflictedActions rdf:about="#Conflict_{conflict_num}">
"""
        for action_ref in action_refs:
            conflict_xml += f"""        <tesa:hasAction rdf:resource="#{action_ref}"/>
"""
        conflict_xml += """    </tesa:ConflictedActions>
"""
        instances.append(conflict_xml)
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write(ontology_header)
        f.write('\n'.join(instances))
        f.write('\n' + ontology_footer)
    
    total_actions = num_conflicts * actions_per_conflict
    print(f"✓ Generated {output_file}")
    print(f"  - {num_conflicts} conflicts × {actions_per_conflict} actions = {total_actions} total actions")


def main():
    """Generate ontology files for both test suites."""
    
    print("=" * 80)
    print("TESA ONTOLOGY GENERATOR - TEST SUITES")
    print("=" * 80)
    print()
    
    # Test Suite 1: Fixed Conflicts (10), Variable Actions
    print("Test Suite 1: Fixed Conflicts (10), Variable Actions per Conflict")
    print("-" * 80)
    
    suite1_configs = [
        (10, 2, "test_10c_2a.owl"),    # Baseline
        (10, 5, "test_10c_5a.owl"),    # Small increase
        (10, 10, "test_10c_10a.owl"),  # Medium
        (10, 15, "test_10c_15a.owl"),  # Getting larger
        (10, 20, "test_10c_20a.owl"),  # Large
        (10, 30, "test_10c_30a.owl"),  # Very large
        (10, 50, "test_10c_50a.owl"),  # Extreme
    ]
    
    for conflicts, actions, filename in suite1_configs:
        generate_ontology(conflicts, actions, filename)
    
    print()
    print("Test Suite 2: Fixed Actions (10), Variable Conflicts")
    print("-" * 80)
    
    suite2_configs = [
        (5, 10, "test_5c_10a.owl"),    # Few conflicts
        (10, 10, "test_10c_10a.owl"),  # Medium (already created above)
        (15, 10, "test_15c_10a.owl"),  # More conflicts
        (25, 10, "test_25c_10a.owl"),  # Many conflicts
        (50, 10, "test_50c_10a.owl"),  # Very many conflicts
    ]
    
    # Skip 10c_10a since it was already created in Suite 1
    for conflicts, actions, filename in suite2_configs:
        if filename != "test_10c_10a.owl":
            generate_ontology(conflicts, actions, filename)
        else:
            print(f"✓ Skipping {filename} (already created)")
            print(f"  - {conflicts} conflicts × {actions} actions = {conflicts * actions} total actions")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Test Suite 1 - Fixed Conflicts (10), Variable Actions:")
    print("  test_10c_2a.owl   - 10 conflicts × 2 actions = 20 total")
    print("  test_10c_5a.owl   - 10 conflicts × 5 actions = 50 total")
    print("  test_10c_10a.owl  - 10 conflicts × 10 actions = 100 total")
    print("  test_10c_15a.owl  - 10 conflicts × 15 actions = 150 total")
    print("  test_10c_20a.owl  - 10 conflicts × 20 actions = 200 total")
    print("  test_10c_30a.owl  - 10 conflicts × 30 actions = 300 total")
    print("  test_10c_50a.owl  - 10 conflicts × 50 actions = 500 total")
    print()
    print("Test Suite 2 - Fixed Actions (10), Variable Conflicts:")
    print("  test_5c_10a.owl   - 5 conflicts × 10 actions = 50 total")
    print("  test_10c_10a.owl  - 10 conflicts × 10 actions = 100 total (shared)")
    print("  test_15c_10a.owl  - 15 conflicts × 10 actions = 150 total")
    print("  test_25c_10a.owl  - 25 conflicts × 10 actions = 250 total")
    print("  test_50c_10a.owl  - 50 conflicts × 10 actions = 500 total")
    print()
    print("Total files generated: 11 ontologies")
    print("All files ready for benchmark testing!")
    print()


if __name__ == "__main__":
    main()
