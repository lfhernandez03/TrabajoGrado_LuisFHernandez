"""
STANDARDIZED VOCABULARY FOR RDF GENERATION AND SPARQL QUERIES

This file defines the CANONICAL (normalized) values for all controlled vocabularies
used in the movie-graph-rag ontologies. ALL RDF generators and query builders
MUST use these exact values to ensure:

1. Exact string matching works in SPARQL
2. No false negatives due to normalization differences (accents, spaces, case)
3. Gemini LLM knows exactly which values are valid

Import this module in:
- rdf_context_generator.py
- rdf_bridge_generator.py
- ontology_query_builder.py
"""

# ============================================================================
# EMOTIONAL STATES (EmotionalContext.moodDescription in RDF)
# ============================================================================
# These EXACT strings are stored in RDF and must match user context queries
# NOTE: Values are stored WITHOUT accents for SPARQL compatibility (exact string matching)
# This prevents false negatives from accent/normalization differences
MOOD_VOCABULARY = {
    'feliz': 'feliz',               # happy, joyful, upbeat
    'relajado': 'relajado',         # relaxed, calm, peaceful
    'estresado': 'estresado',       # stressed, anxious, tense
    'triste': 'triste',             # sad, melancholic, sorrowful
    'ansioso': 'ansioso',           # anxious, worried, uneasy
    'emocionado': 'emocionado',     # excited, thrilled, energetic
    'aburrido': 'aburrido',         # bored, disinterested, apathetic
    'curioso': 'curioso',           # curious, inquisitive, interested
    'romantico': 'romantico',       # romantic, sentimental (NO accents - compatibility!)
    'nostalgico': 'nostalgico',     # nostalgic, wistful (NO accents - compatibility!)
    'aventurero': 'aventurero',     # adventurous, daring, bold
    'nervioso': 'nervioso',         # nervous, jittery, on-edge
    'reflexivo': 'reflexivo',       # reflective, thoughtful, introspective
    'concentrado': 'concentrado',   # focused, concentrated
    'contemplativo': 'contemplativo', # contemplative, meditative
    'social': 'social',             # social, outgoing, communicative
}

# ============================================================================
# ENERGY LEVELS (EmotionalContext.desiredEnergyLevel in RDF)
# ============================================================================
# Low: Slow pacing, quiet moments, introspection
# Medium: Normal pacing, balanced
# High: Fast pacing, action-packed, intense
ENERGY_VOCABULARY = {
    'bajo': 'bajo',                 # low energy, relaxing
    'medio': 'medio',               # medium energy, moderate
    'alto': 'alto',                 # high energy, exciting
}

# ============================================================================
# COMPANION TYPES (SocialContext.companionType in RDF)
# ============================================================================
# IMPORTANT: Use underscores INTERNALLY (Python), but store WITHOUT in RDF
# This prevents matching issues in SPARQL literal strings
COMPANION_VOCABULARY = {
    'solo': 'solo',                         # alone
    'pareja': 'pareja',                     # with partner/spouse
    'familia': 'familia',                   # with family
    'familia_con_niños': 'familia con niños',  # with family AND children
    'amigos': 'amigos',                     # with friends
    'compañeros': 'compañeros',             # with colleagues
    'grupo_grande': 'grupo grande',         # with large group
}

# ============================================================================
# GENRES (Standardized to match ontology definitions)
# ============================================================================
# These match the Genre classes in movie-ontology.ttl
GENRE_VOCABULARY = {
    'Action': 'Action',
    'Adventure': 'Adventure',
    'Animation': 'Animation',
    'Comedy': 'Comedy',
    'Crime': 'Crime',
    'Documentary': 'Documentary',
    'Drama': 'Drama',
    'Fantasy': 'Fantasy',
    'Horror': 'Horror',
    'Mystery': 'Mystery',
    'Romance': 'Romance',
    'Science Fiction': 'Science Fiction',
    'Thriller': 'Thriller',
    'War': 'War',
    'History': 'History',
    'Music': 'Music',
    'Family': 'Family',
}

# ============================================================================
# RATING/CERTIFICATION VALUES
# ============================================================================
# US Motion Picture Association (MPAA) certified ratings
CERTIFICATION_VOCABULARY = {
    'G': 'G',              # General Audiences
    'PG': 'PG',            # Parental Guidance Suggested
    'PG-13': 'PG-13',      # Parents Strongly Cautioned
    'R': 'R',              # Restricted
    'NC-17': 'NC-17',      # No One 17 and Under Admitted
}

