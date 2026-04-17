from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()

# ======+ Middlewares +======
app.add_middleware(CORSMiddleware, "*", "*")

app.add_middleware(GZipMiddleware)

# ======+ Routers +========
...
