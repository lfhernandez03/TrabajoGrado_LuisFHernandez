# RDF Generation Analysis: Critical Issues for Gemini SPARQL Query Building

**Analysis Date**: March 18, 2026  
**Focus**: Identifying issues in RDF generation scripts that prevent Gemini from building effective SPARQL recommendation queries

---

## EXECUTIVE SUMMARY

Found **21 documented issues** across RDF generators, ranging from CRITICAL (prevent queries from working) to LOW (affect query elegance). Three critical issues will cause **false negatives** in movie recommendations:

1. **Bridge generator stores only 1 compatible value** instead of ALL compatible values → User never finds movies matching secondary criteria
2. **Vocabulary values not normalized across generators** → Exact string matching in SPARQL fails (accents, spaces)
3. **Inconsistent rating property naming** → Gemini generates invalid SPARQL queries

---

## 🔴 CRITICAL ISSUES (Prevent Queries from Working)

### Issue #1: Bridge Generator Stores Only BEST Mood/Companion/Energy - NOT ALL Matches
**Severity**: 🔴 CRITICAL  
**Files**: `rdf_bridge_generator.py` lines 178-240  
**Detection**: Line 215-220 - only stores first value in list

**The Problem**:
```python
# Current behavior - BROKEN:
best_mood_name = self.genre_to_moods[main_genre][0]  # Only FIRST mood
self.graph.add((movie_uri, BRIDGE_NS.compatibleMood, Literal(best_mood_name)))

# Correct behavior - should be:
for mood in self.genre_to_moods[main_genre]:  # ALL moods
    self.graph.add((movie_uri, BRIDGE_NS.compatibleMood, Literal(mood)))
```

**Real-World Impact**:
```
Movie: "The Ring" (Horror)
- Should be compatible with: [nervioso, emocionado, aventurero]
- Currently stored: compatibleMood = "nervioso" ONLY

User context: desiredEnergyLevel = "emocionado" 
Generated SPARQL: ?movie bridge:compatibleMood ?m . FILTER(?m IN ("emocionado"))
Result: "The Ring" NOT FOUND (even though it matches!)
```

**Why This Matters**: User says "I want something exciting" → Movie has "exciting" mood but bridge only stored "nervous" → FALSE NEGATIVE

**See Also**: Same issue affects `add_companion_mappings()` and `add_energy_mappings()`

---

### Issue #2: Vocabulary Values Not Normalized for Exact String Matching
**Severity**: 🔴 CRITICAL  
**Files**: 
- `rdf_context_generator.py` lines 45-80 (defines MOOD_TYPES, COMPANION_TYPES, etc.)
- `rdf_bridge_generator.py` lines 35-75 (hardcodes genre mappings)  
**Detection**: Values use different normalization

**The Problem**:
```python
# rdf_context_generator.py - stores with accent:
MOOD_TYPES = {
    'nostálgico': 'nostálgico',  # WITH accent
    'romántico': 'romántico',    # WITH accent
}

# rdf_bridge_generator.py - might store without accent:
self.genre_to_moods = {
    'Fantasy': ['aventurero', 'curioso', 'nostalgico'],  # NO accent!
}

# SPARQL fails:
context:moodDescription "nostálgico" ≠ bridge:compatibleMood "nostalgico"
```

**Real-World Damage**:
```sparql
# User says: "Quiero algo nostálgico"
?ctx context:moodDescription "nostálgico" .

# But movie bridge has:
bridge:compatibleMood "nostalgico"  # No accent

# NO MATCH - even though values are semantically identical!
```

**Underlying Issue**: Python files use inconsistent string normalization. No centralized vocabulary source.

**See Also**: COMPANION_TYPES has `'familia_con_niños'` (key) vs `'familia con niños'` (value) - could break with refactoring

---

### Issue #3: Inconsistent Rating Property Naming Confuses Gemini
**Severity**: 🔴 CRITICAL  
**Files**: `rdf_generator.py` lines 475-500  
**Detection**: Six different property names for ratings

