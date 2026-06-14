#!/usr/bin/env python3
"""
Generador de Notas de Ontologia para Obsidian
Procesa cada archivo TTL de forma independiente y genera una subcarpeta
con un archivo .md por cada recurso (clase / propiedad).

Los [[wiki links]] usan el nombre local del recurso referenciado — Obsidian
los resuelve entre subcarpetas, construyendo el grafo de conexiones.

Uso:
    python generate_ontology_notes.py
    python generate_ontology_notes.py --output ./docs/ontology-graph

Requiere: rdflib (pip install rdflib)
"""

import argparse
from pathlib import Path
from collections import defaultdict

from rdflib import Graph, RDF, RDFS, OWL, URIRef, BNode

# ─── Rutas ──────────────────────────────────────────────────────────────────

SCRIPT_DIR  = Path(__file__).parent
WORKSPACE   = SCRIPT_DIR.parent
DEFAULT_OUT = WORKSPACE / "ONTOLOGIAS"

# Cada entrada: (nombre_carpeta, ruta_ttl)
ONTOLOGY_FILES = [
    ("movie-ontology",   SCRIPT_DIR / "data/ontologies/base/movie-ontology.ttl"),
    ("context-ontology", SCRIPT_DIR / "data/ontologies/base/context-ontology.ttl"),
    ("bridge-ontology",  SCRIPT_DIR / "data/ontologies/bridge/bridge-ontology.ttl"),
]

# ─── Namespaces del proyecto (para identificar "recursos propios") ────────────

OUR_NAMESPACES = {
    "http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#",
    "http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#",
    "http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#",
}

EXTERNAL_PREFIXES = {
    "http://www.w3.org/2002/07/owl#":              "owl",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://www.w3.org/2000/01/rdf-schema#":       "rdfs",
    "http://www.w3.org/2001/XMLSchema#":           "xsd",
    "http://schema.org/":                          "schema",
    "http://dbpedia.org/ontology/":                "dbo",
    "http://xmlns.com/foaf/0.1/":                  "foaf",
    "http://data.linkedmdb.org/resource/movie/":   "lmdb",
    "http://www.w3.org/2003/11/swrl#":             "swrl",
}

# ─── Utilidades URI ──────────────────────────────────────────────────────────

def local_name(uri: URIRef) -> str:
    s = str(uri)
    return s.split("#")[-1] if "#" in s else s.split("/")[-1]


def is_project_resource(uri) -> bool:
    """True si el URI pertenece a cualquiera de nuestras tres ontologias."""
    if not isinstance(uri, URIRef):
        return False
    s = str(uri)
    return any(s.startswith(ns) for ns in OUR_NAMESPACES)


def fmt_uri(uri) -> str:
    """
    - Recurso propio (cualquier ontologia) → [[local_name]]
    - Recurso externo conocido             → `prefix:local`
    - Resto                                → `<uri>`
    """
    if isinstance(uri, BNode):
        return "_:bnode"
    if not isinstance(uri, URIRef):
        return str(uri)

    if is_project_resource(uri):
        return f"[[{local_name(uri)}]]"

    s = str(uri)
    for ns, prefix in EXTERNAL_PREFIXES.items():
        if s.startswith(ns):
            return f"`{prefix}:{local_name(uri)}`"
    return f"`<{s}>`"


# ─── Lectura del grafo ───────────────────────────────────────────────────────

def get_label(g: Graph, uri: URIRef) -> str:
    for lit in g.objects(uri, RDFS.label):
        if getattr(lit, "language", None) == "en":
            return str(lit)
    for lit in g.objects(uri, RDFS.label):
        return str(lit)
    return local_name(uri)


def get_comment(g: Graph, uri: URIRef) -> str:
    for lit in g.objects(uri, RDFS.comment):
        if getattr(lit, "language", None) == "en":
            return str(lit).strip()
    for lit in g.objects(uri, RDFS.comment):
        return str(lit).strip()
    return ""


def owl_characteristics(g: Graph, uri: URIRef) -> list[str]:
    flags = {
        OWL.FunctionalProperty:         "Funcional",
        OWL.InverseFunctionalProperty:  "Inversamente Funcional",
        OWL.TransitiveProperty:         "Transitiva",
        OWL.SymmetricProperty:          "Simetrica",
        OWL.AsymmetricProperty:         "Asimetrica",
        OWL.ReflexiveProperty:          "Reflexiva",
        OWL.IrreflexiveProperty:        "Irreflexiva",
    }
    return [label for rdf_type, label in flags.items() if (uri, RDF.type, rdf_type) in g]


# ─── Generadores de contenido MD ─────────────────────────────────────────────

