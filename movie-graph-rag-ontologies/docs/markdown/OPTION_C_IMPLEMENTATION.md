# Option C Implementation: Best + All Values Storage

## Strategy Overview

**Option C** was chosen for bridge-ontology value storage:

```
bridge:bestCompatibleMood "nervioso"           # Fast, exact match (score 0.9)
bridge:allCompatibleMoods "nervioso|emocionado|aventurero"  # All valid options
```

Same pattern for:
- `bridge:bestCompatibleCompanion` + `bridge:allCompatibleCompanions`
- `bridge:bestCompatibleEnergyLevel` + `bridge:allCompatibleEnergyLevels`

## Advantages of Option C

1. **No Cartesian Product**: Single literal value per property prevents SPARQL row multiplication
2. **Fast Queries**: SPARQL filters use `bestCompatible*` for optimal performance
3. **Flexible Matching**: Backend can parse `allCompatible*` pipe-separated values for secondary moods
4. **Semantic Compatibility**: Supports both rigid (exact match) and flexible (semantic) recommendations
5. **Gemini-Friendly**: LLM can query best values or parse all values for post-processing

## Implementation Details

### Files Modified

#### 1. `rdf_bridge_generator.py`
- Updated `add_mood_mappings()` to store:
  - `bridge:bestCompatibleMood "nervioso"`
  - `bridge:allCompatibleMoods "nervioso|emocionado|aventurero"`
- Updated `add_companion_mappings()` with same pattern
- Updated `add_energy_mappings()` with same pattern

#### 2. `ontology_query_builder.py`
- SPARQL filters use `bridge:bestCompatibleMood ?bestMood` for queries
- Can optionally use `bridge:allCompatibleMoods` for flexible matching

## SPARQL Usage Examples

### Example 1: Fast Exact Matching (Current Implementation)
```sparql
OPTIONAL { ?movie bridge:bestCompatibleMood ?bestMood }
FILTER(!BOUND(?bestMood) || ?bestMood = "relajado")
```
**Result**: Only returns movies where best mood is exactly "relajado"

### Example 2: Flexible Matching (Post-Processing)
```sparql
OPTIONAL { ?movie bridge:allCompatibleMoods ?allMoods }
```
Then in backend, split by `|` and check if user's requested mood is in the list:
```python
moods = allMoods.split("|")  # ["nervioso", "emocionado", "aventurero"]
if "emocionado" in moods:
    # Include this movie
```

### Example 3: Combined Query
```sparql
PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>

SELECT ?movie ?title ?bestMood ?allMoods ?bestCompanion
WHERE {
  ?movie rdf:type movie:FeatureFilm ;
         movie:hasTitle ?title ;
         bridge:bestCompatibleMood ?bestMood ;
         bridge:allCompatibleMoods ?allMoods ;
         bridge:bestCompatibleCompanion ?bestCompanion .
}
LIMIT 10
```

## Query Performance Impact

### Before (Old Properties)
```sparql
?movie bridge:compatibleMood "relajado"   # Multiple rows per movie
?movie bridge:compatibleMood "feliz"      # Cartesian product! 
?movie bridge:compatibleMood "aburrido"
```
Result: 1 movie × 3 mood values = **3 rows** (inefficient)

### After (Option C)
```sparql
?movie bridge:bestCompatibleMood "relajado"    # Single row
```
Result: 1 movie = **1 row** (optimal)

For flexible matching, single query returns all moods for post-processing:
```sparql
?movie bridge:allCompatibleMoods "relajado|feliz|aburrido"  # Single row
```

## Backend Integration

### Simple Query (Current)
```python
# Use bestCompatible* for standard recommendations
sparql_query = """
  OPTIONAL { ?movie bridge:bestCompatibleMood ?bestMood }
  FILTER(?bestMood = "relajado")
"""
```

### Advanced Query (Optional Enhancement)
```python
def parse_all_compatible_moods(all_moods_string: str) -> list[str]:
    """Parse pipe-separated moods from allCompatibleMoods property."""
    return all_moods_string.split("|") if all_moods_string else []

# In recommendation engine
for movie in results:
    all_moods = parse_all_compatible_moods(movie.get("allCompatibleMoods"))
    if user_mood in all_moods:
        # Secondary match (accept this movie even if not best)
        add_to_recommendations(movie, score=0.8)
```

