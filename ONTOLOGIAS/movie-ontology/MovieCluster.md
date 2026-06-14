# MovieCluster

## Metadata

- **Tipo:** `owl:Class`
- **Ontologia:** movie-ontology
- **Etiqueta:** Movie Cluster

## Descripcion

Grouping of similar movies detected by clustering algorithms (Louvain, Leiden) for GraphRAG. Enables hierarchical navigation and search space reduction for LLM.

## Superclases

- [[Entity]]

## Propiedades donde es Dominio

- [[clusterCentrality]] -> `xsd:decimal`
- [[clusterCohesion]] -> `xsd:decimal`
- [[clusterDescription]] -> `xsd:string`
- [[clusterID]] -> `xsd:string`
- [[clusterLabel]] -> `xsd:string`
- [[clusterSize]] -> `xsd:integer`
- [[containsMovie]] -> [[Movie]]

## Propiedades donde es Rango

- [[belongsToCluster]] <- [[Movie]]