def md_class(g: Graph, cls: URIRef, onto_name: str) -> str:
    name    = local_name(cls)
    label   = get_label(g, cls)
    comment = get_comment(g, cls)

    lines = [f"# {name}", ""]
    lines += ["## Metadata", ""]
    lines += [
        f"- **Tipo:** `owl:Class`",
        f"- **Ontologia:** {onto_name}",
    ]
    if label and label != name:
        lines.append(f"- **Etiqueta:** {label}")
    lines.append("")

    if comment:
        lines += ["## Descripcion", "", comment, ""]

    supers = [o for o in g.objects(cls, RDFS.subClassOf) if isinstance(o, URIRef)]
    if supers:
        lines += ["## Superclases", ""]
        for s in sorted(supers, key=str):
            lines.append(f"- {fmt_uri(s)}")
        lines.append("")

    subs = [s for s in g.subjects(RDFS.subClassOf, cls) if isinstance(s, URIRef)]
    if subs:
        lines += ["## Subclases", ""]
        for s in sorted(subs, key=str):
            lines.append(f"- {fmt_uri(s)}")
        lines.append("")

    equivs = [o for o in g.objects(cls, OWL.equivalentClass) if isinstance(o, URIRef)]
    if equivs:
        lines += ["## Clases Equivalentes", ""]
        for e in sorted(equivs, key=str):
            lines.append(f"- {fmt_uri(e)}")
        lines.append("")

    dom_props = [s for s in g.subjects(RDFS.domain, cls) if isinstance(s, URIRef)]
    if dom_props:
        lines += ["## Propiedades donde es Dominio", ""]
        for p in sorted(dom_props, key=str):
            ranges = [o for o in g.objects(p, RDFS.range) if isinstance(o, URIRef)]
            rng = ", ".join(fmt_uri(r) for r in sorted(ranges, key=str)) or "-"
            lines.append(f"- {fmt_uri(p)} -> {rng}")
        lines.append("")

    rng_props = [s for s in g.subjects(RDFS.range, cls) if isinstance(s, URIRef)]
    if rng_props:
        lines += ["## Propiedades donde es Rango", ""]
        for p in sorted(rng_props, key=str):
            domains = [o for o in g.objects(p, RDFS.domain) if isinstance(o, URIRef)]
            dom = ", ".join(fmt_uri(d) for d in sorted(domains, key=str)) or "-"
            lines.append(f"- {fmt_uri(p)} <- {dom}")
        lines.append("")

    return "\n".join(lines)


def md_property(g: Graph, prop: URIRef, prop_kind: str, onto_name: str) -> str:
    name    = local_name(prop)
    label   = get_label(g, prop)
    comment = get_comment(g, prop)

    kind_label = (
        "Propiedad de Objeto (`owl:ObjectProperty`)"
        if prop_kind == "object"
        else "Propiedad de Dato (`owl:DatatypeProperty`)"
    )

    lines = [f"# {name}", ""]
    lines += ["## Metadata", ""]
    lines += [
        f"- **Tipo:** {kind_label}",
        f"- **Ontologia:** {onto_name}",
    ]
    if label and label != name:
        lines.append(f"- **Etiqueta:** {label}")
    lines.append("")

    if comment:
        lines += ["## Descripcion", "", comment, ""]

    domains = [o for o in g.objects(prop, RDFS.domain) if isinstance(o, URIRef)]
    if domains:
        lines += ["## Dominio", ""]
        for d in sorted(domains, key=str):
            lines.append(f"- {fmt_uri(d)}")
        lines.append("")

    ranges = [o for o in g.objects(prop, RDFS.range) if isinstance(o, URIRef)]
    if ranges:
        lines += ["## Rango", ""]
        for r in sorted(ranges, key=str):
            lines.append(f"- {fmt_uri(r)}")
        lines.append("")

    if prop_kind == "object":
        inverses = [o for o in g.objects(prop, OWL.inverseOf) if isinstance(o, URIRef)]
        if inverses:
            lines += ["## Propiedad Inversa", ""]
            for inv in sorted(inverses, key=str):
                lines.append(f"- {fmt_uri(inv)}")
            lines.append("")

        inv_of = [s for s in g.subjects(OWL.inverseOf, prop) if isinstance(s, URIRef)]
        if inv_of:
            lines += ["## Inversa de", ""]
            for inv in sorted(inv_of, key=str):
                lines.append(f"- {fmt_uri(inv)}")
            lines.append("")

    sub_props = [s for s in g.subjects(RDFS.subPropertyOf, prop) if isinstance(s, URIRef)]
    if sub_props:
        lines += ["## Sub-propiedades", ""]
        for sp in sorted(sub_props, key=str):
            lines.append(f"- {fmt_uri(sp)}")
        lines.append("")

    super_props = [o for o in g.objects(prop, RDFS.subPropertyOf) if isinstance(o, URIRef)]
    if super_props:
        lines += ["## Super-propiedades", ""]
        for sp in sorted(super_props, key=str):
            lines.append(f"- {fmt_uri(sp)}")
        lines.append("")

    chars = owl_characteristics(g, prop)
    if chars:
        lines += ["## Caracteristicas OWL", ""]
        for c in chars:
            lines.append(f"- {c}")
        lines.append("")

    return "\n".join(lines)