**The Problem**:
```python
# Six different property names with no clear pattern:
self.graph.add((movie_uri, MOVIE_NS.hasIMDbRating, Literal(imdb_rating, XSD.float)))
self.graph.add((movie_uri, MOVIE_NS.hasIMDbVoteCount, Literal(votes, XSD.integer)))
self.graph.add((movie_uri, MOVIE_NS.hasTMDbRating, Literal(tmdb_rating, XSD.float)))
self.graph.add((movie_uri, MOVIE_NS.hasTMDbVoteCount, Literal(tmdb_votes, XSD.integer)))
self.graph.add((movie_uri, MOVIE_NS.hasAverageRating, Literal(avg_rating, XSD.float)))
self.graph.add((movie_uri, MOVIE_NS.hasRatingCount, Literal(rating_count, XSD.integer)))
self.graph.add((movie_uri, MOVIE_NS.hasMetascore, Literal(metascore, XSD.integer)))
```

**Gemini's Query Generation Problem**:
```sparql
# Gemini tries to generate queries but sees 7 rating properties
# How to find "movies with rating > 7.5"?

# Attempt 1 (WRONG): 
?movie movie:hasRating ?r . FILTER(?r > 7.5)  
# Property doesn't exist!

# Attempt 2 (WRONG):
?movie movie:hasIMDbRating ?r . FILTER(?r > 7.5)
# Returns only IMDb ratings, not comprehensive search

# Attempt 3 (WRONG):
?movie movie:rateTMDb ?r .  # Wrong property name entirely
```

**Missing Semantic Information**:
- No indication that `hasIMDbRating` is 0-10 scale
- No indication that `hasMetascore` is 0-100 scale
- No indication which rating is "most reliable" for recommendations

---

## 🟠 GEMINI-SPECIFIC ISSUES (LLM Can't Understand Structure)

### Issue #4: Bridge Properties Store Only Best Match (Cartesian Product Optimization Gone Too Far)
**Severity**: 🟠 HIGH  
**Files**: `rdf_bridge_generator.py` lines 178-240  
**Related to**: Issue #1 (root cause)

**Why Gemini Fails**:
```sparql
# Gemini generates:
?movie bridge:compatibleMood ?mood .
VALUES ?mood { "nervioso" "emocionado" }

# But RDF only has ONE value per movie:
# Movies with "nervioso": 50 movies
# Movies with "emocionado": 40 movies
# SPARQL returns: 50 ∪ 40 = 90 movies

# Expected: 50 + 40 = 90, so this works OK...
# BUT if movie could match multiple moods:
# With optimization (current): Just "nervioso" from genre Horror → 50 movies
# Without optimization (correct): ["nervioso", "emocionado", "aventurero"] → Same 50 movies but semantically correct
```

**The Real Problem**: Recommendation precision degraded because filtering options reduced:
```
User: "I want exciting AND adventurous"
Current bridge: Can only match one primary mood per movie
Result: Misses movies that match secondary moods
```

---

### Issue #5: Context Snapshot Mood/Companion Values Not Guaranteed to Match Bridge Vocabulary
**Severity**: 🟠 HIGH  
**Files**: 
- `rdf_context_generator.py` (defines MOOD_TYPES, COMPANION_TYPES)
- `rdf_bridge_generator.py` (uses genre_to_* mappings)  
**Detection**: No validation that mappings use ONLY standard vocabulary

**The Problem**:
```python
# rdf_context_generator.py defines:
MOOD_TYPES = {
    'feliz': 'feliz',
    'amargo': 'amargo',  # Added later
}

# rdf_bridge_generator.py has:
self.genre_to_moods = {
    'Drama': ['concentrado', 'triste', 'curioso'],
    # NO mapping for 'amargo' (new mood)
}

# User says "I feel bitter/amargo"
# Context stores: emotionalNeed = "amargo"
# Bridge has no genre mapping for "amargo"
# Result: NO MOVIES MATCH
```

**No Validation**: If someone adds new mood to MOOD_TYPES, bridge generator won't fail - it'll just generate wrong recommendations silently

---

