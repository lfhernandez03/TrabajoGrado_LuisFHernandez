"""
Generador de Diagramas de Ontologías para el Trabajo de Grado.

Genera 5 diagramas en formato PNG/SVG desde los archivos TTL:
  1. movie-ontology  → Jerarquía de clases + datatype properties
  2. context-ontology → Clases + object/datatype properties
  3. bridge-ontology  → Propiedades de puente entre ontologías
  4. integration      → Vista general de las 3 ontologías conectadas
  5. flow             → Flujo del pipeline GraphRAG

Requisitos:
  pip install rdflib graphviz
  Graphviz binario: https://graphviz.org/download/
    Windows: winget install Graphviz.Graphviz
    Luego asegurarse de que 'dot' esté en el PATH del sistema.

Uso:
  python generate_diagrams.py [--format png|svg|pdf] [--output-dir <dir>]

"""

import argparse
import hashlib
import os
import re
import sys
from collections import defaultdict
from typing import Optional

try:
    from rdflib import Graph, RDF, RDFS, OWL, URIRef, BNode, Namespace
    from rdflib.namespace import XSD
except ImportError:
    print("❌ Error: rdflib no encontrado. Instálalo con: pip install rdflib")
    sys.exit(1)

try:
    import graphviz
except ImportError:
    print("❌ Error: graphviz (Python) no encontrado. Instálalo con: pip install graphviz")
    sys.exit(1)


# ──────────────────────────────────────────────────────────────
# Configuración de rutas y namespaces
# ──────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ONTOLOGY_BASE_DIR = os.path.join(SCRIPT_DIR, '..', 'ontologies', 'base')
ONTOLOGY_BRIDGE_DIR = os.path.join(SCRIPT_DIR, '..', 'ontologies', 'bridge')
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'docs', 'figures')

MOVIE_NS = Namespace("http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#")
CONTEXT_NS = Namespace("http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#")
BRIDGE_NS = Namespace("http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#")

# ──────────────────────────────────────────────────────────────
# Paleta de colores
# ──────────────────────────────────────────────────────────────

COLORS = {
    # Movie ontology
    'movie_class': '#2563EB',
    'movie_class_light': '#DBEAFE',
    'movie_cluster': '#E8F0FE',

    # Context ontology
    'context_class': '#D97706',
    'context_class_light': '#FEF3C7',
    'context_cluster': '#FFF7ED',

    # Bridge ontology
    'bridge_prop': '#059669',
    'bridge_cluster': '#ECFDF5',
    'bridge_class': '#059669',

    # General
    'font_light': '#FFFFFF',
    'font_dark': '#1F2937',
    'edge_obj_prop': '#4B5563',
    'edge_subclass': '#9CA3AF',
    'edge_inverse': '#D1D5DB',
    'root_class': '#7C3AED',
    'datatype_bg': '#F3F4F6',
}


# ──────────────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────────────

def safe_id(uri) -> str:
    """Convierte una URI a un ID seguro para Graphviz (sin caracteres especiales)."""
    s = str(uri)
    # Crear un ID legible basado en el fragment o el final de la URI
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', s)
    # Limitar longitud y evitar colisiones
    if len(clean) > 80:
        h = hashlib.md5(s.encode()).hexdigest()[:8]
        clean = clean[-60:] + '_' + h
    return clean


def short_name(uri) -> str:
    """Extrae el nombre corto de una URI."""
    s = str(uri)
    if '#' in s:
        return s.split('#')[-1]
    elif '/' in s:
        return s.split('/')[-1]
    return s


def get_label(g: Graph, uri: URIRef, lang: str = 'es') -> str:
    """Obtiene rdfs:label en el idioma preferido, o fallback al nombre corto."""
    for label in g.objects(uri, RDFS.label):
        if hasattr(label, 'language') and label.language == lang:
            return str(label)
    for label in g.objects(uri, RDFS.label):
        if hasattr(label, 'language') and label.language == 'en':
            return str(label)
    for label in g.objects(uri, RDFS.label):
        return str(label)
    return short_name(uri)


def is_blank(node) -> bool:
    return isinstance(node, BNode)


def belongs_to_ns(uri: URIRef, ns: Namespace) -> bool:
    return str(uri).startswith(str(ns))


