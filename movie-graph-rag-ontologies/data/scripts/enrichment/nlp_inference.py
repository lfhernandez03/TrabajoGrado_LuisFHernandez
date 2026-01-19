import os
import sys
import pandas as pd
from keybert import KeyBERT
from transformers import pipeline
import logging
import json
import ast
from pathlib import Path

# Agregar rutas necesarias
current_dir = Path(__file__).resolve().parent
config_dir = current_dir.parent / 'config'
sys.path.insert(0, str(config_dir))

# Paths absolutos relativos a DATA
DATA_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = DATA_ROOT / "data" / "processed"

# Import desde config
from config import (
    GENRE_TONE_MAPPING, 
    HISTORICAL_PERIOD_MAPPING, 
    MOVIE_TYPE_RULES, 
    MULTI_TONE_CONFIG, 
    NLP_STOPWORDS, 
    PLOT_STRUCTURE_RULES, 
    THEME_KEYWORDS, 
    TONE_KEYWORDS, 
    TONE_THRESHOLDS, 
    TONE_WEIGHTS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NLPInferencer:
    """Infiere atributos semánticos usando NLP"""

    def __init__(self):
        logger.info("Inicializando modelos NLP...")
        self.keyword_model = KeyBERT()
        self.sentiment_analyzer = pipeline("sentiment-analysis")

    def _clean_text(self, text):
        """Limpia texto removiendo stopwords"""
        if not text: 
            return ""
        text_lower = text.lower()
        for stopword in NLP_STOPWORDS:
            text_lower = text_lower.replace(stopword, '')
        return text_lower
    
    def _extract_main_genre(self, genres_value):
        """
        Extrae el género principal de diferentes formatos de entrada.
        Maneja: JSON, listas de Python, strings separados por |, y strings simples.
        """
        if pd.isna(genres_value) or genres_value == '':
            logger.debug("Género vacío o nulo")
            return None
        
        try:
            # Caso 1: Si ya es una lista de Python
            if isinstance(genres_value, list):
                if len(genres_value) > 0:
                    # Si el primer elemento es un diccionario con 'name'
                    if isinstance(genres_value[0], dict) and 'name' in genres_value[0]:
                        return genres_value[0]['name']
                    # Si es un string directo
                    elif isinstance(genres_value[0], str):
                        return genres_value[0]
                return None
            
            # Caso 2: Si es un string
            genres_str = str(genres_value).strip()
            
            # Caso 2a: JSON array (ej: [{"id": 28, "name": "Action"}])
            if genres_str.startswith('['):
                try:
                    genres_list = json.loads(genres_str)
                    if len(genres_list) > 0 and isinstance(genres_list[0], dict):
                        return genres_list[0].get('name', None)
                except json.JSONDecodeError:
                    # Intentar con ast.literal_eval
                    try:
                        genres_list = ast.literal_eval(genres_str)
                        if len(genres_list) > 0:
                            if isinstance(genres_list[0], dict):
                                return genres_list[0].get('name', None)
                            elif isinstance(genres_list[0], str):
                                return genres_list[0]
                    except:
                        pass
            
            # Caso 2b: String separado por pipe (ej: "Action|Adventure|Sci-Fi")
            if '|' in genres_str:
                return genres_str.split('|')[0].strip()
            
            # Caso 2c: String separado por coma (ej: "Action, Adventure, Sci-Fi")
            if ',' in genres_str:
                return genres_str.split(',')[0].strip()
            
            # Caso 2d: String simple (un solo género)
            return genres_str
            
        except Exception as e:
            logger.warning(f"Error extrayendo género principal: {e}")
            return None
    
    def _normalize_genre_name(self, genre):
        """
        Normaliza nombres de géneros para mantener consistencia.
        """
        if not genre:
            return None
        
        genre = str(genre).strip()
        
        # Mapeo de variaciones comunes a nombres estándar
        genre_normalization = {
            'Sci-Fi': 'Science Fiction',
            'SciFi': 'Science Fiction',
            'SF': 'Science Fiction',
            'Sci-fi': 'Science Fiction',
            'Rom-Com': 'Romance',
            'Romantic Comedy': 'Romance',
            'Rom Com': 'Romance',
            'Action & Adventure': 'Action',
            'Action/Adventure': 'Action',
            'Animated': 'Animation',
            'Musical': 'Music',
            'Musicals': 'Music',
            'Suspense': 'Thriller',
            'Psychological Thriller': 'Thriller',
            'Historical': 'History',
            'Historical Drama': 'History',
            'War Film': 'War',
            'Biography': 'Documentary',
            'Biographical': 'Documentary',
            'TV Movie': 'Drama',  # Fallback para TV movies
        }
        
        # Retornar nombre normalizado o el original si no necesita normalización
        return genre_normalization.get(genre, genre)
    
    def add_main_genre_column(self, df):
        """
        Agrega columna 'main_genre' al DataFrame.
        Extrae el primer género de la columna 'genres' o 'genres_list'.
        """
        logger.info("Agregando columna 'main_genre'...")
        
        main_genres = []
        extraction_stats = {
            'success': 0,
            'failed': 0,
            'normalized': 0
        }
        
        for idx, row in df.iterrows():
            # Intentar primero con 'genres', luego con 'genres_list'
            genre_value = None
            if 'genres' in df.columns:
                genre_value = row['genres']
            elif 'genres_list' in df.columns:
                genre_value = row['genres_list']
            
            # Extraer género principal
            main_genre = self._extract_main_genre(genre_value)
            
            if main_genre:
                extraction_stats['success'] += 1
                
                # Normalizar nombre
                original_genre = main_genre
                main_genre = self._normalize_genre_name(main_genre)
                
                if original_genre != main_genre:
                    extraction_stats['normalized'] += 1
                    logger.debug(f"Normalizado: '{original_genre}' → '{main_genre}'")
            else:
                extraction_stats['failed'] += 1
                logger.warning(f"No se pudo extraer género para película {row.get('clean_title', 'Unknown')} (ID: {row.get('movieId', 'Unknown')})")
            
            main_genres.append(main_genre)
        
        # Agregar columna al DataFrame
        df['main_genre'] = main_genres
        
        # Mostrar estadísticas
        logger.info(f"\n=== Estadísticas de Extracción de Géneros ===")
        logger.info(f"Total películas: {len(df)}")
        logger.info(f"Extracciones exitosas: {extraction_stats['success']} ({extraction_stats['success']/len(df)*100:.1f}%)")
        logger.info(f"Extracciones fallidas: {extraction_stats['failed']} ({extraction_stats['failed']/len(df)*100:.1f}%)")
        logger.info(f"Géneros normalizados: {extraction_stats['normalized']}")
        
        # Mostrar distribución de géneros principales
        logger.info(f"\n=== Distribución de Géneros Principales ===")
        genre_counts = df['main_genre'].value_counts()
        for genre, count in genre_counts.head(15).items():
            logger.info(f"  {genre}: {count} ({count/len(df)*100:.1f}%)")
        
        # Películas sin género
        no_genre_count = df['main_genre'].isna().sum()
        if no_genre_count > 0:
            logger.warning(f"\n⚠ {no_genre_count} películas sin género principal")
            # Mostrar ejemplos
            no_genre_movies = df[df['main_genre'].isna()][['movieId', 'clean_title', 'year']].head(5)
            logger.warning("Ejemplos de películas sin género:")
            for _, movie in no_genre_movies.iterrows():
                logger.warning(f"  - {movie['clean_title']} ({movie['year']}) [ID: {movie['movieId']}]")
        
        return df
    
    def infer_tone(self, keywords, genres, overview='', tagline=''):
        """Infiere tono con sistema de scoring multi-nivel"""
        # Preparar textos
        keyword_str = self._clean_text(' '.join(keywords) if keywords else '')
        overview_str = self._clean_text(overview)
        tagline_str = self._clean_text(tagline)

        tone_scores = {}

        # 1. Scoring basado en keywords y overview
        for tone, keyword_groups in TONE_KEYWORDS.items():
            score = 0

            # Keywords primarias
            for word in keyword_groups['primary']:
                if word in keyword_str:
                    score += TONE_WEIGHTS['keyword_primary']
                if word in overview_str:
                    score += TONE_WEIGHTS['overview_primary']
                if word in tagline_str:
                    score += TONE_WEIGHTS['tagline']

            # Keywords secundarias
            for word in keyword_groups['secondary']:
                if word in keyword_str:
                    score += TONE_WEIGHTS['keyword_secondary']
                if word in overview_str:
                    score += TONE_WEIGHTS['overview_secondary']
            
            if score > 0:
                tone_scores[tone] = score

        # 2. Boost por coincidencia de género
        if genres:
            main_genre = genres[0] if isinstance(genres, list) else genres
            if main_genre in GENRE_TONE_MAPPING:
                genre_tone_info = GENRE_TONE_MAPPING[main_genre]
                genre_tone = genre_tone_info['primary']
                genre_boost = TONE_WEIGHTS['genre_match'] * genre_tone_info['confidence']
                tone_scores[genre_tone] = tone_scores.get(genre_tone, 0) + genre_boost
        
        # 3. Determinar tono(s) final(es)
        if not tone_scores:
            # Fallback completo a género
            main_genre = genres[0] if isinstance(genres, list) and genres else 'Drama'
            return GENRE_TONE_MAPPING.get(main_genre, {'primary': 'DramaticTone'})['primary']
        
        # Ordenar por score
        sorted_tones = sorted(tone_scores.items(), key=lambda x: x[1], reverse=True)
        primary_tone, primary_score = sorted_tones[0]
        
        # Verificar umbral mínimo
        if primary_score < TONE_THRESHOLDS['min_score']:
            main_genre = genres[0] if isinstance(genres, list) and genres else 'Drama'
            return GENRE_TONE_MAPPING.get(main_genre, {'primary': 'DramaticTone'})['primary']
        
        # Detectar tonos múltiples si está habilitado
        if MULTI_TONE_CONFIG['enabled'] and len(sorted_tones) > 1:
            secondary_tone, secondary_score = sorted_tones[1]
            score_diff = primary_score - secondary_score
            
            if (secondary_score >= MULTI_TONE_CONFIG['secondary_tone_min_score'] and
                score_diff <= MULTI_TONE_CONFIG['score_difference_threshold']):
                return f"{primary_tone}|{secondary_tone}"
        
        return primary_tone
    
    def infer_theme(self, keywords, overview=''):
        """Infiere temas principales de la narrativa"""
        combined_text = self._clean_text(f"{' '.join(keywords) if keywords else ''} {overview}")
        
        theme_scores = {}
        for theme, theme_keywords in THEME_KEYWORDS.items():
            score = sum(2 if word in combined_text else 0 for word in theme_keywords)
            if score > 0:
                theme_scores[theme] = score
        
        if not theme_scores:
            return None
        
        # Retornar top 3 temas
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        return '|'.join([theme for theme, _ in sorted_themes[:3]])
    
    def infer_plot_structure(self, keywords, overview='', runtime=0, genres=None):
        """Infiere estructura narrativa"""
        combined_text = self._clean_text(f"{' '.join(keywords) if keywords else ''} {overview}")
        
        structure_scores = {}
        for structure, rules in PLOT_STRUCTURE_RULES.items():
            score = 0
            
            # Keywords match
            keyword_matches = sum(1 for word in rules['keywords'] if word in combined_text)
            score += keyword_matches * 2
            
            # Runtime match
            if runtime > 0:
                runtime_min, runtime_max = rules['runtime_range']
                if runtime_min <= runtime <= runtime_max:
                    score += 1
            
            # Genre match
            if genres:
                genre_matches = sum(1 for g in genres if g in rules['genres'])
                score += genre_matches
            
            if score > 0:
                structure_scores[structure] = score
        
        if not structure_scores:
            return 'LinearNarrative'  # Default
        
        return max(structure_scores, key=structure_scores.get)
    
    def infer_historical_period(self, year, keywords, overview=''):
        """Infiere período histórico"""
        combined_text = self._clean_text(f"{' '.join(keywords) if keywords else ''} {overview}")
        
        period_scores = {}
        for period, rules in HISTORICAL_PERIOD_MAPPING.items():
            score = 0
            
            # Year range
            if year:
                year_min, year_max = rules['year_range']
                if year_min <= int(year) <= year_max:
                    score += 3
            
            # Keywords
            keyword_matches = sum(1 for word in rules['keywords'] if word in combined_text)
            score += keyword_matches
            
            if score > 0:
                period_scores[period] = score
        
        if not period_scores:
            return 'Contemporary'  # Default
        
        return max(period_scores, key=period_scores.get)
    
    def infer_movie_type(self, runtime, genres):
        """Clasifica tipo de película"""
        if not runtime or not genres:
            return 'FeatureFilm'
        
        for movie_type, rules in MOVIE_TYPE_RULES.items():
            # Check runtime
            if 'runtime_min' in rules and runtime < rules['runtime_min']:
                continue
            if 'runtime_max' in rules and runtime > rules['runtime_max']:
                continue
            
            # Check genres
            if 'any' in rules['genres']:
                return movie_type
            
            if any(g in rules['genres'] for g in genres):
                return movie_type
        
        return 'FeatureFilm'  # Default
    
    def get_inference_confidence(self, tone_result, theme_result, structure_result):
        """Calcula nivel de confianza global de la inferencia"""
        confidence_scores = []
        
        # Tone confidence (basado en múltiples tonos o score alto)
        if '|' in tone_result:
            confidence_scores.append(0.7)  # Media-alta si hay múltiples tonos
        else:
            confidence_scores.append(0.8)  # Alta si es tono único claro
        
        # Theme confidence
        if theme_result and '|' in theme_result:
            theme_count = len(theme_result.split('|'))
            confidence_scores.append(min(0.9, 0.6 + (theme_count * 0.1)))
        elif theme_result:
            confidence_scores.append(0.7)
        else:
            confidence_scores.append(0.3)
        
        # Structure confidence (siempre conservador)
        confidence_scores.append(0.6)
        
        return sum(confidence_scores) / len(confidence_scores)
    
    def process_single_movie(self, row):
        """Procesa una película individual y retorna sus inferencias"""
        try:
            # Preparar datos
            keywords = row['keywords'].split('|') if pd.notna(row['keywords']) else []
            
            # Usar main_genre si existe, sino extraer de genres
            if 'main_genre' in row and pd.notna(row['main_genre']):
                genres = [row['main_genre']]
            elif 'genres_list' in row and pd.notna(row['genres_list']):
                genres = row['genres_list'].split('|')
            elif 'genres' in row and pd.notna(row['genres']):
                # Intentar extraer del formato original
                main_genre = self._extract_main_genre(row['genres'])
                genres = [main_genre] if main_genre else []
            else:
                genres = []
            
            overview = row['overview'] if pd.notna(row['overview']) else ''
            tagline = row['tagline'] if pd.notna(row['tagline']) else ''
            runtime = row['runtime'] if pd.notna(row['runtime']) else 0
            year = row['year'] if pd.notna(row['year']) else None
            
            # Inferencias
            logger.info("  → Infiriendo atributos semánticos...")
            tone = self.infer_tone(keywords, genres, overview, tagline)
            theme = self.infer_theme(keywords, overview)
            plot_structure = self.infer_plot_structure(keywords, overview, runtime, genres)
            historical_period = self.infer_historical_period(year, keywords, overview)
            movie_type = self.infer_movie_type(runtime, genres)
            confidence = self.get_inference_confidence(tone, theme, plot_structure)
            
            # Resultados
            result = {
                'movieId': row['movieId'],
                'clean_title': row['clean_title'],
                'year': row['year'],
                'tone': tone,
                'theme': theme,
                'plot_structure': plot_structure,
                'historical_period': historical_period,
                'movie_type': movie_type,
                'inference_confidence': confidence
            }
            
            logger.info(f"Género principal: {genres[0] if genres else 'N/A'}")
            logger.info(f"Tono: {tone}")
            logger.info(f"Tema: {theme}")
            logger.info(f"Estructura: {plot_structure}")
            logger.info(f"Período: {historical_period}")
            logger.info(f"Tipo: {movie_type}")
            logger.info(f"Confianza: {confidence:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error procesando {row['clean_title']}: {e}")
            # Valores por defecto en caso de error
            return {
                'movieId': row['movieId'],
                'clean_title': row['clean_title'],
                'year': row['year'],
                'tone': 'DramaticTone',
                'theme': None,
                'plot_structure': 'LinearNarrative',
                'historical_period': 'Contemporary',
                'movie_type': 'FeatureFilm',
                'inference_confidence': 0.3
            }
    
    def process_dataframe(self, df):
        """Procesa un DataFrame completo de películas"""
        logger.info(f"Procesando {len(df)} películas...")
        results = []
        
        for idx, row in df.iterrows():
            logger.info(f"\n[{idx+1}/{len(df)}] Procesando: {row['clean_title']} ({row['year']})")
            result = self.process_single_movie(row)
            results.append(result)
        
        return pd.DataFrame(results)
    
    def generate_statistics(self, df_nlp):
        """Genera estadísticas de las inferencias"""
        logger.info("\n=== ESTADÍSTICAS DE INFERENCIAS ===")
        logger.info(f"Total películas procesadas: {len(df_nlp)}")
        
        # Distribución de Tonos
        logger.info(f"\nDistribución de Tonos:")
        tone_dist = df_nlp['tone'].value_counts()
        for tone, count in tone_dist.items():
            logger.info(f"  {tone}: {count} ({count/len(df_nlp)*100:.1f}%)")
        
        # Distribución de Tipos de Película
        logger.info(f"\nDistribución de Tipos de Película:")
        type_dist = df_nlp['movie_type'].value_counts()
        for movie_type, count in type_dist.items():
            logger.info(f"  {movie_type}: {count} ({count/len(df_nlp)*100:.1f}%)")
        
        # Distribución de Períodos Históricos
        logger.info(f"\nDistribución de Períodos Históricos:")
        period_dist = df_nlp['historical_period'].value_counts()
        for period, count in period_dist.items():
            logger.info(f"  {period}: {count} ({count/len(df_nlp)*100:.1f}%)")
        
        # Distribución de Estructuras Narrativas
        logger.info(f"\nDistribución de Estructuras Narrativas:")
        structure_dist = df_nlp['plot_structure'].value_counts()
        for structure, count in structure_dist.items():
            logger.info(f"  {structure}: {count} ({count/len(df_nlp)*100:.1f}%)")
        
        # Métricas de confianza
        logger.info(f"\nConfianza promedio: {df_nlp['inference_confidence'].mean():.2%}")
        logger.info(f"Confianza mínima: {df_nlp['inference_confidence'].min():.2%}")
        logger.info(f"Confianza máxima: {df_nlp['inference_confidence'].max():.2%}")
    
    def save_results(self, df_final, df_nlp):
        """Guarda los resultados en archivos CSV"""
        # Archivo completo con todas las columnas
        output_file = PROCESSED_DIR / 'movies_nlp_enriched.csv'
        logger.info(f"\nGuardando resultados completos en {output_file}...")
        df_final.to_csv(output_file, index=False)
        
        # Archivo resumen solo con inferencias
        summary_file = PROCESSED_DIR / 'nlp_inference_summary.csv'
        logger.info(f"Guardando resumen en {summary_file}...")
        df_nlp.to_csv(summary_file, index=False)
        
        return str(output_file), str(summary_file)


def run_nlp_pipeline(input_file=None):
    """Pipeline principal de procesamiento NLP"""
    logger.info("=== Iniciando Procesamiento NLP ===")
    
    # 1. Cargar datos
    if input_file is None:
        input_file = PROCESSED_DIR / 'movies_enriched.csv'
    logger.info(f"Cargando datos desde {input_file}...")
    df = pd.read_csv(input_file)
    logger.info(f"Total películas cargadas: {len(df)}")
    
    # 2. Inicializar inferencer
    inferencer = NLPInferencer()
    
    # 3. Agregar columna main_genre PRIMERO
    df = inferencer.add_main_genre_column(df)
    
    # 4. Procesar todas las películas
    df_nlp = inferencer.process_dataframe(df)
    
    # 5. Merge con datos originales
    logger.info("\n=== Generando DataFrame Final ===")
    df_final = df.merge(
        df_nlp[['movieId', 'tone', 'theme', 'plot_structure', 
                'historical_period', 'movie_type', 'inference_confidence']], 
        on='movieId', 
        how='left'
    )
    
    # 6. Guardar resultados
    output_file, summary_file = inferencer.save_results(df_final, df_nlp)
    
    # 7. Generar estadísticas
    inferencer.generate_statistics(df_nlp)

    # 8. Resumen final
    logger.info("\n=== Procesamiento NLP Completado ===")
    logger.info(f"Archivo completo: {output_file}")
    logger.info(f"Archivo resumen: {summary_file}")
    
    return df_final, df_nlp


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Infiere atributos semanticos de peliculas')
    parser.add_argument('--max-movies', type=int, default=None, help='Numero maximo de peliculas a procesar')
    args = parser.parse_args()
    
    # Si se proporciona max_movies, usar solo ese numero de peliculas del archivo de entrada
    if args.max_movies:
        logger.info(f"Limitando procesamiento a {args.max_movies} peliculas")
        input_file = PROCESSED_DIR / "movies_enriched.csv"
        if input_file.exists():
            df = pd.read_csv(input_file).head(args.max_movies)
            logger.info(f"Total peliculas cargadas: {len(df)}")
            
            # Procesamiento
            inferencer = NLPInferencer()
            df = inferencer.add_main_genre_column(df)
            df_nlp = inferencer.process_dataframe(df)
            
            # Merge
            df_final = df.merge(
                df_nlp[['movieId', 'tone', 'theme', 'plot_structure', 
                        'historical_period', 'movie_type', 'inference_confidence']], 
                on='movieId', 
                how='left'
            )
            
            # Guardar
            output_file, summary_file = inferencer.save_results(df_final, df_nlp)
            inferencer.generate_statistics(df_nlp)
            
            logger.info("\n=== Procesamiento NLP Completado ===")
            logger.info(f"Archivo completo: {output_file}")
            logger.info(f"Archivo resumen: {summary_file}")
    else:
        # Ejecutar pipeline completo
        df_final, df_nlp = run_nlp_pipeline()