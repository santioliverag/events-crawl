# Sistema de Crawling de Eventos - Salto

Sistema automatizado para extraer eventos de la página oficial de la Intendencia de Salto (salto.gub.uy) y generar posts visuales para Instagram.

## Características

- 🕸️ **Web Scraping Asincrónico**: Extrae eventos de salto.gub.uy/eventos
- 🗄️ **Base de Datos SQLite**: Almacena eventos y evita duplicados
- 🎨 **Generación de Posts**: Crea imágenes optimizadas para Instagram
- 📱 **Publicación Automática**: Publica directamente en Instagram
- 🤖 **Automatización Completa**: Desde extracción hasta publicación
- 🌙 **Branding Personalizado**: Incluye iconografía y branding de Salto

## Instalación

1. **Clonar o descargar el proyecto**
   ```bash
   cd events-crawl
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar Instagram (Opcional)**
   ```bash
   # Para publicación automática en Instagram
   export INSTAGRAM_USERNAME="tu_usuario_instagram"
   export INSTAGRAM_PASSWORD="tu_contraseña_instagram"
   
   # Instalar dependencia de Instagram
   pip install instagrapi
   ```
   
   📖 **Ver guía completa**: [INSTAGRAM_SETUP.md](INSTAGRAM_SETUP.md)

4. **Ejecutar el sistema**
   ```bash
   python main.py
   ```

## Estructura del Proyecto

```
events-crawl/
├── main.py                 # Script principal
├── src/
│   ├── __init__.py
│   ├── scraper.py          # Web scraper para eventos
│   ├── database.py         # Gestor de base de datos
│   └── instagram_generator.py  # Generador de posts
├── images/                 # Imágenes descargadas de eventos
├── posts/                  # Posts de Instagram generados
├── requirements.txt        # Dependencias
├── events.db              # Base de datos SQLite (se crea automáticamente)
└── events_crawler.log     # Log del sistema
```

## Funcionalidades

### Web Scraping
- Extrae título, fecha, descripción e imagen de cada evento
- Maneja fechas en español automáticamente
- Descarga imágenes de forma asincrónica
- Evita duplicados verificando la base de datos

### Base de Datos
- Almacena todos los eventos extraídos
- Registra el estado de procesamiento
- Incluye logs de todas las acciones
- Estadísticas de eventos procesados

### Generación de Posts
- Crea imágenes cuadradas (1080x1080) para Instagram
- Diseño moderno y minimalista
- Combina imagen del evento con información textual
- Branding personalizado con colores institucionales

## Configuración

### Colores del Diseño
El sistema utiliza una paleta de colores sólidos (sin degradados):
- **Azul Principal**: #1a5490 (institucional)
- **Azul Secundario**: #2c7cb8
- **Acento**: #f39c12 (naranja/dorado)
- **Texto**: #2c3e50
- **Fondo**: #f8f9fa

### Personalización
Puedes modificar los colores y el diseño editando el archivo `src/instagram_generator.py`:

```python
self.colors = {
    'primary': '#1a5490',      # Cambiar color principal
    'secondary': '#2c7cb8',    # Cambiar color secundario
    'accent': '#f39c12',       # Cambiar color de acento
    # ... más colores
}
```

## Uso Automático

Para ejecutar el sistema de forma programada, usa el script `run_scheduler.py`:

```bash
# Ver ejemplos de configuración para cron
python3 run_scheduler.py --show-cron

# Ejecutar manualmente el scheduler
python3 run_scheduler.py
```

### Cron (Linux/Mac)
```bash
# Ejecutar cada día a las 9:00 AM
0 9 * * * /usr/local/bin/python3 /ruta/al/proyecto/run_scheduler.py

# Cada 6 horas
0 */6 * * * /usr/local/bin/python3 /ruta/al/proyecto/run_scheduler.py
```

### Scripts Disponibles

- **`main.py`**: Script principal del sistema
- **`manage.py`**: Herramientas de gestión y testing
  - `python3 manage.py stats` - Ver estadísticas
  - `python3 manage.py list` - Listar eventos
  - `python3 manage.py test-scraper` - Probar scraper
  - `python3 manage.py test-generator` - Probar generador
  - `python3 manage.py cleanup` - Limpiar datos antiguos
- **`run_scheduler.py`**: Script para ejecución programada

### Logs

El sistema genera logs detallados en:
- **Archivo**: `events_crawler.log`
- **Consola**: Información en tiempo real

## Dependencias Principales

- **aiohttp**: Cliente HTTP asincrónico para web scraping
- **beautifulsoup4**: Parser HTML para extraer datos
- **Pillow**: Procesamiento y generación de imágenes
- **aiofiles**: Operaciones de archivos asincrónicas

## Estadísticas

El sistema proporciona estadísticas sobre:
- Total de eventos procesados
- Posts generados
- Eventos pendientes
- Historial de procesamiento

## Solución de Problemas

### Error al cargar fuentes
Si hay problemas con las fuentes, el sistema usa fuentes por defecto. Para mejores resultados, asegúrate de tener fuentes del sistema disponibles.

### Errores de conexión
El sistema reintenta automáticamente las conexiones fallidas y registra los errores en el log.

### Imágenes no se descargan
Verifica la conectividad a internet y que las URLs de las imágenes sean accesibles.

## Contribución

Para mejorar el sistema:
1. Modifica los archivos en `src/`
2. Ejecuta pruebas con `pytest`
3. Verifica los logs para asegurar funcionamiento correcto

## Licencia

Este proyecto está diseñado para uso con eventos públicos de la Intendencia de Salto.