# ──────────────────────────────────────────────────────────────
# Extracción de información desde RDF
# ──────────────────────────────────────────────────────────────

def extract_classes(g: Graph, ns: Optional[Namespace] = None):
    classes = set()
    for s in g.subjects(RDF.type, OWL.Class):
        if is_blank(s):
            continue
        if ns and not belongs_to_ns(s, ns):
            continue
        classes.add(s)
    return classes


def extract_subclass_relations(g: Graph, ns: Optional[Namespace] = None):
    relations = []
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if is_blank(s) or is_blank(o):
            continue
        if ns and (not belongs_to_ns(s, ns) or not belongs_to_ns(o, ns)):
            continue
        relations.append((s, o))
    return relations


def extract_object_properties(g: Graph, ns: Optional[Namespace] = None):
    props = []
    for s in g.subjects(RDF.type, OWL.ObjectProperty):
        if is_blank(s):
            continue
        if ns and not belongs_to_ns(s, ns):
            continue
        domain = g.value(s, RDFS.domain)
        range_ = g.value(s, RDFS.range)
        inverse = g.value(s, OWL.inverseOf)
        if domain and is_blank(domain):
            domain = None
        if range_ and is_blank(range_):
            range_ = None
        props.append({
            'uri': s,
            'name': short_name(s),
            'label': get_label(g, s),
            'domain': domain,
            'range': range_,
            'inverse': inverse,
        })
    return props


def extract_datatype_properties(g: Graph, ns: Optional[Namespace] = None):
    by_domain = defaultdict(list)
    for s in g.subjects(RDF.type, OWL.DatatypeProperty):
        if is_blank(s):
            continue
        if ns and not belongs_to_ns(s, ns):
            continue
        domain = g.value(s, RDFS.domain)
        if domain and is_blank(domain):
            continue
        range_ = g.value(s, RDFS.range)
        range_label = short_name(range_) if range_ else 'string'
        prop_name = short_name(s)
        if domain:
            by_domain[str(domain)].append(f"{prop_name}: {range_label}")
    return by_domain


# ──────────────────────────────────────────────────────────────
# Generador: Movie Ontology
# ──────────────────────────────────────────────────────────────

