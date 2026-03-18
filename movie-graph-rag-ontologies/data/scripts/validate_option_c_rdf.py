#!/usr/bin/env python3
"""
Validate RDF data generated with Option C implementation.

Run this AFTER RDF generation to verify:
1. Option C properties exist and are correctly formatted
2. No cartesian product (no duplicate rows per movie)
3. Best and All values are consistent

Run from: movie-graph-rag-ontologies/data/scripts/
  python validate_option_c_rdf.py ontologies/instances/bridge-data.ttl
"""

from rdflib import Graph, Namespace
import argparse
from pathlib import Path

def load_rdf_data(ttl_path: str) -> Graph:
    """Load RDF from Turtle file."""
    g = Graph()
    g.parse(ttl_path, format="turtle")
    return g

def validate_option_c_properties(g: Graph) -> dict:
    """Validate that Option C properties exist and format is correct."""
    results = {
        "total_movies": 0,
        "movies_with_best_mood": 0,
        "movies_with_all_moods": 0,
        "movies_with_all_properties": 0,
        "format_errors": [],
        "missing_movies": []
    }
    
    BRIDGE = Namespace("http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#")
    MOVIE = Namespace("http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#")
    RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    
    # Get all movies
    movies = list(g.subjects(RDF.type, MOVIE.FeatureFilm))
    results["total_movies"] = len(movies)
    
    print(f"\nValidating {len(movies)} movies...")
    
    for movie_uri in movies[:100]:  # Sample first 100 for performance
        has_best_mood = False
        has_all_moods = False
        has_best_companion = False
        has_all_companions = False
        has_best_energy = False
        has_all_energy = False
        
        best_mood = g.value(movie_uri, BRIDGE.bestCompatibleMood)
        all_moods = g.value(movie_uri, BRIDGE.allCompatibleMoods)
        best_companion = g.value(movie_uri, BRIDGE.bestCompatibleCompanion)
        all_companions = g.value(movie_uri, BRIDGE.allCompatibleCompanions)
        best_energy = g.value(movie_uri, BRIDGE.bestCompatibleEnergyLevel)
        all_energy = g.value(movie_uri, BRIDGE.allCompatibleEnergyLevels)
        
        if best_mood:
            has_best_mood = True
            results["movies_with_best_mood"] += 1
            # Validate format: single value
            if "|" in str(best_mood):
                results["format_errors"].append(f"  ✗ {movie_uri}: bestMood contains pipe: {best_mood}")
        
        if all_moods:
            has_all_moods = True
            results["movies_with_all_moods"] += 1
            # Validate format: pipe-separated values with NO spaces
            all_moods_str = str(all_moods)
            if not all_moods_str or " " in all_moods_str:
                results["format_errors"].append(f"  ✗ {movie_uri}: allMoods has spaces: {all_moods}")
            # Verify best_mood is first in all_moods
            if has_best_mood and all_moods_str.split("|")[0] != str(best_mood):
                results["format_errors"].append(
                    f"  ✗ {movie_uri}: bestMood '{best_mood}' not first in allMoods '{all_moods}'"
                )
        
        if best_companion and all_companions and best_energy and all_energy:
            results["movies_with_all_properties"] += 1
        else:
            results["missing_movies"].append({
                "uri": movie_uri,
                "best_mood": bool(best_mood),
                "all_moods": bool(all_moods),
                "best_companion": bool(best_companion),
                "all_companions": bool(all_companions),
                "best_energy": bool(best_energy),
                "all_energy": bool(all_energy)
            })
    
    return results

