# compatibleMood

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** compatible mood

## Descripcion

Valores de moodDescription compatibles con esta película.
    
    Valores normalizados (de MOOD_TYPES en rdf_context_generator.py):
    'feliz', 'relajado', 'estresado', 'triste', 'ansioso', 'emocionado',
    'aburrido', 'curioso', 'concentrado', 'romantico', 'nostalgico',
    'aventurero', 'nervioso', 'solo'
    
    Una película puede tener múltiples valores (cardinalidad ilimitada).
    Usado para matching SPARQL exacto con EmotionalContext.moodDescription.

## Dominio

- [[Movie]]

## Rango

- `xsd:string`
