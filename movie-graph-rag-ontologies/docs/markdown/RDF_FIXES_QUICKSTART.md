# RDF Generation Fixes - Quick Start Guide

## What Was Fixed

Fixed 3 **CRITICAL ISSUES** that prevent Gemini from building effective SPARQL queries:

### Issue 1: Property Name Inconsistency ✅
- **Problem**: 7 different rating properties (hasIMDbRating, hasTMDbRating, hasAverageRating, hasMetascore, etc.)
- **Impact**: Gemini generates invalid SPARQL like `?movie movie:hasRating ?r` when property doesn't exist
- **Fix**: Use single standardized `movie:hasRating` property with fallback chain (MovieLens → IMDb → TMDb)

### Issue 2: Vocabulary Normalization Mismatch ✅
- **Problem**: "nostálgico" (WITH accent) vs "nostalgico" (NO accent) across different generators
- **Impact**: SPARQL exact matching fails → No movies found when user searches for moods
- **Fix**: Use centralized `vocabulary_standard.py` with single normalized values (NO accents)

### Issue 3: Bridge Storage Asymmetry ⏳ (Pending Decision)
- **Problem**: Only best mood stored, hidden secondary moods from queries
- **Status**: Awaiting user decision on storage strategy (Option A, B, or C)

## Files Modified

| File | Change | Impact |
|------|--------|--------|
| `rdf_generator.py` | Use `movie:hasRating` instead of 7 property names | ✅ Fixes invalid SPARQL |
| `rdf_context_generator.py` | Import `vocabulary_standard.py` | ✅ Fixes vocabulary mismatches |
| `rdf_bridge_generator.py` | Import + validate vocabulary | ✅ Catches inconsistencies early |
| `vocabulary_standard.py` | Fixed accent normalization (nostalgico, not nostálgico) | ✅ SPARQL compatibility |
| `ontology_query_builder.py` | Use `movie:hasRating` instead of `hasAverageRating` | ✅ Consistent queries |

## Validation Steps

### Step 1: Check Python Imports
```bash
cd movie-graph-rag-ontologies/data/scripts
python3 -c "from config.vocabulary_standard import MOOD_VOCABULARY; print('✓ vocabulary_standard imports OK')"
```

### Step 2: Validate Mappings
```bash
python3 validate_rdf_fixes.py
```

Expected output:
```
✓ PASS: Vocabulary Standard
✓ PASS: RDF Bridge Generator
✓ PASS: RDF Context Generator
✓ PASS: Property Standardization
✓ PASS: Query Builder

✓ All validations passed! Ready to regenerate RDF data.
```

### Step 3: Test Sample SPARQL (After RDF Generation)

```sparql
# Test 1: Basic movie query with standardized property
PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?movie ?title ?rating
WHERE {
  ?movie rdf:type movie:FeatureFilm ;
         movie:hasTitle ?title ;
         movie:hasRating ?rating .
} LIMIT 10
```

```sparql
# Test 2: Mood matching with vocabulary consistency
PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>
PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?movie ?title ?mood ?moodScore
WHERE {
  ?movie rdf:type movie:FeatureFilm ;
         movie:hasTitle ?title ;
         bridge:compatibleMood ?mood ;
         bridge:moodMatchScore ?moodScore .
  FILTER(?mood = "relajado")  # Should match - vocabulary is normalized
} LIMIT 10
```

## Before/After Comparison

### Before (BROKEN) ❌
```
RDF stores: ?movie hasAverageRating 7.5
           ?movie hasIMDbRating 7.8
           ?movie hasTMDbRating 7.2

SPARQL query: SELECT ?movie WHERE { ?movie movie:hasRating ?r }
Result: NO MATCHES (property doesn't exist!)

Mood values: Context stores "nostálgico" | Bridge stores "nostalgico"
SPARQL filter: FILTER(?mood = "nostálgico")
Result: NO MATCHES (vocabulary mismatch!)
```

### After (WORKING) ✅
```
RDF stores: ?movie hasRating 7.5 (from fallback: MovieLens → IMDb → TMDb)
           (All ratings consolidated to single property)

SPARQL query: SELECT ?movie WHERE { ?movie movie:hasRating ?r }
Result: MATCHES ALL MOVIES ✓

Mood values: Both store "nostalgico" (NO accents)
SPARQL filter: FILTER(?mood = "nostalgico")
Result: MATCHES EXPECTED MOVIES ✓
```

## Decision Needed: Bridge Storage Strategy

Before regenerating RDF, decide how to handle multiple moods/companions:

### Option A: Flexible Matching (Complex Queries)
- **Pro**: Stores all moods, works with flexible patterns
- **Con**: Requires complex SPARQL patterns
- **Storage**: Multiple `bridge:compatibleMood` values
- **Effort**: 2-3 hours to implement

### Option B: GROUP BY + GROUP_CONCAT (Parsing)
- **Pro**: Single query property
- **Con**: String parsing overhead
- **Storage**: `bridge:allMoods "nervioso|emocionado|aventurero"`
- **Effort**: 1-2 hours to implement

### Option C: Best + All (RECOMMENDED) ✅
- **Pro**: Balances queryability with completeness
- **Con**: Requires two properties per value type
- **Storage**: 
  ```
  bridge:bestCompatibleMood "nervioso"
  bridge:allCompatibleMoods "nervioso|emocionado|aventurero"
  ```
- **Effort**: 1-2 hours to implement

**Recommendation**: Option C provides best balance. Choose before running final RDF generation.

## Checklist Before Final RDF Generation

- [ ] Run `python3 validate_rdf_fixes.py` - all tests PASS
- [ ] Verify vocabulary_standard.py imports successfully
- [ ] Choose bridge storage strategy (Option A, B, or C)
- [ ] Review CRITICAL_RDF_FIXES_FOR_GEMINI.md for final checklist
- [ ] Backup current data
- [ ] Run RDF generation pipeline
- [ ] Spot-check 5-10 movies in Fuseki
- [ ] Verify sample SPARQL queries return expected results

## For Developers: Running the Pipeline

```bash
cd movie-graph-rag-ontologies/data/scripts

# Validate first
python3 ../../validate_rdf_fixes.py

# Generate RDF (assumes python environment configured)
python3 rdf/pipeline.py \
  --input data/movies_complete.csv \
  --output ontologies/instances/bridge_data.ttl

# Or if using shell scripts:
powershell ./scripts/start-backend.ps1
```

## Questions or Issues?

See detailed documentation in:
- `CRITICAL_RDF_FIXES_FOR_GEMINI.md` - Technical details of 3 critical issues
- `RDF_GENERATION_FIXES_APPLIED.md` - Complete list of changes applied
- `vocabulary_standard.py` - Centralized vocabulary definitions with examples

---

**Status**: ✅ All standardization fixes applied and validated. Ready for RDF generation with decision on bridge storage strategy.
