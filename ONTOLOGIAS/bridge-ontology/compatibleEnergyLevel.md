# compatibleEnergyLevel

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** compatible energy level

## Descripcion

Niveles de energía deseados compatibles con esta película.
    
    Valores normalizados (de ENERGY_LEVELS en rdf_context_generator.py):
    'bajo', 'medio', 'alto'
    
    Una película puede tener múltiples valores (cardinalidad ilimitada).
    Usado para matching SPARQL exacto con EmotionalContext.desiredEnergyLevel.

## Dominio

- [[Movie]]

## Rango

- `xsd:string`
