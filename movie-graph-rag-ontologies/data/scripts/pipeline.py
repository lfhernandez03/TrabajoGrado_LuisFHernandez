"""
Pipeline completo para procesar peliculas y generar datos RDF.

Ejecuta en orden:
1. ETL: Carga y procesa datos base de MovieLens
2. Enrichment: Enriquece con APIs externas (TMDb, OMDb)
3. NLP Inference: Anade inferencias contextuales mediante NLP
4. RDF Generation: Genera tripletas RDF para peliculas, contextos y bridges
5. Fuseki Import: Importa los datos al contenedor Fuseki

Uso:
    python pipeline.py [--max-movies N] [--skip-enrichment] [--skip-import]
"""

import subprocess
import sys
import logging
from pathlib import Path
import argparse
import urllib.request
import urllib.error
import base64
from dotenv import load_dotenv
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde .env
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
    logger.debug(f"Cargadas variables de entorno desde {env_file}")
else:
    logger.debug(f"No se encontro archivo .env en {env_file}")

# Paths
SCRIPTS_DIR = Path(__file__).parent
DATA_ROOT = SCRIPTS_DIR.parent
PROCESSED_DIR = DATA_ROOT / "dataset" / "processed"
ETL_DIR = SCRIPTS_DIR / "etl"
ENRICHMENT_DIR = SCRIPTS_DIR / "enrichment"
RDF_DIR = SCRIPTS_DIR / "rdf"
ONTOLOGIES_INSTANCES_DIR = DATA_ROOT / "ontologies" / "instances"

# Python executable (usar el mismo que ejecuta este script)
PYTHON = sys.executable


def run_script(script_path: Path, description: str, args: list = None) -> bool:
    """
    Ejecuta un script Python y reporta el resultado.
    
    Args:
        script_path: Ruta al script a ejecutar
        description: Descripcion para logs
        args: Argumentos adicionales para el script
        
    Returns:
        True si exitoso, False si hubo error
    """
    logger.info("="*70)
    logger.info(f"EJECUTANDO: {description}")
    logger.info(f"Script: {script_path}")
    logger.info("="*70)
    
    cmd = [PYTHON, str(script_path)]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Mostrar output en tiempo real
            text=True
        )
        logger.info(f"✓ {description} completado exitosamente\n")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Error en {description}")
        logger.error(f"Codigo de salida: {e.returncode}\n")
        return False
    except Exception as e:
        logger.error(f"✗ Error ejecutando {description}: {e}\n")
        return False


def cleanup_intermediate_files(skip_nlp: bool = True) -> None:
    """
    Limpia archivos intermedios, mantiene solo el archivo final.
    
    Args:
        skip_nlp: Si True, NLP no fue ejecutado, elimina movies_nlp_enriched.csv del check
    """
    logger.info("\n" + "="*70)
    logger.info("LIMPIANDO ARCHIVOS INTERMEDIOS")
    logger.info("="*70)
    
    # Archivos intermedios a eliminar
    intermediate_files = [
        "movies_processed.csv",           # del ETL
        "movies_enriched.csv",            # del enrichment
        "nlp_inference_summary.csv"       # resumen del NLP (si se ejecuto)
    ]
    
    # Determinar archivo final a mantener
    nlp_file = PROCESSED_DIR / "movies_nlp_enriched.csv"
    enriched_file = PROCESSED_DIR / "movies_enriched.csv"
    
    if not skip_nlp and nlp_file.exists():
        # NLP fue ejecutado, mantener movies_nlp_enriched.csv
        final_file = "movies_nlp_enriched.csv"
    elif enriched_file.exists():
        # NLP no fue ejecutado, pero enrichment si, mantener movies_enriched.csv
        final_file = "movies_enriched.csv"
    else:
        logger.warning("No se encontro archivo final de datos enriquecidos")
        return
    
    # Verificar que el archivo final existe
    final_path = PROCESSED_DIR / final_file
    if not final_path.exists():
        logger.warning(f"Archivo final no encontrado: {final_file}")
        return
    
    logger.info(f"Archivo final a mantener: {final_file}")
    logger.info(f"Eliminando archivos intermedios...")
    
    deleted_count = 0
    for filename in intermediate_files:
        filepath = PROCESSED_DIR / filename
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info(f"  ✓ Eliminado: {filename}")
                deleted_count += 1
            except Exception as e:
                logger.warning(f"  ✗ No se pudo eliminar {filename}: {e}")
        else:
            logger.debug(f"  - No existe: {filename}")
    
    logger.info(f"Archivos eliminados: {deleted_count}")
    logger.info(f"Archivo final listo en: {final_path}")
    logger.info("="*70 + "\n")