def generate_movie_ontology_diagram(g: Graph, output_path: str, fmt: str):
    """Genera diagrama de la ontología de dominio cinematográfico."""

    dot = graphviz.Digraph(
        name='movie_ontology',
        comment='Ontologia de Dominio Cinematografico',
        format=fmt,
        engine='dot',
    )
    dot.attr(
        rankdir='TB',
        fontname='Helvetica',
        fontsize='14',
        label='<<B>Ontologia de Dominio Cinematografico</B><BR/><I>movie-ontology v1.0</I>>',
        labelloc='t',
        pad='0.5',
        nodesep='0.4',
        ranksep='0.6',
        bgcolor='white',
    )
    dot.attr('node', fontname='Helvetica', fontsize='10', style='filled')
    dot.attr('edge', fontname='Helvetica', fontsize='8')

    classes = extract_classes(g, MOVIE_NS)
    subclass_rels = extract_subclass_relations(g, MOVIE_NS)
    datatype_props = extract_datatype_properties(g, MOVIE_NS)
    obj_props = extract_object_properties(g, MOVIE_NS)

    # Grupos tematicos para clustering visual
    groups_config = [
        ('Movie', {'Movie', 'FeatureFilm', 'Documentary', 'ShortFilm', 'AnimatedFilm'}, '#DBEAFE'),
        ('Person', {'Person', 'Director', 'Actor', 'Producer', 'Screenwriter',
                    'Cinematographer', 'Composer', 'Editor'}, '#EDE9FE'),
        ('Genre', {'Genre', 'MainGenre', 'Subgenre'}, '#D1FAE5'),
        ('Narrative', {'NarrativeElement', 'Theme', 'Tone', 'DramaticTone',
                       'ComedyTone', 'SuspensefulTone', 'RomanticTone', 'DarkTone',
                       'PlotStructure', 'LinearNarrative', 'NonLinearNarrative',
                       'EpisodicNarrative'}, '#FEF3C7'),
        ('Role', {'Role', 'ActingRole', 'LeadRole', 'SupportingRole', 'CameoRole',
                  'CreativeRole', 'PrimaryRole', 'CollaborativeRole'}, '#FCE7F3'),
        ('Cultural', {'CulturalContext', 'CountryOfOrigin', 'HistoricalPeriod',
                      'Contemporary', 'Historical', 'Futuristic', 'Language'}, '#E0E7FF'),
        ('Rating', {'Rating', 'CriticRating', 'UserRating', 'AggregateRating',
                    'AgeRatingCategory', 'GeneralAudience', 'ParentalGuidance',
                    'Teen', 'Mature', 'AdultOnly'}, '#FEE2E2'),
        ('Award', {'Award', 'FilmAward', 'BestPicture', 'BestForeignFilm', 'BestDocumentary',
                   'PersonAward', 'BestDirector', 'BestActor', 'BestActress',
                   'BestSupportingActor', 'BestSupportingActress', 'BestScreenplay',
                   'AwardParticipation'}, '#FEF9C3'),
        ('Core', {'Entity', 'Attribute', 'Keyword', 'ProductionCompany',
                  'Certification', 'MovieCluster'}, '#F3F4F6'),
    ]

    for group_name, group_classes, bg_color in groups_config:
        with dot.subgraph(name=f'cluster_{group_name}') as c:
            c.attr(
                label=f'<<B>{group_name}</B>>',
                style='rounded,filled',
                fillcolor=bg_color,
                color='#D1D5DB',
                fontname='Helvetica',
                fontsize='11',
            )
            for cls in classes:
                name = short_name(cls)
                if name not in group_classes:
                    continue
                sid = safe_id(cls)

                dt_list = datatype_props.get(str(cls), [])
                if dt_list and len(dt_list) <= 12:
                    attrs_str = '\\l'.join(dt_list) + '\\l'
                    node_label = f'{{{name}|{attrs_str}}}'
                    c.node(sid, node_label, shape='record',
                           fillcolor=COLORS['movie_class'],
                           fontcolor=COLORS['font_light'])
                elif dt_list:
                    attrs_str = '\\l'.join(dt_list[:8]) + f'\\l... (+{len(dt_list) - 8} mas)\\l'
                    node_label = f'{{{name}|{attrs_str}}}'
                    c.node(sid, node_label, shape='record',
                           fillcolor=COLORS['movie_class'],
                           fontcolor=COLORS['font_light'])
                else:
                    is_root = name in {'Entity', 'Attribute'}
                    c.node(sid, name, shape='ellipse',
                           fillcolor=COLORS['root_class'] if is_root else COLORS['movie_class'],
                           fontcolor=COLORS['font_light'])

    # Relaciones subClassOf
    for child, parent in subclass_rels:
        dot.edge(safe_id(child), safe_id(parent),
                 style='dashed', color=COLORS['edge_subclass'], arrowhead='empty')

    # Object Properties principales
    IMPORTANT_PROPS = {
        'hasDirector', 'hasActor', 'hasGenre', 'hasKeyword',
        'hasProductionCompany', 'belongsToCluster', 'isSimilarTo',
        'hasRole', 'inMovie', 'hasTone', 'hasTheme',
        'hasCountryOfOrigin', 'hasLanguage', 'hasAgeRating', 'hasRating',
        'hasAwardParticipation', 'hasAward', 'hasCertification',
    }
    for prop in obj_props:
        if prop['name'] in IMPORTANT_PROPS and prop['domain'] and prop['range']:
            dot.edge(safe_id(prop['domain']), safe_id(prop['range']),
                     label=prop['name'],
                     color=COLORS['edge_obj_prop'],
                     fontcolor=COLORS['edge_obj_prop'],
                     style='bold', arrowhead='vee', fontsize='7')

    dot.render(output_path, cleanup=True)
    print(f"  ✅ movie-ontology -> {output_path}.{fmt}")


# ──────────────────────────────────────────────────────────────
# Generador: Context Ontology
# ──────────────────────────────────────────────────────────────

