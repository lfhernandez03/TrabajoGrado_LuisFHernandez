import pandas as pd
import logging
from pathlib import Path
import sys

# Add parent directory to path to allow imports when run as a script
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from config.config import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_data_root() -> Path:
    """Obtiene ruta raiz del proyecto de datos con validacion"""
    # Comenzar desde el script y navegar hacia la raiz del proyecto
    script_file = Path(__file__).resolve()
    
    # Buscar directorio 'data' subiendo desde el script
    current = script_file.parent
    while current.parent != current:  # Evitar loop infinito en raiz
        if (current / "dataset").exists() or (current / "ontologies").exists():
            return current
        current = current.parent
    
    # Fallback al metodo anterior si no se encuentra
    fallback = script_file.parents[2]
    if not (fallback / "dataset").exists():
        logger.warning(f"Could not find data directory. Using fallback: {fallback}")
    
    return fallback

DATA_ROOT = _get_data_root()
RAW_DATA_DIR = DATA_ROOT / "dataset" / "raw"
PROCESSED_DIR = DATA_ROOT / "dataset" / "processed"

# Validar que los directorios existan
if not RAW_DATA_DIR.exists():
    raise FileNotFoundError(f"Raw data directory not found: {RAW_DATA_DIR}")
if not PROCESSED_DIR.exists():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created processed data directory: {PROCESSED_DIR}")

logger.info(f"Data root: {DATA_ROOT}")
logger.info(f"Raw data: {RAW_DATA_DIR}")
logger.info(f"Processed data: {PROCESSED_DIR}")

class MovieLensLoader: 
    '''Carga y preprocesa datos de MovieLens'''
    def __init__(self, data_path: Path | str | None = None):
        self.data_path = Path(data_path) if data_path else RAW_DATA_DIR
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data path does not exist: {self.data_path}")

    def load_movies(self, max_movies=None):
        '''Carga movies.csv'''
        logger.info("Cargando movies.csv")
        movies_file = self.data_path / "movies.csv"
        if not movies_file.exists():
            raise FileNotFoundError(f"movies.csv not found at {movies_file}")
        
        movies = pd.read_csv(movies_file)

        if max_movies:
            #Seleccionar peliculas mas populares
            ratings_file = self.data_path / "ratings.csv"
            if not ratings_file.exists():
                raise FileNotFoundError(f"ratings.csv not found at {ratings_file}")
            
            ratings = pd.read_csv(ratings_file)
            popular_movies = ratings.groupby('movieId').size().nlargest(max_movies).index
            movies = movies[movies['movieId'].isin(popular_movies)]
        
        logger.info(f"Cargadas {len(movies)} peliculas")
        return movies

    def load_links(self):
        """Carga links.csv (IMDb y TMDB IDs)"""
        logger.info("Cargando links.csv")
        links_file = self.data_path / "links.csv"
        if not links_file.exists():
            raise FileNotFoundError(f"links.csv not found at {links_file}")
        
        # Especificar dtype para mantener imdbId como string y preservar ceros iniciales
        links = pd.read_csv(
            links_file,
            dtype={'imdbId': str, 'tmdbId': str}
        )
        # Asegurar formato de 8 digitos (estandar IMDb) con ceros a la izquierda y prefijo 'tt'
        links['imdbId'] = links['imdbId'].apply(
            lambda x: f"tt{x.zfill(8)}" if pd.notna(x) and x != '' else x
        )
        return links
    
    def load_ratings(self):
        """Carga ratings.csv"""
        logger.info("Cargando ratings.csv...")
        ratings = pd.read_csv(self.data_path / "ratings.csv")
        return ratings
    
    def merge_data(self, movies, links, ratings):
        """Combina datasets"""

        # Merge movies con links
        df = movies.merge(links, on='movieId', how='left')

        # Agregar estadisticas de ratings
        rating_stats = ratings.groupby('movieId').agg({
            'rating': ['mean', 'count']
        }).reset_index()
        rating_stats.columns = ['movieId', 'avg_rating', 'rating_count']

        df = df.merge(rating_stats, on='movieId', how='left')

        # Extraer anio del titulo
        df['year'] = df['title'].str.extract(r'\((\d{4})\)')
        df['clean_title'] = df['title'].str.replace(r'\s*\(\d{4}\)', '', regex=True)

        # Separar generos
        df['genres_list'] = df['genres'].str.split('|')
        
        return df

    def save_processed_data(
        self,
        df,
        output_path: Path | str | None = None,
        max_movies: int | None = None,
        incremental: bool = True
    ):
        """Guarda el DataFrame procesado en CSV"""
        import os
        output_dir = Path(output_path) if output_path else PROCESSED_DIR
        # Crear directorio si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Convertir genres_list a string para CSV
        df_copy = df.copy()
        df_copy['genres_list'] = df_copy['genres_list'].apply(lambda x: '|'.join(x) if isinstance(x, list) else x)
        filepath = output_dir / "movies_processed.csv"

        if incremental and filepath.exists():
            logger.info("Modo incremental ETL: combinando con movies_processed.csv existente")
            existing_df = pd.read_csv(filepath)
            df_copy = pd.concat([existing_df, df_copy], ignore_index=True)
            df_copy = df_copy.drop_duplicates(subset=['movieId'], keep='last')

        if 'avg_rating' in df_copy.columns and 'rating_count' in df_copy.columns:
            df_copy = df_copy.sort_values(by=['avg_rating', 'rating_count'], ascending=[False, False])

        if max_movies:
            df_copy = df_copy.head(max_movies)

        df_copy.to_csv(filepath, index=False)
        logger.info(f"Datos guardados en: {filepath}")
        return filepath
    
# Uso
if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Carga y procesa datos de MovieLens')
    parser.add_argument('--max-movies', type=int, default=None, help='Numero maximo de peliculas a procesar')
    parser.add_argument(
        '--no-incremental',
        action='store_true',
        help='Desactiva merge incremental y sobrescribe salida con el lote actual'
    )
    args = parser.parse_args()
    
    max_movies = args.max_movies
    logger.info(f"Peliculas a procesar: {max_movies if max_movies else 'TODAS'}")
    
    loader = MovieLensLoader()
    movies = loader.load_movies(max_movies=max_movies)
    links = loader.load_links()
    ratings = loader.load_ratings()
    df = loader.merge_data(movies, links, ratings)
    
    # Ordenar por promedio de rating (descendente) y cantidad de ratings
    df = df.sort_values(by=['avg_rating', 'rating_count'], ascending=[False, False])
    # Guardar datos procesados
    loader.save_processed_data(
        df,
        max_movies=max_movies,
        incremental=not args.no_incremental
    )
