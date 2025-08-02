# main.py
from fastapi import FastAPI
from app.modules.project_management.api.routes import router as module_router

app = FastAPI(title="Bheem Project Management Module")
app.include_router(module_router, prefix="/api/project_management")

