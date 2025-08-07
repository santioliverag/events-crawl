#!/usr/bin/env python3
"""
Script para ejecutar el sistema de forma programada
Útil para configurar con cron o task scheduler
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

# Añadir directorio src al path
sys.path.append(str(Path(__file__).parent / 'src'))

from database import DatabaseManager
from main import main as run_main_process


def setup_scheduler_logging():
    """Configura logging específico para el scheduler"""
    log_file = f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - SCHEDULER - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


async def scheduled_run():
    """Ejecuta el proceso principal con manejo de errores para scheduler"""
    logger = setup_scheduler_logging()
    
    try:
        logger.info("=== INICIO DE EJECUCIÓN PROGRAMADA ===")
        
        # Verificar estado de la base de datos antes
        db = DatabaseManager()
        stats_before = db.get_stats()
        logger.info(f"Estado inicial - Eventos: {stats_before.get('total_events', 0)}, "
                   f"Posts: {stats_before.get('posts_generated', 0)}")
        
        # Ejecutar proceso principal
        await run_main_process()
        
        # Verificar estado después
        stats_after = db.get_stats()
        new_events = stats_after.get('total_events', 0) - stats_before.get('total_events', 0)
        new_posts = stats_after.get('posts_generated', 0) - stats_before.get('posts_generated', 0)
        
        logger.info(f"Estado final - Eventos: {stats_after.get('total_events', 0)} (+{new_events}), "
                   f"Posts: {stats_after.get('posts_generated', 0)} (+{new_posts})")
        
        if new_events > 0:
            logger.info(f"✅ Se procesaron {new_events} eventos nuevos y se generaron {new_posts} posts")
        else:
            logger.info("ℹ️  No se encontraron eventos nuevos")
        
        logger.info("=== FIN DE EJECUCIÓN PROGRAMADA ===")
        
    except Exception as e:
        logger.error(f"❌ Error en ejecución programada: {e}")
        sys.exit(1)


def show_cron_examples():
    """Muestra ejemplos de configuración para cron"""
    print("\n📅 Ejemplos de configuración para Cron (Linux/Mac):")
    print("=" * 50)
    
    script_path = Path(__file__).absolute()
    python_path = sys.executable
    
    examples = [
        ("Cada día a las 9:00 AM", "0 9 * * *"),
        ("Cada 6 horas", "0 */6 * * *"),
        ("Lunes a Viernes a las 8:00 AM", "0 8 * * 1-5"),
        ("Cada domingo a las 10:00 AM", "0 10 * * 0"),
    ]
    
    for description, schedule in examples:
        print(f"\n# {description}")
        print(f"{schedule} {python_path} {script_path}")
    
    print(f"\n📝 Para editar crontab: crontab -e")
    print(f"📋 Para ver crontab actual: crontab -l")
    
    print("\n🪟 Para Windows Task Scheduler:")
    print("Crear tarea básica → Trigger → Acción:")
    print(f"Programa: {python_path}")
    print(f"Argumentos: {script_path}")
    print(f"Iniciar en: {script_path.parent}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scheduler para el sistema de crawling de eventos')
    parser.add_argument('--show-cron', action='store_true', 
                       help='Mostrar ejemplos de configuración para cron')
    
    args = parser.parse_args()
    
    if args.show_cron:
        show_cron_examples()
    else:
        asyncio.run(scheduled_run())
