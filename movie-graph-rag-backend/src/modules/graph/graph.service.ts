import {
  Injectable,
  Logger,
  InternalServerErrorException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios from 'axios';

/**
 * GRAPH SERVICE - Cliente SPARQL para Apache Jena Fuseki
 * Este servicio actúa como un cliente HTTP para ejecutar consultas SPARQL contra
 * un servidor Apache Jena Fuseki. Proporciona una capa de abstracción que simplifica la
 * comunicación con el grafo de conocimiento, manejando:
 *
 * 1. CONSULTAS SELECT (executeQuery):
 *    - Ejecuta consultas SPARQL de lectura
 *    - Transforma los resultados de formato SPARQL JSON a objetos JavaScript simples
 *    - Tipado genérico para mayor seguridad de tipos
 *    - Ejemplo: Buscar películas por género, obtener detalles de un usuario, etc.
 *
 * 2. ACTUALIZACIONES (executeUpdate):
 *    - Ejecuta operaciones SPARQL de escritura (INSERT, DELETE, UPDATE)
 *    - Modifica el estado del grafo de conocimiento
 *    - Ejemplo: Crear un nuevo contexto de usuario, registrar una interacción, etc.
 */

interface SparqlBinding {
  [key: string]: { value: any };
}

interface SparqlResponse {
  results: {
    bindings: SparqlBinding[];
  };
}

@Injectable()
export class GraphService {
  private readonly logger = new Logger(GraphService.name);
  private readonly fusekiUrl: string;
  private readonly datasetId: string;
  private readonly authConfig: { username: string; password: string };

  constructor(private configService: ConfigService) {
    // Obtenemos valores del .env
    const fusekiUrl = this.configService.get<string>('FUSEKI_URL');
    const datasetId = this.configService.get<string>('FUSEKI_DATASET');
    if (!fusekiUrl || !datasetId) {
      throw new Error(
        'FUSEKI_URL or FUSEKI_DATASET is not defined in environment variables',
      );
    }
    this.fusekiUrl = fusekiUrl;
    this.datasetId = datasetId;

    // Configuración de autenticación (requerida)
    const fusekiUser = this.configService.get<string>('FUSEKI_USER');
    const fusekiPassword = this.configService.get<string>('FUSEKI_PASSWORD');
    if (!fusekiUser || !fusekiPassword) {
      this.logger.warn(
        'FUSEKI_USER and FUSEKI_PASSWORD not configured - Fuseki operations may fail if authentication is enabled',
      );
    }
    this.authConfig = {
      username: fusekiUser || '',
      password: fusekiPassword || '',
    };
  }

  /**
   * Ejecuta una consulta SPARQL de tipo SELECT.
   * @param sparqlQuery La consulta en formato string.
   */
  async executeQuery<T extends Record<string, any> = Record<string, any>>(
    sparqlQuery: string,
  ): Promise<T[]> {
    const endpoint = `${this.fusekiUrl}/${this.datasetId}/query`;

    try {
      this.logger.log('Ejecutando consulta SPARQL SELECT en Fuseki...');

      const response = await axios.post<SparqlResponse>(
        endpoint,
        `query=${encodeURIComponent(sparqlQuery)}`,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            Accept: 'application/sparql-results+json',
          },
          auth: this.authConfig,
          timeout: 30000, // 30 segundos timeout
        },
      );

      // Mapeamos los resultados para que sean más fáciles de leer en JS
      const bindings = response.data?.results?.bindings ?? [];
      return this.mapBindings(bindings) as T[];
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      this.logger.error(`Error en Fuseki (Select): ${errorMessage}`);
      throw new InternalServerErrorException(
        'Error al consultar el Grafo de Conocimiento',
      );
    }
  }

  /**
   * Ejecuta una actualización SPARQL (INSERT, DELETE, etc).
   * @param updateQuery La consulta de actualización.
   */
  async executeUpdate(updateQuery: string): Promise<void> {
    const endpoint = `${this.fusekiUrl}/${this.datasetId}/update`;

    try {
      this.logger.log(
        'Ejecutando actualización SPARQL (Update/Insert) en Fuseki...',
      );

      await axios.post(endpoint, `update=${encodeURIComponent(updateQuery)}`, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        auth: this.authConfig,
        timeout: 30000, // 30 segundos timeout
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      this.logger.error(`Error en Fuseki (Update): ${errorMessage}`);
      throw new InternalServerErrorException(
        'Error al actualizar el Grafo de Conocimiento',
      );
    }
  }

  /**
   * Limpia los resultados de SPARQL para eliminar el formato .value
   */
  private mapBindings(bindings: SparqlBinding[]): Record<string, any>[] {
    return bindings.map((binding) => {
      const simplified: Record<string, any> = {};
      Object.keys(binding).forEach((key) => {
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        simplified[key] = binding[key].value;
      });
      return simplified;
    });
  }
}
