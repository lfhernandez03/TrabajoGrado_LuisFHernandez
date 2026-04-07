from rdflib import Graph, Literal, URIRef
import pandas as pd
import logging
from urllib.parse import quote
import re
import sys
from pathlib import Path
import argparse

# Agregar el directorio de config al path para importar namespaces
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from namespaces import (
    MOVIE_NS, MOVIE_DATA_NS, PERSON_DATA_NS, GENRE_DATA_NS,
    KEYWORD_DATA_NS, COMPANY_DATA_NS, ROLE_DATA_NS, TONE_DATA_NS,
    THEME_DATA_NS, PLOT_STRUCTURE_DATA_NS, HISTORICAL_PERIOD_DATA_NS,
    COUNTRY_DATA_NS, LANGUAGE_DATA_NS, SCHEMA, DBO,
    RDF, RDFS, XSD, OWL, bind_all_namespaces
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Paths absolutos relativos a DATA
DATA_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = DATA_ROOT / "dataset" / "processed"
ONTOLOGIES_DIR = DATA_ROOT / "ontologies" / "instances"

class RDFMovieGenerator:
    """Genera tripletas RDF para películas siguiendo movie-ontology.ttl"""
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
        
    def _bind_namespaces(self):
        """Vincular namespaces al grafo usando la función centralizada"""
        bind_all_namespaces(self.graph)
    
    def _sanitize_uri(self, text):
        """Sanitiza texto para crear URIs válidas"""
        if pd.isna(text) or text == '':
            return None
        # Eliminar caracteres especiales y espacios
        text = str(text).strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s]+', '_', text)
        return quote(text)
    
    def _create_movie_uri(self, movie_id, title):
        """Crea URI única para una película"""
        safe_title = self._sanitize_uri(title)
        return MOVIE_DATA_NS[f"movie_{movie_id}_{safe_title}"]
    
    def _create_person_uri(self, name):
        """Crea URI única para una persona"""
        safe_name = self._sanitize_uri(name)
        if safe_name:
            return PERSON_DATA_NS[safe_name]
        return None
    
    def _create_genre_uri(self, genre):
        """Crea URI única para un género"""
        safe_genre = self._sanitize_uri(genre)
        if safe_genre:
            return GENRE_DATA_NS[safe_genre]
        return None
    
    def _create_keyword_uri(self, keyword):
        """Crea URI única para una keyword"""
        safe_keyword = self._sanitize_uri(keyword)
        if safe_keyword:
            return KEYWORD_DATA_NS[safe_keyword]
        return None
    
    def _create_company_uri(self, company):
        """Crea URI única para una compañía"""
        safe_company = self._sanitize_uri(company)
        if safe_company:
            return COMPANY_DATA_NS[safe_company]
        return None
    
    def _create_role_uri(self, movie_id, actor_name, character_name):
        """Crea URI única para un rol"""
        safe_actor = self._sanitize_uri(actor_name)
        safe_char = self._sanitize_uri(character_name)
        if safe_actor and safe_char:
            return ROLE_DATA_NS[f"role_{movie_id}_{safe_actor}_{safe_char}"]
        return None
    
    def _create_tone_uri(self, tone_name):
        """Crea URI única para un tono"""
        safe_tone = self._sanitize_uri(tone_name)
        if safe_tone:
            return TONE_DATA_NS[safe_tone]
        return None
    
    def _create_theme_uri(self, theme_name):
        """Crea URI única para un tema"""
        safe_theme = self._sanitize_uri(theme_name)
        if safe_theme:
            return THEME_DATA_NS[safe_theme]
        return None
    
    def _create_plot_structure_uri(self, structure_name):
        """Crea URI única para una estructura de trama"""
        safe_structure = self._sanitize_uri(structure_name)
        if safe_structure:
            return PLOT_STRUCTURE_DATA_NS[safe_structure]
        return None
    
    def _create_historical_period_uri(self, period_name):
        """Crea URI única para un período histórico"""
        safe_period = self._sanitize_uri(period_name)
        if safe_period:
            return HISTORICAL_PERIOD_DATA_NS[safe_period]
        return None
    
    def _create_country_uri(self, country_name):
        """Crea URI única para un país"""
        safe_country = self._sanitize_uri(country_name)
        if safe_country:
            return COUNTRY_DATA_NS[safe_country]
        return None
    
    def _create_language_uri(self, language_code):
        """Crea URI única para un idioma"""
        safe_language = self._sanitize_uri(language_code)
        if safe_language:
            return LANGUAGE_DATA_NS[safe_language]
        return None
    
    def _safe_literal(self, value, datatype=None):
        """Crea un Literal seguro manejando valores nulos"""
        if pd.isna(value) or value == '' or value == 'N/A':
            return None
        return Literal(value, datatype=datatype)
    
    def _get_tone_class(self, tone_name):
        """Determina la clase específica de tono basándose en el nombre"""
        tone_mapping = {
            'ComedyTone': MOVIE_NS.ComedyTone,
            'DarkTone': MOVIE_NS.DarkTone,
            'SuspensefulTone': MOVIE_NS.SuspensefulTone,
            'RomanticTone': MOVIE_NS.RomanticTone,
            'DramaticTone': MOVIE_NS.DramaticTone
        }
        return tone_mapping.get(tone_name, MOVIE_NS.Tone)
    
    def _get_plot_structure_class(self, structure_name):
        """Determina la clase específica de estructura de trama basándose en el nombre"""
        structure_mapping = {
            'LinearNarrative': MOVIE_NS.LinearNarrative,
            'NonLinearNarrative': MOVIE_NS.NonLinearNarrative,
            'EpisodicNarrative': MOVIE_NS.EpisodicNarrative
        }
        return structure_mapping.get(structure_name, MOVIE_NS.PlotStructure)
    
    def _get_historical_period_class(self, period_name):
        """Determina la clase específica de período histórico basándose en el nombre"""
        period_mapping = {
            'Contemporary': MOVIE_NS.Contemporary,
            'Historical': MOVIE_NS.Historical,
            'Futuristic': MOVIE_NS.Futuristic
        }
        return period_mapping.get(period_name, MOVIE_NS.HistoricalPeriod)
    
    def _safe_int(self, value):
        """Convierte a entero de forma segura"""
        try:
            if pd.notna(value) and value != '':
                return int(float(value))
        except:
            pass
        return None
    
    def _safe_float(self, value):
        """Convierte a float de forma segura"""
        try:
            if pd.notna(value) and value != '':
                return float(value)
        except:
            pass
        return None

    def _normalize_tmdb_image_url(self, path_or_url):
        """Normaliza poster/backdrop de TMDb a URL absoluta."""
        if pd.isna(path_or_url) or path_or_url == '' or path_or_url == 'N/A':
            return None

        value = str(path_or_url).strip()
        if value.startswith('http://') or value.startswith('https://'):
            return value
        if not value.startswith('/'):
            value = f'/{value}'
        return f'{TMDB_IMAGE_BASE_URL}{value}'
    
    def add_movie(self, row):
        """Agrega una película completa al grafo con todas sus relaciones"""
        movie_id = row['movieId']
        title = row['clean_title']
        
        # Crear URI de la película
        movie_uri = self._create_movie_uri(movie_id, title)
        
        # Determinar tipo de película según movie_type
        movie_type = row.get('movie_type', 'FeatureFilm')
        if pd.notna(movie_type) and movie_type != '':
            movie_class = MOVIE_NS[movie_type]
        else:
            movie_class = MOVIE_NS.FeatureFilm
        
        # Declarar que es una película del tipo específico
        self.graph.add((movie_uri, RDF.type, movie_class))
        
        logger.info(f"Procesando: {title} (ID: {movie_id})")
        
        # ============= PROPIEDADES BASICAS =============
        self._add_basic_properties(movie_uri, row)
        
        # ============= GANEROS =============
        self._add_genres(movie_uri, row)
        
        # ============= CREW =============
        self._add_crew(movie_uri, row)
        
        # ============= ACTORES Y ROLES =============
        self._add_actors_and_roles(movie_uri, movie_id, row)
        
        # ============= KEYWORDS =============
        self._add_keywords(movie_uri, row)
        
        # ============= COMPAAAAS DE PRODUCCIAN =============
        self._add_production_companies(movie_uri, row)
        
        # ============= ELEMENTOS NARRATIVOS =============
        self._add_narrative_elements(movie_uri, row)
        
        # ============= RATINGS =============
        self._add_ratings(movie_uri, row)
        
        # ============= CONTEXTO CULTURAL =============
        self._add_cultural_context(movie_uri, row)
        
        # ============= CERTIFICACIAN =============
        self._add_certification(movie_uri, row)
        
        return movie_uri
    
    def _add_basic_properties(self, movie_uri, row):
        """Agrega propiedades básicas de la película"""
        # Título
        if title := self._safe_literal(row.get('clean_title')):
            self.graph.add((movie_uri, MOVIE_NS.hasTitle, title))
        
        # Título original
        if original_title := self._safe_literal(row.get('original_title')):
            self.graph.add((movie_uri, MOVIE_NS.hasOriginalTitle, original_title))
        
        # Tagline
        if tagline := self._safe_literal(row.get('tagline')):
            self.graph.add((movie_uri, MOVIE_NS.hasTagline, tagline))
        
        # Plot/Overview
        if overview := self._safe_literal(row.get('overview')):
            self.graph.add((movie_uri, MOVIE_NS.hasPlotSummary, overview))
        
        # Fecha de estreno
        if release_date := self._safe_literal(row.get('release_date'), XSD.date):
            self.graph.add((movie_uri, MOVIE_NS.releaseDate, release_date))
        
        # Duración en minutos
        if runtime := self._safe_int(row.get('runtime')):
            self.graph.add((movie_uri, MOVIE_NS.runtime, Literal(runtime, datatype=XSD.integer)))
        
        # Presupuesto
        if budget := self._safe_int(row.get('budget')):
            self.graph.add((movie_uri, MOVIE_NS.hasBudget, Literal(budget, datatype=XSD.decimal)))
        
        # Taquilla
        if revenue := self._safe_int(row.get('revenue')):
            self.graph.add((movie_uri, MOVIE_NS.hasBoxOffice, Literal(revenue, datatype=XSD.decimal)))
        
        # Popularidad
        if popularity := self._safe_float(row.get('popularity')):
            self.graph.add((movie_uri, MOVIE_NS.hasPopularity, Literal(popularity, datatype=XSD.float)))
        
        # IDs externos
        if imdb_id := self._safe_literal(row.get('imdbId')):
            self.graph.add((movie_uri, MOVIE_NS.hasIMDbID, imdb_id))
        
        if tmdb_id := self._safe_literal(row.get('tmdbId')):
            self.graph.add((movie_uri, MOVIE_NS.hasTMDbID, tmdb_id))

        # Recursos visuales TMDb
        poster_url = self._normalize_tmdb_image_url(row.get('poster_path'))
        if poster_url:
            self.graph.add((movie_uri, MOVIE_NS.hasPosterUrl, Literal(poster_url)))
            self.graph.add((movie_uri, SCHEMA.image, Literal(poster_url)))

        backdrop_url = self._normalize_tmdb_image_url(row.get('backdrop_path'))
        if backdrop_url:
            self.graph.add((movie_uri, MOVIE_NS.hasBackdropUrl, Literal(backdrop_url)))
    
    def _add_genres(self, movie_uri, row):
        """Agrega géneros como instancias"""
        # Procesar géneros one-hot encoding
        genre_columns = [col for col in row.index if col.startswith('genre_')]
        
        for genre_col in genre_columns:
            if row[genre_col] == 1:
                genre_name = genre_col.replace('genre_', '')
                genre_uri = self._create_genre_uri(genre_name)
                
                if genre_uri:
                    # Crear instancia del género
                    self.graph.add((genre_uri, RDF.type, MOVIE_NS.MainGenre))
                    self.graph.add((genre_uri, MOVIE_NS.genreName, Literal(genre_name)))
                    
                    # Relacionar película con género
                    self.graph.add((movie_uri, MOVIE_NS.hasMainGenre, genre_uri))
    
    def _add_crew(self, movie_uri, row):
        """Agrega miembros del crew"""
        # Director
        if director := row.get('main_director'):
            if pd.notna(director) and director != '':
                director_uri = self._create_person_uri(director)
                if director_uri:
                    self.graph.add((director_uri, RDF.type, MOVIE_NS.Director))
                    self.graph.add((director_uri, MOVIE_NS.hasName, Literal(director)))
                    self.graph.add((movie_uri, MOVIE_NS.hasDirector, director_uri))
        
        # Producer
        if producer := row.get('main_producer'):
            if pd.notna(producer) and producer != '':
                producer_uri = self._create_person_uri(producer)
                if producer_uri:
                    self.graph.add((producer_uri, RDF.type, MOVIE_NS.Producer))
                    self.graph.add((producer_uri, MOVIE_NS.hasName, Literal(producer)))
                    self.graph.add((movie_uri, MOVIE_NS.hasProducer, producer_uri))
        
        # Writer/Screenwriter
        if writer := row.get('main_writer'):
            if pd.notna(writer) and writer != '':
                writer_uri = self._create_person_uri(writer)
                if writer_uri:
                    self.graph.add((writer_uri, RDF.type, MOVIE_NS.Screenwriter))
                    self.graph.add((writer_uri, MOVIE_NS.hasName, Literal(writer)))
                    self.graph.add((movie_uri, MOVIE_NS.hasScreenwriter, writer_uri))
        
        # Cinematographer
        if cinematographer := row.get('cinematographer'):
            if pd.notna(cinematographer) and cinematographer != '':
                cinematographer_uri = self._create_person_uri(cinematographer)
                if cinematographer_uri:
                    self.graph.add((cinematographer_uri, RDF.type, MOVIE_NS.Cinematographer))
                    self.graph.add((cinematographer_uri, MOVIE_NS.hasName, Literal(cinematographer)))
                    self.graph.add((movie_uri, MOVIE_NS.hasCinematographer, cinematographer_uri))
        
        # Composer
        if composer := row.get('composer'):
            if pd.notna(composer) and composer != '':
                composer_uri = self._create_person_uri(composer)
                if composer_uri:
                    self.graph.add((composer_uri, RDF.type, MOVIE_NS.Composer))
                    self.graph.add((composer_uri, MOVIE_NS.hasName, Literal(composer)))
                    self.graph.add((movie_uri, MOVIE_NS.hasComposer, composer_uri))
        
        # Editor
        if editor := row.get('editor'):
            if pd.notna(editor) and editor != '':
                editor_uri = self._create_person_uri(editor)
                if editor_uri:
                    self.graph.add((editor_uri, RDF.type, MOVIE_NS.Editor))
                    self.graph.add((editor_uri, MOVIE_NS.hasName, Literal(editor)))
                    self.graph.add((movie_uri, MOVIE_NS.hasEditor, editor_uri))
    
    def _add_actors_and_roles(self, movie_uri, movie_id, row):
        """Agrega actores y sus roles (lead y supporting)"""
        # Lead Actors (3)
        for i in range(1, 4):
            actor_col = f'lead_actor_{i}'
            char_col = f'lead_character_{i}'
            
            actor_name = row.get(actor_col)
            char_name = row.get(char_col)
            
            if pd.notna(actor_name) and actor_name != '':
                actor_uri = self._create_person_uri(actor_name)
                
                if actor_uri:
                    # Crear el actor
                    self.graph.add((actor_uri, RDF.type, MOVIE_NS.Actor))
                    self.graph.add((actor_uri, MOVIE_NS.hasName, Literal(actor_name)))
                    self.graph.add((movie_uri, MOVIE_NS.hasActor, actor_uri))
                    
                    # Crear el rol si hay personaje
                    if pd.notna(char_name) and char_name != '':
                        role_uri = self._create_role_uri(movie_id, actor_name, char_name)
                        
                        if role_uri:
                            self.graph.add((role_uri, RDF.type, MOVIE_NS.LeadRole))
                            self.graph.add((role_uri, MOVIE_NS.characterName, Literal(char_name)))
                            self.graph.add((role_uri, MOVIE_NS.isLeadRole, Literal(True, datatype=XSD.boolean)))
                            self.graph.add((actor_uri, MOVIE_NS.playsRole, role_uri))
                            self.graph.add((role_uri, MOVIE_NS.inMovie, movie_uri))
        
        # Supporting Actors (5)
        for i in range(1, 6):
            actor_col = f'supporting_actor_{i}'
            char_col = f'supporting_character_{i}'
            
            actor_name = row.get(actor_col)
            char_name = row.get(char_col)
            
            if pd.notna(actor_name) and actor_name != '':
                actor_uri = self._create_person_uri(actor_name)
                
                if actor_uri:
                    # Crear el actor
                    self.graph.add((actor_uri, RDF.type, MOVIE_NS.Actor))
                    self.graph.add((actor_uri, MOVIE_NS.hasName, Literal(actor_name)))
                    self.graph.add((movie_uri, MOVIE_NS.hasActor, actor_uri))
                    
                    # Crear el rol si hay personaje
                    if pd.notna(char_name) and char_name != '':
                        role_uri = self._create_role_uri(movie_id, actor_name, char_name)
                        
                        if role_uri:
                            self.graph.add((role_uri, RDF.type, MOVIE_NS.SupportingRole))
                            self.graph.add((role_uri, MOVIE_NS.characterName, Literal(char_name)))
                            self.graph.add((role_uri, MOVIE_NS.isLeadRole, Literal(False, datatype=XSD.boolean)))
                            self.graph.add((actor_uri, MOVIE_NS.playsRole, role_uri))
                            self.graph.add((role_uri, MOVIE_NS.inMovie, movie_uri))
    
    def _add_keywords(self, movie_uri, row):
        """Agrega keywords como instancias"""
        keywords_str = row.get('keywords')
        
        if pd.notna(keywords_str) and keywords_str != '':
            keywords = keywords_str.split('|')
            
            for keyword in keywords:
                keyword = keyword.strip()
                if keyword:
                    keyword_uri = self._create_keyword_uri(keyword)
                    
                    if keyword_uri:
                        self.graph.add((keyword_uri, RDF.type, MOVIE_NS.Keyword))
                        self.graph.add((keyword_uri, MOVIE_NS.keywordText, Literal(keyword)))
                        self.graph.add((movie_uri, MOVIE_NS.hasKeyword, keyword_uri))
    
    def _add_production_companies(self, movie_uri, row):
        """Agrega compañías de producción"""
        companies_str = row.get('production_companies')
        
        if pd.notna(companies_str) and companies_str != '':
            companies = companies_str.split('|')
            
            for company in companies:
                company = company.strip()
                if company:
                    company_uri = self._create_company_uri(company)
                    
                    if company_uri:
                        self.graph.add((company_uri, RDF.type, MOVIE_NS.ProductionCompany))
                        self.graph.add((company_uri, MOVIE_NS.companyName, Literal(company)))
                        self.graph.add((movie_uri, MOVIE_NS.hasProductionCompany, company_uri))
    
    def _add_narrative_elements(self, movie_uri, row):
        """Agrega elementos narrativos (tone, theme, plot_structure) como Object Properties con instancias"""
        # Tone (puede tener múltiples valores separados por |)
        tone = row.get('tone')
        if pd.notna(tone) and tone != '':
            # Procesar múltiples tonos separados por |
            tones = [t.strip() for t in str(tone).split('|') if t.strip()]
            for tone_name in tones:
                tone_uri = self._create_tone_uri(tone_name)
                if tone_uri:
                    # Determinar la clase específica de tono
                    tone_class = self._get_tone_class(tone_name)
                    
                    # Crear instancia del tono
                    self.graph.add((tone_uri, RDF.type, tone_class))
                    self.graph.add((tone_uri, MOVIE_NS.toneName, Literal(tone_name)))
                    
                    # Relacionar película con tono usando Object Property
                    self.graph.add((movie_uri, MOVIE_NS.hasTone, tone_uri))
        
        # Theme (puede ser string o múltiples separados por |)
        theme = row.get('theme')
        if pd.notna(theme) and theme != '':
            # Procesar múltiples temas separados por |
            themes = [t.strip() for t in str(theme).split('|') if t.strip()]
            for theme_name in themes:
                theme_uri = self._create_theme_uri(theme_name)
                if theme_uri:
                    # Crear instancia del tema
                    self.graph.add((theme_uri, RDF.type, MOVIE_NS.Theme))
                    self.graph.add((theme_uri, MOVIE_NS.themeName, Literal(theme_name)))
                    
                    # Relacionar película con tema usando Object Property
                    self.graph.add((movie_uri, MOVIE_NS.hasTheme, theme_uri))
        
        # Plot Structure
        plot_structure = row.get('plot_structure')
        if pd.notna(plot_structure) and plot_structure != '':
            plot_structure_uri = self._create_plot_structure_uri(plot_structure)
            if plot_structure_uri:
                # Determinar la clase específica de estructura
                plot_class = self._get_plot_structure_class(plot_structure)
                
                # Crear instancia de la estructura de trama
                self.graph.add((plot_structure_uri, RDF.type, plot_class))
                
                # Relacionar película con estructura usando Object Property
                self.graph.add((movie_uri, MOVIE_NS.hasPlotStructure, plot_structure_uri))
    
    def _add_ratings(self, movie_uri, row):
        """
        Agrega calificaciones y votos usando propiedades ESTANDARIZADAS para consistencia con Gemini queries.
        
        IMPORTANTE: Usa propiedades genéricas (hasRating, hasVoteCount) en lugar de múltiples variantes
        (hasTMDbRating, hasIMDbRating, hasAverageRating, etc) que confunden a Gemini al generar SPARQL.
        
        Strategy:
        1. Prioridad: usar hasAverageRating (MovieLens aggregate)
        2. Fallback: usar IMDb rating si no existe promedio
        3. Fallback: usar TMDb rating si no existe IMDb
        
        Resultado: Una sola propiedad 'movie:hasRating' para que Gemini sepa dónde buscar
        """
        # Determinar rating a usar (con fallback chain)
        final_rating = None
        rating_source = None
        
        if avg_rating := self._safe_float(row.get('avg_rating')):
            final_rating = avg_rating
            rating_source = 'MovieLens'
        elif imdb_rating := self._safe_float(row.get('imdb_rating')):
            final_rating = imdb_rating
            rating_source = 'IMDb'
        elif tmdb_rating := self._safe_float(row.get('tmdb_rating')):
            final_rating = tmdb_rating
            rating_source = 'TMDb'
        
        # Agregar rating único estandarizado para Gemini
        if final_rating:
            self.graph.add((movie_uri, MOVIE_NS.hasRating, 
                          Literal(final_rating, datatype=XSD.float)))
            # Comentario en log para debugging
            logger.debug(f"Movie rating: {final_rating} (source: {rating_source})")
        
        # Determinar vote count con fallback chain
        final_vote_count = None
        
        if rating_count := self._safe_int(row.get('rating_count')):
            final_vote_count = rating_count
        elif imdb_votes := row.get('imdb_votes'):
            if pd.notna(imdb_votes) and imdb_votes != '':
                imdb_votes_clean = str(imdb_votes).replace(',', '')
                if votes := self._safe_int(imdb_votes_clean):
                    final_vote_count = votes
        elif tmdb_votes := self._safe_int(row.get('tmdb_votes')):
            final_vote_count = tmdb_votes
        
        # Agregar vote count único estandarizado
        if final_vote_count:
            self.graph.add((movie_uri, MOVIE_NS.hasVoteCount, 
                          Literal(final_vote_count, datatype=XSD.integer)))
        
        # NOTA: No agregamos hasTMDbRating, hasIMDbRating, hasAverageRating, hasMetascore por separado
        # para evitar confundir a Gemini. Si se necesita información source, usar logging en lugar de RDF.
    
    
    def _add_cultural_context(self, movie_uri, row):
        """Agrega contexto cultural (países, idiomas, período histórico) usando Object Properties"""
        # Idioma original (como código ISO) - mantener como Data Property
        if original_language := row.get('original_language'):
            if pd.notna(original_language) and original_language != '':
                self.graph.add((movie_uri, MOVIE_NS.hasOriginalLanguage, 
                              Literal(original_language)))
        
        # Países de producción - crear instancias y usar Object Property
        countries_str = row.get('countries')
        if pd.notna(countries_str) and countries_str != '':
            # Mantener también la propiedad de datos para compatibilidad
            self.graph.add((movie_uri, MOVIE_NS.hasProductionCountries, 
                          Literal(countries_str)))
            
            # Crear instancias de países
            countries = [c.strip() for c in str(countries_str).split('|') if c.strip()]
            for country_name in countries:
                country_uri = self._create_country_uri(country_name)
                if country_uri:
                    # Crear instancia del país
                    self.graph.add((country_uri, RDF.type, MOVIE_NS.CountryOfOrigin))
                    self.graph.add((country_uri, MOVIE_NS.countryName, Literal(country_name)))
                    
                    # Relacionar película con país usando Object Property
                    self.graph.add((movie_uri, MOVIE_NS.hasCountryOfOrigin, country_uri))
        
        # Idiomas hablados - crear instancias y usar Object Property
        languages_str = row.get('languages')
        if pd.notna(languages_str) and languages_str != '':
            # Mantener también la propiedad de datos para compatibilidad
            self.graph.add((movie_uri, MOVIE_NS.hasSpokenLanguages, 
                          Literal(languages_str)))
            
            # Crear instancias de idiomas
            languages = [l.strip() for l in str(languages_str).split('|') if l.strip()]
            for language_code in languages:
                language_uri = self._create_language_uri(language_code)
                if language_uri:
                    # Crear instancia del idioma
                    self.graph.add((language_uri, RDF.type, MOVIE_NS.Language))
                    
                    # Relacionar película con idioma usando Object Property
                    self.graph.add((movie_uri, MOVIE_NS.hasLanguage, language_uri))
        
        # Período histórico (de inferencia NLP) - usar Object Property
        historical_period = row.get('historical_period')
        if pd.notna(historical_period) and historical_period != '':
            period_uri = self._create_historical_period_uri(historical_period)
            if period_uri:
                # Determinar la clase específica de período
                period_class = self._get_historical_period_class(historical_period)
                
                # Crear instancia del período histórico
                self.graph.add((period_uri, RDF.type, period_class))
                self.graph.add((period_uri, MOVIE_NS.periodName, Literal(historical_period)))
                
                # Relacionar película con período usando Object Property
                self.graph.add((movie_uri, MOVIE_NS.hasHistoricalPeriod, period_uri))
    
    def _add_certification(self, movie_uri, row):
        """Agrega certificación etaria"""
        certification = row.get('certification_us')
        
        if pd.notna(certification) and certification != '' and certification != 'N/A':
            # Crear instancia de certificación
            cert_uri = URIRef(f"{MOVIE_DATA_NS}certification_{certification}")
            
            self.graph.add((cert_uri, RDF.type, MOVIE_NS.Certification))
            self.graph.add((cert_uri, MOVIE_NS.certificationRating, Literal(certification)))
            self.graph.add((cert_uri, MOVIE_NS.certificationCountry, Literal("US")))
            self.graph.add((movie_uri, MOVIE_NS.hasCertification, cert_uri))
    
    def generate_from_dataframe(self, df, max_movies=None):
        """Genera tripletas RDF desde un DataFrame"""
        logger.info(f"Generando tripletas RDF para {len(df)} películas...")
        
        if max_movies:
            df = df.head(max_movies)
            logger.info(f"Procesando solo las primeras {max_movies} películas")
        
        for idx, row in df.iterrows():
            try:
                self.add_movie(row)
            except Exception as e:
                logger.error(f"Error procesando película {row.get('movieId')}: {e}")
                continue
        
        logger.info(f"Generación completada. Total de tripletas: {len(self.graph)}")
        return self.graph
    
    def save_graph(self, output_file, format='turtle'):
        """Guarda el grafo en un archivo"""
        logger.info(f"Guardando grafo en {output_file}...")
        self.graph.serialize(destination=output_file, format=format)
        logger.info(f"Grafo guardado exitosamente")

    def save_graph_incremental(self, output_file, processed_movie_ids=None, format='turtle'):
        """Hace merge incremental removiendo subgrafos previos por movieId y agregando los nuevos."""
        output_path = Path(output_file)
        if not output_path.exists() or not processed_movie_ids:
            self.save_graph(output_file, format=format)
            return

        logger.info("Modo incremental RDF movies: fusionando con TTL existente")
        existing_graph = Graph()
        existing_graph.parse(str(output_path), format=format)

        for movie_id in processed_movie_ids:
            movie_prefix = f"{MOVIE_DATA_NS}movie_{movie_id}_"
            role_prefix = f"{ROLE_DATA_NS}role_{movie_id}_"

            resources_to_remove = set()
            for subject in set(existing_graph.subjects()):
                if not isinstance(subject, URIRef):
                    continue
                subject_str = str(subject)
                if subject_str.startswith(movie_prefix) or subject_str.startswith(role_prefix):
                    resources_to_remove.add(subject)

            for resource in resources_to_remove:
                existing_graph.remove((resource, None, None))
                existing_graph.remove((None, None, resource))

        existing_graph += self.graph
        self.graph = existing_graph
        self.graph.serialize(destination=str(output_path), format=format)
        logger.info(f"Grafo incremental guardado exitosamente ({len(self.graph):,} tripletas)")
    
    def get_statistics(self):
        """Obtiene estadísticas del grafo generado"""
        stats = {
            'total_triples': len(self.graph),
            'movies': len(list(self.graph.subjects(RDF.type, MOVIE_NS.FeatureFilm))),
            'actors': len(list(self.graph.subjects(RDF.type, MOVIE_NS.Actor))),
            'directors': len(list(self.graph.subjects(RDF.type, MOVIE_NS.Director))),
            'genres': len(list(self.graph.subjects(RDF.type, MOVIE_NS.MainGenre))),
            'keywords': len(list(self.graph.subjects(RDF.type, MOVIE_NS.Keyword))),
            'companies': len(list(self.graph.subjects(RDF.type, MOVIE_NS.ProductionCompany))),
            'roles': len(list(self.graph.subjects(RDF.type, MOVIE_NS.LeadRole))) + 
                    len(list(self.graph.subjects(RDF.type, MOVIE_NS.SupportingRole)))
        }
        return stats


