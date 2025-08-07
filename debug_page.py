#!/usr/bin/env python3
"""
Script para debuggear la estructura de una página de evento
"""

import asyncio
import aiohttp
import ssl
from bs4 import BeautifulSoup

async def debug_event_page():
    url = "https://www.salto.gub.uy/eventos/coros-en-concierto"
    
    # Configurar SSL
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                print("=== ESTRUCTURA DE LA PÁGINA ===")
                print(f"URL: {url}")
                print()
                
                # Buscar elementos que podrían contener fechas
                print("=== ELEMENTOS CON CLASES QUE CONTIENEN 'DATE' ===")
                date_elements = soup.find_all(attrs={"class": lambda x: x and 'date' in str(x).lower()})
                for i, elem in enumerate(date_elements):
                    print(f"{i+1}. {elem.name} - class='{elem.get('class')}' - texto: '{elem.get_text(strip=True)[:100]}'")
                
                print("\n=== ELEMENTOS CON CLASES QUE CONTIENEN 'TIME' ===")
                time_elements = soup.find_all(attrs={"class": lambda x: x and 'time' in str(x).lower()})
                for i, elem in enumerate(time_elements):
                    print(f"{i+1}. {elem.name} - class='{elem.get('class')}' - texto: '{elem.get_text(strip=True)[:100]}'")
                
                print("\n=== TODOS LOS ELEMENTOS <time> ===")
                time_tags = soup.find_all('time')
                for i, elem in enumerate(time_tags):
                    print(f"{i+1}. {elem} - texto: '{elem.get_text(strip=True)}'")
                
                print("\n=== ELEMENTOS QUE CONTIENEN NÚMEROS COMO 2025, 08, AGO ===")
                all_text = soup.get_text()
                import re
                
                # Buscar patrones de fecha
                patterns = [
                    r'2025\s*\d{1,2}\s*\d{1,2}',
                    r'\d{1,2}\s*/\s*\d{1,2}\s*/\s*2025',
                    r'\d{1,2}\s+de\s+\w+\s+de\s+2025',
                    r'ago\w*\s+\d{1,2}',
                    r'\d{1,2}\s+ago\w*'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, all_text, re.IGNORECASE)
                    if matches:
                        print(f"Patrón '{pattern}': {matches}")
                
                print("\n=== ELEMENTOS .field ===")
                field_elements = soup.find_all(class_='field')
                for i, elem in enumerate(field_elements):
                    print(f"{i+1}. class='{elem.get('class')}' - texto: '{elem.get_text(strip=True)[:200]}'")
                
                print("\n=== GUARDANDO HTML PARA INSPECCIÓN ===")
                with open('debug_event.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("HTML guardado en debug_event.html")
            
            else:
                print(f"Error: {response.status}")

if __name__ == "__main__":
    asyncio.run(debug_event_page())