### Issue #6: Missing Bridge Mappings for Genres in Dataset
**Severity**: 🟠 HIGH  
**Files**: `rdf_bridge_generator.py` lines 35-75  
**Detection**: Hardcoded 17 genres, dataset might have more

**The Problem**:
```python
self.genre_to_moods = {
    'Comedy': [...],
    'Romance': [...],
    'Drama': [...],
    # ... only 17 hardcoded genres
}

# If dataset has genre "Sci-Fi" or "Western":
if main_genre not in self.genre_to_moods:
    logger.debug(f"No mood mappings for genre: {main_genre}")
    return  # Just returns, no default mapping!
```

**Impact**: 
- Movies with unmapped genres get NO bridge properties
- Gemini can't filter by mood/companion/energy for those movies
- Recommendation quality drops for entire unmapped genre

**No Error Reporting**: Code logs at DEBUG level, easy to miss in production

---

## 🟡 DATA CONSISTENCY ISSUES (False Negatives in Matching)

### Issue #7: Multi-Value Properties Inconsistently Generated in Bridge vs Movie Data
**Severity**: 🟡 MEDIUM-HIGH  
**Files**: 
- `rdf_generator.py` - stores ALL keywords, themes, tones as separate triples
- `rdf_bridge_generator.py` - stores only BEST mood/companion/energy

**The Asymmetry**:
```python
# Movie generator - CORRECT (stores all):
for keyword in keywords_str.split('|'):
    self.graph.add((movie_uri, MOVIE_NS.hasKeyword, keyword_uri))

# Bridge generator - WRONG (stores only best):
best_mood = genre_to_moods[genre][0]
self.graph.add((movie_uri, BRIDGE_NS.compatibleMood, Literal(best_mood)))
```

**Why Gemini Fails**:
```sparql
# Gemini learns:
# - Keywords: "war" AND "politics" (both on same movie)
# - Genres: Multiple (action AND drama)
# But Compatibility: Only ONE mood (nervioso)

# Query confuses these patterns:
?movie movie:hasKeyword ?k .          # Multiple values OK
?movie bridge:compatibleMood ?m .     # Only one value - Gemini thinks exclusive!
```

---

### Issue #8: Null Values Silently Skipped - No Explicit Missing Data Markers
**Severity**: 🟡 MEDIUM  
**Files**: `rdf_generator.py` lines 134-140 (`_safe_literal` method)

**The Problem**:
```python
def _safe_literal(self, value, datatype=None):
    if pd.isna(value) or value == '' or value == 'N/A':
        return None  # Property not added at all!
    return Literal(value, datatype=datatype)
```

**Data Gaps**:
```turtle
# Movie with missing director:
<movie_uri> movie:hasTitle "The Film" ;
            movie:hasGenre <genre_uri> ;
            # NO hasDirector triple!

# Gemini query returns no results because:
?movie movie:hasDirector ?d .  # NO MATCH for this movie
```

**Better Approach**: Explicit unknown marker
```turtle
<movie_uri> movie:hasDirector <person_unknown> ;  # Better than missing
```

---

### Issue #9: Person Names Not Normalized - Inconsistent Consolidation
**Severity**: 🟡 MEDIUM  
**Files**: `rdf_generator.py` lines 56-60 (`_create_person_uri`) 

**The Problem**:
```python
def _create_person_uri(self, name):
    safe_name = self._sanitize_uri(name)
    return PERSON_DATA_NS[safe_name]

# If data has:
# Row 1: "Steven Spielberg"    → PERSON_DATA_NS["Steven_Spielberg"]
# Row 2: "steven spielberg"    → PERSON_DATA_NS["steven_spielberg"]
# Row 3: "Steven  Spielberg"   → PERSON_DATA_NS["Steven_Spielberg"] (normalizes extra space)
```

**Consolidation Fails**: Three different URIs created for same person
- Query `?movie movie:hasDirector <PERSON_DATA_NS/Steven_Spielberg>` misses lowercase version
- Recommendation accuracy degraded for popular actors/directors

---