def md_index(onto_name: str, resources: list[tuple[str, str]]) -> str:
    """Indice _index.md local de una sola ontologia."""
    classes   = sorted([n for n, t in resources if t == "class"])
    obj_props = sorted([n for n, t in resources if t == "object"])
    dat_props = sorted([n for n, t in resources if t == "data"])

    lines = [
        f"# {onto_name}",
        "",
        "> Notas generadas automaticamente desde el archivo TTL.",
        "",
    ]

    if classes:
        lines += [f"## Clases ({len(classes)})", ""]
        for n in classes:
            lines.append(f"- [[{n}]]")
        lines.append("")

    if obj_props:
        lines += [f"## Propiedades de Objeto ({len(obj_props)})", ""]
        for n in obj_props:
            lines.append(f"- [[{n}]]")
        lines.append("")

    if dat_props:
        lines += [f"## Propiedades de Dato ({len(dat_props)})", ""]
        for n in dat_props:
            lines.append(f"- [[{n}]]")
        lines.append("")

    return "\n".join(lines)


def md_global_index(summary: list[tuple[str, list[tuple[str, str]]]]) -> str:
    """Indice raiz _index.md que enlaza las tres subcarpetas."""
    lines = [
        "# Indice de Ontologias",
        "",
        "> Notas generadas automaticamente. Abrir en Obsidian para ver el grafo.",
        "",
    ]
    for onto_name, resources in summary:
        n_cls = sum(1 for _, t in resources if t == "class")
        n_obj = sum(1 for _, t in resources if t == "object")
        n_dat = sum(1 for _, t in resources if t == "data")
        lines += [
            f"## [[{onto_name}/_index|{onto_name}]]",
            "",
            f"- Clases: {n_cls}",
            f"- Propiedades de Objeto: {n_obj}",
            f"- Propiedades de Dato: {n_dat}",
            "",
        ]
    return "\n".join(lines)


# ─── Procesador por ontologia ────────────────────────────────────────────────

def process_ontology(onto_name: str, ttl_path: Path, output_root: Path) -> list[tuple[str, str]]:
    """
    Carga un TTL de forma independiente y genera los .md en output_root/onto_name/.
    Devuelve la lista [(nombre_archivo, tipo)] de recursos generados.
    """
    onto_dir = output_root / onto_name
    onto_dir.mkdir(parents=True, exist_ok=True)

    g = Graph()
    g.parse(str(ttl_path), format="turtle")
    print(f"  {ttl_path.name}: {len(g):,} triples")

    # Solo los URIs que pertenecen a ESTE archivo
    this_ns = None
    for ns in OUR_NAMESPACES:
        if onto_name.replace("-", "") in ns.replace("-", ""):
            this_ns = ns
            break

    def belongs_here(uri) -> bool:
        return isinstance(uri, URIRef) and this_ns and str(uri).startswith(this_ns)

    resources: list[tuple[str, str]] = []
    written = 0

    # Clases
    for cls in sorted(g.subjects(RDF.type, OWL.Class), key=str):
        if not belongs_here(cls):
            continue
        content = md_class(g, cls, onto_name)
        (onto_dir / f"{local_name(cls)}.md").write_text(content, encoding="utf-8")
        resources.append((local_name(cls), "class"))
        written += 1

    # Propiedades de objeto
    for prop in sorted(g.subjects(RDF.type, OWL.ObjectProperty), key=str):
        if not belongs_here(prop):
            continue
        content = md_property(g, prop, "object", onto_name)
        (onto_dir / f"{local_name(prop)}.md").write_text(content, encoding="utf-8")
        resources.append((local_name(prop), "object"))
        written += 1

    # Propiedades de dato
    for prop in sorted(g.subjects(RDF.type, OWL.DatatypeProperty), key=str):
        if not belongs_here(prop):
            continue
        content = md_property(g, prop, "data", onto_name)
        (onto_dir / f"{local_name(prop)}.md").write_text(content, encoding="utf-8")
        resources.append((local_name(prop), "data"))
        written += 1

    # Indice local
    (onto_dir / "_index.md").write_text(md_index(onto_name, resources), encoding="utf-8")

    n_cls = sum(1 for _, t in resources if t == "class")
    n_obj = sum(1 for _, t in resources if t == "object")
    n_dat = sum(1 for _, t in resources if t == "data")
    print(f"    -> {n_cls} clases, {n_obj} obj.props, {n_dat} data props  ({written} archivos)")

    return resources


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Genera notas Obsidian independientes por cada ontologia TTL"
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUT,
        help="Carpeta raiz de salida (default: ../ONTOLOGIAS/)"
    )
    args = parser.parse_args()

    output_root: Path = args.output
    output_root.mkdir(parents=True, exist_ok=True)
    print(f"Directorio raiz: {output_root}\n")

    summary: list[tuple[str, list[tuple[str, str]]]] = []

    for onto_name, ttl_path in ONTOLOGY_FILES:
        if not ttl_path.exists():
            print(f"  ADVERTENCIA: {ttl_path} no encontrado")
            continue
        print(f"Procesando {onto_name} ...")
        resources = process_ontology(onto_name, ttl_path, output_root)
        summary.append((onto_name, resources))

    # Indice global
    (output_root / "_index.md").write_text(md_global_index(summary), encoding="utf-8")

    total = sum(len(r) for _, r in summary)
    print(f"\nTotal: {total} archivos .md generados en {output_root}/")
    print("  _index.md global generado")


if __name__ == "__main__":
    main()
