from rdflib import Graph, Literal, URIRef
import pandas as pd
import logging
import sys
import re
from urllib.parse import quote
from pathlib import Path

# Agregar el directorio de config al path para importar namespaces
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from namespaces import (
    BRIDGE_NS, MOVIE_NS, CONTEXT_NS,
    MOVIE_DATA_NS, CONTEXT_DATA_NS, GENRE_DATA_NS,
    RDF, RDFS, XSD, OWL, bind_all_namespaces
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths absolutos relativos a DATA
DATA_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = DATA_ROOT / "data" / "processed"
ONTOLOGIES_DIR = DATA_ROOT / "ontologies" / "instances"

class RDFBridgeGenerator:
    """
    Genera conexiones entre películas y contextos usando bridge-ontology.
    Implementa lógica de mapeo basada en características de las películas.
    """
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
        
        # Mapeos de géneros a contextos
        self._initialize_mappings()
    
    def _bind_namespaces(self):
        """Vincular namespaces al grafo usando la función centralizada"""
        bind_all_namespaces(self.graph)
    
    def _initialize_mappings(self):
        """
        Inicializa mapeos de géneros a contextos usando valores normalizados.
        
        IMPORTANTE: Valores deben coincidir exactamente con los vocabularios de rdf_context_generator.py:
        - MOOD_TYPES: 'feliz', 'relajado', 'estresado', 'triste', 'ansioso', etc.
        - COMPANION_TYPES: 'solo', 'pareja', 'familia', 'familia con niños', 'amigos', etc.
        - ENERGY_LEVELS: 'bajo', 'medio', 'alto'
        
        La ontología v3 NO tiene clases Mood/CompanionType/TimeOfDay, solo propiedades en
        EmotionalContext y SocialContext.
        """
        
        # Mapeo: Género -> Moods (valores normalizados lowercase, sin tildes)
        self.genre_to_moods = {
            'Comedy': ['feliz', 'relajado', 'aburrido'],
            'Romance': ['romantico', 'feliz', 'solo'],
            'Drama': ['concentrado', 'triste', 'curioso'],
            'Action': ['emocionado', 'estresado', 'aventurero'],
            'Thriller': ['estresado', 'emocionado', 'curioso'],
            'Horror': ['nervioso', 'emocionado', 'aventurero'],
            'Science Fiction': ['curioso', 'concentrado', 'aventurero'],
            'Fantasy': ['aventurero', 'curioso', 'nostalgico'],
            'Animation': ['feliz', 'nostalgico', 'relajado'],
            'Documentary': ['curioso', 'concentrado', 'aburrido'],
            'Crime': ['curioso', 'estresado', 'concentrado'],
            'Mystery': ['curioso', 'concentrado', 'emocionado'],
            'Adventure': ['aventurero', 'emocionado', 'feliz'],
            'War': ['concentrado', 'estresado', 'curioso'],
            'History': ['curioso', 'concentrado', 'nostalgico'],
            'Music': ['feliz', 'emocionado', 'nostalgico'],
            'Family': ['feliz', 'relajado', 'nostalgico'],
        }
        
        # Mapeo: Género -> CompanionTypes (valores normalizados, con tildes y espacios donde apliquen)
        self.genre_to_companions = {
            'Romance': ['pareja', 'solo'],
            'Comedy': ['amigos', 'familia', 'pareja'],
            'Horror': ['amigos', 'pareja', 'solo'],
            'Action': ['amigos', 'solo'],
            'Drama': ['solo', 'pareja'],
            'Animation': ['familia', 'familia con niños'],
            'Family': ['familia', 'familia con niños', 'familia extendida'],
            'Documentary': ['solo', 'pareja'],
            'Science Fiction': ['amigos', 'solo'],
            'Fantasy': ['amigos', 'familia'],
            'Adventure': ['amigos', 'familia'],
            'Thriller': ['amigos', 'pareja', 'solo'],
            'Crime': ['solo', 'amigos'],
            'Mystery': ['solo', 'pareja'],
        }
        
        # Mapeo: Género -> Niveles de energía (reemplaza TimeOfDay en v3)
        # Valores: 'bajo', 'medio', 'alto' según ENERGY_LEVELS
        self.genre_to_energy_level = {
            'Horror': ['alto'],
            'Thriller': ['alto', 'medio'],
            'Romance': ['bajo', 'medio'],
            'Comedy': ['medio'],
            'Action': ['alto'],
            'Drama': ['bajo', 'medio'],
            'Documentary': ['bajo'],
            'Animation': ['medio', 'bajo'],
            'Family': ['medio'],
            'Science Fiction': ['medio', 'alto'],
            'Fantasy': ['medio', 'alto'],
            'Adventure': ['alto', 'medio'],
            'Crime': ['medio'],
            'Mystery': ['medio', 'bajo'],
            'War': ['medio', 'alto'],
            'Music': ['medio', 'alto'],
        }
        
        # Géneros aptos para niños
        self.kid_friendly_genres = [
            'Animation', 'Family', 'Adventure', 'Fantasy', 'Music'
        ]
    
    def _sanitize_uri(self, text):
        """Sanitiza texto para crear URIs válidas (consistente con rdf_generator.py)"""
        if pd.isna(text) or text == '':
            return None
        # Eliminar caracteres especiales y espacios
        text = str(text).strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s]+', '_', text)
        return quote(text)
    
    def _create_movie_uri(self, movie_id, title):
        """Crea URI de película (idéntico a rdf_generator.py)"""
        safe_title = self._sanitize_uri(title)
        return MOVIE_DATA_NS[f"movie_{movie_id}_{safe_title}"]
    
    def _create_context_snapshot_uri(self, snapshot_id):
        """
        Crea URI de un ContextSnapshot.
        
        IMPORTANTE: En v3, NO creamos URIs de mood/companion/timeofday individuales.
        Esos son valores literales (strings) en EmotionalContext/SocialContext.
        """
        return CONTEXT_DATA_NS[f"snapshot_{snapshot_id}"]
    
    def _calculate_mood_match_score(self, genre, mood):
        """Calcula score de coincidencia entre género y mood"""
        if genre not in self.genre_to_moods:
            return 0.5  # score neutro por defecto
        
        moods_list = self.genre_to_moods[genre]
        if mood in moods_list:
            # Primer mood: 0.9, segundo: 0.8, tercero: 0.7
            position = moods_list.index(mood)
            return 0.9 - (position * 0.1)
        return 0.3  # score bajo si no está en la lista
    
    def _calculate_social_match_score(self, genre, companion):
        """Calcula score de coincidencia entre género y companion"""
        if genre not in self.genre_to_companions:
            return 0.5
        
        companions_list = self.genre_to_companions[genre]
        if companion in companions_list:
            position = companions_list.index(companion)
            return 0.9 - (position * 0.1)
        return 0.4
    
    def _calculate_energy_match_score(self, genre, energy_level):
        """Calcula score de coincidencia entre género y nivel de energía deseado"""
        if genre not in self.genre_to_energy_level:
            return 0.6
        
        energy_list = self.genre_to_energy_level[genre]
        if energy_level in energy_list:
            position = energy_list.index(energy_level)
            return 0.9 - (position * 0.1)
        return 0.4
    
    def _calculate_compatibility_score(self, mood_score, social_score, energy_score):
        """Calcula score global de compatibilidad (promedio ponderado)"""
        return round((mood_score * 0.4 + social_score * 0.3 + energy_score * 0.3), 2)
    
    def add_mood_mappings(self, movie_uri, main_genre):
        """
        Agrega características emocionales compatibles como data properties.
        
        IMPORTANTE: NO creamos conexiones alignsWithMood aquí.
        Esas se crean dinámicamente durante GraphRAG queries.
        
        En su lugar, agregamos valores literales de moods compatibles que
        el LLM puede usar para matching.
        """
        if main_genre not in self.genre_to_moods:
            logger.debug(f"No mood mappings for genre: {main_genre}")
            return
        
        for idx, mood_name in enumerate(self.genre_to_moods[main_genre]):
            score = self._calculate_mood_match_score(main_genre, mood_name)
            
            # Agregar mood compatible como data property
            self.graph.add((movie_uri, BRIDGE_NS.compatibleMood, Literal(mood_name)))
            self.graph.add((movie_uri, BRIDGE_NS.moodMatchScore, 
                          Literal(score, datatype=XSD.float)))
    
    def add_companion_mappings(self, movie_uri, main_genre):
        """
        Agrega tipos de compañía compatibles como data properties.
        
        Estas se usarn para matching dinámico con SocialContext.companionType.
        """
        if main_genre not in self.genre_to_companions:
            logger.debug(f"No companion mappings for genre: {main_genre}")
            return
        
        for companion_name in self.genre_to_companions[main_genre]:
            score = self._calculate_social_match_score(main_genre, companion_name)
            
            # Agregar companion compatible como data property
            self.graph.add((movie_uri, BRIDGE_NS.compatibleCompanion, Literal(companion_name)))
            self.graph.add((movie_uri, BRIDGE_NS.socialMatchScore, 
                          Literal(score, datatype=XSD.float)))
    
    def add_energy_mappings(self, movie_uri, main_genre):
        """
        Agrega niveles de energía compatibles como data properties.
        
        Se usa para matching con EmotionalContext.desiredEnergyLevel.
        """
        if main_genre not in self.genre_to_energy_level:
            logger.debug(f"No energy mappings for genre: {main_genre}")
            return
        
        for energy_level in self.genre_to_energy_level[main_genre]:
            score = self._calculate_energy_match_score(main_genre, energy_level)
            
            # Agregar energy level compatible como data property
            self.graph.add((movie_uri, BRIDGE_NS.compatibleEnergyLevel, Literal(energy_level)))
            self.graph.add((movie_uri, BRIDGE_NS.energyMatchScore, 
                          Literal(score, datatype=XSD.float)))
    
    def add_time_constraint_mappings(self, movie_uri, runtime):
        """
        El runtime ya está disponible en movie:runtime (movie-ontology).
        SWRL rules en bridge-ontology usarán movie:runtime y context:availableTime directamente.
        
        No es necesario duplicar esta información aquí.
        """
        pass  # Runtime ya está en la película, se usa directamente en SPARQL/SWRL
    
    def add_content_constraint_mappings(self, movie_uri, main_genre, certification):
        """
        Agrega flags simples para restricciones de contenido.
        El LLM/SPARQL usará estos para filtrado.
        """
        
        # Determinar si es apto para niños
        is_kid_friendly = False
        
        if main_genre in self.kid_friendly_genres:
            is_kid_friendly = True
        
        # Verificar certificación
        if not pd.isna(certification):
            cert = str(certification).upper()
            if cert in ['G', 'PG']:
                is_kid_friendly = True
            elif cert in ['R', 'NC-17']:
                is_kid_friendly = False
        
        # Agregar como data property booleana
        self.graph.add((movie_uri, BRIDGE_NS.isKidFriendly, 
                       Literal(is_kid_friendly, datatype=XSD.boolean)))
    
    def add_device_mappings(self, movie_uri, main_genre):
        """
        Dispositivos no son parte de context-ontology v3.
        Eliminado para simplificar.
        """
        pass
    
    def add_intensity_mappings(self, movie_uri, main_genre):
        """
        Intensidad ahora está cubierta por compatibleEnergyLevel.
        Eliminado para evitar redundancia.
        """
        pass
    
    def add_movie_context_bridge(self, row):
        """Agrega todas las conexiones bridge para una película"""
        movie_id = row['movieId']
        title = row['clean_title']
        main_genre = row.get('main_genre', '')
        runtime = row.get('runtime', 120)
        certification = row.get('certification', None)
        year = row.get('year', None)
        
        if pd.isna(main_genre) or main_genre == '':
            logger.warning(f"No main_genre for movie {movie_id}: {title}")
            return
        
        # Crear URI de la película
        movie_uri = self._create_movie_uri(movie_id, title)
        
        # Agregar tipo e información básica de la película para hacer las consultas self-contained
        self.graph.add((movie_uri, RDF.type, MOVIE_NS.Movie))
        self.graph.add((movie_uri, MOVIE_NS.hasTitle, Literal(title)))
        if year and not pd.isna(year):
            # Note: La ontología no tiene propiedad 'year', solo releaseDate
            # Podríamos agregar esto si se necesita, o usar releaseDate directamente
            pass
        if runtime and not pd.isna(runtime):
            self.graph.add((movie_uri, MOVIE_NS.runtime, Literal(int(runtime), datatype=XSD.integer)))
        
        # Agregar todos los mapeos
        self.add_mood_mappings(movie_uri, main_genre)
        self.add_companion_mappings(movie_uri, main_genre)
        self.add_energy_mappings(movie_uri, main_genre)
        self.add_time_constraint_mappings(movie_uri, runtime)
        self.add_content_constraint_mappings(movie_uri, main_genre, certification)
        # device_mappings e intensity_mappings eliminados (no están en v3)
        
        # Calcular y agregar compatibility score global
        mood_scores = list(self.graph.objects(movie_uri, BRIDGE_NS.moodMatchScore))
        social_scores = list(self.graph.objects(movie_uri, BRIDGE_NS.socialMatchScore))
        energy_scores = list(self.graph.objects(movie_uri, BRIDGE_NS.energyMatchScore))
        
        if mood_scores and social_scores and energy_scores:
            avg_mood = sum(float(s) for s in mood_scores) / len(mood_scores)
            avg_social = sum(float(s) for s in social_scores) / len(social_scores)
            avg_energy = sum(float(s) for s in energy_scores) / len(energy_scores)
            
            compatibility = self._calculate_compatibility_score(avg_mood, avg_social, avg_energy)
            self.graph.add((movie_uri, BRIDGE_NS.compatibilityScore, 
                          Literal(compatibility, datatype=XSD.float)))
    
    def generate_from_dataframe(self, df, max_movies=None):
        """Genera conexiones bridge para todas las películas en el DataFrame"""
        logger.info("="*60)
        logger.info("GENERANDO CONEXIONES BRIDGE PELÍCULA-CONTEXTO")
        logger.info("="*60)
        
        if max_movies:
            df = df.head(max_movies)
            logger.info(f"Procesando primeras {max_movies} películas")
        else:
            logger.info(f"Procesando todas las {len(df)} películas")
        
        total = len(df)
        for idx, row in df.iterrows():
            if idx % 100 == 0:
                logger.info(f"Progreso: {idx}/{total} películas procesadas ({idx/total*100:.1f}%)")
            
            try:
                self.add_movie_context_bridge(row)
            except Exception as e:
                logger.error(f"Error procesando película {row['movieId']}: {e}")
                continue
        
        logger.info("="*60)
        logger.info(f"GENERACIÓN COMPLETADA: {len(self.graph):,} tripletas bridge")
        logger.info("="*60)
    
    def save_graph(self, output_file, format='turtle'):
        """Guarda el grafo en un archivo"""
        logger.info(f"Guardando grafo bridge en {output_file}...")
        self.graph.serialize(destination=output_file, format=format)
        logger.info(f"✓ Grafo guardado exitosamente")
    
    def get_statistics(self):
        """Obtiene estadísticas del grafo generado"""
        stats = {
            'total_triples': len(self.graph),
            'movies_with_compatible_moods': len(set(self.graph.subjects(BRIDGE_NS.compatibleMood, None))),
            'movies_with_compatible_companions': len(set(self.graph.subjects(BRIDGE_NS.compatibleCompanion, None))),
            'movies_with_compatible_energy': len(set(self.graph.subjects(BRIDGE_NS.compatibleEnergyLevel, None))),
            'movies_with_kid_friendly_flag': len(set(self.graph.subjects(BRIDGE_NS.isKidFriendly, None))),
            'movies_with_compatibility_score': len(list(self.graph.subjects(BRIDGE_NS.compatibilityScore, None))),
        }
        return stats