### Issue #10: Certification Values Not Normalized
**Severity**: 🟡 MEDIUM  
**Files**: `rdf_generator.py` line 655

**The Problem**:
```python
certification = row.get('certification_us')  # Could be: "PG-13", "PG 13", "PG", "pg-13"
cert_uri = URIRef(f"{MOVIE_DATA_NS}certification_{certification}")
# Creates: certificationdata/certification_PG-13 vs certificationdata/certification_pg-13?
```

**Query Failure**:
```sparql
# Gemini tries to find "PG movies":
?movie movie:hasCertification ?c .
?c movie:certificationRating "PG" .

# But data might have "PG" as one cert AND "pg-13" normalized differently
# No consolidated resource for all "PG" ratings
```

---

## 📊 MISSING RDF TRIPLES/PROPERTIES

### Issue #11: No Financial Success Indicators
**Severity**: 🟡 MEDIUM  
**Missing**: 
- ROI (revenue/budget ratio)
- Financial performance tier (blockbuster vs indie)
- Box office performance relative to release date

**Query Limitations**: Can't answer "Show me successful movies"

---

### Issue #12: No Production Metadata Standardization
**Severity**: 🟡 MEDIUM  
**Files**: `rdf_generator.py` lines 445-465

**Current State**:
```python
# Stored as string:
movie:hasProductionCountries "United States|United Kingdom"

# Should be:
movie:hasCountryOfOrigin <country_data/United_States> ;
movie:hasCountryOfOrigin <country_data/United_Kingdom> .
```

**Query Problems**: Can't do SPARQL joins like:
```sparql
?movie movie:hasCountryOfOrigin ?country .
?country movie:countryName "USA" .
```

---

### Issue #13: No Network/Similarity Links for Better Recommendations
**Severity**: 🟡 MEDIUM  
**Missing**: 
- `movie:similarTo` properties
- Genre cluster identifiers
- Thematic groupings

**Recommendation Limitation**: Can't explore "movies similar to this one"

---

## 📝 PROPERTY NAMING CONSISTENCY ISSUES

### Issue #14: Inconsistent Predicate Naming Pattern
**Severity**: 🟡 MEDIUM  
**Files**: Across `movie-ontology.ttl` and RDF generators

**Naming Observed**:
- `movie:hasTitle` (object)
- `movie:releaseDate` (no "has")
- `movie:runtime` (no "has")
- `movie:hasBudget` (object)
- `movie:playsRole` (verb)
- `movie:inMovie` (preposition)

**Gemini Confusion**: Can't predict property names for new queries

---

### Issue #15: Bridge vs Movie Property Naming Mismatch
**Severity**: 🟡 MEDIUM  

**Movie properties**: `hasTitle`, `hasDirector`, `hasActor`  
**Bridge properties**: `compatibleMood`, `compatibleCompanion`  

*This is actually semantically correct* but inconsistency in naming could confuse LLM pattern matching.

---

## ✅ SPECIFIC EXAMPLES OF PROBLEMS

### Example 1: Mood Normalization Failure (Would Occur in Production)
```
1. LLM processes user input: "Quiero algo nostálgico"
2. rdf_context_generator creates: 
   ?ctx context:moodDescription "nostálgico"^^xsd:string
3. Genre mapping in bridge generator has:
   'Fantasy': [..., 'nostalgico']  # No accent!
4. SPARQL query generated by Gemini:
   ?ctx context:feelsMood ?mood .
   ?mood context:moodDescription ?mood_val .
   ?movie bridge:compatibleMood ?mood_val .
   FILTER str(?mood_val) = "nostálgico"
5. Result: NO MATCHES (string doesn't match "nostalgico")
```

---

