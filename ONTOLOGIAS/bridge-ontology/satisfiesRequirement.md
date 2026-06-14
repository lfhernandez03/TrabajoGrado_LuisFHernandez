# satisfiesRequirement

## Metadata

- **Tipo:** Propiedad de Objeto (`owl:ObjectProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** satisfies requirement

## Descripcion

Indica que una película cumple con los requisitos logísticos del contexto.
    
    Requisitos típicos que puede satisfacer:
    - Tiempo disponible (runtime ≤ availableTime)
    - Restricciones de contenido (no terror, apto para niños)
    - Idioma preferido
    - NO contiene géneros excluidos (excludedGenre)
    - NO viola restricciones negativas (negativeConstraint)
    
    Esta propiedad se infiere automáticamente mediante reglas SWRL cuando:
    1. movie:runtime ≤ context:availableTime
    2. movie:genre NO está en context:excludedGenre
    3. Cumple otras restricciones duras especificadas
    
    CRÍTICO: Si una película NO tiene esta propiedad para un RequirementContext,
    debe ser excluida del resultado final, incluso si tiene alto compatibilityScore.

## Dominio

- [[Movie]]

## Rango

- [[RequirementContext]]

## Propiedad Inversa

- [[isSatisfiedBy]]
