from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from app.core.config import settings

from app.api.v1.endpoints import community, ai_analytics, scheduler, recap

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API and MCP Server for ApexTip AI"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Ajustar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión de módulos
app.include_router(community.router, prefix="/api/v1/community", tags=["Comunidad & Tipsters"])
app.include_router(ai_analytics.router, prefix="/api/v1/ai", tags=["Analista Inteligencia Artificial"])
app.include_router(scheduler.router, prefix="/api/v1/cron", tags=["Motor de Recolección (Cron)"])
app.include_router(recap.router, prefix="/api/v1/cron", tags=["Recapitulador de Resultados"])

# Inicialización de MCP sobre FastAPI
# fastapi-mcp automáticamente convierte las rutas de FastAPI en herramientas MCP
mcp = FastApiMCP(app)

from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

# Montar MCP en el endpoint /mcp (opcional según cómo se exponga, SSE típicamente se hace manual o via la librería)
# En fastapi_mcp, .mount() típicamente añade las rutas SSE
try:
    mcp.mount()
except AttributeError:
    pass # Depende de la versión exacta de fastapi_mcp

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
