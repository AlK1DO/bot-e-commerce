# Eagle Gaming Perú — Chatbot Inteligente ("Eli")

Sistema de atención automatizada y recomendación personalizada de productos tecnológicos para la tienda de comercio electrónico **Eagle Gaming Perú**, desarrollado con **Python 3.12, FastAPI, Google Gemini API y Google Cloud Firestore**.

---

## 🎯 Alineación con los Objetivos de la Tesis

| Objetivo de la Tesis | Implementación en el Backend |
|---|---|
| **Obj. 1: Tiempos y orientación** | Medición automática de `response_time_ms` por cada turno conversacional. Registro histórico en Firestore. |
| **Obj. 2: Arquitectura y flujos** | Clasificación híbrida de intenciones (Reglas deterministas locales + LLM Gemini en fallback), soporte comercial de envíos/pagos/garantías, comparativa de productos y derivación a asesor humano por WhatsApp (`986 638 034`). |
| **Obj. 3: Recomendación personalizada** | Búsqueda y filtrado en catálogo real por presupuesto (`S/ 2500`, rangos `entre 2000 y 3500`), categoría (Laptops, PCs armadas, componentes), resolución de pronombres contextuales ("¿y ese tiene garantía?") y enlace directo a **"Arma tu PC"** (`/arma-tu-pc`). |
| **Obj. 4: Indicadores de evaluación** | Endpoint `/api/analytics/summary` con los 3 indicadores clave: **Tiempo de respuesta**, **Tasa de resolución** y **Satisfacción de usuarios (CSAT)** mediante `/api/chat/feedback`. Exportación a CSV para análisis estadístico en Excel/SPSS. |

---

## 🚀 Inicio Rápido (Backend)

### 1. Requisitos
- Python 3.12+
- Credenciales de Firebase en `Backend/credentials/firebase-service-account.json`
- Archivo `.env` configurado dentro de `Backend/` (ver `Backend/.env.example`)

### 2. Instalación de dependencias
```powershell
cd Backend
pip install -r requirements.txt
```

### 3. Ejecutar el servidor
```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
- API Base: `http://localhost:8000`
- Documentación interactiva (Swagger UI): `http://localhost:8000/docs` *(activa solo en `APP_ENV=development`)*

### 4. Ejecutar la suite completa de pruebas unitarias
```powershell
.\venv\Scripts\python.exe -m unittest discover -s test -v
```
*(40 pruebas unitarias automatizadas cubren contratos de API, intents, filtros de catálogo, seguridad, rate limiting y persistencia).*

---

## 📡 Contrato de Endpoints de la API

### 1. Chatbot (`/api/chat`)

#### `POST /api/chat`
Procesa un mensaje del usuario. Rate limit: **20 req/min por IP**.
- **Request Body:**
  ```json
  {
    "message": "Recomiéndame una laptop gamer por 3500 soles",
    "session_id": "sesion-uuid-1234",
    "user_id": "usr-5678"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "message": "¡Aquí tienes excelentes opciones dentro de tu presupuesto! ...",
    "intent": "recomendacion",
    "resolved": true,
    "products": [
      {
        "id": "prod-1",
        "name": "Laptop Lenovo Legion 5",
        "summary": "Ryzen 7 · 16GB RAM · RTX 4060",
        "price": 3499.0,
        "stock": 5,
        "product_url": "https://eaglegaming.pe/producto/lenovo-legion-5"
      }
    ],
    "quick_replies": ["¿Cómo se paga?", "¿Tienen garantía?", "Ver PCs armadas"],
    "response_time_ms": 284.5
  }
  ```

#### `GET /api/chat/history/{session_id}?limit=50`
Recupera el historial previo de mensajes para restaurar la conversación cuando el usuario vuelve o inicia sesión. Rate limit: **10 req/min**.

#### `POST /api/chat/feedback`
Registra la calificación de satisfacción del cliente (1 a 5 estrellas). Permite evaluar el **Objetivo 4** de la tesis.
- **Request Body:**
  ```json
  {
    "session_id": "sesion-uuid-1234",
    "rating": 5,
    "comment": "Muy rápida y acertada la recomendación",
    "user_id": "usr-5678"
  }
  ```

---

### 2. Catálogo de Productos (`/api/products`)

- **`GET /api/products`**: Búsqueda con filtros (`categoria`, `marca`, `precio_min`, `precio_max`, `solo_stock`, `texto`). Rate limit: **60 req/min**.
- **`GET /api/products/{id}`**: Detalle de un producto individual por ID.

---

### 3. Administración y Métricas de Tesis (`/api/analytics`)
*(Protegidos mediante header `X-Api-Key` o parámetro `?api_key=dev-only`)*

#### `GET /api/analytics/summary`
Retorna el consolidado de métricas evaluativas:
```json
{
  "total_messages": 128,
  "resolved_count": 115,
  "resolution_rate_pct": 89.8,
  "avg_response_time_ms": 312.4,
  "min_response_time_ms": 45.2,
  "max_response_time_ms": 820.1,
  "top_intents": [
    {"intent": "precio", "count": 42},
    {"intent": "recomendacion", "count": 31},
    {"intent": "disponibilidad", "count": 25}
  ],
  "satisfaction": {
    "total_ratings": 38,
    "avg_rating_stars": 4.76,
    "satisfaction_rate_pct": 94.7,
    "stars_breakdown": {"1": 0, "2": 1, "3": 1, "4": 8, "5": 28}
  }
}
```

#### `GET /api/analytics/export?api_key=dev-only`
Descarga directa del archivo **`metricas_chatbot_eagle_gaming.csv`** con cada turno conversacional registrado, tiempos, intents, y calificaciones para procesar en SPSS o Excel.

#### `DELETE /api/analytics/cleanup?days=30&api_key=dev-only`
Purga sesiones con más de N días de antigüedad para mantener el almacenamiento de Firestore dentro de los límites gratuitos.

---

## 🛡️ Seguridad Implementada

1. **Security Headers Middleware:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Server: EagleGaming-API`.
2. **Anti-XSS:** Sanitización estricta de tags HTML (`<script>`, `<iframe>`, `<img>`) en mensajes y comentarios.
3. **Rate Limiting:** Control de tráfico por IP con `slowapi` en todos los endpoints públicos.
4. **Anti-Prompt-Injection:** Pre-filtro determinista por patrones maliciosos y cláusulas de instrucción no confiable en el prompt del sistema.
5. **Aislamiento de Errores:** Manejador global 500 para evitar fugas de stack traces o rutas locales del sistema operativo.
6. **Ocultamiento de Swagger en Producción:** `/docs` se desactiva cuando `APP_ENV=production`.
