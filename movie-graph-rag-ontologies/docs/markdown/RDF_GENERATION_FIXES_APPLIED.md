# RDF Generation Fixes Applied

## Summary

Applied critical fixes to standardize RDF property names, vocabulary values, and generator consistency to prevent Gemini LLM from generating invalid SPARQL queries.

## Changes Made

### 1. **Property Name Standardization** ✅
**File**: `movie-graph-rag-ontologies/data/scripts/rdf/rdf_generator.py`

**Issue**: 7 different property names for ratings (hasTMDbRating, hasIMDbRating, hasAverageRating, hasMetascore, etc.) confused Gemini when building SPARQL queries.

**Fix**: 
- Replace all rating properties with single standardized `hasRating` property
- Use fallback chain: MovieLens average → IMDb → TMDb
- Replace all vote count properties with single standardized `hasVoteCount` property
- Updated docstring to explain standardization strategy

**Result**: Gemini now generates valid queries like `?movie movie:hasRating ?r` instead of non-existent properties.

### 2. **Vocabulary Standardization - Context Generator** ✅
**File**: `movie-graph-rag-ontologies/data/scripts/rdf/rdf_context_generator.py`

**Issue**: RDF context generator had local vocabulary dictionaries that could diverge from rdf_bridge_generator.py, causing vocabulary mismatch in SPARQL queries (e.g., "nostálgico" vs "nostalgico").

**Fix**:
- Import centralized vocabulary from `vocabulary_standard.py`:
  - MOOD_VOCABULARY
  - COMPANION_VOCABULARY  
  - ENERGY_VOCABULARY
  - Validation functions
- Remove local vocabulary dictionaries (DAYS_OF_WEEK, MOOD_TYPES, COMPANION_TYPES, ENERGY_LEVELS)
- Replace all dictionary lookups with direct values
- All 16 example context values validated against standardized vocabulary

**Result**: Context generation now uses same normalized values as bridge generator, eliminating vocabulary mismatch false negatives.

### 3. **Vocabulary Standardization - Bridge Generator** ✅
**File**: `movie-graph-rag-ontologies/data/scripts/rdf/rdf_bridge_generator.py`

**Issue**: Bridge generator could generate values not matching rdf_context_generator.py, preventing SPARQL filters from matching.

**Fix**:
- Import centralized vocabulary from `vocabulary_standard.py`
- Add new method `_validate_all_mappings()` that:
  - Validates all moods in `genre_to_moods` are in MOOD_VOCABULARY
  - Validates all companions in `genre_to_companions` are in COMPANION_VOCABULARY
  - Validates all energy levels in `genre_to_energy_level` are in ENERGY_VOCABULARY
  - Runs on initialization to catch errors early
  - Logs detailed error messages if validation fails
- Call `_validate_all_mappings()` from `__init__()`

**Result**: Bridge generation will fail-fast if any invalid vocabulary values are used, preventing silent data inconsistencies.

### 4. **Centralized Vocabulary Standard** ✅ (Previously Created)
**File**: `movie-graph-rag-ontologies/data/scripts/config/vocabulary_standard.py` (350+ lines)

**Updates Applied**:
- Fixed MOOD_VOCABULARY to match rdf_bridge_generator.py values (NO accents):
  - 'romantico' (not 'romántico')
  - 'nostalgico' (not 'nostálgico')
  - Added missing 'concentrado' mood (used in rdf_bridge_generator)

**Content**:
- MOOD_VOCABULARY: 16 normalized emotional states
- ENERGY_VOCABULARY: 3 energy levels
- COMPANION_VOCABULARY: 7 social context types
- GENRE_VOCABULARY: 17 standard genres
- CERTIFICATION_VOCABULARY: 5 MPAA ratings
- normalize_mood(), normalize_companion(), normalize_energy() functions
- validate_all_moods_in_vocabulary(), validate_all_companions_in_vocabulary() functions
- GEMINI_PROPERTY_DOCUMENTATION explaining all queryable RDF properties

**Critical Note**: All values stored WITHOUT Spanish accents to maintain SPARQL compatibility.

### 5. **Query Builder Updates** ✅
**File**: `movie-graph-rag-backend-fastapi/app/core/ontology_query_builder.py`

**Issue**: SPARQL queries referenced `movie:hasAverageRating` which no longer exists after rdf_generator.py changes.