def import_to_fuseki(
    fuseki_url: str = "http://localhost:3030",
    fuseki_dataset: str = "movies",
    fuseki_user: str = "",
    fuseki_password: str = ""
) -> bool:
    """
    Importa los datos RDF generados a Fuseki mediante HTTP POST al endpoint /data.
    
    Archivos importados:
    - movies_data.ttl: Tripletas de peliculas
    - bridge_data.ttl: Conexiones pelicula-contexto con propiedades temporales
    
    (contexts_data.ttl esta DEPRECATED - contextos se generan dinamicamente)
    """
    logger.info("="*70)
    logger.info("IMPORTANDO DATOS A FUSEKI")
    logger.info("="*70)

    data_endpoint = f"{fuseki_url.rstrip('/')}/{fuseki_dataset.strip('/')}/data"
    ttl_files = [
        ONTOLOGIES_INSTANCES_DIR / "movies_data.ttl",
        ONTOLOGIES_INSTANCES_DIR / "bridge_data.ttl",
    ]

    missing_files = [str(path) for path in ttl_files if not path.exists()]
    if missing_files:
        logger.error("✗ Faltan archivos TTL para importar a Fuseki:")
        for missing in missing_files:
            logger.error(f"  - {missing}")
        logger.error("")
        return False

    auth_header = None
    if fuseki_user:
        credentials = f"{fuseki_user}:{fuseki_password}".encode("utf-8")
        auth_header = "Basic " + base64.b64encode(credentials).decode("ascii")

    try:
        for ttl_path in ttl_files:
            logger.info(f"Subiendo {ttl_path.name} a {data_endpoint}")
            payload = ttl_path.read_bytes()
            request = urllib.request.Request(
                url=data_endpoint,
                data=payload,
                method="POST",
                headers={
                    "Content-Type": "text/turtle",
                    "Accept": "application/json",
                },
            )
            if auth_header:
                request.add_header("Authorization", auth_header)

            with urllib.request.urlopen(request, timeout=60):
                pass

        logger.info("✓ Datos importados a Fuseki exitosamente\n")
        return True
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            error_body = ""
        logger.error(f"✗ Error HTTP importando a Fuseki: {e.code} {e.reason}")
        if error_body:
            logger.error(error_body)
        logger.error("")
        return False
    except Exception as e:
        logger.error(f"✗ Error importando a Fuseki: {e}\n")
        return False


