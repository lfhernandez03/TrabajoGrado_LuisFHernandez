# alignsWithMood

## Metadata

- **Tipo:** Propiedad de Objeto (`owl:ObjectProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** aligns with mood

## Descripcion

Conecta una película con el estado emocional del contexto de usuario.
    
    Esta alineación considera:
    - moodDescription: Cómo se siente el usuario actualmente
    - emotionalNeed: Qué busca sentir (puede diferir del mood actual)
    - desiredEnergyLevel: Nivel de energía/intensidad deseado
    - moodIntensity: Cuán intenso es el estado emocional
    
    El LLM interpreta estas dimensiones para determinar la alineación.
    
    Ejemplos de alineación:
    - Usuario "estresado" + emotionalNeed "escapar" → Películas relajantes
    - Usuario "triste" + desiredEnergyLevel "alto" → Películas energéticas (contraintuitivo)
    - Usuario "alegre" + desiredEnergyLevel "medio" → Comedias ligeras
    
    NO es una lógica rígida: el LLM usa su conocimiento del catálogo para decidir.

## Dominio

- [[Movie]]

## Rango

- [[EmotionalContext]]

## Propiedad Inversa

- [[isAlignedWith]]