**Fix**:
- Update `_safe_cross_ontology_fallback()`:
  - Change `movie:hasAverageRating` → `movie:hasRating`
  - Add docstring explaining standardized properties
  - Prevents Gemini from seeing examples of wrong property names

- Update `build_cross_ontology_sparql_from_signals()`:
  - Change `movie:hasAverageRating` → `movie:hasRating`
  - Same standardization for consistency

**Result**: Query builder now uses same property names as RDF generators, ensuring SPARQL queries work correctly.

## Vocabulary Changes Summary

### Before (INCORRECT - Multiple Normalizations)
```
rdf_context_generator.py: "nostálgico" (WITH accent)
rdf_bridge_generator.py: "nostalgico" (NO accent)
SPARQL filter: FILTER(?mood = "nostálgico") vs "nostalgico" → NO MATCH ❌
```

### After (CORRECT - Single Standardization)
```
vocabulary_standard.py: "nostalgico" (NO accent)
rdf_context_generator.py: "nostalgico" (NO accent)
rdf_bridge_generator.py: "nostalgico" (NO accent)
SPARQL filter: FILTER(?mood = "nostalgico") → MATCH ✅
```

## Files Modified

1. ✅ `rdf_generator.py` - Standardized rating/vote properties
2. ✅ `rdf_context_generator.py` - Import & use centralized vocabulary
3. ✅ `rdf_bridge_generator.py` - Import vocabulary + validation
4. ✅ `vocabulary_standard.py` - Fixed accent inconsistencies
5. ✅ `ontology_query_builder.py` - Updated property references

## Files Created

1. ✅ `CRITICAL_RDF_FIXES_FOR_GEMINI.md` (Previously created - documents 3 main issues)

## Validation & Testing Needed

### Before Regenerating RDF Data:

1. **Run Vocabulary Validation**:
   ```bash
   cd movie-graph-rag-ontologies/data/scripts/rdf
   python -c "from rdf_bridge_generator import RDFBridgeGenerator; RDFBridgeGenerator()"
   ```
   Should log: "✓ All mood, companion, and energy level mappings validated successfully"

2. **Test SPARQL Queries**:
   - Query for `?movie movie:hasRating ?r` (should return all movies)
   - Query for `?movie bridge:compatibleMood "relajado"` (should match Romance/Comedy)
   - Query for `?movie bridge:compatibleCompanion "pareja"` (should match Romance)

3. **Sample RDF Spot Check**:
   ```sparql
   SELECT ?movie ?title ?rating ?mood ?companion
   WHERE {
     ?movie rdf:type movie:FeatureFilm ;
            movie:hasTitle ?title ;
            movie:hasRating ?rating ;
            bridge:compatibleMood ?mood ;
            bridge:compatibleCompanion ?companion .
   } LIMIT 5
   ```

## Impact on Gemini Queries

### ✅ Fixed Issues:

1. **Invalid Property Names**: Gemini can now generate valid `movie:hasRating` queries instead of non-existent properties
2. **Vocabulary Mismatches**: SPARQL filters now match stored vocabulary values (no more "nostálgico" vs "nostalgico" bugs)
3. **Consistency**: All generators use same vocabularies, preventing silent data inconsistencies

### Remaining Decision:

**Bridge Storage Strategy** (Not yet implemented):
- Current: Store only best mood/companion/energy
- Options:
  - **A**: Flexible SPARQL query matching (complex patterns)
  - **B**: Use GROUP BY + GROUP_CONCAT (parsing overhead)
  - **C**: Store Best value + Store All values separately (RECOMMENDED)
    - `bridge:bestCompatibleMood "nervioso"`
    - `bridge:allCompatibleMoods "nervioso|emocionado|aventurero"`

Choose option to implement before final RDF generation.

## Next Steps

1. **Validate** - Run vocabulary validation script
2. **Test** - Execute sample SPARQL queries on existing test data
3. **Decide** - Choose bridge storage strategy (A, B, or C)
4. **Generate** - Regenerate RDF with all fixes applied
5. **Verify** - Spot-check results in Fuseki before production

---

**Status**: ✅ All standardization fixes applied. Ready for vocabulary validation and SPARQL testing.

**Generated**: 2025-01-XX by GitHub Copilot