def run_pipeline(
    max_movies: int = None,
    skip_enrichment: bool = False,
    include_nlp: bool = False,
    skip_import: bool = False,
    incremental: bool = True,
    fuseki_url: str = None,
    fuseki_dataset: str = None,
    fuseki_user: str = None,
    fuseki_password: str = None
) -> bool:
    """
    Ejecuta el pipeline completo de procesamiento.
    
    Args:
        max_movies: Numero maximo de peliculas a procesar (None = todas)
        skip_enrichment: Si True, omite el enriquecimiento (usa datos existentes)
        include_nlp: Si True, incluye NLP inference (DEPRECATED - no recomendado)
        skip_import: Si True, omite la importacion a Fuseki
        incremental: Si True, hace merge incremental (upsert) en vez de sobrescritura total
        fuseki_url: URL de Fuseki (usara variable entorno FUSEKI_URL o localhost por defecto)
        fuseki_dataset: Dataset en Fuseki
        fuseki_user: Usuario Fuseki
        fuseki_password: Password Fuseki
        
    Returns:
        True si todo el pipeline fue exitoso
    """
    import os
    
    # Obtener valores de variables de entorno con defaults seguros
    fuseki_url = fuseki_url or os.getenv("FUSEKI_URL", "http://localhost:3030")
    fuseki_dataset = fuseki_dataset or os.getenv("FUSEKI_DATASET", "Cine")
    fuseki_user = fuseki_user or os.getenv("FUSEKI_USER", "")
    fuseki_password = fuseki_password or os.getenv("FUSEKI_PASSWORD", "")
    
    logger.info("\n" + "="*70)
    logger.info("INICIANDO PIPELINE DE PROCESAMIENTO DE PELICULAS")
    logger.info("="*70)
    logger.info(f"Peliculas a procesar: {max_movies if max_movies else 'TODAS'}")
    logger.info(f"Omitir enriquecimiento: {skip_enrichment}")
    if include_nlp:
        logger.warning(f"⚠ NLP Inference HABILITADO (DEPRECATED - no recomendado)")
    else:
        logger.info(f"NLP Inference: DESHABILITADO")
    logger.info(f"Omitir importacion Fuseki: {skip_import}")
    logger.info(f"Modo incremental: {incremental}")
    logger.info(f"Fuseki URL: {fuseki_url}")
    logger.info(f"Fuseki Dataset: {fuseki_dataset}")
    logger.info("="*70 + "\n")
    
    steps = []
    
    # PASO 1: ETL - Carga y procesamiento base
    etl_args = []
    if max_movies:
        etl_args.extend(['--max-movies', str(max_movies)])
    if not incremental:
        etl_args.append('--no-incremental')
    steps.append({
        'script': ETL_DIR / 'data_loader.py',
        'description': 'ETL - Carga y procesamiento de datos base',
        'args': etl_args
    })
    
    if not skip_enrichment:
        # PASO 2: Enrichment - APIs externas
        enrichment_args = []
        if max_movies:
            enrichment_args.extend(['--max-movies', str(max_movies)])
        if not incremental:
            enrichment_args.append('--no-incremental')
        steps.append({
            'script': ENRICHMENT_DIR / 'enrichment.py',
            'description': 'Enrichment - Enriquecimiento con TMDb/OMDb',
            'args': enrichment_args
        })
        
        # PASO 3: NLP Inference (OPCIONAL, DEPRECATED)
        if include_nlp:
            nlp_args = []
            if max_movies:
                nlp_args.extend(['--max-movies', str(max_movies)])
            if not incremental:
                nlp_args.append('--no-incremental')
            steps.append({
                'script': ENRICHMENT_DIR / 'nlp_inference.py',
                'description': 'NLP Inference - Inferencias contextuales (DEPRECATED)',
                'args': nlp_args
            })
        else:
            logger.info("⊘ Omitiendo NLP Inference (DEPRECATED)")
    else:
        logger.info("⊘ Omitiendo enriquecimiento (usando datos existentes)\n")
    
    # PASO 4: RDF Generation - Peliculas
    # Determinar archivo de entrada con fallback logic
    nlp_enriched_file = PROCESSED_DIR / 'movies_nlp_enriched.csv'
    enriched_file = PROCESSED_DIR / 'movies_enriched.csv'
    
    if include_nlp and nlp_enriched_file.exists():
        # Si NLP estuvo disponible, usar movies_nlp_enriched.csv
        input_csv = nlp_enriched_file
    elif not skip_enrichment and nlp_enriched_file.exists():
        # Si no paso NLP pero enrichment si, y existe movies_nlp_enriched, usarlo
        input_csv = nlp_enriched_file
    elif enriched_file.exists():
        # Fallback: usar movies_enriched.csv si NLP no genero el suyo
        input_csv = enriched_file
    else:
        # Ultimo recurso: dejar que rdf_generator use su propia logica de fallback
        input_csv = None
    
    rdf_args = []
    if max_movies:
        rdf_args.extend(['--max-movies', str(max_movies)])
    if input_csv:
        rdf_args.extend(['--input-file', str(input_csv)])
    if not incremental:
        rdf_args.append('--no-incremental')
    steps.append({
        'script': RDF_DIR / 'rdf_generator.py',
        'description': 'RDF Generation - Tripletas de peliculas',
        'args': rdf_args
    })
    
    # PASO 5: RDF Generation - Bridges (reemplazando rdf_context_generator + rdf_bridge_generator)
    # Construir argumentos para regenerate_bridge_data.py
    bridge_input_file = ONTOLOGIES_INSTANCES_DIR / 'bridge_data.ttl'
    movies_data_file = ONTOLOGIES_INSTANCES_DIR / 'movies_data.ttl'
    bridge_output_file = ONTOLOGIES_INSTANCES_DIR / 'bridge_data.ttl'
    
    bridge_args = [
        '--movies', str(movies_data_file),
        '--output', str(bridge_output_file)
    ]
    
    # Si existe un bridge_data.ttl previo Y se quiere merge incremental, pasarlo
    # De lo contrario, generar un nuevo bridge_data.ttl solo con la data procesada
    if bridge_input_file.exists() and incremental:
        bridge_args.extend(['--bridge', str(bridge_input_file)])
    
    steps.append({
        'script': RDF_DIR / 'regenerate_bridge_data.py',
        'description': 'RDF Generation - Bridges pelicula-contexto (temporal)',
        'args': bridge_args
    })
    
    # Ejecutar todos los pasos
    for i, step in enumerate(steps, 1):
        logger.info(f"\n>>> PASO {i}/{len(steps)}: {step['description']}")
        
        if not run_script(step['script'], step['description'], step['args']):
            logger.error(f"✗ Pipeline FALLO en el paso {i}")
            return False
    
    # PASO FINAL: Importar a Fuseki (opcional)
    if not skip_import:
        logger.info(f"\n>>> PASO FINAL: Importacion a Fuseki")
        if not import_to_fuseki(
            fuseki_url=fuseki_url,
            fuseki_dataset=fuseki_dataset,
            fuseki_user=fuseki_user,
            fuseki_password=fuseki_password,
        ):
            logger.error("✗ Pipeline FALLO en la importacion a Fuseki")
            return False
    else:
        logger.info("\n⊘ Omitiendo importacion a Fuseki")
    
    # Limpiar archivos intermedios (condicional segun si NLP corrio)
    cleanup_intermediate_files(skip_nlp=(not include_nlp))
    
    # Success!
    logger.info("\n" + "="*70)
    logger.info("✓ PIPELINE COMPLETADO EXITOSAMENTE")
    logger.info("="*70)
    logger.info("\nProximos pasos:")
    if skip_import:
        logger.info("  - Ejecuta el pipeline con importacion para actualizar Fuseki")
        logger.info("  - Revisa que Fuseki este disponible en: http://localhost:3030")
    else:
        logger.info("  - Verifica los datos en Fuseki: http://localhost:3030")
        logger.info("  - Ejecuta queries SPARQL para validar la importacion")
    logger.info("="*70 + "\n")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Pipeline completo para procesar peliculas y generar datos RDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Pipeline completo (todas las peliculas)
  python pipeline.py
  
  # Pipeline con limite de peliculas
  python pipeline.py --max-movies 100
  
  # Regenerar RDF sin enriquecer nuevamente
  python pipeline.py --skip-enrichment
  
  # Generar archivos sin importar a GraphDB
  python pipeline.py --skip-import

  # Importar a Fuseki especificando dataset
  python pipeline.py --fuseki-dataset Cine
  
  # Combinacion: 500 peliculas sin importar
  python pipeline.py --max-movies 500 --skip-import