def generate_context_ontology_diagram(g: Graph, output_path: str, fmt: str):
    """Genera diagrama de la ontologia de contexto de usuario."""

    dot = graphviz.Digraph(
        name='context_ontology',
        comment='Ontologia de Contexto de Usuario',
        format=fmt,
        engine='dot',
    )
    dot.attr(
        rankdir='TB',
        fontname='Helvetica',
        fontsize='14',
        label='<<B>Ontologia de Contexto de Usuario</B><BR/><I>context-ontology v3.0 - Interaction-Driven</I>>',
        labelloc='t',
        pad='0.5',
        nodesep='0.6',
        ranksep='0.8',
        bgcolor='white',
    )
    dot.attr('node', fontname='Helvetica', fontsize='10', style='filled')
    dot.attr('edge', fontname='Helvetica', fontsize='9')

    classes = extract_classes(g, CONTEXT_NS)
    datatype_props = extract_datatype_properties(g, CONTEXT_NS)
    obj_props = extract_object_properties(g, CONTEXT_NS)

    for cls in classes:
        name = short_name(cls)
        sid = safe_id(cls)
        dt_list = datatype_props.get(str(cls), [])

        if dt_list:
            attrs_str = '\\l'.join(dt_list) + '\\l'
            node_label = f'{{{name}|{attrs_str}}}'
            dot.node(sid, node_label, shape='record',
                     fillcolor=COLORS['context_class'],
                     fontcolor=COLORS['font_light'])
        else:
            dot.node(sid, name, shape='ellipse',
                     fillcolor=COLORS['context_class'],
                     fontcolor=COLORS['font_light'],
                     width='1.5')

    # Object Properties
    drawn_edges = set()
    for prop in obj_props:
        if prop['domain'] and prop['range'] and not is_blank(prop['domain']) and not is_blank(prop['range']):
            d_id = safe_id(prop['domain'])
            r_id = safe_id(prop['range'])
            edge_key = (d_id, r_id, prop['name'])
            reverse_pair = (r_id, d_id)
            if edge_key not in drawn_edges and reverse_pair not in {(k[0], k[1]) for k in drawn_edges}:
                inverse_label = ''
                if prop['inverse'] and not is_blank(prop['inverse']):
                    inverse_label = f' / {short_name(prop["inverse"])}'

                dot.edge(d_id, r_id,
                         label=f'{prop["name"]}{inverse_label}',
                         color=COLORS['context_class'],
                         fontcolor=COLORS['font_dark'],
                         style='bold', arrowhead='vee')
                drawn_edges.add(edge_key)

    dot.render(output_path, cleanup=True)
    print(f"  ✅ context-ontology -> {output_path}.{fmt}")


# ──────────────────────────────────────────────────────────────
# Generador: Bridge Ontology
# ──────────────────────────────────────────────────────────────

