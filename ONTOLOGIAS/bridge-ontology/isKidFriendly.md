# isKidFriendly

## Metadata

- **Tipo:** Propiedad de Dato (`owl:DatatypeProperty`)
- **Ontologia:** bridge-ontology
- **Etiqueta:** is kid friendly

## Descripcion

Indica si la película es apropiada para audiencia infantil.

Señal primaria — certificación MPAA:
- G            → siempre true
- PG           → true SOLO si tiene género Animation o Children
- PG-13, R, NC-17 → siempre false

Señal secundaria — géneros (cuando no hay certificación):
- Animation, Children, Family → true
- cualquier otro → false

IMPORTANTE: Este predicado se usa como filtro DURO solo cuando
el contexto indica children_age_hint = 'young' (niños pequeños).
Cuando children_age_hint es null o 'teen', se usa como señal de
scoring positiva pero NO excluye películas del resultado.

## Dominio

- [[Movie]]

## Rango

- `xsd:boolean`

## Caracteristicas OWL

- Funcional
