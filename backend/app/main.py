from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.app.db.database import Base, engine
from backend.app import models  # noqa: F401 - registers SQLAlchemy models
from backend.app.routers.auth import router as auth_router
from backend.app.routers.transactions import router as transactions_router
from backend.app.routers.bills import router as bills_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Personal Income & Expense Tracker API", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(bills_router)

@app.get("/")
def root():
    return {"message": "Personal Income & Expense Tracker API is running"}
