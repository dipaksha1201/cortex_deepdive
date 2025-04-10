from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controller.deep_dive import api_router
from controller.maestro import router as maestro_api_router
import uvicorn

app = FastAPI(
    title="Cortex",
    description="Knowledge workers second brain",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(maestro_api_router, prefix="/api", tags=["maestro"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to Cortex Deep Dive",
        "status": "operational"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=False,
        workers=4
    )