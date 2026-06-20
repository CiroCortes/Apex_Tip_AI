Actúa como un Desarrollador Backend Senior especialista en Python, FastAPI, Arquitectura Limpia y Sistemas de Inteligencia Artificial Avanzada. Vamos a construir el backend completo para "ApexTip AI", una plataforma premium de apuestas deportivas e información analítica asistida por IA y una comunidad de Tipsters.

El stack tecnológico obligatorio es:
- Framework: FastAPI (Asíncrono, Python 3.11+)
- Base de Datos: Supabase (PostgreSQL) para persistencia relacional.
- Autenticación: Middleware para validar tokens JWT de Firebase Auth (extrayendo el uid del usuario).
- Motor de IA Principal: Google GenAI SDK (Gemini 1.5 Pro/Flash) con un mecanismo de fallback estructurado hacia otra API (como Anthropic Claude) en caso de error de conexión.
- Protocolo de Contexto: Soporte e integración para MCP (Model Context Protocol) para permitir interactuar con las herramientas de desarrollo de forma automatizada.
- Metodología: Spec-Driven Development utilizando Pydantic v2 para esquemas estrictos y autogeneración de OpenAPI.
- Despliegue: Dockerizado y listo para Render.

Deportes a soportar en el diseño de datos: Fútbol, Hockey sobre hielo, Baloncesto, eSports y Tenis.

Necesito que generes la arquitectura inicial estructurada en las siguientes capas de Clean Architecture:

1. CAPA DE DOMINIO Y MODELOS (Supabase / Pydantic):
- Define los modelos de base de datos relacionales para Supabase y sus equivalentes en Pydantic:
  * Usuarios/Perfiles: Sincronizado con Firebase UID, indicando si el rol es 'user' o 'tipster', y su estado de suscripción ('free' o 'premium').
  * Red Social (Comunidad): Tabla 'followers' (seguidor_id, seguido_id) y tabla 'posts/predicciones_tipster' para que los tipsters publiquen sus cuotas recomendadas, permitiendo dar 'Me gusta' y comentarios.
  * Predicciones IA: Almacenamiento de predicciones generadas por Gemini (evento, deporte, mercado, cuota estimada, probabilidad calculada, resultado final y estado de acierto).

2. SERVICIO DEL ANALISTA IA (gemini_service.py):
- Implementa un servicio asíncrono con el SDK oficial de Gemini que implemente "Structured Outputs" usando Pydantic.
- Debe incluir un "System Prompt" diseñado para un Analista Estadístico Deportivo Profesional cuyo objetivo es maximizar la precisión matemática hacia un 80% analizando data cruda (goles, xG, posesión, rachas, H2H).
- El JSON de retorno debe estructurarse estrictamente con: 'fixture_id', 'prediccion_mercado', 'porcentaje_confianza', 'analisis_justificado' y 'cuota_minima_recomendada'.
- Implementa un bloque try/except que, ante un fallo de la API de Gemini, actúe de fallback llamando a una clase contenedora secundaria (simulando Claude/DeepSeek).

3. INTEGRACIÓN MCP (mcp_server.py):
- Crea un endpoint o inicializador de servidor MCP básico que exponga herramientas esenciales del sistema (como 'consultar_rendimiento_tipster' o 'generar_pronostico_ia') para que clientes habilitados con MCP puedan interactuar con el contexto de la app.

4. CONFIGURACIÓN Y ENTRYPOINT:
- 'app/core/config.py' usando Pydantic Settings para gestionar de forma segura las llaves de Supabase, Firebase, Gemini y variables MCP.
- 'app/main.py' con la inicialización de FastAPI configurando CORS, routers y documentación OpenAPI automática.

Entrega código limpio, completamente tipado (Type Hints), modular, asíncrono y listo para producción, libre de explicaciones innecesarias en prosa para centrarte en la calidad del software.

necesito que este back sea creado con SDD, este es el enlace a git :  https://github.com/github/spec-kit