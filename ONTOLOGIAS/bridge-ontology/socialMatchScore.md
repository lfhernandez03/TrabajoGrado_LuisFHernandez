# socialMatchScore

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** social match score

## Descripcion

Qué tan apropiada es la película para el contexto social (0.0-1.0).
    
    Factores:
    - Adecuación para companionType
    - Apropiado para groupSize
    - Cumplimiento de hasChildren (si aplica)
    
    Ejemplo: hasChildren=true
    → Película G/PG: socialMatchScore=1.0
    → Película R: socialMatchScore=0.0 (exclusión automática)

## Dominio

- [[Movie]]

## Rango

- `xsd:float`

## Caracteristicas OWL

- Funcional