# Uso
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Genera tripletas RDF de películas')
    parser.add_argument('--max-movies', type=int, default=None, help='Numero maximo de peliculas a procesar')
    parser.add_argument(
        '--no-incremental',
        action='store_true',
        help='Desactiva merge incremental y sobrescribe TTL con el lote actual'
    )
    parser.add_argument(
        '--input-file',
        type=str,
        default=None,
        help='Archivo CSV de entrada (default: movies_nlp_enriched.csv si existe, else movies_enriched.csv)'
    )
    parser.add_argument('legacy_max_movies', nargs='?', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    
    # Determinar archivo de entrada con fallback logic
    if args.input_file:
        input_file = Path(args.input_file)
        if not input_file.exists():
            logger.error(f"Archivo especificado no existe: {input_file}")
            sys.exit(1)
    else:
        # Fallback: intenta movies_nlp_enriched.csv, luego movies_enriched.csv
        nlp_enriched = PROCESSED_DIR / 'movies_nlp_enriched.csv'
        enriched = PROCESSED_DIR / 'movies_enriched.csv'
        
        if nlp_enriched.exists():
            input_file = nlp_enriched
            logger.info("Usando movies_nlp_enriched.csv (NLP inference incluido)")
        elif enriched.exists():
            input_file = enriched
            logger.info("Usando movies_enriched.csv (NLP inference no disponible)")
        else:
            logger.error(f"No se encontraron archivos de entrada en {PROCESSED_DIR}")
            sys.exit(1)
    
    # Cargar datos
    logger.info(f"Cargando datos de {input_file.name}...")
    df = pd.read_csv(input_file)
    
    logger.info(f"Total de películas en el dataset: {len(df)}")
    
    # Crear generador
    generator = RDFMovieGenerator()
    
    # Determinar cuántas películas procesar
    max_movies = args.max_movies if args.max_movies is not None else args.legacy_max_movies
    if max_movies:
        logger.info(f"Procesando {max_movies} películas (especificado por argumento)")
    else:
        logger.info("Procesando TODAS las películas del dataset")
    
    # Generar tripletas
    generator.generate_from_dataframe(df, max_movies=max_movies)
    processed_df = df.head(max_movies) if max_movies else df
    processed_movie_ids = [str(movie_id) for movie_id in processed_df['movieId'].tolist()]
    
    # Guardar grafo
    output_file = ONTOLOGIES_DIR / 'movies_data.ttl'
    if args.no_incremental:
        generator.save_graph(str(output_file), format='turtle')
    else:
        generator.save_graph_incremental(
            str(output_file),
            processed_movie_ids=processed_movie_ids,
            format='turtle'
        )
    
    # Mostrar estadísticas
    stats = generator.get_statistics()
    logger.info("\n" + "="*50)
    logger.info("=== ESTADASTICAS DEL GRAFO GENERADO ===")
    logger.info("="*50)
    for key, value in stats.items():
        logger.info(f"  {key.replace('_', ' ').title()}: {value:,}")
    logger.info("="*50)
    logger.info(f"\nArchivo generado: {output_file}")
    logger.info(f"Tamaño del grafo: {len(generator.graph):,} tripletas")
