import requests
import time
import logging
import sys
from pathlib import Path

# Ensure scripts directory is on sys.path so imports work when running the script directly
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

DATA_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = DATA_ROOT / "data" / "processed"

from config.config import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MovieEnricher:
    """Enriquece datos de peliculas con APIs externas (TMDB)"""

    def __init__(self):
        self.tmdb_key = TMDB_API_KEY
        self.omdb_key = OMDB_API_KEY
        
    def fetch_omdb_data(self, imdb_id):
        """Obtiene datos de OMDb API"""
        if pd.isna(imdb_id) or imdb_id == '':
            return None
        
        try:
            # El imdb_id ya viene con formato 'tt0114709' desde data_loader
            imdb_id_str = str(imdb_id)
            
            # Si no tiene el prefijo 'tt', agregarlo
            if not imdb_id_str.startswith('tt'):
                imdb_id_str = f"tt{imdb_id_str.zfill(7)}"
            
            logger.info(f"Consultando OMDb para IMDb ID: {imdb_id_str}")

            url = f"{OMDB_BASE_URL}?i={imdb_id_str}&apikey={self.omdb_key}&plot=full"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Respuesta OMDb: {data.get('Response', 'False')}")

                if data.get('Response') == 'True':
                    return {
                        'plot': data.get('Plot', ''),
                        'awards': data.get('Awards', ''),
                        'rated': data.get('Rated', ''),
                        'rating': data.get('Ratings', ''),
                        'imdb_rating': data.get('imdbRating', ''),
                        'imdb_votes': data.get('imdbVotes', ''),
                        'metascore': data.get('Metascore', '')
                    }
                else:
                    logger.warning(f"OMDb error: {data.get('Error', 'Unknown error')}")
            
            time.sleep(RATE_LIMIT_DELAY)
            return None
            
        except Exception as e:
            logger.error(f"Error fetching OMDb data for {imdb_id}: {e}")
            return None


    def fetch_tmdb_data(self, tmdb_id):
        """Obtiene datos completos de TMDb API"""
        if pd.isna(tmdb_id):
            return None
        
        try:
            tmdb_id = int(tmdb_id)
            
            # Detalles de la película
            movie_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}?api_key={self.tmdb_key}&language=es-ES"
            movie_response = requests.get(movie_url, timeout=10)
            
            # Credits (cast y crew)
            credits_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits?api_key={self.tmdb_key}"
            credits_response = requests.get(credits_url, timeout=10)
            
            # Keywords
            keywords_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/keywords?api_key={self.tmdb_key}"
            keywords_response = requests.get(keywords_url, timeout=10)

            # Certificacion etaria
            release_dates_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/release_dates?api_key={self.tmdb_key}"
            release_dates_response = requests.get(release_dates_url, timeout=10)
            
            result = {}
            
            # Datos principales de la película
            if movie_response.status_code == 200:
                movie_data = movie_response.json()
                result['budget'] = movie_data.get('budget', 0)
                result['tagline'] = movie_data.get('tagline', '')
                result['adult'] = movie_data.get('adult', False)
                result['overview'] = movie_data.get('overview', '')
                result['revenue'] = movie_data.get('revenue', 0)
                result['runtime'] = movie_data.get('runtime', 0)
                result['tmdb_rating'] = movie_data.get('vote_average', 0)
                result['tmdb_votes'] = movie_data.get('vote_count', 0)
                result['popularity'] = movie_data.get('popularity', 0)
                result['release_date'] = movie_data.get('release_date', '')
                result['original_language'] = movie_data.get('original_language', '')
                result['original_title'] = movie_data.get('original_title', '')
                result['poster_path'] = movie_data.get('poster_path', '')
                result['backdrop_path'] = movie_data.get('backdrop_path', '')
                
                # Países de producción
                countries = movie_data.get('production_countries', [])
                result['countries'] = '|'.join([c.get('name', '') for c in countries])
                
                # Idiomas hablados
                languages = movie_data.get('spoken_languages', [])
                result['languages'] = '|'.join([l.get('name', '') for l in languages])

                # Companias de produccion
                companies = movie_data.get('production_companies', [])
                result['production_companies'] = '|'.join([c.get('name', '') for c in companies])
            
            # Certificación etaria
            if release_dates_response.status_code == 200:
                release_data = release_dates_response.json()
                certifications = self._extract_certifications(release_data)
                result['certification_us'] = certifications.get('US', '')

            # Credits
            if credits_response.status_code == 200:
                credits = credits_response.json()
                crew = credits.get('crew', [])
                cast = credits.get('cast', [])
                
                # Extraer roles específicos del crew
                result['director'] = self._extract_crew_members(crew, 'Director')
                result['writer'] = self._extract_crew_members(crew, 'Screenplay')
                result['cinematographer'] = self._extract_crew_member(crew, 'Director of Photography')
                result['composer'] = self._extract_crew_member(crew, 'Original Music Composer')
                result['editor'] = self._extract_crew_member(crew, 'Editor')
                result['producer'] = self._extract_crew_members(crew, 'Producer')
                
                # Clasificar actores por rol según la ontología
                lead_actors = []
                supporting_actors = []
                lead_characters = []
                supporting_characters = []
                
                for actor in cast[:15]:  # Top 15 actores
                    actor_order = actor.get('order', 999)
                    actor_name = actor.get('name', '')
                    character_name = actor.get('character', '')
                    
                    # LeadRole: primeros 3 actores (order 0-2)
                    if actor_order < 3:
                        lead_actors.append(actor_name)
                        lead_characters.append(character_name)
                    # SupportingRole: actores 4-15 (order 3-14)
                    elif actor_order < 15:
                        supporting_actors.append(actor_name)
                        supporting_characters.append(character_name)
                
                # Guardar clasificación según ontología
                result['lead_actors'] = '|'.join(lead_actors)
                result['lead_characters'] = '|'.join(lead_characters)
                result['supporting_actors'] = '|'.join(supporting_actors)
                result['supporting_characters'] = '|'.join(supporting_characters)
                
                # Mantener campo general para compatibilidad
                result['actors'] = '|'.join([actor.get('name', '') for actor in cast[:15]])
                result['characters'] = '|'.join([actor.get('character', '') for actor in cast[:15]])
            
            # Keywords
            if keywords_response.status_code == 200:
                keywords_data = keywords_response.json()
                keywords_list = [kw['name'] for kw in keywords_data.get('keywords', [])]
                result['keywords'] = '|'.join(keywords_list)
            
            time.sleep(RATE_LIMIT_DELAY)
            return result
            
        except Exception as e:
            logger.error(f"Error fetching TMDb data para {tmdb_id}: {e}")
            return None
    
    def _extract_certifications(self, release_data):
            """Extrae certificaciones por país"""
            certifications = {}
            results = release_data.get('results', [])
            
            for country_data in results:
                country_code = country_data.get('iso_3166_1', '')
                releases = country_data.get('release_dates', [])
                
                # Buscar la certificación (puede haber múltiples releases)
                for release in releases:
                    cert = release.get('certification', '')
                    if cert:  # Si hay certificación, la guardamos
                        certifications[country_code] = cert
                        break  # Tomamos la primera certificación válida
            
            return certifications

    def _extract_crew_member(self, crew, job_title):
        """Extrae nombre de un miembro del crew por puesto"""
        for person in crew:
            if person.get('job') == job_title:
                return person.get('name', '')
        return ''
    
    def _extract_crew_members(self, crew, job_title):
        """Extrae nombres de múltiples miembros del crew por puesto"""
        members = [person.get('name', '') for person in crew if person.get('job') == job_title]
        return '|'.join(members) if members else ''
    
    def enrich_dataframe(self, df):
        """Enriquece DataFrame completo"""
        logger.info("Iniciando enriquecimiento de datos con TMDb...")
        
        enriched_data = []
        
        for idx, row in df.iterrows():
            logger.info(f"Procesando {idx+1}/{len(df)}: {row['clean_title']}")
            
            # Datos base
            movie_data = row.to_dict()
            
            # TMDb
            tmdb_data = self.fetch_tmdb_data(row['tmdbId'])
            if tmdb_data:
                logger.info(f"Datos TMDb obtenidos para {row['clean_title']}")
                movie_data.update(tmdb_data)
            else:
                logger.warning(f"No se obtuvieron datos TMDb para {row['clean_title']}")
            
            # OMDb
            omdb_data = self.fetch_omdb_data(row['imdbId'])
            if omdb_data:
                logger.info(f"Datos OMDb obtenidos para {row['clean_title']}")
                movie_data.update(omdb_data)
            else:
                logger.warning(f"No se obtuvieron datos OMDb para {row['clean_title']}")
            
            enriched_data.append(movie_data)
        
        enriched_df = pd.DataFrame(enriched_data)
        logger.info("Enriquecimiento completado")
        
        # Aplicar transformaciones para evitar listas
        logger.info("Aplicando transformaciones de datos...")
        enriched_df = self._expand_genres(enriched_df)
        enriched_df = self._expand_actors(enriched_df)
        enriched_df = self._simplify_crew(enriched_df)
        
        # Mostrar columnas agregadas
        new_columns = set(enriched_df.columns) - set(df.columns)
        logger.info(f"Columnas agregadas: {new_columns}")
        
        return enriched_df
    
    def _expand_genres(self, df):
        """Convierte géneros en columnas one-hot encoding"""
        if 'genres' not in df.columns:
            return df
        
        logger.info("Expandiendo géneros a one-hot encoding...")
        
        # Obtener todos los géneros únicos
        all_genres = set()
        for genres_str in df['genres'].dropna():
            if genres_str:
                genres = genres_str.split('|')
                all_genres.update(genres)
        
        # Crear columna binaria por cada género
        for genre in sorted(all_genres):
            df[f'genre_{genre}'] = df['genres'].apply(
                lambda x: 1 if pd.notna(x) and genre in x.split('|') else 0
            )
        
        logger.info(f"Géneros expandidos: {len(all_genres)} columnas creadas")
        return df
    
    def _expand_actors(self, df):
        """Expande actores y personajes a columnas individuales"""
        logger.info("Expandiendo actores a columnas individuales...")
        
        # Actores principales (3 primeros)
        if 'lead_actors' in df.columns:
            for i in range(3):
                df[f'lead_actor_{i+1}'] = df['lead_actors'].apply(
                    lambda x: x.split('|')[i] if pd.notna(x) and x and len(x.split('|')) > i else ''
                )
            df = df.drop('lead_actors', axis=1)
        
        # Personajes principales (3 primeros)
        if 'lead_characters' in df.columns:
            for i in range(3):
                df[f'lead_character_{i+1}'] = df['lead_characters'].apply(
                    lambda x: x.split('|')[i] if pd.notna(x) and x and len(x.split('|')) > i else ''
                )
            df = df.drop('lead_characters', axis=1)
        
        # Actores secundarios (5 primeros)
        if 'supporting_actors' in df.columns:
            for i in range(5):
                df[f'supporting_actor_{i+1}'] = df['supporting_actors'].apply(
                    lambda x: x.split('|')[i] if pd.notna(x) and x and len(x.split('|')) > i else ''
                )
            df = df.drop('supporting_actors', axis=1)
        
        # Personajes secundarios (5 primeros)
        if 'supporting_characters' in df.columns:
            for i in range(5):
                df[f'supporting_character_{i+1}'] = df['supporting_characters'].apply(
                    lambda x: x.split('|')[i] if pd.notna(x) and x and len(x.split('|')) > i else ''
                )
            df = df.drop('supporting_characters', axis=1)
        
        # Mantener campo general de actores si existe (para compatibilidad)
        if 'actors' in df.columns:
            df = df.drop('actors', axis=1)
        if 'characters' in df.columns:
            df = df.drop('characters', axis=1)
        
        logger.info("Actores expandidos: 3 principales + 5 secundarios")
        return df
    
    def _simplify_crew(self, df):
        """Simplifica datos del crew manteniendo solo el primero para roles múltiples"""
        logger.info("Simplificando datos del crew...")
        
        # Director: solo el primero (puede haber múltiples directores)
        if 'director' in df.columns:
            df['main_director'] = df['director'].apply(
                lambda x: x.split('|')[0] if pd.notna(x) and x else ''
            )
            df = df.drop('director', axis=1)
        
        # Productor: solo el primero (puede haber múltiples productores)
        if 'producer' in df.columns:
            df['main_producer'] = df['producer'].apply(
                lambda x: x.split('|')[0] if pd.notna(x) and x else ''
            )
            df = df.drop('producer', axis=1)
        
        # Writer: solo el primero (puede haber múltiples escritores)
        if 'writer' in df.columns:
            df['main_writer'] = df['writer'].apply(
                lambda x: x.split('|')[0] if pd.notna(x) and x else ''
            )
            df = df.drop('writer', axis=1)
        
        logger.info("Crew simplificado: director, productor y escritor principales")
        logger.info("Crew técnico mantenido: cinematographer, composer, editor")
        return df


# Uso
if __name__ == "__main__":
    import pandas as pd
    import argparse
    
    # Add scripts directory to path
    SCRIPTS_DIR = Path(__file__).resolve().parent.parent
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    
    from etl.data_loader import MovieLensLoader
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enriquece datos de peliculas con APIs externas')
    parser.add_argument('--max-movies', type=int, default=None, help='Numero maximo de peliculas a procesar')
    args = parser.parse_args()
    
    max_movies = args.max_movies
    logger.info(f"Peliculas a procesar: {max_movies if max_movies else 'TODAS'}")
    
    loader = MovieLensLoader()
    movies = loader.load_movies(max_movies=max_movies)
    links = loader.load_links()
    ratings = loader.load_ratings()
    df = loader.merge_data(movies, links, ratings)
    
    enricher = MovieEnricher()
    enriched_df = enricher.enrich_dataframe(df)
    
    # Guardar con todas las columnas en ruta absoluta
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    enriched_df.to_csv(PROCESSED_DIR / "movies_enriched.csv", index=False)
    