def generate_bridge_ontology_diagram(g: Graph, output_path: str, fmt: str):
    """Genera diagrama de la ontologia de interconexion (bridge)."""

    dot = graphviz.Digraph(
        name='bridge_ontology',
        comment='Ontologia de Interconexion (Bridge)',
        format=fmt,
        engine='dot',
    )
    dot.attr(
        rankdir='LR',
        fontname='Helvetica',
        fontsize='14',
        label='<<B>Ontologia de Interconexion (Bridge)</B><BR/><I>bridge-ontology v2.0 - Alineacion Semantica Dinamica</I>>',
        labelloc='t',
        pad='0.5',
        nodesep='0.5',
        ranksep='1.2',
        bgcolor='white',
    )
    dot.attr('node', fontname='Helvetica', fontsize='10', style='filled')
    dot.attr('edge', fontname='Helvetica', fontsize='8')

    # Clases externas referenciadas (movie-ontology)
    with dot.subgraph(name='cluster_movie') as c:
        c.attr(label='<<B>movie-ontology</B>>',
               style='rounded,filled',
               fillcolor=COLORS['movie_cluster'],
               color=COLORS['movie_class'],
               fontname='Helvetica')
        c.node('mo_Movie', 'Movie', shape='ellipse',
               fillcolor=COLORS['movie_class'], fontcolor=COLORS['font_light'])

    # Clases externas referenciadas (context-ontology)
    with dot.subgraph(name='cluster_context') as c:
        c.attr(label='<<B>context-ontology</B>>',
               style='rounded,filled',
               fillcolor=COLORS['context_cluster'],
               color=COLORS['context_class'],
               fontname='Helvetica')
        c.node('co_ContextSnapshot', 'ContextSnapshot', shape='ellipse',
               fillcolor=COLORS['context_class'], fontcolor=COLORS['font_light'])
        c.node('co_RequirementContext', 'RequirementContext', shape='ellipse',
               fillcolor=COLORS['context_class'], fontcolor=COLORS['font_light'])
        c.node('co_EmotionalContext', 'EmotionalContext', shape='ellipse',
               fillcolor=COLORS['context_class'], fontcolor=COLORS['font_light'])
        c.node('co_SocialContext', 'SocialContext', shape='ellipse',
               fillcolor=COLORS['context_class'], fontcolor=COLORS['font_light'])
        c.node('co_User', 'User', shape='ellipse',
               fillcolor=COLORS['context_class'], fontcolor=COLORS['font_light'])

    # Bridge Data Properties (scoring) box
    bridge_dp = extract_datatype_properties(g, BRIDGE_NS)
    scoring_props = bridge_dp.get(str(MOVIE_NS.Movie), [])
    if scoring_props:
        attrs_str = '\\l'.join(scoring_props[:10]) + '\\l'
        score_label = f'{{Scoring Metrics|{attrs_str}}}'
        dot.node('scoring_box', score_label,
                 shape='record', fillcolor=COLORS['bridge_cluster'],
                 fontcolor=COLORS['font_dark'], color=COLORS['bridge_prop'],
                 style='filled,bold')
        dot.edge('mo_Movie', 'scoring_box',
                 label='bridge data props',
                 style='dotted', color=COLORS['bridge_prop'],
                 fontcolor=COLORS['bridge_prop'])

    # Bridge Object Properties
    bridge_relations = [
        ('mo_Movie', 'co_ContextSnapshot', 'isRecommendedIn', 'recommends'),
        ('mo_Movie', 'co_RequirementContext', 'satisfiesRequirement', 'isSatisfiedBy'),
        ('mo_Movie', 'co_EmotionalContext', 'alignsWithMood', 'isAlignedWith'),
        ('mo_Movie', 'co_SocialContext', 'suitableForSocialContext', 'isSuitableFor'),
        ('co_User', 'mo_Movie', 'hasWatched', 'wasWatchedBy'),
        ('co_User', 'mo_Movie', 'hasRated', 'wasRatedBy'),
    ]
    for src, tgt, fwd, inv in bridge_relations:
        dot.edge(src, tgt,
                 label=f'<<B>{fwd}</B><BR/><I>inv: {inv}</I>>',
                 color=COLORS['bridge_prop'],
                 fontcolor=COLORS['font_dark'],
                 style='bold', arrowhead='vee', penwidth='2')

    # SWRL rules box
    swrl_label = (
        '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">'
        '<TR><TD BGCOLOR="#FEF3C7"><B>SWRL Rules</B></TD></TR>'
        '<TR><TD ALIGN="LEFT" BGCOLOR="#FFFBEB">'
        '1. runtime ≤ availableTime<BR ALIGN="LEFT"/>'
        '   ⟹ satisfiesRequirement<BR ALIGN="LEFT"/><BR ALIGN="LEFT"/>'
        '2. hasChildren=true<BR ALIGN="LEFT"/>'
        '   ⟹ solo cert G/PG<BR ALIGN="LEFT"/><BR ALIGN="LEFT"/>'
        '3. excludedGenre match<BR ALIGN="LEFT"/>'
        '   ⟹ violatesConstraint<BR ALIGN="LEFT"/>'
        '</TD></TR></TABLE>>'
    )
    dot.node('swrl_box', swrl_label,
             shape='plaintext', fillcolor='#FEF3C7',
             fontcolor=COLORS['font_dark'], color='#D97706',
             style='filled')
    dot.edge('swrl_box', 'mo_Movie',
             style='dotted', color='#D97706',
             label='infiere', fontcolor='#D97706')

    dot.render(output_path, cleanup=True)
    print(f"  ✅ bridge-ontology -> {output_path}.{fmt}")


# ──────────────────────────────────────────────────────────────
# Generador: Diagrama de Integracion General
# ──────────────────────────────────────────────────────────────

