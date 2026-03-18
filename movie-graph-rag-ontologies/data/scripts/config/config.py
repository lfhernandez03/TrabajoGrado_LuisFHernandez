import os 
from dotenv import load_dotenv

load_dotenv()

# API KEYS - Validar variables de entorno críticas
OMDB_API_KEY = os.getenv('OMDB_API_KEY')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

if not OMDB_API_KEY:
    raise ValueError(
        "OMDB_API_KEY not configured. "
        "Please set OMDB_API_KEY environment variable in .env file. "
        "Get it from https://www.omdbapi.com/apikey.aspx"
    )

if not TMDB_API_KEY:
    raise ValueError(
        "TMDB_API_KEY not configured. "
        "Please set TMDB_API_KEY environment variable in .env file. "
        "Get it from https://www.themoviedb.org/settings/api"
    )

# URLs de APIs
OMDB_BASE_URL = "http://www.omdbapi.com/"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Configuracion de procesamiento
BATCH_SIZE = 50 # Procesar en lotes para evitar rate limiting
MAX_MOVIES = 500 # Limitar para el prototipo
RATE_LIMIT_DELAY = 0.5 # Segundos entre requests (OMDB: 45 req/min = min 1.33s, TMDB: 40 req/10s = min 0.25s) 

# Namespace de la ontologia
MOVIE_NS = "http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology"

# Mapeo de géneros MovieLens → Ontología
GENRE_MAPPING = {
    'Action': 'Action',
    'Adventure': 'Adventure',
    'Animation': 'Animation',
    'Children': 'Children',
    'Comedy': 'Comedy',
    'Crime': 'Crime',
    'Documentary': 'Documentary',
    'Drama': 'Drama',
    'Fantasy': 'Fantasy',
    'Film-Noir': 'FilmNoir',
    'Horror': 'Horror',
    'Musical': 'Musical',
    'Mystery': 'Mystery',
    'Romance': 'Romance',
    'Sci-Fi': 'SciFi',
    'Thriller': 'Thriller',
    'War': 'War',
    'Western': 'Western'
}

# 1. MAPEO DE PALABRAS CLAVE A TONOS
TONE_KEYWORDS = {
    'ComedyTone': {
        'primary': ['comedy', 'funny', 'hilarious', 'humor', 'laugh'],
        'secondary': ['witty', 'parody', 'satire', 'slapstick', 'comedic', 'amusing', 'joke', 'gag']
    },
    'DarkTone': {
        'primary': ['dark', 'noir', 'gritty', 'violent', 'brutal'],
        'secondary': ['bleak', 'cynical', 'harsh', 'disturbing', 'macabre', 'sinister', 'evil', 'twisted']
    },
    'SuspensefulTone': {
        'primary': ['suspense', 'thriller', 'tense', 'mystery', 'intrigue'],
        'secondary': ['conspiracy', 'paranoia', 'danger', 'chase', 'escape', 'pursuit', 'investigation']
    },
    'RomanticTone': {
        'primary': ['love', 'romance', 'romantic', 'passion', 'relationship'],
        'secondary': ['heartbreak', 'affair', 'dating', 'marriage', 'wedding', 'couple', 'soulmate']
    },
    'DramaticTone': {
        'primary': ['drama', 'emotional', 'intense', 'serious', 'tragic'],
        'secondary': ['conflict', 'struggle', 'family', 'personal', 'crisis', 'loss', 'redemption']
    }
}

# 2. PESOS PARA CÁLCULO DE SCORE
TONE_WEIGHTS = {
    'keyword_primary': 3,      # Palabra clave primaria en keywords
    'keyword_secondary': 2,    # Palabra clave secundaria en keywords
    'overview_primary': 2,     # Palabra clave primaria en sinopsis
    'overview_secondary': 1,   # Palabra clave secundaria en sinopsis
    'genre_match': 1.5,        # Coincidencia con género principal
    'tagline': 1               # Aparición en tagline
}

# 3. UMBRALES DE DECISIÓN
TONE_THRESHOLDS = {
    'min_score': 2,            # Score mínimo para asignar un tono
    'high_confidence': 5,      # Score para confianza alta (>80%)
    'multi_tone_threshold': 3  # Diferencia mínima para considerar tono secundario
}

