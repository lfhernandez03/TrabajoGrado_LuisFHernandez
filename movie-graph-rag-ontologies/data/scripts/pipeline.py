"""
Pipeline completo para procesar películas y generar datos RDF.

Ejecuta en orden:
1. ETL: Carga y procesa datos base de MovieLens
2. Enrichment: Enriquece con APIs externas (TMDb, OMDb)
3. NLP Inference: Añade inferencias contextuales mediante NLP
4. RDF Generation: Genera tripletas RDF para películas, contextos y bridges
5. GraphDB Import: Importa los datos al contenedor GraphDB

Uso:
    python pipeline.py [--max-movies N] [--skip-enrichment] [--skip-import]
"""

import subprocess
import sys
import logging
from pathlib import Path
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
SCRIPTS_DIR = Path(__file__).parent
ETL_DIR = SCRIPTS_DIR / "etl"
ENRICHMENT_DIR = SCRIPTS_DIR / "enrichment"
RDF_DIR = SCRIPTS_DIR / "rdf"

# Python executable (usar el mismo que ejecuta este script)
PYTHON = sys.executable


def run_script(script_path: Path, description: str, args: list = None) -> bool:
    """
    Ejecuta un script Python y reporta el resultado.
    
    Args:
        script_path: Ruta al script a ejecutar
        description: Descripción para logs
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
        logger.error(f"Código de salida: {e.returncode}\n")
        return False
    except Exception as e:
        logger.error(f"✗ Error ejecutando {description}: {e}\n")
        return False


def cleanup_intermediate_files() -> None:
    """Limpia archivos intermedios, mantiene solo el archivo final."""
    logger.info("\n" + "="*70)
    logger.info("LIMPIANDO ARCHIVOS INTERMEDIOS")
    logger.info("="*70)
    
    DATA_ROOT = SCRIPTS_DIR.parent
    PROCESSED_DIR = DATA_ROOT / "dataset" / "processed"
    
    # Archivos intermedios a eliminar
    intermediate_files = [
        "movies_processed.csv",           # del ETL
        "movies_enriched.csv",            # del enrichment
        "nlp_inference_summary.csv"       # resumen del NLP
    ]
    
    # Archivo final a mantener
    final_file = "movies_nlp_enriched.csv"
    
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


def import_to_graphdb() -> bool:
    """Importa los datos RDF generados a GraphDB mediante Docker."""
    logger.info("="*70)
    logger.info("IMPORTANDO DATOS A GRAPHDB")
    logger.info("="*70)
    
    try:
        result = subprocess.run(
            ["docker", "exec", "graphdb-tesis", "/bin/bash", 
             "/docker-entrypoint-initdb.d/02-import-ontologies.sh"],
            check=True,
            capture_output=False,
            text=True
        )
        logger.info("✓ Datos importados a GraphDB exitosamente\n")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Error importando a GraphDB")
        logger.error(f"Código de salida: {e.returncode}\n")
        return False
    except FileNotFoundError:
        logger.error("✗ Docker no encontrado. Asegúrate de que Docker esté instalado y corriendo\n")
        return False
    except Exception as e:
        logger.error(f"✗ Error importando a GraphDB: {e}\n")
        return False


def run_pipeline(max_movies: int = None, skip_enrichment: bool = False, skip_import: bool = False) -> bool:
    """
    Ejecuta el pipeline completo de procesamiento.
    
    Args:
        max_movies: Número máximo de películas a procesar (None = todas)
        skip_enrichment: Si True, omite el enriquecimiento (usa datos existentes)
        skip_import: Si True, omite la importación a GraphDB
        
    Returns:
        True si todo el pipeline fue exitoso
    """
    logger.info("\n" + "="*70)
    logger.info("INICIANDO PIPELINE DE PROCESAMIENTO DE PELÍCULAS")
    logger.info("="*70)
    logger.info(f"Películas a procesar: {max_movies if max_movies else 'TODAS'}")
    logger.info(f"Omitir enriquecimiento: {skip_enrichment}")
    logger.info(f"Omitir importación GraphDB: {skip_import}")
    logger.info("="*70 + "\n")
    
    steps = []
    
    # PASO 1: ETL - Carga y procesamiento base
    etl_args = ['--max-movies', str(max_movies)] if max_movies else None
    steps.append({
        'script': ETL_DIR / 'data_loader.py',
        'description': 'ETL - Carga y procesamiento de datos base',
        'args': etl_args
    })
    
    if not skip_enrichment:
        # PASO 2: Enrichment - APIs externas
        enrichment_args = ['--max-movies', str(max_movies)] if max_movies else None
        steps.append({
            'script': ENRICHMENT_DIR / 'enrichment.py',
            'description': 'Enrichment - Enriquecimiento con TMDb/OMDb',
            'args': enrichment_args
        })
        
        # PASO 3: NLP Inference
        nlp_args = ['--max-movies', str(max_movies)] if max_movies else None
        steps.append({
            'script': ENRICHMENT_DIR / 'nlp_inference.py',
            'description': 'NLP Inference - Inferencias contextuales',
            'args': nlp_args
        })
    else:
        logger.info("⊘ Omitiendo enriquecimiento (usando datos existentes)\n")
    
    # PASO 4: RDF Generation - Películas
    rdf_args = [str(max_movies)] if max_movies else None
    steps.append({
        'script': RDF_DIR / 'rdf_generator.py',
        'description': 'RDF Generation - Tripletas de películas',
        'args': rdf_args
    })
    
    # PASO 5: RDF Generation - Contextos
    steps.append({
        'script': RDF_DIR / 'rdf_context_generator.py',
        'description': 'RDF Generation - Contextos',
        'args': None
    })
    
    # PASO 6: RDF Generation - Bridges
    steps.append({
        'script': RDF_DIR / 'rdf_bridge_generator.py',
        'description': 'RDF Generation - Bridges película-contexto',
        'args': rdf_args
    })
    
    # Ejecutar todos los pasos
    for i, step in enumerate(steps, 1):
        logger.info(f"\n>>> PASO {i}/{len(steps)}: {step['description']}")
        
        if not run_script(step['script'], step['description'], step['args']):
            logger.error(f"✗ Pipeline FALLÓ en el paso {i}")
            return False
    
    # PASO 7: Importar a GraphDB (opcional)
    if not skip_import:
        logger.info(f"\n>>> PASO FINAL: Importación a GraphDB")
        if not import_to_graphdb():
            logger.error("✗ Pipeline FALLÓ en la importación a GraphDB")
            return False
    else:
        logger.info("\n⊘ Omitiendo importación a GraphDB")
    
    # Limpiar archivos intermedios
    cleanup_intermediate_files()
    
    # Success!
    logger.info("\n" + "="*70)
    logger.info("✓ PIPELINE COMPLETADO EXITOSAMENTE")
    logger.info("="*70)
    logger.info("\nPróximos pasos:")
    if skip_import:
        logger.info("  - Ejecuta el pipeline con importación para actualizar GraphDB")
        logger.info("  - O ejecuta manualmente: docker exec graphdb-tesis /bin/bash /docker-entrypoint-initdb.d/02-import-ontologies.sh")
    else:
        logger.info("  - Verifica los datos en GraphDB: http://localhost:7200")
        logger.info("  - Ejecuta queries SPARQL para validar la importación")
    logger.info("="*70 + "\n")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Pipeline completo para procesar películas y generar datos RDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Pipeline completo (todas las películas)
  python pipeline.py
  
  # Pipeline con límite de películas
  python pipeline.py --max-movies 100
  
  # Regenerar RDF sin enriquecer nuevamente
  python pipeline.py --skip-enrichment
  
  # Generar archivos sin importar a GraphDB
  python pipeline.py --skip-import
  
  # Combinación: 500 películas sin importar
  python pipeline.py --max-movies 500 --skip-import
        """
    )
    
    parser.add_argument(
        '--max-movies',
        type=int,
        help='Número máximo de películas a procesar (default: todas)'
    )
    
    parser.add_argument(
        '--skip-enrichment',
        action='store_true',
        help='Omitir enriquecimiento con APIs (usa datos existentes)'
    )
    
    parser.add_argument(
        '--skip-import',
        action='store_true',
        help='Omitir importación a GraphDB'
    )
    
    args = parser.parse_args()
    
    # Ejecutar pipeline
    success = run_pipeline(
        max_movies=args.max_movies,
        skip_enrichment=args.skip_enrichment,
        skip_import=args.skip_import
    )
    
    # Exit code según resultado
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