def generate_integration_diagram(output_path: str, fmt: str):
    """Genera diagrama de alto nivel mostrando como se conectan las 3 ontologias."""

    dot = graphviz.Digraph(
        name='integration',
        comment='Arquitectura Modular de Ontologias',
        format=fmt,
        engine='neato',
    )
    dot.attr(
        fontname='Helvetica',
        fontsize='14',
        label='<<B>Arquitectura Modular de Ontologias para GraphRAG</B><BR/>'
              '<I>Sistema de Recomendacion de Peliculas Basado en Contexto</I>>',
        labelloc='t',
        overlap='false',
        splines='true',
        bgcolor='white',
        pad='1',
    )
    dot.attr('node', fontname='Helvetica', fontsize='9', style='filled')
    dot.attr('edge', fontname='Helvetica', fontsize='8')

    # movie-ontology cluster
    with dot.subgraph(name='cluster_movie') as c:
        c.attr(
            label='<<B>movie-ontology v1.0</B><BR/><I>Dominio Cinematografico</I>>',
            style='rounded,filled',
            fillcolor='#DBEAFE',
            color=COLORS['movie_class'],
            fontname='Helvetica',
            penwidth='2',
        )
        for name in ['Movie', 'Person', 'Genre', 'Attribute', 'MovieCluster']:
            c.node(f'mo_{name}', name, shape='ellipse',
                   fillcolor=COLORS['movie_class'], fontcolor=COLORS['font_light'],
                   width='1.2')
        c.edge('mo_Movie', 'mo_Person', label='hasDirector\nhasActor',
               color='#6B7280', fontcolor='#6B7280', fontsize='7')
        c.edge('mo_Movie', 'mo_Genre', label='hasGenre',
               color='#6B7280', fontcolor='#6B7280', fontsize='7')
        c.edge('mo_Movie', 'mo_Attribute', label='hasKeyword\nhasTone',
               color='#6B7280', fontcolor='#6B7280', fontsize='7')
        c.edge('mo_Movie', 'mo_MovieCluster', label='belongsToCluster',
               color='#6B7280', fontcolor='#6B7280', fontsize='7')

    # context-ontology cluster
    with dot.subgraph(name='cluster_context') as c:
        c.attr(
            label='<<B>context-ontology v3.0</B><BR/><I>Contexto de Interaccion</I>>',
            style='rounded,filled',
            fillcolor='#FEF3C7',
            color=COLORS['context_class'],
            fontname='Helvetica',
            penwidth='2',
        )
        for name in ['User', 'ContextSnapshot', 'SocialContext',
                     'EmotionalContext', 'RequirementContext']:
            c.node(f'co_{name}', name, shape='ellipse',
                   fillcolor=COLORS['context_class'], fontcolor=COLORS['font_light'],
                   width='1.3')
        c.edge('co_User', 'co_ContextSnapshot', label='hasCurrentContext',
               color='#92400E', fontcolor='#92400E', fontsize='7')
        c.edge('co_ContextSnapshot', 'co_SocialContext', label='withCompanion',
               color='#92400E', fontcolor='#92400E', fontsize='7')
        c.edge('co_ContextSnapshot', 'co_EmotionalContext', label='feelsMood',
               color='#92400E', fontcolor='#92400E', fontsize='7')
        c.edge('co_ContextSnapshot', 'co_RequirementContext', label='hasRequirement',
               color='#92400E', fontcolor='#92400E', fontsize='7')

    # bridge-ontology (nodo central)
    dot.node(
        'bridge_center',
        '<<B>bridge-ontology v2.0</B><BR/><I>Alineacion Semantica</I><BR/><BR/>'
        'isRecommendedIn<BR/>'
        'satisfiesRequirement<BR/>'
        'alignsWithMood<BR/>'
        'suitableForSocialContext<BR/>'
        'compatibilityScore<BR/>'
        'SWRL Rules>',
        shape='box',
        style='rounded,filled',
        fillcolor=COLORS['bridge_cluster'],
        color=COLORS['bridge_prop'],
        fontcolor=COLORS['font_dark'],
        penwidth='2',
        width='3',
    )

    # Conexiones bridge
    dot.edge('bridge_center', 'mo_Movie',
             label='conecta con\ndominio filmico',
             color=COLORS['bridge_prop'], fontcolor=COLORS['bridge_prop'],
             penwidth='2.5', style='bold', arrowhead='vee')
    dot.edge('bridge_center', 'co_ContextSnapshot',
             label='conecta con\ncontexto de usuario',
             color=COLORS['bridge_prop'], fontcolor=COLORS['bridge_prop'],
             penwidth='2.5', style='bold', arrowhead='vee')
    dot.edge('bridge_center', 'co_EmotionalContext',
             label='alignsWithMood',
             color=COLORS['bridge_prop'], fontcolor=COLORS['bridge_prop'],
             style='dashed')
    dot.edge('bridge_center', 'co_SocialContext',
             label='suitableForSocialContext',
             color=COLORS['bridge_prop'], fontcolor=COLORS['bridge_prop'],
             style='dashed')
    dot.edge('bridge_center', 'co_RequirementContext',
             label='satisfiesRequirement',
             color=COLORS['bridge_prop'], fontcolor=COLORS['bridge_prop'],
             style='dashed')

    # GraphRAG Engine
    dot.node(
        'graphrag',
        '<<B>GraphRAG Query Engine</B><BR/><I>NestJS + LLM (OpenAI)</I>>',
        shape='box',
        style='rounded,filled,bold',
        fillcolor='#1F2937',
        fontcolor=COLORS['font_light'],
        penwidth='2',
        width='3.5',
    )
    dot.edge('graphrag', 'bridge_center',
             label='usa propiedades\nde puente',
             color='#374151', fontcolor='#374151',
             penwidth='2', style='bold')
    dot.edge('graphrag', 'mo_Movie',
             label='consulta SPARQL',
             color='#374151', fontcolor='#374151', style='dashed')
    dot.edge('graphrag', 'co_ContextSnapshot',
             label='extrae contexto\ndel usuario',
             color='#374151', fontcolor='#374151', style='dashed')

    dot.render(output_path, cleanup=True)
    print(f"  ✅ integracion -> {output_path}.{fmt}")


