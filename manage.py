#!/usr/bin/env python3
"""
Script de gestión para el sistema de crawling de eventos
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Añadir directorio src al path
sys.path.append(str(Path(__file__).parent / 'src'))

from database import DatabaseManager
from scraper import EventScraper
from instagram_generator import InstagramPostGenerator
from instagram_publisher import InstagramPublisherSimple


def show_stats():
    """Muestra estadísticas de la base de datos"""
    db = DatabaseManager()
    stats = db.get_stats()
    
    print("\n📊 Estadísticas del Sistema")
    print("=" * 40)
    print(f"Total de eventos: {stats.get('total_events', 0)}")
    print(f"Posts generados: {stats.get('posts_generated', 0)}")
    print(f"Publicados en Instagram: {stats.get('instagram_posted', 0)}")
    print(f"Posts pendientes: {stats.get('pending_posts', 0)}")
    
    # Mostrar eventos recientes
    recent_events = db.get_recent_events(5)
    if recent_events:
        print("\n📅 Eventos Recientes:")
        print("-" * 40)
        for event in recent_events:
            status = "✅" if event['post_generated'] else "⏳"
            print(f"{status} {event['title'][:50]}...")
            if event.get('formatted_date'):
                print(f"   📅 {event['formatted_date']}")


def list_events():
    """Lista todos los eventos en la base de datos"""
    db = DatabaseManager()
    recent_events = db.get_recent_events(20)
    
    if not recent_events:
        print("No hay eventos en la base de datos.")
        return
    
    print("\n📋 Lista de Eventos")
    print("=" * 60)
    
    for i, event in enumerate(recent_events, 1):
        post_status = "✅ Post generado" if event['post_generated'] else "⏳ Pendiente"
        instagram_status = "📱 Publicado" if event['instagram_posted'] else "❌ No publicado"
        
        print(f"\n{i}. {event['title']}")
        print(f"   📅 Fecha: {event.get('formatted_date', 'No especificada')}")
        print(f"   📝 {event.get('description', '')[:100]}...")
        print(f"   🎨 {post_status}")
        print(f"   📱 {instagram_status}")


async def test_scraper():
    """Prueba el scraper sin guardar en base de datos"""
    print("🕸️ Probando web scraper...")
    
    scraper = EventScraper()
    events = await scraper.scrape_events()
    
    if events:
        print(f"\n✅ Encontrados {len(events)} eventos:")
        for i, event in enumerate(events[:3], 1):  # Mostrar solo los primeros 3
            print(f"\n{i}. {event.get('title', 'Sin título')}")
            print(f"   📅 {event.get('formatted_date', 'Fecha no encontrada')}")
            print(f"   📝 {event.get('description', 'Sin descripción')[:100]}...")
            if event.get('image_url'):
                print(f"   🖼️ Imagen: {event['image_url']}")
    else:
        print("❌ No se encontraron eventos")


async def test_post_generator():
    """Prueba el generador de posts con datos de ejemplo"""
    print("🎨 Probando generador de posts...")
    
    # Datos de ejemplo
    sample_event = {
        'title': 'EVENTO DE PRUEBA - Festival de Arte',
        'description': 'Un evento de prueba para verificar el generador de posts de Instagram. Este evento incluye múltiples actividades artísticas y culturales.',
        'formatted_date': '25/12/2024',
        'event_date': '2024-12-25',
        'image_path': None  # Sin imagen para esta prueba
    }
    
    generator = InstagramPostGenerator()
    
    try:
        post_path = await generator.create_post(sample_event)
        print(f"✅ Post de prueba generado: {post_path}")
    except Exception as e:
        print(f"❌ Error generando post: {e}")


def cleanup_old_data(days: int = 30):
    """Limpia eventos antiguos"""
    db = DatabaseManager()
    
    print(f"🧹 Limpiando eventos más antiguos de {days} días...")
    
    try:
        db.cleanup_old_events(days)
        print("✅ Limpieza completada")
    except Exception as e:
        print(f"❌ Error en limpieza: {e}")


async def test_instagram():
    """Prueba la configuración de Instagram"""
    print("📱 Probando configuración de Instagram...")
    
    publisher = InstagramPublisherSimple()
    
    if not publisher.is_configured():
        print("❌ Instagram no configurado")
        print("\n💡 Para configurar Instagram:")
        print("   export INSTAGRAM_USERNAME='tu_usuario'")
        print("   export INSTAGRAM_PASSWORD='tu_contraseña'")
        print("   pip install instagrapi")
        print("\n📖 Ver guía completa: INSTAGRAM_SETUP.md")
        return
    
    try:
        success = await publisher.login()
        if success:
            print("✅ Instagram configurado correctamente")
            print(f"   Usuario: @{publisher.username}")
        else:
            print("❌ Error de autenticación en Instagram")
            print("   Verifica usuario y contraseña")
    except Exception as e:
        print(f"❌ Error conectando a Instagram: {e}")


def main():
    """Función principal del script de gestión"""
    parser = argparse.ArgumentParser(description='Gestión del sistema de crawling de eventos')
    parser.add_argument('action', choices=[
        'stats', 'list', 'test-scraper', 'test-generator', 'test-instagram', 'cleanup'
    ], help='Acción a realizar')
    parser.add_argument('--days', type=int, default=30, 
                       help='Días para la limpieza de eventos antiguos')
    
    args = parser.parse_args()
    
    if args.action == 'stats':
        show_stats()
    elif args.action == 'list':
        list_events()
    elif args.action == 'test-scraper':
        asyncio.run(test_scraper())
    elif args.action == 'test-generator':
        asyncio.run(test_post_generator())
    elif args.action == 'test-instagram':
        asyncio.run(test_instagram())
    elif args.action == 'cleanup':
        cleanup_old_data(args.days)


if __name__ == "__main__":
    main()