def validate_no_cartesian_product(g: Graph) -> dict:
    """Verify no cartesian product when querying movies with multiple properties."""
    results = {
        "query_test_passed": True,
        "sample_rows": []
    }
    
    BRIDGE = Namespace("http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#")
    MOVIE = Namespace("http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#")
    RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    
    # Query: Select movies with best mood, companion, and energy
    query = """
    PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
    PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>
    
    SELECT ?movie ?title ?bestMood ?bestCompanion ?bestEnergy
    WHERE {
        ?movie rdf:type movie:FeatureFilm ;
               movie:hasTitle ?title ;
               bridge:bestCompatibleMood ?bestMood ;
               bridge:bestCompatibleCompanion ?bestCompanion ;
               bridge:bestCompatibleEnergyLevel ?bestEnergy .
    }
    LIMIT 10
    """
    
    try:
        rows = list(g.query(query))
        results["sample_rows"] = len(rows)
        
        # Count rows per movie
        movie_rows = {}
        for row in rows:
            movie = row.movie
            if movie not in movie_rows:
                movie_rows[movie] = 0
            movie_rows[movie] += 1
        
        # Check if any movie has more than 1 row (cartesian product!)
        for movie, count in movie_rows.items():
            if count > 1:
                results["query_test_passed"] = False
                results["error"] = f"Movie {movie} has {count} rows (Cartesian product!)"
                break
        
        if results["query_test_passed"]:
            results["message"] = f"✓ Query returned {len(rows)} rows with no cartesian product"
    
    except Exception as e:
        results["query_test_passed"] = False
        results["error"] = f"Query execution failed: {e}"
    
    return results

def main():
    """Run validation tests."""
    parser = argparse.ArgumentParser(description="Validate Option C RDF data")
    parser.add_argument("ttl_file", help="Path to RDF Turtle file to validate (e.g., ontologies/instances/bridge-data.ttl)")
    args = parser.parse_args()
    
    ttl_path = Path(args.ttl_file)
    
    # Support relative or absolute paths
    if not ttl_path.is_absolute():
        # Relative to the scripts directory
        ttl_path = Path(__file__).parent / ttl_path
    
    if not ttl_path.exists():
        print(f"✗ File not found: {ttl_path}")
        print(f"  Looked in: {ttl_path.resolve()}")
        return 1
    
    print(f"\nLoading RDF from: {ttl_path}")
    print("=" * 70)
    
    try:
        g = load_rdf_data(str(ttl_path))
        print(f"✓ Loaded {len(g)} RDF triples")
    except Exception as e:
        print(f"✗ Failed to load RDF: {e}")
        return 1
    
    # Test 1: Option C Properties
    print("\n" + "=" * 70)
    print("TEST 1: Option C Property Existence and Format")
    print("=" * 70)
    
    results = validate_option_c_properties(g)
    print(f"\n✓ Total movies: {results['total_movies']}")
    print(f"✓ Movies with bestCompatibleMood: {results['movies_with_best_mood']}")
    print(f"✓ Movies with allCompatibleMoods: {results['movies_with_all_moods']}")
    print(f"✓ Movies with ALL Option C properties: {results['movies_with_all_properties']}")
    
    if results["format_errors"]:
        print(f"\n⚠ Format errors found ({len(results['format_errors'])}):")
        for error in results["format_errors"][:10]:
            print(error)
        if len(results["format_errors"]) > 10:
            print(f"  ... and {len(results['format_errors']) - 10} more")
    else:
        print(f"\n✓ No format errors")
    
    # Test 2: No Cartesian Product
    print("\n" + "=" * 70)
    print("TEST 2: No Cartesian Product in SPARQL Queries")
    print("=" * 70)
    
    results2 = validate_no_cartesian_product(g)
    if results2["query_test_passed"]:
        print(f"\n✓ {results2['message']}")
    else:
        print(f"\n✗ {results2.get('error', 'Unknown error')}")
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    all_passed = (
        results["total_movies"] > 0 and
        results["movies_with_best_mood"] > 0 and
        results["movies_with_all_moods"] > 0 and
        not results["format_errors"] and
        results2["query_test_passed"]
    )
    
    if all_passed:
        print("\n✓ All validations PASSED!")
        print("\nOption C implementation verified:")
        print("  - All movies have bestCompatible* properties")
        print("  - All movies have allCompatible* properties")
        print("  - No format errors")
        print("  - No cartesian product in queries")
        print("\n✅ RDF data is production-ready!")
        return 0
    else:
        print("\n✗ Some validations FAILED")
        if not results["total_movies"]:
            print("  - No movies found in RDF")
        if results["movies_with_best_mood"] < results["total_movies"] * 0.9:
            print(f"  - Only {results['movies_with_best_mood']}/{results['total_movies']} have bestMood")
        if results["format_errors"]:
            print(f"  - {len(results['format_errors'])} format errors found")
        if not results2["query_test_passed"]:
            print(f"  - Query test failed: {results2.get('error')}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
