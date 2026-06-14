# hourOfDay

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** context-ontology
- **Etiqueta:** hour of day

## Descripcion

Hour of the day in 24h format (valid range: 0-23, where 0=midnight, 23=11 PM). IMPORTANT: The LLM must always return values in this standard range to ensure consistency. Captures temporal information without bias. Example: '3 AM on Tuesday' is encoded as hourOfDay=3. The system can use this for context without forcing predefined categories like 'early morning'.

## Dominio

- [[ContextSnapshot]]

## Rango

- `xsd:integer`

## Caracteristicas OWL

- Funcional
