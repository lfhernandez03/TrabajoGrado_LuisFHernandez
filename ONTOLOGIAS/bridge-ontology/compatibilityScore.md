# compatibilityScore

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** compatibility score

## Descripcion

Puntuación de compatibilidad global (0.0-1.0) entre una película y el contexto actual.
    
    GENERACIÓN:
    Esta puntuación es calculada por el LLM durante el proceso de GraphRAG, NO es 
    un valor precomputado. El LLM considera:
    
    1. Alineación emocional (alignsWithMood)
    2. Adecuación social (suitableForSocialContext)
    3. Cumplimiento de requisitos (satisfiesRequirement)
    4. Alineación temporal (dayOfWeek, hourOfDay del contexto)
    5. Popularidad, calificación y otros factores del dominio fílmico
    
    INTERPRETACIÓN:
    - 0.90 - 1.00: Altamente recomendada (match casi perfecto)
    - 0.75 - 0.89: Buena opción (coincide en la mayoría de dimensiones)
    - 0.60 - 0.74: Opción aceptable (algunas coincidencias)
    - 0.00 - 0.59: Baja compatibilidad (pocas coincidencias)
    
    USO EN RANKING:
    Las películas se ordenan por compatibilityScore DESC para generar el top-k.
    
    RESTRICCIÓN TÉCNICA: Valores válidos [0.0, 1.0]. Ver sección de axiomas.

## Dominio

- [[Movie]]

## Rango

- `xsd:float`

## Caracteristicas OWL

- Funcional