# ============================================================================
# DAYS OF WEEK (ContextSnapshot.dayOfWeek in RDF)
# ============================================================================
DAYS_OF_WEEK_VOCABULARY = {
    'Monday': 'Monday',
    'Tuesday': 'Tuesday',
    'Wednesday': 'Wednesday',
    'Thursday': 'Thursday',
    'Friday': 'Friday',
    'Saturday': 'Saturday',
    'Sunday': 'Sunday',
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_mood(mood_input: str) -> str:
    """
    Normalize mood input to standard vocabulary value.
    
    Args:
        mood_input: Raw user input (may have typos, accents, case variations)
    
    Returns:
        Standardized mood value from MOOD_VOCABULARY
        
    Raises:
        ValueError if mood not found in vocabulary
    """
    if not mood_input:
        return None
    
    normalized = str(mood_input).strip().lower()
    
    # Try exact match first
    for standard_value in MOOD_VOCABULARY.values():
        if normalized == standard_value.lower():
            return standard_value
    
    # Try without accents (for cases like "nostalgico" vs "nostálgico")
    import unicodedata
    no_accents = ''.join(
        c for c in unicodedata.normalize('NFD', normalized)
        if unicodedata.category(c) != 'Mn'
    )
    
    for standard_value in MOOD_VOCABULARY.values():
        standard_no_accents = ''.join(
            c for c in unicodedata.normalize('NFD', standard_value.lower())
            if unicodedata.category(c) != 'Mn'
        )
        if no_accents == standard_no_accents:
            return standard_value
    
    raise ValueError(f"Unknown mood: {mood_input}. Valid values: {list(MOOD_VOCABULARY.values())}")


def normalize_energy(energy_input: str) -> str:
    """Normalize energy level to standard vocabulary."""
    if not energy_input:
        return None
    
    normalized = str(energy_input).strip().lower()
    for standard_value in ENERGY_VOCABULARY.values():
        if normalized == standard_value.lower():
            return standard_value
    
    raise ValueError(f"Unknown energy level: {energy_input}. Valid values: {list(ENERGY_VOCABULARY.values())}")


def normalize_companion(companion_input: str) -> str:
    """Normalize companion type to standard vocabulary."""
    if not companion_input:
        return None
    
    normalized = str(companion_input).strip().lower()
    
    # Handle both underscore and space variants
    for key, standard_value in COMPANION_VOCABULARY.items():
        if normalized == key.lower() or normalized == standard_value.lower():
            return standard_value
    
    raise ValueError(f"Unknown companion type: {companion_input}. Valid values: {list(COMPANION_VOCABULARY.values())}")


def normalize_genre(genre_input: str) -> str:
    """Normalize genre to standard vocabulary."""
    if not genre_input:
        return None
    
    normalized = str(genre_input).strip()
    
    for standard_value in GENRE_VOCABULARY.values():
        if normalized.lower() == standard_value.lower():
            return standard_value
    
    raise ValueError(f"Unknown genre: {genre_input}. Valid values: {list(GENRE_VOCABULARY.values())}")


# ============================================================================
# VALIDATION FOR RDF GENERATORS
# ============================================================================

def validate_all_moods_in_vocabulary(mood_list: list) -> bool:
    """
    Validate that all moods in a list are in the standard vocabulary.
    
    Args:
        mood_list: List of mood strings to validate
    
    Returns:
        True if all valid, raises ValueError otherwise
    """
    valid_moods = set(MOOD_VOCABULARY.values())
    for mood in mood_list:
        if mood not in valid_moods:
            raise ValueError(f"Mood '{mood}' not in vocabulary. Valid: {valid_moods}")
    return True


def validate_all_companions_in_vocabulary(companion_list: list) -> bool:
    """Validate that all companion types are in vocabulary."""
    valid_companions = set(COMPANION_VOCABULARY.values())
    for companion in companion_list:
        if companion not in valid_companions:
            raise ValueError(f"Companion '{companion}' not in vocabulary. Valid: {valid_companions}")
    return True


# ============================================================================
# GEMINI ASSISTANT DOCUMENTATION
# ============================================================================

GEMINI_PROPERTY_DOCUMENTATION = """
# Queryable Movie Properties for SPARQL

## Movie Data Properties
- movie:hasTitle (xsd:string) - Movie title
- movie:hasRuntime (xsd:int) - Duration in minutes
- movie:hasRating (xsd:float) - Average rating 0.0-10.0
- movie:hasReleaseDate (xsd:date) - ISO 8601 format
- movie:hasMainGenre (Genre) - Primary genre

## Bridge Ontology Compatibility Properties (for semantic matching)
- bridge:compatibleMood (xsd:string) - Best compatible mood
  Valid values: feliz, relajado, estresado, triste, ansioso, emocionado, aburrido, curioso, romántico, nostálgico, aventurero, nervioso, reflexivo, contemplativo, social

- bridge:compatibleCompanion (xsd:string) - Best compatible companion type
  Valid values: solo, pareja, familia, familia con niños, amigos, compañeros, grupo grande

- bridge:compatibleEnergyLevel (xsd:string) - Best compatible energy level
  Valid values: bajo, medio, alto

- bridge:isKidFriendly (xsd:boolean) - Appropriate for children
- bridge:compatibilityScore (xsd:float) - Overall compatibility 0.0-1.0

## User Context Properties (ContextSnapshot)
- context:feelsMood (EmotionalContext) - User's emotional state
  - context:moodDescription (xsd:string) - Mood value
  - context:desiredEnergyLevel (xsd:string) - Preferred energy
  
- context:withCompanion (SocialContext) - Company situation
  - context:companionType (xsd:string) - Who they're with
  - context:hasChildren (xsd:boolean) - Children present?

- context:hasRequirement (RequirementContext) - Constraints
  - context:availableTime (xsd:int) - Max minutes available
  - context:contentRestrictions (xsd:string) - Items to exclude
"""
