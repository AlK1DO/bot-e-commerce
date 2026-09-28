# Eagle Gaming Perú — Backend

## Página de pruebas

Con el servidor iniciado, abre http://127.0.0.1:8000/preview/.
El frontend pequeño está en `preview/` y utiliza `/api/chat` en el mismo servidor.
No requiere npm ni dependencias adicionales. Incluye el logo proporcionado,
productos, estado de la consulta y manejo de errores. Cada envío puede consumir
una llamada a Gemini; los botones de ejemplo solo rellenan el mensaje.
La página no añade memoria conversacional ni confirma que haya respondido la IA:
el backend puede utilizar sus reglas locales si el proveedor falla.

Python 3.12.10, FastAPI y Firestore. Ejecutar desde `Backend` con el entorno
virtual y la configuración de Firebase disponibles:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## Chat y catálogo

`POST /api/chat` recibe `message` y un `session_id` opcional. Por ejemplo:

```json
{"message": "¿Cuánto cuesta la laptop Lenovo?"}
```

El chat clasifica una intención principal por reglas locales y consulta
`productos` mediante ProductService. Precios, disponibilidad, características
y garantías se redactan directamente a partir del catálogo, sin un modelo de IA.
Se muestran como máximo cinco productos y se solicita precisar la búsqueda si
hay más coincidencias. Un campo ausente no se interpreta como cero ni como
disponibilidad confirmada.

En `products`, `price` y `stock` pueden ser `null`. El frontend debe representar
ese valor como información no disponible. `resolved` es false cuando falta la
información solicitada, no hay resultados o se requiere precisar la consulta.
Las URLs se toman del campo `url`; no se infieren imágenes desde `url1/2/3`.

La búsqueda admite consultas técnicas simples. Aún no resuelve referencias como
“ese producto”, no guarda historial ni usa `session_id` para mantener contexto.
La extracción por reglas no equivale a comprensión general del lenguaje.
Recomendaciones y métricas continúan pendientes.

## Información comercial

Las respuestas de envíos, recojo, horarios, ubicaciones, pagos y datos de
entrega se mantienen separadas del catálogo en
`app/domain/commercial_information.py`. Esta es una base de conocimiento
controlada: no usa Gemini ni Firestore y por ello no inventa condiciones.
Los datos operativos internos de embalaje no se presentan al cliente.

Antes de publicar una política de pagos o una dirección exacta, completa los
datos marcados como pendientes en ese archivo. Los datos personales se solicitan
solamente en un checkout autenticado; el chat no debe recibir DNI.

## Gemini (fase 8)

Agregar en `.env` (no subir claves al repositorio):

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=tu_clave
GEMINI_MODEL=id_del_modelo_de_tu_cuenta
GEMINI_TIMEOUT_SECONDS=8
```

Seleccionar un modelo compatible con generateContent y salida JSON en Google
AI Studio. Reiniciar la API después de cambiar estas variables. `AI_PROVIDER=none`
desactiva las llamadas a IA. Si falta configuración o falla el proveedor, se usan
reglas locales y se registra un aviso sin claves ni mensajes del cliente.

`LLMService` es el único punto de acceso del chat a la IA. `GeminiProvider` usa
la API REST con `httpx`, ya incluido en requirements.txt, y un timeout de 20 s.
Las consultas comerciales, saludos y búsquedas simples se resuelven sin llamar
a Gemini. Gemini recibe los mensajes ambiguos o recomendaciones para extraer intención y términos de
búsqueda mediante JSON validado con Pydantic. No recibe credenciales de Firebase
ni el catálogo. Los datos comerciales se redactan desde Firestore, no desde la IA.
Esto no incorpora todavía memoria de conversación ni recomendaciones por IA.

Implementación del proveedor en `app/ai/providers/gemini_provider.py`.
El archivo vacío previo `geminni_provider.py` no se utiliza.
Referencia: https://ai.google.dev/api/generate-content

## Pruebas locales

No necesitan Firebase ni claves de IA:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s test
```
