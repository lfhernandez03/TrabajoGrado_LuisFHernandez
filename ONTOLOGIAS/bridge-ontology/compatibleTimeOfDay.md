# compatibleTimeOfDay

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** compatible time of day

## Descripcion

Momento del día en que esta película es más apropiada.
    Valores válidos: 'morning', 'afternoon', 'evening', 'night'.
    Cardinalidad ilimitada. Inferido desde géneros, mood y compañía compatibles.
    Matching SPARQL exacto con time_of_day inferido desde ContextSnapshot.hourOfDay.

## Dominio

- [[Movie]]

## Rango

- `xsd:string`
