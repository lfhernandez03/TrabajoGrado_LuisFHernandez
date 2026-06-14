# requirementMatchScore

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** requirement match score

## Descripcion

Qué tan bien la película cumple con los requisitos logísticos (0.0-1.0).
    
    Factores:
    - Runtime vs availableTime
    - Ausencia de géneros excluidos
    - Idioma preferido
    - Otras restricciones negativas
    
    Si satisfiesRequirement es true → requirementMatchScore debería ser alto (≥0.8)

## Dominio

- [[Movie]]

## Rango

- `xsd:float`

## Caracteristicas OWL

- Funcional
