# Configuración de Instagram - Publicación Automática

Esta guía te ayudará a configurar la publicación automática en Instagram para el sistema de crawling de eventos.

## 🚀 Opción Recomendada: Instagram Simple

La forma más fácil de configurar la publicación automática es usando usuario y contraseña.

### 1. Instalar Dependencias

```bash
pip install instagrapi
```

### 2. Configurar Credenciales

**Opción A: Variables de Entorno (Recomendado)**

```bash
# En terminal (temporal)
export INSTAGRAM_USERNAME="tu_usuario_instagram"
export INSTAGRAM_PASSWORD="tu_contraseña_instagram"

# Para hacerlo permanente, agregar al .bashrc/.zshrc
echo 'export INSTAGRAM_USERNAME="tu_usuario_instagram"' >> ~/.zshrc
echo 'export INSTAGRAM_PASSWORD="tu_contraseña_instagram"' >> ~/.zshrc
```

**Opción B: Archivo de Configuración**

1. Copia el archivo de ejemplo:
```bash
cp instagram_config.example instagram_config.py
```

2. Edita `instagram_config.py` y configura:
```python
INSTAGRAM_USERNAME = "tu_usuario_instagram"
INSTAGRAM_PASSWORD = "tu_contraseña_instagram"
AUTO_PUBLISH_INSTAGRAM = True
```

### 3. Probar Configuración

```bash
python3 -c "
import asyncio
from src.instagram_publisher import InstagramPublisherSimple

async def test():
    publisher = InstagramPublisherSimple()
    if publisher.is_configured():
        success = await publisher.login()
        print('✅ Instagram configurado correctamente' if success else '❌ Error en configuración')
    else:
        print('❌ Instagram no configurado')

asyncio.run(test())
"
```

## 🔧 Opción Avanzada: Instagram Business API

Para uso en producción a gran escala, puedes usar la API oficial de Meta.

### Requisitos

1. **Cuenta Business de Instagram**
2. **Página de Facebook** conectada a la cuenta de Instagram
3. **App de Facebook Developer**
4. **Access Token** de larga duración

### Configuración

1. Ve a [Facebook Developers](https://developers.facebook.com/)
2. Crea una nueva app
3. Agrega el producto "Instagram Basic Display"
4. Configura los permisos necesarios
5. Obtén tu Access Token

Luego configura las variables:

```bash
export INSTAGRAM_ACCESS_TOKEN="tu_token_aqui"
export INSTAGRAM_BUSINESS_ACCOUNT_ID="tu_business_id"
export FACEBOOK_PAGE_ID="tu_page_id"
```

## 🎯 Uso del Sistema

### Ejecución Manual

```bash
# Ejecutar crawling con publicación automática
python3 main.py
```

### Ejecución Programada

```bash
# Configurar cron para ejecutar diariamente a las 9 AM
crontab -e

# Agregar línea:
0 9 * * * /usr/local/bin/python3 /ruta/completa/al/proyecto/main.py
```

### Ejecución con Scheduler

```bash
# Usar el scheduler incluido
python3 run_scheduler.py
```

## 📊 Verificar Estado

```bash
# Ver estadísticas incluyendo posts publicados
python3 manage.py stats

# Listar eventos con estado de publicación
python3 manage.py list
```

## ⚙️ Configuración Avanzada

### Limitar Publicaciones

Edita `instagram_config.py`:

```python
AUTO_PUBLISH_INSTAGRAM = True
MAX_POSTS_PER_DAY = 5           # Máximo 5 posts por día
PUBLISH_DELAY_MINUTES = 10      # Esperar 10 min entre posts
```

### Personalizar Captions

Modifica el método `_generate_caption` en `src/instagram_publisher.py` para personalizar el texto de los posts.

### Solo Generar Posts (Sin Publicar)

```python
AUTO_PUBLISH_INSTAGRAM = False
```

## 🛠️ Solución de Problemas

### Error de Login

- Verifica usuario y contraseña
- Intenta iniciar sesión manualmente en Instagram
- Desactiva temporalmente 2FA
- Usa una contraseña de aplicación si tienes 2FA

### Error de Rate Limit

- Reduce `MAX_POSTS_PER_DAY`
- Aumenta `PUBLISH_DELAY_MINUTES`
- Espera unas horas antes de intentar de nuevo

### Posts No Se Publican

- Verifica que `AUTO_PUBLISH_INSTAGRAM = True`
- Revisa los logs en `events_crawler.log`
- Prueba la conexión con el comando de test

### Cuenta Bloqueada Temporalmente

- Espera 24-48 horas
- Reduce la frecuencia de publicación
- Considera usar la API oficial para mayor confiabilidad

## 🔐 Seguridad

- **Nunca** hardcodees credenciales en el código
- Usa variables de entorno o archivos de configuración no versionados
- Considera usar tokens de aplicación en lugar de contraseñas
- Mantén las dependencias actualizadas

## 📱 Formato de Posts

Los posts generados incluyen:

- **Título del evento** con emoji
- **Fecha** (si está disponible)
- **Descripción** truncada
- **Hashtags** relevantes (#EventosSalto #Salto #Uruguay)
- **Link** al sitio oficial

Ejemplo:
```
🎉 COROS EN CONCIERTO

📅 08/08/2025

Coro del Tump (Montevideo) - Coro Departamental de Salt, Coro Byblos - Coro del CENUR y Coro Ostinato, se presentan en el Aula Magna...

#EventosSalto #Salto #Uruguay #Cultura

📍 salto.gub.uy/eventos
```
