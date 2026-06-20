from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from app.core.config import settings

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

# Inicialización de MCP sobre FastAPI
# fastapi-mcp automáticamente convierte las rutas de FastAPI en herramientas MCP
mcp = FastApiMCP(app)

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
