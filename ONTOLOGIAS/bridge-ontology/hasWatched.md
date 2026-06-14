# hasWatched

## Metadata

- **Tipo:** Propiedad de Objeto (`owl:ObjectProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** has watched

## Descripcion

El usuario ha visto esta película previamente.
    
    Uso en GraphRAG:
    - Para evitar recomendar películas ya vistas (a menos que el usuario lo solicite)
    - Para identificar preferencias del usuario basadas en historial
    - Para calcular similaridad entre películas vistas y candidatas
    
    IMPORTANTE: Esta propiedad puede provenir de:
    1. Sistema de ratings (userId ha calificado movieId)
    2. Historial de visualización
    3. Inferencia del LLM si el usuario menciona haber visto la película

## Dominio

- [[User]]

## Rango

- [[Movie]]

## Propiedad Inversa

- [[wasWatchedBy]]
