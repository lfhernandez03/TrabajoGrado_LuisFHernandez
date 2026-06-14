# suitableForSocialContext

## Metadata

- **Tipo:** Propiedad de Objeto (`owl:ObjectProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** suitable for social context

## Descripcion

Indica que una película es apropiada para el contexto social especificado.
    
    Factores sociales considerados:
    - companionType: Solo, pareja, familia, niños, amigos
    - hasChildren: Presencia de niños (crítico para filtros de clasificación)
    - groupSize: Cantidad de personas (grupos grandes necesitan consenso)
    
    Lógica de adecuación:
    - hasChildren=true → Películas aptas para niños (G, PG)
    - groupSize > 4 → Preferir "crowd-pleasers" con amplio consenso
    - companionType="pareja" → Puede incluir romance, drama íntimo
    - companionType="amigos" → Preferir acción, comedia, películas sociales
    
    El LLM usa esta propiedad para filtrar películas que NO son socialmente apropiadas.

## Dominio

- [[Movie]]

## Rango

- [[SocialContext]]

## Propiedad Inversa

- [[isSuitableFor]]
