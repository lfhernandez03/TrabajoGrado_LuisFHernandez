# compatibleCompanion

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** compatible companion

## Descripcion

Valores de companionType compatibles con esta película.
    
    Valores normalizados (de COMPANION_TYPES en rdf_context_generator.py):
    'solo', 'pareja', 'familia', 'familia con niños', 'familia extendida',
    'amigos', 'compañeros de trabajo'
    
    Una película puede tener múltiples valores (cardinalidad ilimitada).
    Usado para matching SPARQL exacto con SocialContext.companionType.

## Dominio

- [[Movie]]

## Rango

- `xsd:string`
