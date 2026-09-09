from fastapi import FastAPI
from .routes.users import router as users_router
from .routes.auth import router as auth_router

app = FastAPI(
    title="Demo User Management API",
    description="Sample service for AI SWE Agent benchmark",
    version="1.0.0",
)

app.include_router(users_router)
app.include_router(auth_router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "user-management-api"}
