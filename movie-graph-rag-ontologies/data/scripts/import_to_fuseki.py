#!/usr/bin/env python3
"""
Importa archivos TTL generados a Fuseki.

Uso:
    python import_to_fuseki.py
    python import_to_fuseki.py --fuseki-url http://localhost:3030 --dataset movies
"""

import requests
import argparse
from pathlib import Path
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
DATA_ROOT = Path(__file__).resolve().parents[2]  # movie-graph-rag-ontologies/
DATA_DIR = DATA_ROOT / "data"
ONTOLOGIES_DIR = DATA_DIR / "ontologies" / "instances"

MOVIES_TTL = ONTOLOGIES_DIR / "movies_data.ttl"
CONTEXTS_TTL = ONTOLOGIES_DIR / "contexts_data.ttl"
BRIDGE_TTL = ONTOLOGIES_DIR / "bridge_data.ttl"

def import_ttl_to_fuseki(ttl_file, fuseki_url, dataset, username=None, password=None):
    """Import a TTL file to Fuseki using HTTP POST."""
    
    if not ttl_file.exists():
        logger.error(f"✗ File not found: {ttl_file}")
        return False
    
    url = f"{fuseki_url}/{dataset}/data"
    
    logger.info(f"Uploading {ttl_file.name} to {url}")
    logger.info(f"File size: {ttl_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    try:
        with open(ttl_file, 'rb') as f:
            # Upload with turtle content type
            auth = None
            if username and password:
                auth = (username, password)
            
            response = requests.post(
                url,
                data=f,
                headers={'Content-Type': 'text/turtle'},
                auth=auth,
                timeout=300  # 5 minutes timeout
            )
        
        if response.status_code in [200, 201, 204]:
            logger.info(f"✓ Successfully imported {ttl_file.name}")
            return True
        else:
            logger.error(f"✗ Failed to import {ttl_file.name}")
            logger.error(f"  Status: {response.status_code}")
            logger.error(f"  Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"✗ Timeout uploading {ttl_file.name} (> 5 minutes)")
        return False
    except Exception as e:
        logger.error(f"✗ Error uploading {ttl_file.name}: {e}")
        return False

def main():
    # Load environment variables from .env
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    # Get credentials from environment variables
    env_fuseki_url = os.getenv("FUSEKI_URL", "http://localhost:3030")
    env_fuseki_dataset = os.getenv("FUSEKI_DATASET", "movies")
    env_fuseki_user = os.getenv("FUSEKI_USER")
    env_fuseki_password = os.getenv("FUSEKI_PASSWORD")
    
    parser = argparse.ArgumentParser(description="Import TTL files to Fuseki")
    parser.add_argument("--fuseki-url", default=env_fuseki_url, 
                       help=f"Fuseki base URL (default: {env_fuseki_url})")
    parser.add_argument("--dataset", default=env_fuseki_dataset,
                       help=f"Fuseki dataset name (default: {env_fuseki_dataset})")
    parser.add_argument("--username", default=env_fuseki_user,
                       help=f"Fuseki username (default: {env_fuseki_user})")
    parser.add_argument("--password", default=env_fuseki_password,
                       help="Fuseki password (default: from .env)")
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("IMPORTING RDF DATA TO FUSEKI")
    logger.info("=" * 70)
    
    # Test connection
    try:
        auth = None
        if args.username and args.password:
            auth = (args.username, args.password)
        
        response = requests.get(f"{args.fuseki_url}/$/stats", timeout=5, auth=auth)
        if response.status_code == 200:
            logger.info(f"✓ Connected to Fuseki at {args.fuseki_url}")
        else:
            logger.error(f"✗ Fuseki returned status {response.status_code}")
            if response.status_code == 401:
                logger.error("  Authentication required. Use --username and --password")
            return 1
    except Exception as e:
        logger.error(f"✗ Cannot connect to Fuseki at {args.fuseki_url}: {e}")
        logger.info("Make sure Fuseki is running: docker ps | grep fuseki")
        return 1
    
    # Import files in order
    files = [
        (MOVIES_TTL, "Movies ontology"),
        (CONTEXTS_TTL, "Contexts ontology"),
        (BRIDGE_TTL, "Bridge ontology (Option C)")
    ]
    
    results = []
    for ttl_file, description in files:
        logger.info(f"\n{description}:")
        success = import_ttl_to_fuseki(ttl_file, args.fuseki_url, args.dataset, 
                                       args.username, args.password)
        results.append((description, success))
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("IMPORT SUMMARY")
    logger.info("=" * 70)
    
    for description, success in results:
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info(f"{status}: {description}")
    
    all_success = all(success for _, success in results)
    
    if all_success:
        logger.info("\n✅ All files imported successfully!")
        logger.info(f"Data available at: {args.fuseki_url}/{args.dataset}")
        return 0
    else:
        logger.info("\n⚠ Some imports failed. Check above for details.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
