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

DATA_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = DATA_ROOT / "dataset" / "raw"
PROCESSED_DIR = DATA_ROOT / "dataset" / "processed"

class MovieLensLoader: 
    '''Carga y preprocesa datos de MovieLens'''
    def __init__(self, data_path: Path | str | None = None):
        self.data_path = Path(data_path) if data_path else RAW_DATA_DIR

    def load_movies(self, max_movies=None):
        '''Carga movies.csv'''
        logger.info("Cargando movies.csv")
        movies = pd.read_csv(self.data_path / "movies.csv")

        if max_movies:
            #Seleccionar peliculas mas populares
            ratings = pd.read_csv(self.data_path / "ratings.csv")
            popular_movies = ratings.groupby('movieId').size().nlargest(max_movies).index
            movies = movies[movies['movieId'].isin(popular_movies)]
        
        logger.info(f"Cargadas {len(movies)} peliculas")
        return movies

    def load_links(self):
        """Carga links.csv (IMDb y TMDB IDs)"""
        logger.info("Cargando links.csv")
        # Especificar dtype para mantener imdbId como string y preservar ceros iniciales
        links = pd.read_csv(
            self.data_path / "links.csv",
            dtype={'imdbId': str, 'tmdbId': str}
        )
        # Asegurar formato de 7 dígitos con ceros a la izquierda y prefijo 'tt'
        links['imdbId'] = links['imdbId'].apply(
            lambda x: f"{x.zfill(7)}" if pd.notna(x) and x != '' else x
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

        # Separar géneros
        df['genres_list'] = df['genres'].str.split('|')
        
        return df

    def save_processed_data(self, df, output_path: Path | str | None = None):
        """Guarda el DataFrame procesado en CSV"""
        import os
        output_dir = Path(output_path) if output_path else PROCESSED_DIR
        # Crear directorio si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Convertir genres_list a string para CSV
        df_copy = df.copy()
        df_copy['genres_list'] = df_copy['genres_list'].apply(lambda x: '|'.join(x) if isinstance(x, list) else x)
        filepath = output_dir / "movies_processed.csv"
        df_copy.to_csv(filepath, index=False)
        logger.info(f"Datos guardados en: {filepath}")
        return filepath
    
# Uso
if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Carga y procesa datos de MovieLens')
    parser.add_argument('--max-movies', type=int, default=None, help='Numero maximo de peliculas a procesar')
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
    loader.save_processed_data(df)
