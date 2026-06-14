# ContextSnapshot

## Metadata

- **Tipo:** `owl:Class`
- **Ontologia:** context-ontology
- **Etiqueta:** Context Snapshot

## Descripcion

Central node that captures the current moment of interaction. Represents the user's 'now': who they are with, how they feel, what they need. The LLM infers this data from the natural language of the conversation, NOT through explicit questions.

## Propiedades donde es Dominio

- [[dayOfWeek]] -> `xsd:string`
- [[feelsMood]] -> [[EmotionalContext]]
- [[hasRequirement]] -> [[RequirementContext]]
- [[hourOfDay]] -> `xsd:integer`
- [[isContextOfUser]] -> [[User]]
- [[requestTimestamp]] -> `xsd:dateTime`
- [[snapshotID]] -> `xsd:string`
- [[userIntent]] -> `xsd:string`
- [[withCompanion]] -> [[SocialContext]]

## Propiedades donde es Rango

- [[hasCurrentContext]] <- [[User]]
- [[isCompanionIn]] <- [[SocialContext]]
- [[isMoodOfSnapshot]] <- [[EmotionalContext]]
- [[isRequirementOf]] <- [[RequirementContext]]
