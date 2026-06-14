# isRecommendedIn

## Metadata

- **Tipo:** Propiedad de Objeto (`owl:ObjectProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** is recommended in

## Descripcion

Conecta una película con el snapshot de contexto en el que fue recomendada.
    Esta propiedad representa la relación central del sistema: una Movie se 
    alinea semánticamente con un ContextSnapshot específico.
    
    Uso en GraphRAG:
    - Permite navegar desde películas hacia contextos (¿en qué contextos se recomienda Inception?)
    - Permite navegar desde contextos hacia películas (¿qué películas se recomiendan para este contexto?)
    - El LLM usa esta propiedad para estructurar la respuesta de recomendación
    
    NO es una relación estática: se crea dinámicamente durante cada query GraphRAG.

## Dominio

- [[Movie]]

## Rango

- [[ContextSnapshot]]

## Propiedad Inversa

- [[recommends]]