# 4. MAPEO MEJORADO GÉNERO → TONO (con scores de confianza)
GENRE_TONE_MAPPING = {
    'Comedy': {'primary': 'ComedyTone', 'confidence': 0.8},
    'Horror': {'primary': 'DarkTone', 'confidence': 0.9},
    'Thriller': {'primary': 'SuspensefulTone', 'confidence': 0.85},
    'Romance': {'primary': 'RomanticTone', 'confidence': 0.8},
    'Drama': {'primary': 'DramaticTone', 'confidence': 0.7},
    'Action': {'primary': 'SuspensefulTone', 'confidence': 0.6},
    'Sci-Fi': {'primary': 'SuspensefulTone', 'confidence': 0.5},
    'Documentary': {'primary': 'DramaticTone', 'confidence': 0.7},
    'Crime': {'primary': 'DarkTone', 'confidence': 0.75},
    'Mystery': {'primary': 'SuspensefulTone', 'confidence': 0.8},
    'Film-Noir': {'primary': 'DarkTone', 'confidence': 0.95},
    'War': {'primary': 'DramaticTone', 'confidence': 0.8}
}

# 5. MAPEO DE TEMAS (para inferir narrativeElement)
THEME_KEYWORDS = {
    'Revenge': ['revenge', 'vengeance', 'retribution', 'payback'],
    'Justice': ['justice', 'law', 'order', 'trial', 'court'],
    'Survival': ['survival', 'survive', 'wilderness', 'stranded', 'apocalypse'],
    'Identity': ['identity', 'self-discovery', 'who am i', 'past', 'memory'],
    'Betrayal': ['betrayal', 'backstab', 'double-cross', 'trust', 'deception'],
    'Redemption': ['redemption', 'second chance', 'forgiveness', 'atonement'],
    'Family': ['family', 'father', 'mother', 'son', 'daughter', 'sibling'],
    'Power': ['power', 'control', 'domination', 'corruption', 'politics'],
    'Freedom': ['freedom', 'liberation', 'escape', 'oppression', 'slavery'],
    'Love': ['love', 'romance', 'relationship', 'marriage', 'couple']
}

# 6. MAPEO DE ESTRUCTURA NARRATIVA (basado en keywords y duración)
PLOT_STRUCTURE_RULES = {
    'LinearNarrative': {
        'keywords': ['journey', 'quest', 'mission', 'search', 'adventure'],
        'runtime_range': (90, 180),  # Películas tradicionales
        'genres': ['Adventure', 'Action', 'Drama']
    },
    'NonLinearNarrative': {
        'keywords': ['flashback', 'memory', 'past', 'timeline', 'fragmented', 'puzzle'],
        'runtime_range': (100, 180),
        'genres': ['Mystery', 'Thriller', 'Drama']
    },
    'EpisodicNarrative': {
        'keywords': ['anthology', 'stories', 'tales', 'vignettes', 'chapters'],
        'runtime_range': (90, 150),
        'genres': ['Comedy', 'Drama', 'Documentary']
    }
}

# 7. MAPEO DE PERÍODO HISTÓRICO (por año y keywords)
HISTORICAL_PERIOD_MAPPING = {
    'Contemporary': {
        'year_range': (2000, 2030),
        'keywords': ['modern', 'today', 'current', 'contemporary', 'now']
    },
    'Historical': {
        'year_range': (1800, 1999),
        'keywords': ['historical', 'period', 'era', 'century', 'ancient', 'medieval', 'victorian']
    },
    'Futuristic': {
        'year_range': (2030, 2200),
        'keywords': ['future', 'futuristic', 'sci-fi', 'dystopian', 'utopian', 'space', 'cyberpunk']
    }
}

# 8. CLASIFICACIÓN DE TIPOS DE PELÍCULA (por runtime y géneros)
MOVIE_TYPE_RULES = {
    'FeatureFilm': {
        'runtime_min': 40,
        'genres': ['Action', 'Drama', 'Comedy', 'Thriller', 'Romance', 'Horror', 'Sci-Fi']
    },
    'Documentary': {
        'runtime_min': 30,
        'genres': ['Documentary']
    },
    'ShortFilm': {
        'runtime_max': 40,
        'genres': ['any']
    },
    'AnimatedFilm': {
        'runtime_min': 40,
        'genres': ['Animation', 'Children']
    }
}

# 9. STOPWORDS PARA LIMPIEZA DE TEXTO (palabras a ignorar)
NLP_STOPWORDS = [
    'movie', 'film', 'story', 'tale', 'about', 'follows', 'tells',
    'based', 'inspired', 'adaptation', 'version', 'chronicles'
]

# 10. CONFIGURACIÓN DE CONFIANZA PARA MÚLTIPLES TONOS
MULTI_TONE_CONFIG = {
    'enabled': True,                    # Permitir múltiples tonos
    'max_tones': 2,                     # Máximo de tonos a asignar
    'secondary_tone_min_score': 3,      # Score mínimo para tono secundario
    'score_difference_threshold': 1.5   # Diferencia máxima entre tonos para considerarlos
}