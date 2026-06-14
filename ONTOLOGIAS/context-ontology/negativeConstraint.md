# negativeConstraint

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** context-ontology
- **Etiqueta:** negative constraint

## Descripcion

General negative constraints beyond genre. Examples: 'no Marvel', 'no sequels', 'nothing old', 'no subtitles', 'no Tarantino', 'no animation'. Allows specifying structured exclusions that GraphRAG must respect when filtering graph nodes. Free text extracted from explicit user negations. DIFFERENCE from excludedGenre: use this for actors, directors, franchises, formats, eras, etc., NOT for genres.

## Dominio

- [[RequirementContext]]

## Rango

- `xsd:string`