# ──────────────────────────────────────────────────────────────
# Generador: Diagrama de Flujo GraphRAG
# ──────────────────────────────────────────────────────────────

def generate_graphrag_flow_diagram(output_path: str, fmt: str):
    """Genera diagrama del flujo completo del pipeline GraphRAG."""

    dot = graphviz.Digraph(
        name='graphrag_flow',
        comment='Flujo del Pipeline GraphRAG',
        format=fmt,
        engine='dot',
    )
    dot.attr(
        rankdir='TB',
        fontname='Helvetica',
        fontsize='14',
        label='<<B>Flujo del Pipeline GraphRAG</B><BR/>'
              '<I>Desde lenguaje natural hasta recomendacion personalizada</I>>',
        labelloc='t',
        pad='0.5',
        nodesep='0.5',
        ranksep='0.7',
        bgcolor='white',
    )
    dot.attr('node', fontname='Helvetica', fontsize='10', style='filled,rounded')
    dot.attr('edge', fontname='Helvetica', fontsize='9')

    steps = [
        ('input', 'Usuario\n"Quiero algo ligero\npara ver con mi pareja"',
         '#E5E7EB', '#1F2937', 'box'),
        ('extract', 'LLM: Extraccion\nde Contexto',
         '#DBEAFE', '#1E40AF', 'box'),
        ('context_rdf', 'context-ontology\n(Tripletas RDF)',
         '#FEF3C7', '#92400E', 'cylinder'),
        ('sparql_gen', 'Generacion Dinamica\nde SPARQL',
         '#DBEAFE', '#1E40AF', 'box'),
        ('fuseki', 'Apache Fuseki\n(Triplestore)',
         '#F3F4F6', '#374151', 'cylinder'),
        ('candidates', 'Peliculas\nCandidatas',
         '#D1FAE5', '#065F46', 'box'),
        ('swrl', 'Filtrado SWRL\n(Restricciones duras)',
         '#FEE2E2', '#991B1B', 'diamond'),
        ('scoring', 'LLM: Scoring\npor Dimensiones\n(0.0 - 1.0)',
         '#DBEAFE', '#1E40AF', 'box'),
        ('ranking', 'Ranking\ntop-K peliculas',
         '#D1FAE5', '#065F46', 'box'),
        ('response', 'Respuesta\nContextualizada\nal Usuario',
         '#E5E7EB', '#1F2937', 'box'),
    ]

    for node_id, label, bg, fc, shape in steps:
        dot.node(node_id, label, shape=shape, fillcolor=bg, fontcolor=fc, penwidth='1.5')

    edges = [
        ('input', 'extract', 'lenguaje natural'),
        ('extract', 'context_rdf', 'instancias RDF'),
        ('context_rdf', 'sparql_gen', 'contexto estructurado'),
        ('sparql_gen', 'fuseki', 'SELECT + filtros'),
        ('fuseki', 'candidates', 'resultados'),
        ('candidates', 'swrl', 'validacion'),
        ('swrl', 'scoring', 'candidatas filtradas'),
        ('scoring', 'ranking', 'scores calculados'),
        ('ranking', 'response', 'top-K + explicacion'),
    ]

    for src, tgt, label in edges:
        dot.edge(src, tgt, label=label, color='#4B5563', fontcolor='#6B7280')

    # Note lateral
    dot.node('onto_note',
             '<<I>movie-ontology<BR/>+ bridge-ontology<BR/>+ context-ontology</I>>',
             shape='note', fillcolor='#FFF7ED', fontcolor='#92400E',
             color='#D97706', style='filled')
    dot.edge('onto_note', 'fuseki', style='dotted', color='#D97706', arrowhead='none')

    dot.render(output_path, cleanup=True)
    print(f"  ✅ graphrag-flow -> {output_path}.{fmt}")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Genera diagramas de las ontologias del sistema de recomendacion de peliculas.'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['png', 'svg', 'pdf'],
        default='png',
        help='Formato de salida (default: png)',
    )
    parser.add_argument(
        '--output-dir', '-o',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Directorio de salida (default: {DEFAULT_OUTPUT_DIR})',
    )
    parser.add_argument(
        '--only',
        choices=['movie', 'context', 'bridge', 'integration', 'flow'],
        help='Generar solo un diagrama especifico',
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    fmt = args.format

    print(f"\n Generador de Diagramas de Ontologias")
    print(f"   Formato: {fmt}")
    print(f"   Salida:  {output_dir}\n")

    targets = [args.only] if args.only else ['movie', 'context', 'bridge', 'integration', 'flow']

    # Movie Ontology
    if 'movie' in targets:
        movie_ttl = os.path.join(ONTOLOGY_BASE_DIR, 'movie-ontology.ttl')
        if os.path.exists(movie_ttl):
            print("  Cargando movie-ontology.ttl...")
            g_movie = Graph()
            g_movie.parse(movie_ttl, format='turtle')
            print(f"   {len(g_movie)} tripletas cargadas")
            generate_movie_ontology_diagram(
                g_movie,
                os.path.join(output_dir, 'movie-ontology-diagram'),
                fmt,
            )
        else:
            print(f"  No encontrado: {movie_ttl}")

    # Context Ontology
    if 'context' in targets:
        context_ttl = os.path.join(ONTOLOGY_BASE_DIR, 'context-ontology.ttl')
        if os.path.exists(context_ttl):
            print("  Cargando context-ontology.ttl...")
            g_context = Graph()
            g_context.parse(context_ttl, format='turtle')
            print(f"   {len(g_context)} tripletas cargadas")
            generate_context_ontology_diagram(
                g_context,
                os.path.join(output_dir, 'context-ontology-diagram'),
                fmt,
            )
        else:
            print(f"  No encontrado: {context_ttl}")

    # Bridge Ontology
    if 'bridge' in targets:
        bridge_ttl = os.path.join(ONTOLOGY_BRIDGE_DIR, 'bridge-ontology.ttl')
        if os.path.exists(bridge_ttl):
            print("  Cargando bridge-ontology.ttl...")
            g_bridge = Graph()
            g_bridge.parse(bridge_ttl, format='turtle')
            print(f"   {len(g_bridge)} tripletas cargadas")
            generate_bridge_ontology_diagram(
                g_bridge,
                os.path.join(output_dir, 'bridge-ontology-diagram'),
                fmt,
            )
        else:
            print(f"  No encontrado: {bridge_ttl}")

    # Integration Diagram
    if 'integration' in targets:
        print("  Generando diagrama de integracion...")
        generate_integration_diagram(
            os.path.join(output_dir, 'ontology-integration'),
            fmt,
        )

    # GraphRAG Flow Diagram
    if 'flow' in targets:
        print("  Generando diagrama de flujo GraphRAG...")
        generate_graphrag_flow_diagram(
            os.path.join(output_dir, 'graphrag-flow'),
            fmt,
        )

    print(f"\n  Completo! Diagramas generados en: {output_dir}\n")


if __name__ == '__main__':
    main()
