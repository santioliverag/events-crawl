"""
Generador de posts de Instagram para eventos
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from PIL import Image, ImageDraw, ImageFont
import textwrap

logger = logging.getLogger(__name__)


class InstagramPostGenerator:
    """Generador de posts visuales para Instagram"""
    
    def __init__(self):
        self.post_size = (1080, 1080)  # Tamaño cuadrado para Instagram
        self.output_dir = Path("posts")
        self.output_dir.mkdir(exist_ok=True)
        
        # Colores del diseño (siguiendo preferencias del usuario: colores sólidos)
        self.colors = {
            'primary': '#1a5490',      # Azul institucional
            'secondary': '#2c7cb8',    # Azul claro
            'accent': '#f39c12',       # Naranja/dorado
            'text': '#2c3e50',         # Gris oscuro
            'text_light': '#ffffff',   # Blanco
            'background': '#f8f9fa',   # Gris muy claro
            'card_bg': '#ffffff'       # Blanco para tarjetas
        }
    
    async def create_post(self, event_data: Dict) -> str:
        """
        Crea un post visual para Instagram usando solo la imagen del evento
        
        Args:
            event_data: Datos del evento
            
        Returns:
            Ruta del archivo de post generado
        """
        try:
            # Verificar si existe imagen del evento
            if not event_data.get('image_path') or not Path(event_data['image_path']).exists():
                # Si no hay imagen, crear una imagen simple con fondo azul y título
                return self._create_fallback_post(event_data)
            
            # Abrir la imagen original del evento
            event_img = Image.open(event_data['image_path'])
            
            # Adaptar la imagen para Instagram (cuadrada)
            final_img = self._adapt_image_for_instagram(event_img)
            
            # Guardar imagen adaptada
            filename = self._generate_filename(event_data['title'])
            filepath = self.output_dir / filename
            
            final_img.save(filepath, 'JPEG', quality=95, optimize=True)
            
            logger.info(f"Post de Instagram generado: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generando post de Instagram: {e}")
            raise
    
    def _load_fonts(self) -> Dict:
        """
        Carga las fuentes para el diseño
        """
        fonts = {}
        
        try:
            # Intentar cargar fuentes del sistema
            fonts['title'] = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 48)
            fonts['subtitle'] = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 32)
            fonts['body'] = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 24)
            fonts['small'] = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 18)
        except:
            try:
                # Fuentes alternativas para Linux
                fonts['title'] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
                fonts['subtitle'] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
                fonts['body'] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                fonts['small'] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            except:
                # Usar fuente por defecto si no se encuentran otras
                fonts['title'] = ImageFont.load_default()
                fonts['subtitle'] = ImageFont.load_default()
                fonts['body'] = ImageFont.load_default()
                fonts['small'] = ImageFont.load_default()
        
        return fonts
    
    def _adapt_image_for_instagram(self, event_img: Image.Image) -> Image.Image:
        """
        Adapta la imagen del evento para Instagram (formato cuadrado)
        Usa fondo azul institucional si es necesario
        """
        try:
            # Convertir a RGB si es necesario
            if event_img.mode != 'RGB':
                event_img = event_img.convert('RGB')
            
            # Obtener dimensiones originales
            original_width, original_height = event_img.size
            target_size = self.post_size[0]  # 1080x1080
            
            # Si la imagen ya es cuadrada y del tamaño correcto
            if original_width == original_height == target_size:
                return event_img
            
            # Crear imagen de fondo cuadrada con color azul institucional
            final_img = Image.new('RGB', (target_size, target_size), self.colors['primary'])
            
            # Calcular el mejor ajuste manteniendo proporción
            if original_width == original_height:
                # Imagen ya cuadrada, solo redimensionar
                resized_img = event_img.resize((target_size, target_size), Image.Resampling.LANCZOS)
                return resized_img
            
            elif original_width > original_height:
                # Imagen horizontal - ajustar por altura
                new_height = target_size
                new_width = int((original_width / original_height) * new_height)
                
                if new_width > target_size:
                    # Si queda muy ancha, ajustar por ancho
                    new_width = target_size
                    new_height = int((original_height / original_width) * new_width)
                
            else:
                # Imagen vertical - ajustar por ancho
                new_width = target_size
                new_height = int((original_height / original_width) * new_width)
                
                if new_height > target_size:
                    # Si queda muy alta, ajustar por altura
                    new_height = target_size
                    new_width = int((original_width / original_height) * new_height)
            
            # Redimensionar la imagen del evento
            resized_img = event_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Centrar la imagen en el fondo azul
            x = (target_size - new_width) // 2
            y = (target_size - new_height) // 2
            
            final_img.paste(resized_img, (x, y))
            
            return final_img
            
        except Exception as e:
            logger.error(f"Error adaptando imagen: {e}")
            # Fallback: crear imagen simple con fondo azul
            return Image.new('RGB', self.post_size, self.colors['primary'])
    
    def _create_fallback_post(self, event_data: Dict) -> str:
        """
        Crea un post simple cuando no hay imagen del evento
        """
        try:
            # Crear imagen con fondo azul y título simple
            img = Image.new('RGB', self.post_size, self.colors['primary'])
            draw = ImageDraw.Draw(img)
            
            # Cargar fuente
            fonts = self._load_fonts()
            
            # Añadir título centrado
            title = event_data.get('title', 'Evento en Salto')
            title_lines = self._wrap_text(title, fonts['title'], self.post_size[0] - 100)
            
            y_offset = (self.post_size[1] - len(title_lines) * 60) // 2
            
            for line in title_lines:
                bbox = draw.textbbox((0, 0), line, font=fonts['title'])
                text_width = bbox[2] - bbox[0]
                x = (self.post_size[0] - text_width) // 2
                
                draw.text((x, y_offset), line, fill=self.colors['text_light'], font=fonts['title'])
                y_offset += 60
            
            # Guardar imagen
            filename = self._generate_filename(event_data['title'])
            filepath = self.output_dir / filename
            
            img.save(filepath, 'JPEG', quality=95, optimize=True)
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error creando post fallback: {e}")
            raise
    
    def _add_event_image(self, base_img: Image.Image, image_path: str) -> Image.Image:
        """
        Añade la imagen del evento al post
        """
        try:
            event_img = Image.open(image_path)
            
            # Redimensionar manteniendo aspecto
            event_img.thumbnail((self.post_size[0], self.post_size[1] // 2), Image.Resampling.LANCZOS)
            
            # Crear nueva imagen con la imagen del evento en la parte superior
            new_img = Image.new('RGB', self.post_size, self.colors['background'])
            
            # Centrar la imagen del evento
            x = (self.post_size[0] - event_img.width) // 2
            y = 50  # Margen superior
            
            new_img.paste(event_img, (x, y))
            
            return new_img
            
        except Exception as e:
            logger.warning(f"No se pudo cargar imagen del evento: {e}")
            return base_img
    
    def _add_info_overlay(self, img: Image.Image, event_data: Dict, fonts: Dict) -> Image.Image:
        """
        Añade la información del evento como overlay
        """
        draw = ImageDraw.Draw(img)
        
        # Posición inicial para el texto
        y_offset = img.height // 2 + 50
        margin = 40
        content_width = img.width - (margin * 2)
        
        # Crear área de contenido con fondo semi-transparente
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Fondo para el área de texto
        text_bg_y = y_offset - 30
        text_bg_height = img.height - text_bg_y - 100
        
        overlay_draw.rectangle(
            [margin - 20, text_bg_y, img.width - margin + 20, text_bg_y + text_bg_height],
            fill=(*self._hex_to_rgb(self.colors['card_bg']), 240)
        )
        
        # Combinar con la imagen base
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # Título del evento
        title = event_data.get('title', 'Evento')
        title_lines = self._wrap_text(title, fonts['title'], content_width)
        
        for line in title_lines:
            draw.text((margin, y_offset), line, fill=self.colors['primary'], font=fonts['title'])
            y_offset += 55
        
        y_offset += 20
        
        # Fecha del evento
        if event_data.get('formatted_date'):
            date_text = f"📅 {event_data['formatted_date']}"
            draw.text((margin, y_offset), date_text, fill=self.colors['accent'], font=fonts['subtitle'])
            y_offset += 45
        
        y_offset += 10
        
        # Descripción del evento
        description = event_data.get('description', '')
        if description:
            # Limpiar y truncar descripción
            clean_desc = self._clean_description(description)
            desc_lines = self._wrap_text(clean_desc, fonts['body'], content_width, max_lines=6)
            
            for line in desc_lines:
                draw.text((margin, y_offset), line, fill=self.colors['text'], font=fonts['body'])
                y_offset += 30
        
        return img
    
    def _add_branding(self, img: Image.Image, fonts: Dict) -> Image.Image:
        """
        Añade branding al post
        """
        draw = ImageDraw.Draw(img)
        
        # Línea decorativa superior
        draw.rectangle([0, 0, img.width, 10], fill=self.colors['primary'])
        
        # Footer con información de la fuente
        footer_y = img.height - 60
        footer_text = "Eventos Salto • salto.gub.uy"
        
        # Fondo para el footer
        draw.rectangle([0, footer_y - 10, img.width, img.height], fill=self.colors['primary'])
        
        # Texto del footer centrado
        bbox = draw.textbbox((0, 0), footer_text, font=fonts['small'])
        text_width = bbox[2] - bbox[0]
        x = (img.width - text_width) // 2
        
        draw.text((x, footer_y), footer_text, fill=self.colors['text_light'], font=fonts['small'])
        
        # Añadir icono o decoración (usando emojis simples)
        moon_icon = "🌙"  # Usando preferencia del usuario por el icono de media luna
        draw.text((20, footer_y), moon_icon, font=fonts['small'])
        
        return img
    
    def _wrap_text(self, text: str, font, max_width: int, max_lines: int = None) -> list:
        """
        Divide el texto en líneas que caben en el ancho especificado
        """
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            
            # Obtener el ancho del texto
            bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Palabra muy larga, dividirla
                    lines.append(word)
                    current_line = ""
            
            # Limitar número de líneas si se especifica
            if max_lines and len(lines) >= max_lines:
                if current_line:
                    lines.append(current_line + "...")
                break
        
        if current_line and (not max_lines or len(lines) < max_lines):
            lines.append(current_line)
        
        return lines
    
    def _clean_description(self, description: str, max_length: int = 300) -> str:
        """
        Limpia y trunca la descripción del evento
        """
        # Eliminar caracteres especiales y espacios extra
        clean = re.sub(r'\s+', ' ', description.strip())
        
        # Truncar si es muy largo
        if len(clean) > max_length:
            clean = clean[:max_length].rsplit(' ', 1)[0] + "..."
        
        return clean
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """
        Convierte color hexadecimal a RGB
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _generate_filename(self, title: str) -> str:
        """
        Genera un nombre de archivo seguro basado en el título
        """
        # Limpiar título para nombre de archivo
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        safe_title = safe_title[:50]  # Limitar longitud
        
        # Añadir timestamp para unicidad
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"evento_{safe_title}_{timestamp}.jpg"
