"""
Publicador automático de Instagram usando la API de Meta (Facebook)
"""

import logging
import os
import json
import asyncio
from typing import Dict, Optional
import aiohttp
from pathlib import Path

logger = logging.getLogger(__name__)


class InstagramPublisher:
    """Publicador automático para Instagram usando Meta API"""
    
    def __init__(self):
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.business_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
        self.page_id = os.getenv('FACEBOOK_PAGE_ID')
        
        # URLs de la API de Meta
        self.base_url = "https://graph.facebook.com/v18.0"
        
        # Validar configuración
        if not all([self.access_token, self.business_account_id]):
            logger.warning("Instagram API no configurada. Configurar variables de entorno para habilitar publicación automática.")
    
    def is_configured(self) -> bool:
        """Verifica si la API de Instagram está configurada"""
        return bool(self.access_token and self.business_account_id)
    
    async def publish_post(self, event_data: Dict, image_path: str) -> Optional[str]:
        """
        Publica un post en Instagram
        
        Args:
            event_data: Datos del evento
            image_path: Ruta de la imagen del post
            
        Returns:
            ID del post publicado o None si falla
        """
        if not self.is_configured():
            logger.warning("Instagram API no configurada. Saltando publicación.")
            return None
        
        try:
            # Generar caption para el post
            caption = self._generate_caption(event_data)
            
            # Subir imagen y crear post
            media_id = await self._upload_media(image_path, caption)
            if not media_id:
                return None
            
            # Publicar el post
            post_id = await self._publish_media(media_id)
            
            if post_id:
                logger.info(f"Post publicado exitosamente en Instagram: {post_id}")
                return post_id
            else:
                logger.error("Error publicando post en Instagram")
                return None
                
        except Exception as e:
            logger.error(f"Error en publicación de Instagram: {e}")
            return None
    
    async def _upload_media(self, image_path: str, caption: str) -> Optional[str]:
        """Sube la imagen a Instagram y crea el container del media"""
        try:
            # Primero necesitamos subir la imagen a un servidor accesible
            # Para desarrollo, vamos a usar un método alternativo
            
            url = f"{self.base_url}/{self.business_account_id}/media"
            
            # Leer la imagen
            with open(image_path, 'rb') as img_file:
                image_data = img_file.read()
            
            # Convertir imagen a base64 para envío
            import base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            data = {
                'image_url': f"data:image/jpeg;base64,{image_b64}",  # Método alternativo
                'caption': caption,
                'access_token': self.access_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    result = await response.json()
                    
                    if response.status == 200 and 'id' in result:
                        logger.info(f"Media subido exitosamente: {result['id']}")
                        return result['id']
                    else:
                        logger.error(f"Error subiendo media: {result}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error subiendo imagen a Instagram: {e}")
            return None
    
    async def _publish_media(self, media_id: str) -> Optional[str]:
        """Publica el media container como post"""
        try:
            url = f"{self.base_url}/{self.business_account_id}/media_publish"
            
            data = {
                'creation_id': media_id,
                'access_token': self.access_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    result = await response.json()
                    
                    if response.status == 200 and 'id' in result:
                        return result['id']
                    else:
                        logger.error(f"Error publicando media: {result}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error publicando media: {e}")
            return None
    
    def _generate_caption(self, event_data: Dict) -> str:
        """Genera el caption para el post de Instagram"""
        title = event_data.get('title', 'Evento en Salto')
        description = event_data.get('description', '')
        formatted_date = event_data.get('formatted_date', '')
        
        # Limpiar descripción
        if description:
            # Limitar descripción y limpiar
            clean_desc = description[:200]
            if len(description) > 200:
                clean_desc += "..."
        else:
            clean_desc = "¡No te pierdas este evento!"
        
        # Construir caption
        caption_parts = [
            f"🎉 {title}",
            ""
        ]
        
        if formatted_date:
            caption_parts.append(f"📅 {formatted_date}")
            caption_parts.append("")
        
        caption_parts.extend([
            clean_desc,
            "",
            "#EventosSalto #Salto #Uruguay #Cultura #Eventos",
            "",
            "📍 Más información en salto.gub.uy/eventos"
        ])
        
        return "\n".join(caption_parts)
    
    async def test_connection(self) -> bool:
        """Prueba la conexión con la API de Instagram"""
        if not self.is_configured():
            return False
        
        try:
            url = f"{self.base_url}/{self.business_account_id}"
            params = {
                'fields': 'name,username',
                'access_token': self.access_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    result = await response.json()
                    
                    if response.status == 200 and 'name' in result:
                        logger.info(f"Conectado a Instagram: @{result.get('username', 'unknown')}")
                        return True
                    else:
                        logger.error(f"Error conectando a Instagram: {result}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error probando conexión con Instagram: {e}")
            return False


class InstagramPublisherSimple:
    """
    Publicador simplificado usando bibliotecas de terceros
    Alternativa más fácil de configurar
    """
    
    def __init__(self):
        self.enabled = False
        try:
            # Intentar importar instagrapi (biblioteca no oficial pero más fácil)
            global Client
            from instagrapi import Client
            
            # Intentar obtener credenciales de diferentes fuentes
            self.username = os.getenv('INSTAGRAM_USERNAME')
            self.password = os.getenv('INSTAGRAM_PASSWORD')
            
            # Si no están en variables de entorno, intentar archivo de configuración
            if not self.username or not self.password:
                try:
                    import sys
                    from pathlib import Path
                    
                    # Agregar directorio padre al path para importar config
                    parent_dir = Path(__file__).parent.parent
                    sys.path.append(str(parent_dir))
                    
                    import instagram_config
                    
                    self.username = getattr(instagram_config, 'INSTAGRAM_USERNAME', None)
                    self.password = getattr(instagram_config, 'INSTAGRAM_PASSWORD', None)
                    
                    if self.username and self.password:
                        logger.info("Credenciales cargadas desde instagram_config.py")
                    
                except (ImportError, AttributeError):
                    logger.debug("No se encontró archivo instagram_config.py")
            
            if self.username and self.password:
                self.enabled = True
                self.client = None
                logger.info("Instagram Simple Publisher configurado")
            else:
                logger.info("Instagram Simple Publisher no configurado (faltan credenciales)")
                
        except ImportError:
            logger.info("instagrapi no instalado. Instagram Simple Publisher no disponible.")
    
    def is_configured(self) -> bool:
        """Verifica si está configurado"""
        return self.enabled
    
    async def login(self) -> bool:
        """Inicia sesión en Instagram"""
        if not self.enabled:
            return False
        
        try:
            self.client = Client()
            success = self.client.login(self.username, self.password)
            
            if success:
                logger.info(f"Sesión iniciada en Instagram como @{self.username}")
                return True
            else:
                logger.error("Error iniciando sesión en Instagram")
                return False
                
        except Exception as e:
            logger.error(f"Error en login de Instagram: {e}")
            return False
    
    async def publish_post(self, event_data: Dict, image_path: str) -> Optional[str]:
        """Publica un post usando instagrapi"""
        if not self.enabled:
            return None
        
        try:
            if not self.client:
                login_success = await self.login()
                if not login_success:
                    return None
            
            # Generar caption
            caption = self._generate_caption(event_data)
            
            # Publicar imagen
            media = self.client.photo_upload(
                path=Path(image_path),
                caption=caption
            )
            
            if media:
                logger.info(f"Post publicado en Instagram: {media.pk}")
                return media.pk
            else:
                logger.error("Error publicando en Instagram")
                return None
                
        except Exception as e:
            logger.error(f"Error publicando en Instagram: {e}")
            return None
    
    def _generate_caption(self, event_data: Dict) -> str:
        """Genera caption para Instagram"""
        title = event_data.get('title', 'Evento en Salto')
        description = event_data.get('description', '')
        formatted_date = event_data.get('formatted_date', '')
        
        # Limpiar descripión
        if description:
            clean_desc = description[:150]
            if len(description) > 150:
                clean_desc += "..."
        else:
            clean_desc = "¡No te pierdas este evento!"
        
        # Construir caption
        parts = [f"🎉 {title}"]
        
        if formatted_date:
            parts.append(f"📅 {formatted_date}")
        
        parts.extend([
            "",
            clean_desc,
            "",
            "#EventosSalto #Salto #Uruguay #Cultura",
            "📍 salto.gub.uy/eventos"
        ])
        
        return "\n".join(parts)
