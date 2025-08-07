"""
Web scraper para extraer eventos de salto.gub.uy
"""

import asyncio
import logging
import re
import ssl
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
import aiofiles

logger = logging.getLogger(__name__)


class EventScraper:
    """Scraper para eventos de la página de Salto"""
    
    def __init__(self):
        self.base_url = "https://www.salto.gub.uy"
        self.events_url = "https://www.salto.gub.uy/eventos"
        self.session = None
        
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
    
    async def scrape_events(self) -> List[Dict]:
        """
        Extrae todos los eventos de la página principal
        """
        events = []
        
        # Configurar SSL context para evitar problemas de certificados
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            self.session = session
            
            try:
                # Headers para parecer un navegador real
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                # Obtener página principal de eventos
                async with session.get(self.events_url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Error al acceder a {self.events_url}: {response.status}")
                        return events
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Buscar enlaces a páginas individuales de eventos
                    event_links = []
                    
                    # Buscar todos los artículos de eventos y extraer sus enlaces
                    articles = soup.find_all('article') or soup.find_all('div', class_=lambda x: x and 'evento' in str(x).lower())
                    
                    for article in articles:
                        # Buscar enlace dentro del artículo
                        link_elem = article.find('a', href=True)
                        if link_elem:
                            href = link_elem.get('href')
                            if href and not href.startswith('http'):
                                href = urljoin(self.base_url, href)
                            if href and href not in event_links:
                                event_links.append(href)
                    
                    # Si no encontramos enlaces en artículos, buscar todos los enlaces de la página
                    if not event_links:
                        all_links = soup.find_all('a', href=True)
                        for link in all_links:
                            href = link.get('href')
                            if href and ('evento' in href.lower() or '/node/' in href):
                                full_url = urljoin(self.base_url, href)
                                if full_url not in event_links and full_url != self.events_url:
                                    event_links.append(full_url)
                    
                    logger.info(f"Encontrados {len(event_links)} enlaces de eventos")
                    
                    # Procesar cada enlace de evento individualmente
                    for event_url in event_links:
                        try:
                            event_data = await self._scrape_individual_event(event_url, headers)
                            if event_data:
                                events.append(event_data)
                        except Exception as e:
                            logger.error(f"Error extrayendo evento de {event_url}: {e}")
                            continue
                            
            except Exception as e:
                logger.error(f"Error en scraping de eventos: {e}")
        
        return events
    
    async def _scrape_individual_event(self, event_url: str, headers: Dict) -> Optional[Dict]:
        """
        Extrae información de una página individual de evento usando selectores CSS específicos
        """
        try:
            logger.info(f"Extrayendo evento de: {event_url}")
            
            async with self.session.get(event_url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Error al acceder a {event_url}: {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                event_data = {}
                
                # Extraer título: .page-content > .title span
                title_elem = soup.select_one('.page-content > .title span')
                if not title_elem:
                    # Alternativas si no se encuentra el selector específico
                    title_elem = soup.select_one('.page-content .title span') or \
                                soup.select_one('.title span') or \
                                soup.select_one('h1') or \
                                soup.select_one('.page-title')
                
                if title_elem:
                    event_data['title'] = title_elem.get_text(strip=True)
                else:
                    logger.warning(f"No se encontró título en {event_url}")
                    return None
                
                # Extraer fecha: buscar primero en el contenido del evento
                date_found = False
                
                # 1. Buscar en el body del evento (donde está la descripción)
                # Tomar solo el PRIMER campo body (contiene la descripción real)
                body_elems = soup.select('.field--name-body')
                if body_elems:
                    body_elem = body_elems[0]  # Solo el primer elemento
                    body_text = body_elem.get_text(strip=True)
                    logger.debug(f"Buscando fecha en body: '{body_text[:200]}...'")
                    date_info = self._parse_date_from_text(body_text)
                    if date_info:
                        event_data.update(date_info)
                        date_found = True
                        logger.info(f"Fecha encontrada en body: {date_info['formatted_date']}")
                
                # 2. Si no se encontró, buscar en header > div (tu selector original)
                if not date_found:
                    date_elem = soup.select_one('header > div')
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        logger.debug(f"Fecha encontrada en header: '{date_text[:100]}...'")
                        date_info = self._parse_date_from_text(date_text)
                        if date_info:
                            event_data.update(date_info)
                            date_found = True
                
                # 3. Buscar en otros selectores alternativos
                if not date_found:
                    alternative_selectors = [
                        'header div',
                        '.date',
                        '.fecha',
                        '.event-date',
                        '.field-name-field-date',
                        '.field-type-datetime',
                        'time',
                        '.datetime'
                    ]
                    
                    for selector in alternative_selectors:
                        alt_elem = soup.select_one(selector)
                        if alt_elem:
                            date_text = alt_elem.get_text(strip=True)
                            logger.debug(f"Intentando selector '{selector}': '{date_text[:100]}...'")
                            date_info = self._parse_date_from_text(date_text)
                            if date_info:
                                event_data.update(date_info)
                                date_found = True
                                break
                
                # 4. Como último recurso, buscar en todo el contenido de la página
                if not date_found:
                    all_text = soup.get_text()
                    logger.debug(f"Buscando fecha en todo el contenido de la página")
                    date_info = self._parse_date_from_text(all_text)
                    if date_info:
                        event_data.update(date_info)
                        date_found = True
                
                if not date_found:
                    logger.warning(f"No se pudo encontrar fecha en {event_url}")
                
                # Extraer imagen: .field > img
                img_elem = soup.select_one('.field > img')
                if img_elem:
                    img_src = img_elem.get('src') or img_elem.get('data-src')
                    if img_src:
                        # Convertir URL relativa a absoluta
                        event_data['image_url'] = urljoin(self.base_url, img_src)
                        
                        # Descargar imagen
                        image_path = await self._download_image(event_data['image_url'], event_data['title'])
                        if image_path:
                            event_data['image_path'] = image_path
                else:
                    logger.info(f"No se encontró imagen en .field para {event_url}")
                
                # Extraer descripción del PRIMER campo body (no del de contacto)
                body_elems = soup.select('.field--name-body')
                if body_elems and len(body_elems) > 0:
                    # Usar solo el primer campo body (contiene la descripción real del evento)
                    first_body = body_elems[0]
                    raw_description = first_body.get_text(strip=True)
                    event_data['description'] = self._clean_description(raw_description)
                else:
                    # Fallback: buscar en otros selectores
                    desc_elem = soup.select_one('.field > p > span') or \
                               soup.select_one('.field p span') or \
                               soup.select_one('.field p') or \
                               soup.select_one('.content p')
                    
                    if desc_elem:
                        raw_description = desc_elem.get_text(strip=True)
                        event_data['description'] = self._clean_description(raw_description)
                    else:
                        # Último recurso
                        event_data['description'] = "¡No te pierdas este evento en Salto!"
                
                # Agregar URL del evento
                event_data['link'] = event_url
                
                # Agregar fecha de scraping
                event_data['scraped_at'] = datetime.now()
                
                logger.info(f"Evento extraído exitosamente: {event_data.get('title', 'Sin título')}")
                return event_data
                
        except Exception as e:
            logger.error(f"Error extrayendo evento individual de {event_url}: {e}")
            return None
    
    def _parse_date_from_text(self, date_text: str) -> Optional[Dict]:
        """
        Extrae información de fecha de un texto
        """
        date_info = {}
        
        try:
            # Buscar fechas en texto libre con más patrones
            date_patterns = [
                r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',  # 6 de agosto de 2025
                r'(\d{1,2})/(\d{1,2})/(\d{4})',            # 06/08/2025
                r'(\d{1,2})-(\d{1,2})-(\d{4})',            # 06-08-2025
                r'(\d{4})\s*(\d{1,2})\s*(\d{1,2})',        # 2025 08 06
                r'(\d{4})-(\d{1,2})-(\d{1,2})',            # 2025-08-06
                r'(\d{1,2})\s+(\w+)\s+(\d{4})',            # 6 agosto 2025
                r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',          # agosto 6, 2025
                r'(\d{1,2})\.(\d{1,2})\.(\d{4})',          # 06.08.2025
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_text)
                if match:
                    try:
                        groups = match.groups()
                        
                        if 'de' in pattern:  # X de mes de año
                            day, month_text, year = groups
                            month = self._parse_month(month_text)
                            if month:
                                event_date = datetime(int(year), month, int(day))
                        elif pattern.startswith(r'(\d{4})'):  # Año primero
                            if len(groups) == 3:
                                year, month, day = groups
                                event_date = datetime(int(year), int(month), int(day))
                        elif pattern.startswith(r'(\w+)'):  # Mes primero (texto)
                            month_text, day, year = groups
                            month = self._parse_month(month_text)
                            if month:
                                event_date = datetime(int(year), month, int(day))
                        elif r'\s+(\w+)\s+' in pattern:  # X mes año
                            day, month_text, year = groups
                            month = self._parse_month(month_text)
                            if month:
                                event_date = datetime(int(year), month, int(day))
                        else:  # Formato día/mes/año o día-mes-año
                            day, month, year = groups
                            event_date = datetime(int(year), int(month), int(day))
                        
                        date_info['event_date'] = event_date
                        date_info['formatted_date'] = event_date.strftime('%d/%m/%Y')
                        logger.debug(f"Fecha parseada exitosamente: {event_date}")
                        break
                        
                    except ValueError as ve:
                        logger.debug(f"Error parseando fecha {match.groups()}: {ve}")
                        continue
            
            # Si no se encontró fecha estructurada, buscar números que podrían ser fecha
            if not date_info:
                numbers = re.findall(r'\d+', date_text)
                if len(numbers) >= 3:
                    try:
                        # Intentar diferentes interpretaciones
                        if len(numbers[0]) == 4:  # Año primero
                            year, month, day = int(numbers[0]), int(numbers[1]), int(numbers[2])
                        else:  # Día primero
                            day, month, year = int(numbers[0]), int(numbers[1]), int(numbers[2])
                            if year < 100:  # Año de 2 dígitos
                                year += 2000
                        
                        event_date = datetime(year, month, day)
                        date_info['event_date'] = event_date
                        date_info['formatted_date'] = event_date.strftime('%d/%m/%Y')
                    except ValueError:
                        pass
            
        except Exception as e:
            logger.debug(f"Error parseando fecha de texto '{date_text}': {e}")
        
        return date_info if date_info else None
    
    def _clean_description(self, description: str) -> str:
        """
        Limpia la descripción del evento removiendo información no deseada
        """
        if not description:
            return ""
        
        # Lista de frases/texto a filtrar
        unwanted_phrases = [
            'Dirección:',
            'Teléfono:',
            'E-mail:',
            'Horario de atención:',
            'Juan Carlos Gómez 32',
            '(+598) 473 2 98 98',
            'info@salto.gub.uy',
            'Lunes a viernes de 8:30 a 15:00 horas',
            'Sitio oficial de la',
            'Intendencia de Salto',
            'Los sitios oficiales tienen dominio salto.gub.uy',
            'Los sitios salto.gub.uy son seguros',
            'Un sitio web con extensión salto.gub.uy',
            'Comparta información confidencial sólo en sitios web oficiales',
        ]
        
        # Limpiar texto
        cleaned = description
        
        # Remover frases no deseadas
        for phrase in unwanted_phrases:
            cleaned = cleaned.replace(phrase, '').strip()
        
        # Limpiar espacios extra y caracteres especiales
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remover líneas que contengan información de contacto específica
        lines = cleaned.split('.')
        filtered_lines = []
        
        for line in lines:
            line = line.strip()
            # Mantener líneas que no sean información de contacto
            if (line and 
                len(line) > 15 and  # Líneas con contenido sustantivo
                not line.startswith('4732') and
                not line.startswith('473') and
                not '@' in line and
                'gub.uy' not in line.lower() and
                'juan carlos gómez' not in line.lower() and
                not re.match(r'^\d+[\s\-\(\)]*\d+', line)):  # No empezar con números de teléfono
                filtered_lines.append(line)
        
        # Unir líneas filtradas
        if filtered_lines:
            cleaned = '. '.join(filtered_lines)
            # Asegurar que termine con punto si no lo tiene
            if not cleaned.endswith('.'):
                cleaned += '.'
        
        # Limpiar espacios extra nuevamente
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Si quedó muy poco texto, usar texto alternativo
        if len(cleaned) < 30:
            return "¡No te pierdas este evento en Salto!"
        
        return cleaned
    
    async def _extract_event_from_article(self, article) -> Optional[Dict]:
        """
        Extrae información de un artículo de evento
        """
        try:
            event_data = {}
            
            # Extraer título
            title_elem = article.find('h2') or article.find('h3') or article.find('h1') or \
                        article.find(class_=lambda x: x and 'title' in x.lower())
            
            if title_elem:
                event_data['title'] = title_elem.get_text(strip=True)
            else:
                logger.warning("No se encontró título en el artículo")
                return None
            
            # Extraer fecha del header o estructura de fecha
            date_info = self._extract_date_from_article(article)
            if date_info:
                event_data.update(date_info)
            
            # Extraer imagen
            img_elem = article.find('img')
            if img_elem:
                img_src = img_elem.get('src') or img_elem.get('data-src')
                if img_src:
                    # Convertir URL relativa a absoluta
                    event_data['image_url'] = urljoin(self.base_url, img_src)
                    
                    # Descargar imagen
                    image_path = await self._download_image(event_data['image_url'], event_data['title'])
                    if image_path:
                        event_data['image_path'] = image_path
            
            # Extraer descripción
            desc_elem = article.find('p') or \
                       article.find(class_=lambda x: x and any(keyword in x.lower() for keyword in ['desc', 'content', 'texto']))
            
            if desc_elem:
                event_data['description'] = desc_elem.get_text(strip=True)
            else:
                # Si no hay descripción específica, usar todo el texto del artículo
                event_data['description'] = article.get_text(strip=True)
            
            # Extraer enlace si existe
            link_elem = article.find('a')
            if link_elem and link_elem.get('href'):
                event_data['link'] = urljoin(self.base_url, link_elem.get('href'))
            
            # Agregar fecha de scraping
            event_data['scraped_at'] = datetime.now()
            
            logger.info(f"Evento extraído: {event_data['title']}")
            return event_data
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del artículo: {e}")
            return None
    
    def _extract_date_from_article(self, article) -> Optional[Dict]:
        """
        Extrae información de fecha del artículo
        """
        date_info = {}
        
        try:
            # Buscar elementos de fecha en el header o estructura específica
            date_container = article.find(class_=lambda x: x and 'date' in x.lower()) or \
                           article.find(class_=lambda x: x and 'fecha' in x.lower())
            
            if not date_container:
                # Buscar por estructura de números grandes (día/mes/año)
                date_numbers = article.find_all(['span', 'div'], 
                                              text=re.compile(r'^\d{1,2}$|^\d{4}$'))
                
                if len(date_numbers) >= 3:
                    # Asumir formato día, mes, año
                    try:
                        day = int(date_numbers[0].get_text(strip=True))
                        month_text = date_numbers[1].get_text(strip=True)
                        year = int(date_numbers[2].get_text(strip=True))
                        
                        # Convertir mes de texto a número
                        month = self._parse_month(month_text)
                        
                        if month:
                            event_date = datetime(year, month, day)
                            date_info['event_date'] = event_date
                            date_info['formatted_date'] = event_date.strftime('%d/%m/%Y')
                    except (ValueError, IndexError):
                        pass
            
            # Buscar fechas en texto libre
            if not date_info:
                text = article.get_text()
                date_patterns = [
                    r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
                    r'(\d{1,2})/(\d{1,2})/(\d{4})',
                    r'(\d{1,2})-(\d{1,2})-(\d{4})',
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, text)
                    if match:
                        try:
                            if 'de' in pattern:
                                day, month_text, year = match.groups()
                                month = self._parse_month(month_text)
                                if month:
                                    event_date = datetime(int(year), month, int(day))
                            else:
                                day, month, year = match.groups()
                                event_date = datetime(int(year), int(month), int(day))
                            
                            date_info['event_date'] = event_date
                            date_info['formatted_date'] = event_date.strftime('%d/%m/%Y')
                            break
                        except ValueError:
                            continue
            
        except Exception as e:
            logger.error(f"Error extrayendo fecha: {e}")
        
        return date_info if date_info else None
    
    def _parse_month(self, month_text: str) -> Optional[int]:
        """
        Convierte nombre de mes en español a número
        """
        months = {
            'enero': 1, 'ene': 1,
            'febrero': 2, 'feb': 2,
            'marzo': 3, 'mar': 3,
            'abril': 4, 'abr': 4,
            'mayo': 5, 'may': 5,
            'junio': 6, 'jun': 6,
            'julio': 7, 'jul': 7,
            'agosto': 8, 'ago': 8,
            'septiembre': 9, 'sep': 9,
            'octubre': 10, 'oct': 10,
            'noviembre': 11, 'nov': 11,
            'diciembre': 12, 'dic': 12
        }
        
        month_lower = month_text.lower().strip()
        return months.get(month_lower)
    
    async def _download_image(self, image_url: str, event_title: str) -> Optional[str]:
        """
        Descarga imagen del evento
        """
        try:
            # Crear nombre de archivo seguro
            safe_title = re.sub(r'[^\w\s-]', '', event_title)
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            
            # Obtener extensión de la URL
            parsed_url = urlparse(image_url)
            extension = parsed_url.path.split('.')[-1] if '.' in parsed_url.path else 'jpg'
            
            filename = f"images/{safe_title[:50]}.{extension}"
            
            # Configurar headers para parecer un navegador
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            async with self.session.get(image_url, headers=headers) as response:
                if response.status == 200:
                    async with aiofiles.open(filename, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    logger.info(f"Imagen descargada: {filename}")
                    return filename
                else:
                    logger.warning(f"Error descargando imagen {image_url}: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error descargando imagen {image_url}: {e}")
        
        return None
