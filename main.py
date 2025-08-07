#!/usr/bin/env python3
"""
Sistema de crawling de eventos de Salto
Extrae eventos de salto.gub.uy y genera posts de Instagram
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from src.scraper import EventScraper
from src.database import DatabaseManager
from src.instagram_generator import InstagramPostGenerator
from src.instagram_publisher import InstagramPublisherSimple

# Configurar logging
logging.basicConfig(
    level=logging.INFO,  # Volver a INFO para logs más limpios
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('events_crawler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Función principal del sistema"""
    logger.info("Iniciando sistema de crawling de eventos")
    
    try:
        # Inicializar componentes
        db_manager = DatabaseManager()
        scraper = EventScraper()
        instagram_generator = InstagramPostGenerator()
        instagram_publisher = InstagramPublisherSimple()
        
        # Crear directorio para imágenes si no existe
        Path("images").mkdir(exist_ok=True)
        Path("posts").mkdir(exist_ok=True)
        
        # Extraer eventos
        logger.info("Extrayendo eventos de salto.gub.uy")
        eventos = await scraper.scrape_events()
        
        if not eventos:
            logger.warning("No se encontraron eventos")
            return
        
        logger.info(f"Encontrados {len(eventos)} eventos")
        
        # Procesar cada evento
        for evento in eventos:
            try:
                # Verificar si el evento ya existe en la BD
                if not db_manager.event_exists(evento['title']):
                    # Guardar en base de datos
                    event_id = db_manager.save_event(evento)
                    logger.info(f"Evento guardado con ID: {event_id}")
                    
                    # Generar post de Instagram
                    post_path = await instagram_generator.create_post(evento)
                    
                    # Actualizar la BD con la ruta del post
                    db_manager.update_event_post_path(event_id, post_path)
                    
                    logger.info(f"Post de Instagram generado: {post_path}")
                    
                    # Publicar automáticamente en Instagram si está configurado
                    if instagram_publisher.is_configured():
                        logger.info(f"Publicando en Instagram: {evento['title']}")
                        
                        try:
                            post_id = await instagram_publisher.publish_post(evento, post_path)
                            
                            if post_id:
                                # Marcar como publicado en la base de datos
                                db_manager.mark_instagram_posted(event_id)
                                logger.info(f"✅ Publicado exitosamente en Instagram: {post_id}")
                            else:
                                logger.warning(f"❌ Error publicando en Instagram: {evento['title']}")
                                
                        except Exception as e:
                            logger.error(f"Error en publicación automática de Instagram: {e}")
                    else:
                        logger.info("Instagram no configurado - solo se generó el post local")
                else:
                    logger.info(f"Evento ya existe: {evento['title']}")
                    
            except Exception as e:
                logger.error(f"Error procesando evento {evento.get('title', 'Desconocido')}: {e}")
        
        logger.info("Proceso completado exitosamente")
        
    except Exception as e:
        logger.error(f"Error en el proceso principal: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
