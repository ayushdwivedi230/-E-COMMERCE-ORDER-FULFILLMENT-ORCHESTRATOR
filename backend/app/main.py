import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import init_db, SessionLocal, get_db
from backend.app.services.seed_data import seed_database
from backend.app.api.orders import router as orders_router
from backend.app.api.products import router as products_router
from backend.app.api.customers import router as customers_router
from backend.app.api.agents import router as agents_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ecommerce")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    logger.info("Initializing database and tables...")
    init_db()
    
    # Auto-seed sample products and customer memory if empty
    db = SessionLocal()
    try:
        seed_database(db)
        logger.info("Database verified and seeded.")
    finally:
        db.close()
        
    yield
    logger.info("Application shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-Agent E-Commerce Order Fulfillment Orchestrator built on Microsoft Agent Framework.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(orders_router)
app.include_router(products_router)
app.include_router(customers_router)
app.include_router(agents_router)


@app.get("/health")
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint that verifies API and database responsiveness."""
    return {
        "status": "HEALTHY",
        "app_name": settings.APP_NAME,
        "database": "CONNECTED",
        "environment": settings.APP_ENV,
    }


@app.post("/api/seed")
def reseed_database(db: Session = Depends(get_db)):
    """Reset / re-seed sample customers, products, and historical memory."""
    seed_database(db)
    return {"message": "Database successfully populated with baseline sample data."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
