"""
Gestor de base de datos para eventos
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestor de base de datos SQLite para eventos"""
    
    def __init__(self, db_path: str = "events.db"):
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """Crea las tablas necesarias si no existen"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tabla principal de eventos
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL UNIQUE,
                        description TEXT,
                        event_date TEXT,
                        formatted_date TEXT,
                        image_url TEXT,
                        image_path TEXT,
                        link TEXT,
                        scraped_at TEXT NOT NULL,
                        post_generated BOOLEAN DEFAULT FALSE,
                        post_path TEXT,
                        instagram_posted BOOLEAN DEFAULT FALSE,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabla de logs de procesamiento
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processing_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER,
                        action TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (event_id) REFERENCES events (id)
                    )
                """)
                
                conn.commit()
                logger.info("Tablas de base de datos creadas/verificadas")
                
        except sqlite3.Error as e:
            logger.error(f"Error creando tablas: {e}")
            raise
    
    def save_event(self, event_data: Dict) -> int:
        """
        Guarda un evento en la base de datos
        
        Args:
            event_data: Diccionario con los datos del evento
            
        Returns:
            ID del evento guardado
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Preparar datos para inserción
                scraped_at = event_data.get('scraped_at', datetime.now())
                if isinstance(scraped_at, datetime):
                    scraped_at = scraped_at.isoformat()
                
                event_date = event_data.get('event_date')
                if isinstance(event_date, datetime):
                    event_date = event_date.isoformat()
                
                cursor.execute("""
                    INSERT INTO events (
                        title, description, event_date, formatted_date,
                        image_url, image_path, link, scraped_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_data.get('title'),
                    event_data.get('description'),
                    event_date,
                    event_data.get('formatted_date'),
                    event_data.get('image_url'),
                    event_data.get('image_path'),
                    event_data.get('link'),
                    scraped_at
                ))
                
                event_id = cursor.lastrowid
                
                # Log de la acción
                self._log_action(cursor, event_id, 'CREATED', 'SUCCESS', 
                               f"Evento '{event_data.get('title')}' guardado")
                
                conn.commit()
                logger.info(f"Evento guardado con ID {event_id}: {event_data.get('title')}")
                
                return event_id
                
        except sqlite3.IntegrityError as e:
            logger.warning(f"Evento ya existe: {event_data.get('title')}")
            raise
        except sqlite3.Error as e:
            logger.error(f"Error guardando evento: {e}")
            raise
    
    def event_exists(self, title: str) -> bool:
        """
        Verifica si un evento ya existe en la base de datos
        
        Args:
            title: Título del evento
            
        Returns:
            True si existe, False si no
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM events WHERE title = ?", (title,))
                result = cursor.fetchone()
                return result is not None
                
        except sqlite3.Error as e:
            logger.error(f"Error verificando existencia del evento: {e}")
            return False
    
    def get_event_by_id(self, event_id: int) -> Optional[Dict]:
        """
        Obtiene un evento por su ID
        
        Args:
            event_id: ID del evento
            
        Returns:
            Diccionario con los datos del evento o None si no existe
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo evento {event_id}: {e}")
            return None
    
    def get_events_without_posts(self) -> List[Dict]:
        """
        Obtiene eventos que no tienen posts generados
        
        Returns:
            Lista de eventos sin posts
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM events 
                    WHERE post_generated = FALSE 
                    ORDER BY event_date ASC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo eventos sin posts: {e}")
            return []
    
    def update_event_post_path(self, event_id: int, post_path: str):
        """
        Actualiza la ruta del post generado para un evento
        
        Args:
            event_id: ID del evento
            post_path: Ruta del archivo de post generado
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE events 
                    SET post_generated = TRUE, post_path = ?
                    WHERE id = ?
                """, (post_path, event_id))
                
                self._log_action(cursor, event_id, 'POST_GENERATED', 'SUCCESS',
                               f"Post generado: {post_path}")
                
                conn.commit()
                logger.info(f"Post path actualizado para evento {event_id}: {post_path}")
                
        except sqlite3.Error as e:
            logger.error(f"Error actualizando post path: {e}")
            raise
    
    def mark_instagram_posted(self, event_id: int):
        """
        Marca un evento como publicado en Instagram
        
        Args:
            event_id: ID del evento
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE events 
                    SET instagram_posted = TRUE
                    WHERE id = ?
                """, (event_id,))
                
                self._log_action(cursor, event_id, 'INSTAGRAM_POSTED', 'SUCCESS',
                               "Publicado en Instagram")
                
                conn.commit()
                logger.info(f"Evento {event_id} marcado como publicado en Instagram")
                
        except sqlite3.Error as e:
            logger.error(f"Error marcando como publicado: {e}")
            raise
    
    def get_recent_events(self, limit: int = 10) -> List[Dict]:
        """
        Obtiene los eventos más recientes
        
        Args:
            limit: Número máximo de eventos a retornar
            
        Returns:
            Lista de eventos recientes
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM events 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo eventos recientes: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas de la base de datos
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total de eventos
                cursor.execute("SELECT COUNT(*) FROM events")
                stats['total_events'] = cursor.fetchone()[0]
                
                # Posts generados
                cursor.execute("SELECT COUNT(*) FROM events WHERE post_generated = TRUE")
                stats['posts_generated'] = cursor.fetchone()[0]
                
                # Publicados en Instagram
                cursor.execute("SELECT COUNT(*) FROM events WHERE instagram_posted = TRUE")
                stats['instagram_posted'] = cursor.fetchone()[0]
                
                # Eventos pendientes
                cursor.execute("SELECT COUNT(*) FROM events WHERE post_generated = FALSE")
                stats['pending_posts'] = cursor.fetchone()[0]
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def _log_action(self, cursor, event_id: int, action: str, status: str, message: str = ""):
        """
        Registra una acción en los logs
        
        Args:
            cursor: Cursor de la base de datos
            event_id: ID del evento
            action: Tipo de acción
            status: Estado de la acción
            message: Mensaje adicional
        """
        try:
            cursor.execute("""
                INSERT INTO processing_logs (event_id, action, status, message)
                VALUES (?, ?, ?, ?)
            """, (event_id, action, status, message))
            
        except sqlite3.Error as e:
            logger.error(f"Error registrando log: {e}")
    
    def cleanup_old_events(self, days: int = 30):
        """
        Limpia eventos antiguos de la base de datos
        
        Args:
            days: Número de días para considerar eventos como antiguos
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM events 
                    WHERE created_at < datetime('now', '-{} days')
                    AND instagram_posted = TRUE
                """.format(days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Eliminados {deleted_count} eventos antiguos")
                
        except sqlite3.Error as e:
            logger.error(f"Error limpiando eventos antiguos: {e}")
            raise
