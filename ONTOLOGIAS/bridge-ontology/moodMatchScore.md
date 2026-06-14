# moodMatchScore

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** mood match score

## Descripcion

Qué tan bien la película coincide con el estado emocional del usuario (0.0-1.0).
    
    Considera:
    - Tono de la película vs moodDescription
    - Cómo satisface el emotionalNeed
    - Alineación con desiredEnergyLevel
    
    Ejemplo: Usuario "estresado" que busca "escapar"
    → Película relajante: moodMatchScore=0.95
    → Película de acción intensa: moodMatchScore=0.30

## Dominio

- [[Movie]]

## Rango

- `xsd:float`

## Caracteristicas OWL

- Funcional
