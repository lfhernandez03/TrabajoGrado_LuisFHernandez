from rdflib import Graph, Literal, URIRef
import pandas as pd
import logging
import sys
import re
from urllib.parse import quote
from pathlib import Path
import argparse

# Agregar el directorio de config al path para importar namespaces y vocabulario centralizado
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from namespaces import (
    BRIDGE_NS, MOVIE_NS, CONTEXT_NS,
    MOVIE_DATA_NS, CONTEXT_DATA_NS, GENRE_DATA_NS,
    RDF, RDFS, XSD, OWL, bind_all_namespaces
)
from vocabulary_standard import (
    MOOD_VOCABULARY,
    COMPANION_VOCABULARY,
    ENERGY_VOCABULARY,
    normalize_mood,
    normalize_companion,
    normalize_energy,
    validate_all_moods_in_vocabulary,
    validate_all_companions_in_vocabulary
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
        
        # Validar que todos los valores en mapeos sean válidos según vocabulario centralizado
        self._validate_all_mappings()
    
    
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
            'Romance': ['romantico', 'feliz', 'emocionado'],
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
            'Animation': ['familia', 'familia_con_niños'],
            'Family': ['familia', 'familia_con_niños'],
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
    
    def _validate_all_mappings(self):
        """
        Valida que todos los valores en genre_to_moods, genre_to_companions, y 
        genre_to_energy_level sean válidos según la vocabularía centralizada.
        
        Esto previene falsos negativos en queries SPARQL cuando valores normalizados
        difieren entre eljbridge generator y context generator.
        """
        errors = []
        
        # Validar moods
        all_moods = set()
        for moods in self.genre_to_moods.values():
            all_moods.update(moods)
        
        invalid_moods = all_moods - set(MOOD_VOCABULARY.keys())
        if invalid_moods:
            errors.append(f"Invalid moods in genre_to_moods: {invalid_moods}")
            logger.error(f"Invalid moods: {invalid_moods}. Valid moods: {MOOD_VOCABULARY.keys()}")
        
        # Validar companions
        all_companions = set()
        for companions in self.genre_to_companions.values():
            all_companions.update(companions)
        
        invalid_companions = all_companions - set(COMPANION_VOCABULARY.keys())
        if invalid_companions:
            errors.append(f"Invalid companions in genre_to_companions: {invalid_companions}")
            logger.error(f"Invalid companions: {invalid_companions}. Valid companions: {COMPANION_VOCABULARY.keys()}")
        
        # Validar energy levels
        all_energies = set()
        for energies in self.genre_to_energy_level.values():
            all_energies.update(energies)
        
        invalid_energies = all_energies - set(ENERGY_VOCABULARY.keys())
        if invalid_energies:
            errors.append(f"Invalid energy levels in genre_to_energy_level: {invalid_energies}")
            logger.error(f"Invalid energy levels: {invalid_energies}. Valid levels: {ENERGY_VOCABULARY.keys()}")
        
        if errors:
            raise ValueError(f"Vocabulary validation failed: {'; '.join(errors)}")
        else:
            logger.info("✓ All mood, companion, and energy level mappings validated successfully")
    
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
        OPCIÓN C: Almacena el mejor mood Y todos los moods compatibles.
        
        ESTRATEGIA (Opción C - Recomendada):
        - bridge:bestCompatibleMood "nervioso" (para queries rápidas/simples)
        - bridge:allCompatibleMoods "nervioso|emocionado|aventurero" (para matching flexible)
        
        VENTAJAS:
        - Queries simples puede filtrar por bestCompatibleMood (compatibilidad 0.9)
        - Queries sofisticadas pueden parsear allCompatibleMoods para matching secundario
        - SIN cartesian product: un solo literal en cada propiedad
        - COMPATIBLE con SPARQL exactas y con parseo en LLM post-processing
        
        DESVENTAJAS:
        - Requiere parseo en backend si usamos allCompatibleMoods (split por |)
        """
        if main_genre not in self.genre_to_moods:
            logger.debug(f"No mood mappings for genre: {main_genre}")
            return
        
        moods_list = self.genre_to_moods[main_genre]
        
        # Mejor mood (score 0.9)
        best_mood_name = moods_list[0]
        best_score = self._calculate_mood_match_score(main_genre, best_mood_name)
        
        # Todos los moods compatibles (separados por |)
        all_moods_string = "|".join(moods_list)
        
        # Almacenar ambos
        self.graph.add((movie_uri, BRIDGE_NS.bestCompatibleMood, Literal(best_mood_name)))
        self.graph.add((movie_uri, BRIDGE_NS.allCompatibleMoods, Literal(all_moods_string)))
        self.graph.add((movie_uri, BRIDGE_NS.moodMatchScore, 
                      Literal(best_score, datatype=XSD.float)))
    
    def add_companion_mappings(self, movie_uri, main_genre):
        """
        OPCIÓN C: Almacena el mejor companion Y todos los companions compatibles.
        
        Mismo patrón que add_mood_mappings:
        - bridge:bestCompatibleCompanion "pareja"
        - bridge:allCompatibleCompanions "pareja|solo|familia"
        """
        if main_genre not in self.genre_to_companions:
            logger.debug(f"No companion mappings for genre: {main_genre}")
            return
        
        companions_list = self.genre_to_companions[main_genre]
        
        # Mejor companion (score 0.9)
        best_companion = companions_list[0]
        best_score = self._calculate_social_match_score(main_genre, best_companion)
        
        # Todos los companions compatibles (separados por |)
        all_companions_string = "|".join(companions_list)
        
        # Almacenar ambos
        self.graph.add((movie_uri, BRIDGE_NS.bestCompatibleCompanion, Literal(best_companion)))
        self.graph.add((movie_uri, BRIDGE_NS.allCompatibleCompanions, Literal(all_companions_string)))
        self.graph.add((movie_uri, BRIDGE_NS.socialMatchScore, 
                      Literal(best_score, datatype=XSD.float)))
    
    def add_energy_mappings(self, movie_uri, main_genre):
        """
        OPCIÓN C: Almacena el mejor energy level Y todos los levels compatibles.
        
        Mismo patrón que add_mood_mappings:
        - bridge:bestCompatibleEnergyLevel "alto"
        - bridge:allCompatibleEnergyLevels "alto|medio"
        """
        if main_genre not in self.genre_to_energy_level:
            logger.debug(f"No energy mappings for genre: {main_genre}")
            return
        
        energy_list = self.genre_to_energy_level[main_genre]
        
        # Mejor energy level (score 0.9)
        best_energy = energy_list[0]
        best_score = self._calculate_energy_match_score(main_genre, best_energy)
        
        # Todos los energy levels compatibles (separados por |)
        all_energy_string = "|".join(energy_list)
        
        # Almacenar ambos
        self.graph.add((movie_uri, BRIDGE_NS.bestCompatibleEnergyLevel, Literal(best_energy)))
        self.graph.add((movie_uri, BRIDGE_NS.allCompatibleEnergyLevels, Literal(all_energy_string)))
        self.graph.add((movie_uri, BRIDGE_NS.energyMatchScore, 
                      Literal(best_score, datatype=XSD.float)))
    
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
        
        # Calcular compatibility score usando los valores únicos agregados
        mood_score = next((float(s) for s in self.graph.objects(movie_uri, BRIDGE_NS.moodMatchScore)), 0.5)
        social_score = next((float(s) for s in self.graph.objects(movie_uri, BRIDGE_NS.socialMatchScore)), 0.5)
        energy_score = next((float(s) for s in self.graph.objects(movie_uri, BRIDGE_NS.energyMatchScore)), 0.5)
        
        compatibility = self._calculate_compatibility_score(mood_score, social_score, energy_score)
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

    def save_graph_incremental(self, output_file, processed_movie_ids=None, format='turtle'):
        """Hace merge incremental removiendo subgrafos previos por movieId y agregando los nuevos."""
        output_path = Path(output_file)
        if not output_path.exists() or not processed_movie_ids:
            self.save_graph(output_file, format=format)
            return

        logger.info("Modo incremental RDF bridge: fusionando con TTL existente")
        existing_graph = Graph()
        existing_graph.parse(str(output_path), format=format)

        for movie_id in processed_movie_ids:
            movie_prefix = f"{MOVIE_DATA_NS}movie_{movie_id}_"

            resources_to_remove = set()
            for subject in set(existing_graph.subjects()):
                if not isinstance(subject, URIRef):
                    continue
                if str(subject).startswith(movie_prefix):
                    resources_to_remove.add(subject)

            for resource in resources_to_remove:
                existing_graph.remove((resource, None, None))
                existing_graph.remove((None, None, resource))

        existing_graph += self.graph
        self.graph = existing_graph
        self.graph.serialize(destination=str(output_path), format=format)
        logger.info(f"✓ Grafo bridge incremental guardado ({len(self.graph):,} tripletas)")
    
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
    parser = argparse.ArgumentParser(description='Genera conexiones RDF bridge película-contexto')
    parser.add_argument('--max-movies', type=int, default=None, help='Numero maximo de peliculas a procesar')
    parser.add_argument(
        '--no-incremental',
        action='store_true',
        help='Desactiva merge incremental y sobrescribe TTL con el lote actual'
    )
    parser.add_argument('legacy_max_movies', nargs='?', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()

    # Cargar datos de películas
    logger.info("Cargando datos de movies_nlp_enriched.csv...")
    df = pd.read_csv(PROCESSED_DIR / 'movies_nlp_enriched.csv')
    
    logger.info(f"Total de películas en el dataset: {len(df)}")
    
    # Crear generador
    generator = RDFBridgeGenerator()
    
    # Determinar cuántas películas procesar
    max_movies = args.max_movies if args.max_movies is not None else args.legacy_max_movies
    if max_movies:
        logger.info(f"Limitando a {max_movies} películas (argumento CLI)")
    else:
        logger.info("Procesando todas las películas")
    
    # Generar conexiones bridge
    generator.generate_from_dataframe(df, max_movies=max_movies)
    processed_df = df.head(max_movies) if max_movies else df
    processed_movie_ids = [str(movie_id) for movie_id in processed_df['movieId'].tolist()]
    
    # Guardar grafo
    output_file = ONTOLOGIES_DIR / 'bridge_data.ttl'
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
    logger.info("\n" + "="*60)
    logger.info("=== ESTADÍSTICAS DEL GRAFO BRIDGE ===")
    logger.info("="*60)
    for key, value in stats.items():
        logger.info(f"  {key.replace('_', ' ').title()}: {value:,}")
    logger.info("="*60)
    logger.info(f"\n✓ Archivo generado: {output_file}")