## Data Format Examples

For a Horror movie with genre_to_moods mapping:
```python
'Horror': ['nervioso', 'emocionado', 'aventurero']
```

Generated RDF (Turtle):
```turtle
<http://data/movie_12345_Scary_Movie> 
    bridge:bestCompatibleMood "nervioso" ;
    bridge:allCompatibleMoods "nervioso|emocionado|aventurero" ;
    bridge:moodMatchScore 0.9 ;
    bridge:bestCompatibleCompanion "amigos" ;
    bridge:allCompatibleCompanions "amigos|pareja|solo" ;
    bridge:socialMatchScore 0.9 ;
    bridge:bestCompatibleEnergyLevel "alto" ;
    bridge:allCompatibleEnergyLevels "alto|medio" ;
    bridge:energyMatchScore 0.9 ;
    bridge:compatibilityScore 0.9 .
```

## Migration from Old Properties

If old properties (`bridge:compatibleMood`, `bridge:compatibleCompanion`, `bridge:compatibleEnergyLevel`) exist in existing RDF:

1. **Option A**: Keep both and transition gradually
   ```sparql
   OPTIONAL { ?movie bridge:bestCompatibleMood ?bestMood }
   OPTIONAL { ?movie bridge:compatibleMood ?oldMood }
   BIND(COALESCE(?bestMood, ?oldMood) AS ?mood)
   ```

2. **Option B**: Replace completely (recommended)
   - Regenerate RDF with Option C implementation
   - Query builder already uses new properties

## Testing & Validation

### Test Query 1: Verify bestCompatible* Properties
```sparql
SELECT ?movie ?title ?bestMood ?bestCompanion ?bestEnergy
WHERE {
  ?movie rdf:type movie:FeatureFilm ;
         movie:hasTitle ?title ;
         bridge:bestCompatibleMood ?bestMood ;
         bridge:bestCompatibleCompanion ?bestCompanion ;
         bridge:bestCompatibleEnergyLevel ?bestEnergy .
}
LIMIT 10
```
**Expected**: Every movie has exactly ONE value for each bestCompatible* property

### Test Query 2: Verify allCompatible* Properties
```sparql
SELECT ?movie ?title (COUNT(?) as ?moodCount)
WHERE {
  ?movie rdf:type movie:FeatureFilm ;
         bridge:allCompatibleMoods ?allMoods .
}
GROUP BY ?movie ?title
LIMIT 10
```
**Expected**: Each movie has ONE allCompatibleMoods value (pipe-separated string)

### Test Query 3: Verify No Cartesian Product
```sparql
SELECT ?movie (COUNT(?movie) as ?rowCount)
WHERE {
  ?movie rdf:type movie:FeatureFilm ;
         bridge:bestCompatibleMood ?bestMood ;
         bridge:bestCompatibleCompanion ?bestCompanion ;
         bridge:bestCompatibleEnergyLevel ?bestEnergy .
}
GROUP BY ?movie
LIMIT 10
```
**Expected**: All ?rowCount values = 1 (no cartesian product!)

## Deployment Checklist

- [x] Updated `rdf_bridge_generator.py` to implement Option C
- [x] Updated `ontology_query_builder.py` to use bestCompatible* properties
- [x] Updated documentation with examples and deployment guide
- [ ] Run RDF generation pipeline with new implementation
- [ ] Verify SPARQL test queries all pass
- [ ] Spot-check 20-30 movies in Fuseki for correct property storage
- [ ] Deploy updated query builder to production
- [ ] Monitor for any query performance regressions
- [ ] Document backend enhancement for flexible moods parsing (optional)

## References

- Bridge Ontology: `movie-graph-rag-ontologies/data/ontologies/instances/bridge-ontology.ttl`
- RDF Generator: `movie-graph-rag-ontologies/data/scripts/rdf/rdf_bridge_generator.py`
- Query Builder: `movie-graph-rag-backend-fastapi/app/core/ontology_query_builder.py`
- Vocabulary Standard: `movie-graph-rag-ontologies/data/scripts/config/vocabulary_standard.py`