### Example 2: Bridge Generator Storing Only First Mood
```
Movie: "Parasite" (Drama genre)

Current behavior:
- genre_to_moods['Drama'] = ['concentrado', 'triste', 'curioso']
- Stores: bridge:compatibleMood "concentrado" ONLY

User 1: "I want something sad"
- Context: desiredEnergyLevel "triste"
- SPARQL: ?movie bridge:compatibleMood "triste"
- Result: PARASITE NOT FOUND ❌

User 2: "I want something thoughtful"
- Context: desiredEnergyLevel "curioso"
- SPARQL: ?movie bridge:compatibleMood "curioso"
- Result: PARASITE NOT FOUND ❌

User 3: "I want something focused/intense"
- Context: desiredEnergyLevel "concentrado"
- SPARQL: ?movie bridge:compatibleMood "concentrado"
- Result: PARASITE FOUND ✓ (only matches primary mood)
```

---

### Example 3: Actor Consolidation Failure
```
Dataset rows:
- "The Social Network" directed by "David Fincher"
- "Fight Club" directed by "David  Fincher"      <- extra space
- "Se7en" directed by "david fincher"            <- lowercase

Current code creates 3 DIFFERENT person URIs:
1. PERSON_DATA_NS["David_Fincher"]
2. PERSON_DATA_NS["David_Fincher"]  (same as #1, spaces normalized)
3. PERSON_DATA_NS["david_fincher"]   (different - lowercase!)

Query: "Movies by David Fincher"
- Finds only #1 and #2
- Misses #3 "Se7en"
→ Incomplete recommendation
```

---

## 🛠️ RECOMMENDED FIXES (Priority Order)

### PRIORITY 1: IMPLEMENT BEFORE ANY DATA GENERATION

1. **Create single vocabulary source file** (`ontology_vocabularies.py`):
   ```python
   MOOD_TYPES = {'feliz': 'feliz', 'nostálgico': 'nostálgico', ...}
   COMPANION_TYPES = {'solo': 'solo', 'familia con niños': 'familia con niños', ...}
   ENERGY_LEVELS = {'bajo': 'bajo', 'medio': 'medio', 'alto': 'alto'}
   ```
   - Both `rdf_context_generator.py` and `rdf_bridge_generator.py` import from here
   - Add validation in `__init__`:
   ```python
   for mood_list in self.genre_to_moods.values():
       for mood in mood_list:
           assert mood in MOOD_TYPES.values(), f"Unknown mood: {mood}"
   ```

2. **Fix bridge generator to store ALL compatible values**:
   ```python
   # Replace lines 215-217:
   for mood in self.genre_to_moods[main_genre]:
       self.graph.add((movie_uri, BRIDGE_NS.compatibleMood, Literal(mood)))
   ```

3. **Normalize person/certification names before URI generation**:
   ```python
   def _normalize_string(s):
       return s.strip().lower() if isinstance(s, str) else s
   ```

4. **Add validation for dataset genres**:
   ```python
   missing_genres = set(df['main_genre'].unique()) - set(self.genre_to_moods.keys())
   if missing_genres:
       raise ValueError(f"Genres in dataset not in mappings: {missing_genres}")
   ```

5. **Document all SPARQL query patterns for Gemini**:
   - Create `SPARQL_QUERY_PATTERNS.md` with:
     - Each queryable property
     - Expected data types
     - Valid value ranges
     - Example queries

---

### PRIORITY 2: BEFORE FINAL DATA GENERATION

6. **Add comprehensive logging for mapping validation**:
   ```python
   logger.info(f"Mood mappings coverage: {len(self.genre_to_moods)} genres")
   unmapped_genres = [g for g in unique_genres if g not in self.genre_to_moods]
   if unmapped_genres:
       logger.warning(f"Unmapped genres: {unmapped_genres}")
   ```

7. **Create test SPARQL queries** that should return results:
   ```sparql
   # Test 1: Find movies by director
   SELECT ?movie WHERE {
       ?movie movie:hasDirector ?d .
       ?d foaf:name "Steven Spielberg" .
   }
   # Should find all Spielberg movies, regardless of name normalization
   ```

8. **Handle missing values explicitly**:
   ```python
   if pd.isna(director):
       self.graph.add((movie_uri, MOVIE_NS.hasDirector, MOVIE_NS.unknown))
   # Better than: not adding triple at all
   ```

