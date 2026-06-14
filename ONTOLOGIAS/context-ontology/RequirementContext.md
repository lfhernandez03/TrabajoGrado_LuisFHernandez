# RequirementContext

## Metadata

- **Tipo:** `owl:Class`
- **Ontologia:** context-ontology
- **Etiqueta:** Requirement Context

## Descripcion

Logistical or practical constraints for the current session. The LLM extracts information like 'I have an hour', 'something short', 'nothing scary' from natural language.

## Propiedades donde es Dominio

- [[availableTime]] -> `xsd:integer`
- [[contentRestrictions]] -> `xsd:string`
- [[excludedGenre]] -> `xsd:string`
- [[isRequirementOf]] -> [[ContextSnapshot]]
- [[negativeConstraint]] -> `xsd:string`
- [[preferredLanguage]] -> `xsd:language`

## Propiedades donde es Rango

- [[hasRequirement]] <- [[ContextSnapshot]]
