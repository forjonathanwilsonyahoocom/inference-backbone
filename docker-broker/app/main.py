from fastapi import FastAPI
from runtime import runtime_router
from on_demand_tools import on_demand_tools_router

app = FastAPI()

app.include_router(runtime_router)
app.include_router(on_demand_tools_router)