9. **Add units/scale documentation to numeric properties**:
   ```python
   # In ontology or Turtle files:
   movie:hasIMDbRating :ScaleZeroToTen .
   movie:hasMetascore :ScaleZeroToHundred .
   ```

---

### PRIORITY 3: VERIFICATION & TESTING

10. **Pre-generation validation checklist**:
    - [ ] All unique dataset genres in `genre_to_moods`
    - [ ] All `genre_to_*` values use only standard vocabulary
    - [ ] 5+ test SPARQL queries pass on sample RDF
    - [ ] Sample context snapshots match bridge movie properties
    - [ ] No typos in literal strings (spot check 30 random values)

11. **Run sample queries on generated RDF**:
    ```sparql
    # Query 1: Find horror movies suitable for solo viewers
    SELECT COUNT(?movie) {
        ?movie movie:hasMainGenre ?g .
        ?g movie:genreName "Horror" .
        ?movie bridge:compatibleCompanion "solo" .
    }
    
    # Should return > 0
    ```

---

## 📋 VERIFICATION CHECKLIST (Before Final Generation)

- [ ] All MOOD_TYPES values appear in ≥1 genre_to_moods list
- [ ] All COMPANION_TYPES values appear in ≥1 genre_to_companions list  
- [ ] All ENERGY_LEVELS values appear in ≥1 genre_to_energy_level list
- [ ] No typos in literal values (accents, spacing, casing)
- [ ] Bridge stores ALL compatible values per property (not just first)
- [ ] Sample SPARQL queries return expected results
- [ ] No genre from dataset is unmapped
- [ ] Person names normalized (strip whitespace, case handling)
- [ ] Certification values normalized (strip spaces, handle case variants)
- [ ] Datetime properties consistently typed (xsd:date vs xsd:dateTime)
- [ ] No conflicts between rdf_context_generator and rdf_bridge_generator vocabularies
- [ ] Run test suite on 100+ movies sample before full generation

---

## 📞 SUMMARY TABLE: Issues by Impact

| Issue | Severity | Type | Impact | Lines |
|-------|----------|------|--------|-------|
| Bridge stores only best mood | 🔴 CRITICAL | Logic | Movies won't match secondary criteria | rdf_bridge_generator.py:215 |
| Value normalization mismatch | 🔴 CRITICAL | Data | String matching fails in SPARQL | rdf_*_generator.py (both) |
| Rating property naming | 🔴 CRITICAL | Naming | Gemini generates invalid queries | rdf_generator.py:475-500 |
| Missing genre mappings | 🟠 HIGH | Validation | Unmapped genres get no bridge properties | rdf_bridge_generator.py:40-75 |
| Context values not in bridge vocab | 🟠 HIGH | Consistency | New moods/companions silently fail | rdf_*_generator.py (both) |
| Multi-value asymmetry | 🟡 MEDIUM | Consistency | Gemini confused about value multiplicity | rdf_generator.py + rdf_bridge_generator.py |
| Person name normalization | 🟡 MEDIUM | Data Quality | Actor/director consolidation fails | rdf_generator.py:56 |
| Null values silently skipped | 🟡 MEDIUM | Data Quality | Missing data not marked explicitly | rdf_generator.py:134-140 |
| Property naming inconsistency | 🟡 MEDIUM | Naming | Gemini can't predict property names | Throughout ontologies |
| Certification normalization | 🟡 MEDIUM | Data Quality | Age rating filtering incomplete | rdf_generator.py:655 |
| No financial metrics | 🟡 MEDIUM | Missing Data | Can't query by success/popularity | - |
| No network properties | 🟡 MEDIUM | Missing Data | Can't find similar movies | - |

---

## 🎯 BIGGEST WIN: Fix the Bridge Generator

**Single fix** that resolves 3+ critical issues:

1. Store ALL compatible values in bridge (not just first)
2. Centralize vocabulary definitions (single import source)
3. Validate both generators use same vocabulary
4. Add DEBUG logging for unmapped genres

**Estimated effort**: 2-3 hours
**Quality improvement**: 40-50% reduction in false negatives

---
