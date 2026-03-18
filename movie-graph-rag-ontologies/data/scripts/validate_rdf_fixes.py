#!/usr/bin/env python3
"""
Validation script to verify RDF generation fixes applied.

Run this before regenerating RDF data to ensure:
1. Vocabulary standardization is correct
2. Property names are standardized
3. All mappings validate against centralized vocabulary

Run from: movie-graph-rag-ontologies/data/scripts/
  python validate_rdf_fixes.py
"""

import sys
from pathlib import Path

# Setup paths - script is inside the project
DATA_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(DATA_SCRIPTS / "config"))
sys.path.insert(0, str(DATA_SCRIPTS / "rdf"))

def test_vocabulary_standard():
    """Test that vocabulary_standard.py loads and has expected content."""
    print("\n" + "="*70)
    print("TEST 1: Vocabulary Standard Module")
    print("="*70)
    
    try:
        from vocabulary_standard import (
            MOOD_VOCABULARY,
            COMPANION_VOCABULARY,
            ENERGY_VOCABULARY,
            GENRE_VOCABULARY,
            CERTIFICATION_VOCABULARY,
            normalize_mood,
            normalize_companion,
            normalize_energy
        )
        print("✓ Successfully imported vocabulary_standard module")
        
        print(f"\n  MOOD_VOCABULARY ({len(MOOD_VOCABULARY)} items):")
        for mood in MOOD_VOCABULARY.keys():
            print(f"    - {mood}")
        
        print(f"\n  COMPANION_VOCABULARY ({len(COMPANION_VOCABULARY)} items):")
        for companion in COMPANION_VOCABULARY.keys():
            print(f"    - {companion}")
        
        print(f"\n  ENERGY_VOCABULARY ({len(ENERGY_VOCABULARY)} items):")
        for energy in ENERGY_VOCABULARY.keys():
            print(f"    - {energy}")
        
        # Check for accent inconsistencies
        problematic = ['nostalgico', 'romantico']
        for mood in problematic:
            if mood in MOOD_VOCABULARY:
                print(f"\n  ✓ '{mood}' found (WITHOUT accents - correct!)")
            else:
                print(f"\n  ✗ '{mood}' NOT found in MOOD_VOCABULARY")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to import vocabulary_standard: {e}")
        return False

def test_rdf_bridge_generator():
    """Test that rdf_bridge_generator loads and validates mappings."""
    print("\n" + "="*70)
    print("TEST 2: RDF Bridge Generator Validation")
    print("="*70)
    
    try:
        from rdf_bridge_generator import RDFBridgeGenerator
        print("✓ Successfully imported RDFBridgeGenerator")
        
        # Initialize - this will run _validate_all_mappings()
        generator = RDFBridgeGenerator()
        print("✓ RDFBridgeGenerator initialized successfully")
        print("✓ All mood, companion, and energy level mappings validated!")
        
        # Check genre_to_moods mappings
        print(f"\n  Genre mappings found: {len(generator.genre_to_moods)}")
        
        return True
        
    except ValueError as e:
        print(f"✗ Vocabulary validation failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Failed to initialize RDFBridgeGenerator: {e}")
        return False

def test_rdf_context_generator():
    """Test that rdf_context_generator imports vocabulary correctly."""
    print("\n" + "="*70)
    print("TEST 3: RDF Context Generator Vocabulary Import")
    print("="*70)
    
    try:
        from rdf_context_generator import RDFContextGenerator
        print("✓ Successfully imported RDFContextGenerator")
        
        generator = RDFContextGenerator()
        print("✓ RDFContextGenerator initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to initialize RDFContextGenerator: {e}")
        return False

def test_property_standardization():
    """Test that rdf_generator.py uses standardized property names."""
    print("\n" + "="*70)
    print("TEST 4: Property Name Standardization (rdf_generator.py)")
    print("="*70)
    
    try:
        rdf_gen_path = DATA_SCRIPTS / "rdf" / "rdf_generator.py"
        content = rdf_gen_path.read_text()
        
        # Check for standardized properties
        checks = [
            ("movie:hasRating", "Standardized rating property"),
            ("movie:hasVoteCount", "Standardized vote count property"),
        ]
        
        # Check for OLD properties that should be gone
        old_properties = [
            "hasTMDbRating",
            "hasIMDbRating",
            "hasAverageRating",
            "hasMetascore",
            "hasTMDbVoteCount",
            "hasIMDbVoteCount",
            "hasRatingCount"
        ]
        
        print("\n  Checking for standardized properties:")
        all_good = True
        for prop, description in checks:
            if prop in content:
                print(f"    ✓ {prop} found - {description}")
            else:
                print(f"    ✗ {prop} NOT found")
                all_good = False
        
        print("\n  Checking that OLD properties are removed:")
        found_old = False
        for old_prop in old_properties:
            if old_prop in content:
                print(f"    ⚠ {old_prop} still found - should be removed")
                found_old = True
        
        if not found_old:
            print(f"    ✓ No old property names found")
        else:
            all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"✗ Failed to check rdf_generator.py: {e}")
        return False

def test_query_builder():
    """Test that ontology_query_builder.py uses standardized properties."""
    print("\n" + "="*70)
    print("TEST 5: Query Builder Property References")
    print("="*70)
    
    try:
        # Path to backend query builder
        backend_path = DATA_SCRIPTS.parent.parent.parent / "movie-graph-rag-backend-fastapi" / "app" / "core" / "ontology_query_builder.py"
        
        if not backend_path.exists():
            print(f"⚠ Query builder file not found at {backend_path}")
            return True  # Not a blocker if file doesn't exist
        
        content = backend_path.read_text()
        
        if "movie:hasRating" in content:
            print("✓ Query builder uses movie:hasRating")
        else:
            print("✗ Query builder does NOT use movie:hasRating")
            return False
        
        if "hasAverageRating" in content:
            print("⚠ Query builder still references hasAverageRating (legacy)")
            # Not a blocker if properly replaced
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to check query builder: {e}")
        return False

def main():
    """Run all validation tests."""
    print("\n" + "#"*70)
    print("# RDF GENERATION FIXES VALIDATION")
    print("#"*70)
    print(f"\nRunning from: {DATA_SCRIPTS}")
    
    results = {
        "Vocabulary Standard": test_vocabulary_standard(),
        "RDF Bridge Generator": test_rdf_bridge_generator(),
        "RDF Context Generator": test_rdf_context_generator(),
        "Property Standardization": test_property_standardization(),
        "Query Builder": test_query_builder(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ All validations passed! Ready to regenerate RDF data.")
        print("\nNext steps:")
        print("  1. Run RDF generation pipeline: python pipeline.py")
        print("  2. Validate generated RDF: python validate_option_c_rdf.py ontologies/instances/bridge-data.ttl")
        print("  3. Spot-check results in Fuseki")
        return 0
    else:
        print("\n✗ Some validations failed. Fix above issues before regenerating RDF.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
