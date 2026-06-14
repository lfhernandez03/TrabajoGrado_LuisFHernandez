# energyMatchScore

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** energy match score

## Descripcion

Qué tan apropiada es la película para el nivel de energía deseado (0.0-1.0).
    
    Reemplaza temporalMatchScore en v3. Considera:
    - desiredEnergyLevel del EmotionalContext ('bajo', 'medio', 'alto')
    - Intensidad/ritmo de la película
    - Alineación con necesidades de activación/relajación
    
    Ejemplo: Usuario con desiredEnergyLevel='alto'
    → Película de acción: energyMatchScore=0.95
    → Película contemplativa: energyMatchScore=0.30

## Dominio

- [[Movie]]

## Rango

- `xsd:float`

## Caracteristicas OWL

- Funcional
