# excludedGenre

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** context-ontology
- **Etiqueta:** excluded genre

## Descripcion

Genres the user explicitly does NOT want to see. Values like 'horror', 'romance', 'science fiction', 'documentary'. Negative preferences are critical: what we DON'T want is as important as what we want. Multiple genres can be specified separated by commas. Extracted from phrases like 'no horror', 'no romantic movies', 'I don't want action'. CONSISTENCY: This property is used specifically for genres; for other exclusions use negativeConstraint.

## Dominio

- [[RequirementContext]]

## Rango

- `xsd:string`
