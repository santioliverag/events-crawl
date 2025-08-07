#!/usr/bin/env python3
"""
Interfaz web para gestionar posts de Instagram
Dashboard visual para decidir qué y cuándo publicar
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PIL import Image

# Añadir directorio src al path
sys.path.append(str(Path(__file__).parent / 'src'))

from database import DatabaseManager
from scraper import EventScraper
from instagram_generator import InstagramPostGenerator
from instagram_publisher import InstagramPublisherSimple

app = Flask(__name__)
app.secret_key = 'eventos_salto_secret_key_2025'

# Configuración
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Asegurar que existan los directorios
Path('uploads').mkdir(exist_ok=True)
Path('templates').mkdir(exist_ok=True)
Path('static/css').mkdir(parents=True, exist_ok=True)
Path('static/js').mkdir(parents=True, exist_ok=True)


@app.route('/')
def dashboard():
    """Dashboard principal con lista de eventos y posts"""
    try:
        db = DatabaseManager()
        
        # Obtener estadísticas
        stats = db.get_stats()
        
        # Obtener eventos recientes
        events = db.get_recent_events(20)
        
        # Obtener eventos sin publicar
        unpublished = db.get_events_without_posts()
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             events=events, 
                             unpublished=unpublished)
    except Exception as e:
        flash(f'Error cargando dashboard: {e}', 'error')
        return render_template('dashboard.html', stats={}, events=[], unpublished=[])


@app.route('/api/extract_events', methods=['POST'])
def extract_events():
    """Extrae nuevos eventos del sitio web"""
    try:
        # Ejecutar scraper en segundo plano
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        scraper = EventScraper()
        events = loop.run_until_complete(scraper.scrape_events())
        
        db = DatabaseManager()
        new_events = 0
        
        for evento in events:
            if not db.event_exists(evento['title']):
                db.save_event(evento)
                new_events += 1
        
        return jsonify({
            'success': True, 
            'message': f'Se encontraron {len(events)} eventos, {new_events} nuevos',
            'new_events': new_events
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/generate_post/<int:event_id>')
def generate_post(event_id):
    """Genera post de Instagram para un evento específico"""
    try:
        db = DatabaseManager()
        event = db.get_event_by_id(event_id)
        
        if not event:
            return jsonify({'success': False, 'error': 'Evento no encontrado'})
        
        # Generar post
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        generator = InstagramPostGenerator()
        post_path = loop.run_until_complete(generator.create_post(event))
        
        # Actualizar base de datos
        db.update_event_post_path(event_id, post_path)
        
        return jsonify({
            'success': True, 
            'message': 'Post generado exitosamente',
            'post_path': post_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/publish_post/<int:event_id>')
def publish_post(event_id):
    """Publica post en Instagram"""
    try:
        db = DatabaseManager()
        event = db.get_event_by_id(event_id)
        
        if not event:
            return jsonify({'success': False, 'error': 'Evento no encontrado'})
        
        if not event['post_path']:
            return jsonify({'success': False, 'error': 'Post no generado aún'})
        
        # Publicar en Instagram
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        publisher = InstagramPublisherSimple()
        
        if not publisher.is_configured():
            return jsonify({'success': False, 'error': 'Instagram no configurado'})
        
        post_id = loop.run_until_complete(publisher.publish_post(event, event['post_path']))
        
        if post_id:
            db.mark_instagram_posted(event_id)
            return jsonify({
                'success': True, 
                'message': 'Publicado exitosamente en Instagram',
                'post_id': post_id
            })
        else:
            return jsonify({'success': False, 'error': 'Error en publicación'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/delete_event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Elimina un evento"""
    try:
        db = DatabaseManager()
        
        # Obtener evento para eliminar archivos
        event = db.get_event_by_id(event_id)
        if event:
            # Eliminar archivos asociados
            if event.get('image_path') and Path(event['image_path']).exists():
                Path(event['image_path']).unlink()
            if event.get('post_path') and Path(event['post_path']).exists():
                Path(event['post_path']).unlink()
        
        # Eliminar de base de datos
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Evento eliminado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/preview/<int:event_id>')
def preview_event(event_id):
    """Vista de previsualización de un evento"""
    try:
        db = DatabaseManager()
        event = db.get_event_by_id(event_id)
        
        if not event:
            flash('Evento no encontrado', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('preview.html', event=event)
    except Exception as e:
        flash(f'Error cargando evento: {e}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/image/<path:filename>')
def serve_image(filename):
    """Sirve imágenes estáticamente"""
    try:
        return send_file(filename)
    except:
        return "Imagen no encontrada", 404


@app.route('/settings')
def settings():
    """Página de configuración"""
    try:
        # Verificar estado de Instagram
        publisher = InstagramPublisherSimple()
        instagram_configured = publisher.is_configured()
        
        return render_template('settings.html', 
                             instagram_configured=instagram_configured)
    except Exception as e:
        flash(f'Error cargando configuración: {e}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/add_event')
def add_event():
    """Página para agregar eventos manualmente"""
    return render_template('add_event.html')


@app.route('/api/create_manual_event', methods=['POST'])
def create_manual_event():
    """Crea un evento manual desde el formulario"""
    try:
        # Obtener datos del formulario
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        event_date = request.form.get('event_date', '')
        link = request.form.get('link', '').strip()
        generate_immediately = request.form.get('generate_immediately') == 'on'
        publish_immediately = request.form.get('publish_immediately') == 'on'
        
        if not title or not description:
            return jsonify({'success': False, 'error': 'Título y descripción son obligatorios'})
        
        # Procesar imagen si se subió
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                if file.content_length > 10 * 1024 * 1024:  # 10MB
                    return jsonify({'success': False, 'error': 'Imagen muy grande (máximo 10MB)'})
                
                filename = secure_filename(file.filename)
                if filename:
                    # Crear nombre único
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    name, ext = os.path.splitext(filename)
                    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
                    safe_title = safe_title.replace(' ', '-')
                    new_filename = f"manual_{safe_title}_{timestamp}{ext}"
                    
                    # Guardar imagen
                    Path('images').mkdir(exist_ok=True)
                    image_path = Path('images') / new_filename
                    file.save(str(image_path))
                    
                    # Redimensionar si es muy grande
                    try:
                        with Image.open(image_path) as img:
                            if img.width > 2000 or img.height > 2000:
                                img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                                img.save(image_path, optimize=True, quality=85)
                    except Exception as e:
                        print(f"Error redimensionando imagen: {e}")
        
        # Formatear fecha
        formatted_date = ""
        if event_date:
            try:
                date_obj = datetime.strptime(event_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d de %B de %Y')
            except:
                formatted_date = event_date
        
        # Crear evento
        event_data = {
            'title': title,
            'description': description,
            'formatted_date': formatted_date,
            'image_path': str(image_path) if image_path else None,
            'link': link if link else None,
            'created_manually': True
        }
        
        # Guardar en base de datos
        db = DatabaseManager()
        event_id = db.save_event(event_data)
        
        # Generar post si se solicitó
        post_path = None
        if generate_immediately and image_path:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                generator = InstagramPostGenerator()
                post_path = loop.run_until_complete(generator.create_post(event_data))
                db.update_event_post_path(event_id, post_path)
            except Exception as e:
                print(f"Error generando post: {e}")
        
        # Publicar si se solicitó
        if publish_immediately and post_path:
            try:
                publisher = InstagramPublisherSimple()
                if publisher.is_configured():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    event_data['post_path'] = post_path
                    post_id = loop.run_until_complete(publisher.publish_post(event_data, post_path))
                    if post_id:
                        db.mark_instagram_posted(event_id)
            except Exception as e:
                print(f"Error publicando: {e}")
        
        return jsonify({
            'success': True, 
            'message': 'Evento creado exitosamente',
            'event_id': event_id,
            'redirect': url_for('preview_event', event_id=event_id)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/test_instagram')
def test_instagram():
    """Prueba conexión con Instagram"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        publisher = InstagramPublisherSimple()
        
        if not publisher.is_configured():
            return jsonify({'success': False, 'error': 'Instagram no configurado'})
        
        success = loop.run_until_complete(publisher.login())
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Conectado exitosamente como @{publisher.username}'
            })
        else:
            return jsonify({'success': False, 'error': 'Error de autenticación'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print("🌐 Iniciando servidor web...")
    print("📱 Dashboard disponible en: http://localhost:8080")
    print("⭐ Usa Ctrl+C para detener")
    
    app.run(debug=True, host='0.0.0.0', port=8080)
