# EmotionalContext

## Metadata

- **Tipo:** `owl:Class`
- **Ontologia:** context-ontology
- **Etiqueta:** Emotional Context

## Descripcion

Current emotional state or mood of the user. The LLM identifies the emotional tone of messages like 'I'm stressed', 'I need something light', 'I want to laugh'. NOT asked directly.

## Propiedades donde es Dominio

- [[desiredEnergyLevel]] -> `xsd:string`
- [[emotionalNeed]] -> `xsd:string`
- [[isMoodOfSnapshot]] -> [[ContextSnapshot]]
- [[moodDescription]] -> `xsd:string`
- [[moodIntensity]] -> `xsd:decimal`

## Propiedades donde es Rango

- [[feelsMood]] <- [[ContextSnapshot]]
