import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router as api_router

# 1. Create the FastAPI Application
app = FastAPI(
    title="CV Nexus API",
    description="AI-powered CV analysis and job matching engine",
    version="1.0.0"
)

# 2. Set up CORS (Cross-Origin Resource Sharing)
# This acts as a security bouncer. Setting it to ["*"] allows any Frontend (React/Vue/HTML) 
# to communicate with this backend without getting blocked by the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# 3. Connect the routes from our API module
# The API will be accessible at http://localhost:8000/api/v1/...
app.include_router(api_router, prefix="/api/v1")

# === Server Execution ===
if __name__ == "__main__":
    print("[SYSTEM] Starting CV Nexus Backend Server...")
    # Run the server on port 8000. 'reload=True' auto-restarts the server if you change the code.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)