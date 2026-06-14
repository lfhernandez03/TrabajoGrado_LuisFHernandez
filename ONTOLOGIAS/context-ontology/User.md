# User

## Metadata

- **Tipo:** `owl:Class`
- **Ontologia:** context-ontology

## Descripcion

Represents the system user. Basic information that persists across sessions. Data is automatically extracted from the profile or history, NOT through forms.

## Propiedades donde es Dominio

- [[hasCurrentContext]] -> [[ContextSnapshot]]
- [[userID]] -> `xsd:string`
- [[userName]] -> `xsd:string`

## Propiedades donde es Rango

- [[isContextOfUser]] <- [[ContextSnapshot]]
