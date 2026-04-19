from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from .api import api_router

app = FastAPI()

app.state.tracks_dao = None
app.state.storage = None

# ======+ Middlewares +======
app.add_middleware(CORSMiddleware, "*", "*")

app.add_middleware(GZipMiddleware)

# ======+ Routers +========
app.include_router(api_router)
