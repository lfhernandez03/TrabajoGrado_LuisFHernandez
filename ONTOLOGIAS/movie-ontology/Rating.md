# Rating

## Metadata

- **Tipo:** `owl:Class`
- **Ontologia:** movie-ontology

## Superclases

- [[Attribute]]

## Subclases

- [[AggregateRating]]
- [[CriticRating]]
- [[UserRating]]

## Clases Equivalentes

- `schema:Rating`

## Propiedades donde es Dominio

- [[ratingCount]] -> `xsd:integer`
- [[ratingDate]] -> `xsd:date`
- [[ratingSource]] -> `xsd:string`
- [[ratingValue]] -> `xsd:decimal`

## Propiedades donde es Rango

- [[hasRating]] <- [[Movie]]