NOTA IMPORTANTE - CONFIGURACION DE CREDENCIALES:
  Las credenciales de Fuseki (usuario/contrasena) SIEMPRE deben configurarse
  mediante variables de entorno por razones de seguridad:
  
  export FUSEKI_URL=http://fuseki-server:3030
  export FUSEKI_USER=admin
  export FUSEKI_PASSWORD=your_secure_password
  
  Las credenciales NO se aceptan como argumentos CLI para evitar que aparezcan
  en logs o en listados de procesos (ps, top, etc).
        """
    )
    
    parser.add_argument(
        '--max-movies',
        type=int,
        help='Numero maximo de peliculas a procesar (default: todas)'
    )
    
    parser.add_argument(
        '--skip-enrichment',
        action='store_true',
        help='Omitir enriquecimiento con APIs (usa datos existentes)'
    )
    
    parser.add_argument(
        '--include-nlp',
        action='store_true',
        help='Incluir NLP inference (DEPRECATED: NLP es redundante, no recomendado)'
    )
    
    parser.add_argument(
        '--skip-import',
        action='store_true',
        help='Omitir importacion a Fuseki'
    )

    parser.add_argument(
        '--no-incremental',
        action='store_true',
        help='Desactiva merge incremental y sobrescribe salidas con el lote actual'
    )

    parser.add_argument(
        '--fuseki-url',
        type=str,
        default='http://localhost:3030',
        help='URL base de Fuseki (default: http://localhost:3030). Tambien puede usar FUSEKI_URL env var'
    )

    parser.add_argument(
        '--fuseki-dataset',
        type=str,
        default=None,
        help='Nombre del dataset de Fuseki (default: desde FUSEKI_DATASET env var o "movies")'
    )
    
    # NOTA IMPORTANTE: No aceptamos --fuseki-user ni --fuseki-password en argumentos CLI por razones de seguridad
    # Las credenciales SIEMPRE deben venir de variables de entorno para evitar que aparezcan en logs o process listings
    
    args = parser.parse_args()
    
    # Ejecutar pipeline - credenciales SIN argumentos CLI (siempre desde variables de entorno)
    success = run_pipeline(
        max_movies=args.max_movies,
        skip_enrichment=args.skip_enrichment,
        include_nlp=args.include_nlp,
        skip_import=args.skip_import,
        incremental=not args.no_incremental,
        fuseki_url=args.fuseki_url,
        fuseki_dataset=args.fuseki_dataset,
        fuseki_user=None,  # Siempre desde env vars
        fuseki_password=None,  # Siempre desde env vars
    )
    
    # Exit code segun resultado
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
