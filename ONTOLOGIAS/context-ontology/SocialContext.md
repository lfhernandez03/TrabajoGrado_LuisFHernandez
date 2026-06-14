# SocialContext

## Metadata

- **Tipo:** `owl:Class`
- **Ontologia:** context-ontology
- **Etiqueta:** Social Context

## Descripcion

Information about who is watching with the user. CRITICAL for age and genre filters. The LLM detects phrases like 'with my family', 'with the kids', 'alone', etc. and extracts it automatically.

## Propiedades donde es Dominio

- [[companionType]] -> `xsd:string`
- [[groupSize]] -> `xsd:integer`
- [[hasChildren]] -> `xsd:boolean`
- [[isCompanionIn]] -> [[ContextSnapshot]]

## Propiedades donde es Rango

- [[withCompanion]] <- [[ContextSnapshot]]
