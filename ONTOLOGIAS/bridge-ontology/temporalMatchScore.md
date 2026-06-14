# temporalMatchScore

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** temporal match score

## Descripcion

DEPRECATED en v3: Usar energyMatchScore en su lugar.
    
    Qué tan apropiada es la película para el momento temporal (0.0-1.0).
    
    Considera:
    - hourOfDay (ej: película intensa a las 3 AM puede ser adecuada)
    - dayOfWeek (ej: fin de semana vs día laboral - sin sesgos rígidos)
    - Duración vs momento del día
    
    El LLM interpreta el contexto temporal sin categorías predefinidas.

## Dominio

- [[Movie]]

## Rango

- `xsd:float`
