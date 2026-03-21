from rdflib import Graph, Literal, URIRef
import logging
from datetime import datetime
import uuid
import sys
from pathlib import Path

# Agregar el directorio de config al path para importar namespaces y vocabulario centralizado
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))
from namespaces import (
    CONTEXT_NS, CONTEXT_DATA_NS,
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
ONTOLOGIES_DIR = DATA_ROOT / "ontologies" / "instances"

class RDFContextGenerator:
    """
    Genera instancias de contextos basadas en context-ontology-v3.ttl
    
    Esta ontología simplificada tiene solo 5 clases esenciales:
    - User: Usuario del sistema
    - ContextSnapshot: Nodo central que captura el momento actual
    - SocialContext: Con quién está viendo
    - EmotionalContext: Cómo se siente y qué necesita emocionalmente
    - RequirementContext: Restricciones prácticas (tiempo, contenido)
    
    Los datos se infieren del lenguaje natural mediante LLM, NO mediante formularios.
    """
    
    # ========================================================================
    # VOCABULARIO CENTRALIZADO - IMPORTADO DE vocabulary_standard.py
    # Estos valores DEBEN usarse para facilitar matching exacto en SPARQL
    # El LLM debe mapear lenguaje natural a estos valores estándar
    # ========================================================================
    # 
    # En lugar de definir vocabularios aquí, importamos desde vocabulary_standard.py
    # para garantizar consistencia con rdf_bridge_generator.py y ontology_query_builder.py
    #
    # Valores disponibles:
    # - MOOD_VOCABULARY: Moods normalizados (feliz, relajado, estresado, etc.)
    # - COMPANION_VOCABULARY: Tipos de compañía (solo, pareja, familia, etc.)
    # - ENERGY_VOCABULARY: Niveles de energía (bajo, medio, alto)
    # - normalize_mood(): Mapea entrada de usuario → valor normalizado
    # - normalize_companion(): Mapea entrada de usuario → valor normalizado
    # - normalize_energy(): Mapea entrada de usuario → valor normalizado
    
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
        
    def _bind_namespaces(self):
        """Vincular namespaces al grafo"""
        self.graph.bind("context", CONTEXT_NS)
        self.graph.bind("contextdata", CONTEXT_DATA_NS)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
    
    def _create_uri(self, prefix, name):
        """Crea URI única para una entidad"""
        safe_name = name.replace(" ", "_").replace("-", "_")
        return CONTEXT_DATA_NS[f"{prefix}_{safe_name}"]
    
    def create_test_users(self):
        """Crea usuarios de prueba"""
        logger.info("Creando usuarios de prueba...")
        
        users = [
            ("user-001", "Luis Hernández", "Usuario de prueba principal"),
            ("user-002", "Camila Arcos", "Usuario de prueba secundario"),
            ("user-003", "Carlos Rodríguez", "Usuario de prueba familiar"),
        ]
        
        for user_id, user_name, description in users:
            user_uri = CONTEXT_DATA_NS[f"User_{user_id}"]
            self.graph.add((user_uri, RDF.type, CONTEXT_NS.User))
            self.graph.add((user_uri, CONTEXT_NS.userID, Literal(user_id, datatype=XSD.string)))
            self.graph.add((user_uri, CONTEXT_NS.userName, Literal(user_name, datatype=XSD.string)))
            self.graph.add((user_uri, RDFS.comment, Literal(description, lang="es")))
        
        logger.info(f"✓ Creados {len(users)} usuarios de prueba")
        return users
    
    def create_example_contexts(self):
        """
        Crea ejemplos de ContextSnapshot con sus contextos relacionados
        Estos ejemplos demuestran cómo el LLM infiere contextos del lenguaje natural
        """
        logger.info("Creando ContextSnapshots de ejemplo...")
        
        # Ejemplo 1: Usuario solo, relajado, con tiempo limitado
        self._create_context_example_1()
        
        # Ejemplo 2: Usuario con familia, buscando algo apto para niños
        self._create_context_example_2()
        
        # Ejemplo 3: Usuario con amigos, grupo grande, busca consenso
        self._create_context_example_3()
        
        # Ejemplo 4: Usuario estresado de madrugada, necesita escapar
        self._create_context_example_4()
        
        logger.info("✓ Creados 4 ContextSnapshots de ejemplo completos")
    
    def _create_context_example_1(self):
        """
        Ejemplo 1: "Quiero ver algo ligero para relajarme después del trabajo, tengo una hora"
        Inferencias:
        - Temporal: Jueves 8:30 PM (día laboral, tarde-noche)
        - Social: Solo
        - Emocional: Relajado, busca desconectar del estrés laboral, energía baja
        - Requisitos: 60 minutos disponibles, nada intenso
        """
        # ContextSnapshot
        ctx_uri = CONTEXT_DATA_NS.Context_Session1
        self.graph.add((ctx_uri, RDF.type, CONTEXT_NS.ContextSnapshot))
        self.graph.add((ctx_uri, CONTEXT_NS.snapshotID, Literal("ctx-001", datatype=XSD.string)))
        self.graph.add((ctx_uri, CONTEXT_NS.requestTimestamp, 
                       Literal("2026-01-09T20:30:00", datatype=XSD.dateTime)))
        self.graph.add((ctx_uri, CONTEXT_NS.dayOfWeek, 
                       Literal("Jueves", datatype=XSD.string)))
        self.graph.add((ctx_uri, CONTEXT_NS.hourOfDay, Literal(20, datatype=XSD.integer)))
        self.graph.add((ctx_uri, CONTEXT_NS.userIntent, 
                       Literal("Buscar algo ligero para relajarme después del trabajo", datatype=XSD.string)))
        self.graph.add((ctx_uri, RDFS.comment, 
                       Literal("Contexto inferido del mensaje: 'Quiero ver algo ligero para relajarme, tengo una hora'. "
                              "Temporal: Jueves 8:30 PM.", lang="es")))
        
        # SocialContext
        social_uri = CONTEXT_DATA_NS.Social_Alone_1
        self.graph.add((social_uri, RDF.type, CONTEXT_NS.SocialContext))
        self.graph.add((social_uri, CONTEXT_NS.companionType, 
                       Literal("solo", datatype=XSD.string)))
        self.graph.add((social_uri, CONTEXT_NS.hasChildren, Literal(False, datatype=XSD.boolean)))
        self.graph.add((social_uri, RDFS.comment, Literal("Usuario viendo solo", lang="es")))
        
        # EmotionalContext
        mood_uri = CONTEXT_DATA_NS.Mood_Relaxed_1
        self.graph.add((mood_uri, RDF.type, CONTEXT_NS.EmotionalContext))
        self.graph.add((mood_uri, CONTEXT_NS.moodDescription, 
                       Literal("relajado", datatype=XSD.string)))
        self.graph.add((mood_uri, CONTEXT_NS.emotionalNeed, 
                       Literal("desconectar del estrés laboral", datatype=XSD.string)))
        self.graph.add((mood_uri, CONTEXT_NS.moodIntensity, Literal(0.7, datatype=XSD.decimal)))
        self.graph.add((mood_uri, CONTEXT_NS.desiredEnergyLevel, 
                       Literal("bajo", datatype=XSD.string)))
        self.graph.add((mood_uri, RDFS.comment, 
                       Literal("Estado inferido de 'quiero relajarme'. Energía baja: "
                              "busca película tranquila que no demande mucha atención.", lang="es")))
        
        # RequirementContext
        req_uri = CONTEXT_DATA_NS.Req_ShortTime_1
        self.graph.add((req_uri, RDF.type, CONTEXT_NS.RequirementContext))
        self.graph.add((req_uri, CONTEXT_NS.availableTime, Literal(60, datatype=XSD.integer)))
        self.graph.add((req_uri, CONTEXT_NS.contentRestrictions, 
                       Literal("nada muy intenso", datatype=XSD.string)))
        self.graph.add((req_uri, RDFS.comment, 
                       Literal("Restricciones inferidas de 'tengo una hora' y 'algo ligero'", lang="es")))
        
        # Relaciones del contexto
        user_uri = CONTEXT_DATA_NS.User_user_001
        self.graph.add((user_uri, CONTEXT_NS.hasCurrentContext, ctx_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.isContextOfUser, user_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.withCompanion, social_uri))
        self.graph.add((social_uri, CONTEXT_NS.isCompanionIn, ctx_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.feelsMood, mood_uri))
        self.graph.add((mood_uri, CONTEXT_NS.isMoodOfSnapshot, ctx_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.hasRequirement, req_uri))
        self.graph.add((req_uri, CONTEXT_NS.isRequirementOf, ctx_uri))
    
    def _create_context_example_2(self):
        """
        Ejemplo 2: "Buscamos algo para ver con los niños este fin de semana"
        Inferencias:
        - Temporal: Sábado 6:00 PM (fin de semana, tarde)
        - Social: Familia con niños, 4 personas
        - Emocional: Alegre/familiar, entretenimiento para todos, energía media
        - Requisitos: Apto para niños, sin violencia/terror, sin lenguaje adulto
        """
        # ContextSnapshot
        ctx_uri = CONTEXT_DATA_NS.Context_Session2
        self.graph.add((ctx_uri, RDF.type, CONTEXT_NS.ContextSnapshot))
        self.graph.add((ctx_uri, CONTEXT_NS.snapshotID, Literal("ctx-002", datatype=XSD.string)))
        self.graph.add((ctx_uri, CONTEXT_NS.requestTimestamp, 
                       Literal("2026-01-10T18:00:00", datatype=XSD.dateTime)))
        self.graph.add((ctx_uri, CONTEXT_NS.dayOfWeek, 
                       Literal("Sábado", datatype=XSD.string)))
        self.graph.add((ctx_uri, CONTEXT_NS.hourOfDay, Literal(18, datatype=XSD.integer)))
        self.graph.add((ctx_uri, CONTEXT_NS.userIntent, 
                       Literal("Película familiar para el fin de semana con los niños", datatype=XSD.string)))
        self.graph.add((ctx_uri, RDFS.comment, 
                       Literal("Contexto inferido de: 'Buscamos algo para ver con los niños este fin de semana'. "
                              "Temporal: Sábado 6:00 PM.", lang="es")))
        
        # SocialContext
        social_uri = CONTEXT_DATA_NS.Social_Family_1
        self.graph.add((social_uri, RDF.type, CONTEXT_NS.SocialContext))
        self.graph.add((social_uri, CONTEXT_NS.companionType, 
                       Literal("familia con niños", datatype=XSD.string)))
        self.graph.add((social_uri, CONTEXT_NS.hasChildren, Literal(True, datatype=XSD.boolean)))
        self.graph.add((social_uri, CONTEXT_NS.groupSize, Literal(4, datatype=XSD.integer)))
        self.graph.add((social_uri, RDFS.comment, Literal("Familia con niños", lang="es")))
        
        # EmotionalContext
        mood_uri = CONTEXT_DATA_NS.Mood_Joyful_1
        self.graph.add((mood_uri, RDF.type, CONTEXT_NS.EmotionalContext))
        self.graph.add((mood_uri, CONTEXT_NS.moodDescription, 
                       Literal("alegre", datatype=XSD.string)))
        self.graph.add((mood_uri, CONTEXT_NS.emotionalNeed, 
                       Literal("entretenimiento para todos", datatype=XSD.string)))
        self.graph.add((mood_uri, CONTEXT_NS.desiredEnergyLevel, 
                       Literal("medio", datatype=XSD.string)))
        self.graph.add((mood_uri, RDFS.comment, 
                       Literal("Tono alegre para ambiente familiar. Energía media: "
                              "entretenimiento dinámico pero no abrumador.", lang="es")))
        
        # RequirementContext
        req_uri = CONTEXT_DATA_NS.Req_KidFriendly_1
        self.graph.add((req_uri, RDF.type, CONTEXT_NS.RequirementContext))
        self.graph.add((req_uri, CONTEXT_NS.contentRestrictions, 
                       Literal("apto para niños, sin violencia, sin terror", datatype=XSD.string)))
        self.graph.add((req_uri, CONTEXT_NS.excludedGenre, 
                       Literal("terror, thriller psicológico", datatype=XSD.string)))
        self.graph.add((req_uri, CONTEXT_NS.negativeConstraint, 
                       Literal("sin escenas intensas, sin lenguaje adulto", datatype=XSD.string)))
        self.graph.add((req_uri, RDFS.comment, 
                       Literal("Restricciones críticas para contexto familiar. "
                              "Incluye exclusiones explícitas de géneros y contenido inapropiado.", lang="es")))
        
        # Relaciones
        self.graph.add((ctx_uri, CONTEXT_NS.withCompanion, social_uri))
        self.graph.add((social_uri, CONTEXT_NS.isCompanionIn, ctx_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.feelsMood, mood_uri))
        self.graph.add((mood_uri, CONTEXT_NS.isMoodOfSnapshot, ctx_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.hasRequirement, req_uri))
        self.graph.add((req_uri, CONTEXT_NS.isRequirementOf, ctx_uri))
    
    def _create_context_example_3(self):
        """
        Ejemplo 3: "Somos 6 amigos, queremos algo que a todos les guste"
        Inferencias:
        - Temporal: Viernes 9:00 PM (fin de semana social)
        - Social: Con amigos, grupo grande (6 personas)
        - Emocional: Necesita consenso grupal, energía alta
        - Requisitos: Crowd-pleaser, sin géneros polarizantes
        """
        # ContextSnapshot
        ctx_uri = CONTEXT_DATA_NS.Context_Session3
        self.graph.add((ctx_uri, RDF.type, CONTEXT_NS.ContextSnapshot))
        self.graph.add((ctx_uri, CONTEXT_NS.snapshotID, Literal("ctx-003", datatype=XSD.string)))
        self.graph.add((ctx_uri, CONTEXT_NS.requestTimestamp, 
                       Literal("2026-01-10T21:00:00", datatype=XSD.dateTime)))
        self.graph.add((ctx_uri, CONTEXT_NS.dayOfWeek, 
                       Literal("Viernes", datatype=XSD.string)))
        self.graph.add((ctx_uri, CONTEXT_NS.hourOfDay, Literal(21, datatype=XSD.integer)))
        self.graph.add((ctx_uri, CONTEXT_NS.userIntent, 
                       Literal("Encontrar película que satisfaga a grupo grande de amigos", datatype=XSD.string)))
        self.graph.add((ctx_uri, RDFS.comment, 
                       Literal("Contexto inferido de: 'Somos 6 amigos, queremos algo que a todos les guste'. "
                              "Temporal: Viernes 9:00 PM.", lang="es")))
        
        # SocialContext
        social_uri = CONTEXT_DATA_NS.Social_Friends_1
        self.graph.add((social_uri, RDF.type, CONTEXT_NS.SocialContext))
        self.graph.add((social_uri, CONTEXT_NS.companionType, 
                       Literal("amigos", datatype=XSD.string)))
        self.graph.add((social_uri, CONTEXT_NS.hasChildren, Literal(False, datatype=XSD.boolean)))
        self.graph.add((social_uri, CONTEXT_NS.groupSize, Literal(6, datatype=XSD.integer)))
        self.graph.add((social_uri, RDFS.comment, 
                       Literal("Grupo grande de amigos. Tamaño crítico: requiere 'crowd-pleasers'", lang="es")))
        
        # EmotionalContext
        mood_uri = CONTEXT_DATA_NS.Mood_Social_1
        self.graph.add((mood_uri, RDF.type, CONTEXT_NS.EmotionalContext))
        self.graph.add((mood_uri, CONTEXT_NS.moodDescription, 
                       Literal("social", datatype=XSD.string)))
        self.graph.add((mood_uri, CONTEXT_NS.emotionalNeed, 
                       Literal("consenso grupal, entretenimiento compartido", datatype=XSD.string)))
        self.graph.add((mood_uri, CONTEXT_NS.desiredEnergyLevel, 
                       Literal("alto", datatype=XSD.string)))
        self.graph.add((mood_uri, RDFS.comment, 
                       Literal("Necesita película con amplio appeal. Energía alta para mantener grupo enganchado.", lang="es")))
        
        # RequirementContext
        req_uri = CONTEXT_DATA_NS.Req_GroupConsensus_1
        self.graph.add((req_uri, RDF.type, CONTEXT_NS.RequirementContext))
        self.graph.add((req_uri, CONTEXT_NS.contentRestrictions, 
                       Literal("nada muy polarizante", datatype=XSD.string)))
        self.graph.add((req_uri, CONTEXT_NS.excludedGenre, 
                       Literal("drama pesado, documental", datatype=XSD.string)))
        self.graph.add((req_uri, CONTEXT_NS.negativeConstraint, 
                       Literal("sin películas muy lentas o contemplativas", datatype=XSD.string)))
        self.graph.add((req_uri, RDFS.comment, 
                       Literal("Exclusiones inferidas para mantener consenso grupal", lang="es")))
        
        # Relaciones
        self.graph.add((ctx_uri, CONTEXT_NS.withCompanion, social_uri))
        self.graph.add((social_uri, CONTEXT_NS.isCompanionIn, ctx_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.feelsMood, mood_uri))
        self.graph.add((mood_uri, CONTEXT_NS.isMoodOfSnapshot, ctx_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.hasRequirement, req_uri))
        self.graph.add((req_uri, CONTEXT_NS.isRequirementOf, ctx_uri))
    
    def _create_context_example_4(self):
        """
        Ejemplo 4: "Son las 3 AM, estoy estresado, necesito desconectar pero nada de terror"
        Inferencias:
        - Temporal: Martes 3:00 AM (madrugada, día laboral)
        - Social: Solo
        - Emocional: Estresado, necesita escapar, pero con energía alta
        - Requisitos: Sin terror, busca intensidad pero no miedo
        """
        # ContextSnapshot
        ctx_uri = CONTEXT_DATA_NS.Context_Session4
        self.graph.add((ctx_uri, RDF.type, CONTEXT_NS.ContextSnapshot))
        self.graph.add((ctx_uri, CONTEXT_NS.snapshotID, Literal("ctx-004", datatype=XSD.string)))
        self.graph.add((ctx_uri, CONTEXT_NS.requestTimestamp, 
                       Literal("2026-01-07T03:00:00", datatype=XSD.dateTime)))
        self.graph.add((ctx_uri, CONTEXT_NS.dayOfWeek, 
                       Literal("Martes", datatype=XSD.string)))
        self.graph.add((ctx_uri, CONTEXT_NS.hourOfDay, Literal(3, datatype=XSD.integer)))
        self.graph.add((ctx_uri, CONTEXT_NS.userIntent, 
                       Literal("Escapar del estrés con película intensa pero no de terror", datatype=XSD.string)))
        self.graph.add((ctx_uri, RDFS.comment, 
                       Literal("Contexto inferido de: 'Son las 3 AM, estoy estresado, necesito desconectar pero nada de terror'. "
                              "Temporal: Martes 3:00 AM (madrugada insomnio).", lang="es")))
        
        # SocialContext
        social_uri = CONTEXT_DATA_NS.Social_Alone_2
        self.graph.add((social_uri, RDF.type, CONTEXT_NS.SocialContext))
        self.graph.add((social_uri, CONTEXT_NS.companionType, 
                       Literal("solo", datatype=XSD.string)))
        self.graph.add((social_uri, CONTEXT_NS.hasChildren, Literal(False, datatype=XSD.boolean)))
        self.graph.add((social_uri, RDFS.comment, 
                       Literal("Usuario solo de madrugada", lang="es")))
        
        # EmotionalContext
        mood_uri = CONTEXT_DATA_NS.Mood_Stressed_1
        self.graph.add((mood_uri, RDF.type, CONTEXT_NS.EmotionalContext))
        self.graph.add((mood_uri, CONTEXT_NS.moodDescription, 
                       Literal("estresado", datatype=XSD.string)))
        self.graph.add((mood_uri, CONTEXT_NS.emotionalNeed, 
                       Literal("escapar del estrés, desconectar", datatype=XSD.string)))
        self.graph.add((mood_uri, CONTEXT_NS.moodIntensity, Literal(0.8, datatype=XSD.decimal)))
        self.graph.add((mood_uri, CONTEXT_NS.desiredEnergyLevel, 
                       Literal("alto", datatype=XSD.string)))
        self.graph.add((mood_uri, RDFS.comment, 
                       Literal("Paradoja emocional: estresado pero busca energía alta. "
                              "Quiere algo épico/intenso que lo saque del estrés, no terror que lo empeore.", lang="es")))
        
        # RequirementContext
        req_uri = CONTEXT_DATA_NS.Req_NoHorror_1
        self.graph.add((req_uri, RDF.type, CONTEXT_NS.RequirementContext))
        self.graph.add((req_uri, CONTEXT_NS.excludedGenre, Literal("terror, horror", datatype=XSD.string)))
        self.graph.add((req_uri, CONTEXT_NS.negativeConstraint, 
                       Literal("sin sustos, sin atmósferas opresivas", datatype=XSD.string)))
        self.graph.add((req_uri, RDFS.comment, 
                       Literal("Exclusión explícita de terror. Prefiere acción/aventura épica para canalizar energía.", lang="es")))
        
        # Relaciones
        self.graph.add((ctx_uri, CONTEXT_NS.withCompanion, social_uri))
        self.graph.add((social_uri, CONTEXT_NS.isCompanionIn, ctx_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.feelsMood, mood_uri))
        self.graph.add((mood_uri, CONTEXT_NS.isMoodOfSnapshot, ctx_uri))
        self.graph.add((ctx_uri, CONTEXT_NS.hasRequirement, req_uri))
        self.graph.add((req_uri, CONTEXT_NS.isRequirementOf, ctx_uri))
    
    def generate_all_contexts(self):
        """Genera todas las instancias de contexto según ontología v3"""
        logger.info("="*70)
        logger.info("GENERANDO INSTANCIAS DE CONTEXTO (Ontología v3 - GraphRAG)")
        logger.info("="*70)
        logger.info("Ontología simplificada con 5 clases:")
        logger.info("  - User")
        logger.info("  - ContextSnapshot (nodo central)")
        logger.info("  - SocialContext")
        logger.info("  - EmotionalContext")
        logger.info("  - RequirementContext")
        logger.info("="*70)
        
        # Crear usuarios de prueba
        self.create_test_users()
        
        # Crear contextos de ejemplo completos
        self.create_example_contexts()
        
        logger.info("="*70)
        logger.info(f"GENERACIÓN COMPLETADA: {len(self.graph):,} tripletas")
        logger.info("="*70)
        
        return self.graph
    
    def save_graph(self, output_file, format='turtle'):
        """Guarda el grafo en un archivo"""
        logger.info(f"\nGuardando grafo en {output_file}...")
        self.graph.serialize(destination=output_file, format=format)
        logger.info(f"✓ Grafo guardado exitosamente")
    
    def get_statistics(self):
        """Obtiene estadísticas del grafo generado"""
        stats = {
            'total_triples': len(self.graph),
            'users': len(list(self.graph.subjects(RDF.type, CONTEXT_NS.User))),
            'context_snapshots': len(list(self.graph.subjects(RDF.type, CONTEXT_NS.ContextSnapshot))),
            'social_contexts': len(list(self.graph.subjects(RDF.type, CONTEXT_NS.SocialContext))),
            'emotional_contexts': len(list(self.graph.subjects(RDF.type, CONTEXT_NS.EmotionalContext))),
            'requirement_contexts': len(list(self.graph.subjects(RDF.type, CONTEXT_NS.RequirementContext))),
        }
        return stats
    
    @classmethod
    def validate_energy_level(cls, value):
        """
        Valida que el nivel de energía sea uno de los valores normalizados
        
        Args:
            value: Valor a validar
            
        Returns:
            El valor normalizado si es válido
            
        Raises:
            ValueError: Si el valor no es válido
        """
        if value not in cls.ENERGY_LEVELS.values():
            valid_values = ', '.join(cls.ENERGY_LEVELS.values())
            raise ValueError(f"Nivel de energía '{value}' no válido. Valores permitidos: {valid_values}")
        return value
    
    @classmethod
    def validate_companion_type(cls, value):
        """
        Valida que el tipo de compañía sea uno de los valores normalizados
        
        Args:
            value: Valor a validar
            
        Returns:
            El valor normalizado si es válido
            
        Raises:
            ValueError: Si el valor no es válido
        """
        if value not in cls.COMPANION_TYPES.values():
            valid_values = ', '.join(cls.COMPANION_TYPES.values())
            raise ValueError(f"Tipo de compañía '{value}' no válido. Valores permitidos: {valid_values}")
        return value
    
    @classmethod
    def validate_day_of_week(cls, value):
        """
        Valida que el día de la semana sea uno de los valores normalizados
        
        Args:
            value: Valor a validar
            
        Returns:
            El valor normalizado si es válido
            
        Raises:
            ValueError: Si el valor no es válido
        """
        if value not in cls.DAYS_OF_WEEK.values():
            valid_values = ', '.join(cls.DAYS_OF_WEEK.values())
            raise ValueError(f"Día de la semana '{value}' no válido. Valores permitidos: {valid_values}")
        return value
    
    @classmethod
    def get_normalized_values_documentation(cls):
        """
        Retorna documentación sobre los valores normalizados
        Útil para el LLM que debe extraer contextos del lenguaje natural
        """
        doc = """
        ========================================================================
        VOCABULARIO CONTROLADO - VALORES NORMALIZADOS
        ========================================================================
        
        El LLM DEBE mapear lenguaje natural a estos valores exactos para 
        facilitar matching SPARQL y evitar errores de coincidencia.
        
        1. NIVELES DE ENERGÍA (desiredEnergyLevel):
           - "bajo"  : Contenido tranquilo, relajante, contemplativo
           - "medio" : Contenido moderado, equilibrado
           - "alto"  : Contenido intenso, dinámico, emocionante
        
        2. TIPOS DE COMPAÑÍA (companionType):
           - "solo"                    : Viendo solo
           - "pareja"                  : Con pareja romántica
           - "familia"                 : Con familia (sin niños pequeños)
           - "familia con niños"       : Con niños presentes (CRÍTICO para filtros)
           - "amigos"                  : Con amigos
           - "compañeros de trabajo"   : Con colegas
           - "grupo grande"            : Grupo de 7+ personas
        
        3. ESTADOS DE ÁNIMO SUGERIDOS (moodDescription):
           Valores preferidos (puede ser flexible pero estos son estándar):
           - "feliz", "alegre", "relajado", "estresado", "triste"
           - "nostálgico", "curioso", "aburrido", "romántico"
           - "reflexivo", "aventurero", "social", "contemplativo"
        
        4. DÍAS DE LA SEMANA (dayOfWeek):
           - "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"
           IMPORTANTE: Primera letra mayúscula, resto minúsculas con tilde
        
        ========================================================================
        EJEMPLOS DE MAPEO LLM → RDF
        ========================================================================
        
        Usuario: "Estoy muy estresado, necesito algo relajante"
        LLM infiere:
          - moodDescription = "estresado"
          - desiredEnergyLevel = "bajo"
          - emotionalNeed = "relajación"
        
        Usuario: "Somos 4 con los niños"
        LLM infiere:
          - companionType = "familia con niños"
          - hasChildren = true
          - groupSize = 4
        
        Usuario: "Quiero algo épico y emocionante"
        LLM infiere:
          - desiredEnergyLevel = "alto"
          - emotionalNeed = "emoción"
        
        Usuario: "Es viernes por la noche con los amigos"
        LLM infiere:
          - dayOfWeek = "Viernes"
          - hourOfDay = 21 (estimado)
          - companionType = "amigos"
        
        ========================================================================
        """
        return doc


if __name__ == "__main__":
    # Mostrar documentación de valores normalizados
    logger.info(RDFContextGenerator.get_normalized_values_documentation())
    
    # Crear generador
    generator = RDFContextGenerator()
    
    # Generar todas las instancias
    generator.generate_all_contexts()
    
    # Guardar grafo
    output_file = ONTOLOGIES_DIR / 'contexts_data.ttl'
    generator.save_graph(str(output_file), format='turtle')
    
    # Mostrar estadísticas
    stats = generator.get_statistics()
    logger.info("\n" + "="*70)
    logger.info("ESTADÍSTICAS DEL GRAFO DE CONTEXTOS")
    logger.info("="*70)
    logger.info(f"  Total de tripletas: {stats['total_triples']:,}")
    logger.info(f"  Usuarios: {stats['users']}")
    logger.info(f"  Context Snapshots: {stats['context_snapshots']}")
    logger.info(f"  Social Contexts: {stats['social_contexts']}")
    logger.info(f"  Emotional Contexts: {stats['emotional_contexts']}")
    logger.info(f"  Requirement Contexts: {stats['requirement_contexts']}")
    logger.info("="*70)
    logger.info(f"\n✓ Archivo generado: {output_file}")
    logger.info("\nESTRUCTURA DE DATOS:")
    logger.info("  Cada ContextSnapshot representa un momento de interacción")
    logger.info("  Los datos se infieren del lenguaje natural (GraphRAG approach)")
    logger.info("  Navegación bidireccional completa entre todas las entidades")
    logger.info("\nVALORES NORMALIZADOS:")
    logger.info("  - desiredEnergyLevel: bajo | medio | alto")
    logger.info("  - companionType: solo | pareja | familia | familia con niños | amigos | etc.")
    logger.info("  - dayOfWeek: Lunes | Martes | ... | Domingo (con mayúscula inicial)")
    logger.info("="*70)