if __name__ == "__main__":
    # Cargar datos de películas
    logger.info("Cargando datos de movies_nlp_enriched.csv...")
    df = pd.read_csv(PROCESSED_DIR / 'movies_nlp_enriched.csv')
    
    logger.info(f"Total de películas en el dataset: {len(df)}")
    
    # Crear generador
    generator = RDFBridgeGenerator()
    
    # Determinar cuántas películas procesar
    max_movies = None
    if len(sys.argv) > 1:
        try:
            max_movies = int(sys.argv[1])
            logger.info(f"Limitando a {max_movies} películas (argumento CLI)")
        except:
            logger.warning(f"Argumento inválido '{sys.argv[1]}', procesando todas")
    else:
        logger.info("Procesando todas las películas")
    
    # Generar conexiones bridge
    generator.generate_from_dataframe(df, max_movies=max_movies)
    
    # Guardar grafo
    output_file = ONTOLOGIES_DIR / 'bridge_data.ttl'
    generator.save_graph(str(output_file), format='turtle')
    
    # Mostrar estadísticas
    stats = generator.get_statistics()
    logger.info("\n" + "="*60)
    logger.info("=== ESTADÍSTICAS DEL GRAFO BRIDGE ===")
    logger.info("="*60)
    for key, value in stats.items():
        logger.info(f"  {key.replace('_', ' ').title()}: {value:,}")
    logger.info("="*60)
    logger.info(f"\n✓ Archivo generado: {output_file}")