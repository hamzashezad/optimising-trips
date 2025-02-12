import logging

from datetime import datetime
import pulp
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from data import (
    AccommodationOption,
    TransportOption,
    accommodation_options,
    inward_transport_options,
    outward_transport_options,
)
from optimisation_model import model, print_solution_costs, w, w_keys


class ModelSolution(BaseModel):
    cost: float
    outward_transport_selection: TransportOption
    inward_transport_selection: TransportOption
    accommodation_selection: AccommodationOption

def format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d, %H:%M %Z")


templates = Jinja2Templates(directory="templates")

templates.env.filters["format_datetime"] = format_datetime

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "outward_transport_options": outward_transport_options,
            "inward_transport_options": inward_transport_options,
            "accommodation_options": accommodation_options,
        },
    )


@app.post("/solve", response_class=HTMLResponse)
async def solve_model(request: Request):
    model.solve()
    print_solution_costs()

    logging.info("Status:", pulp.LpStatus[model.status])

    selection = [(i, j, k) for i, j, k in w_keys if w[(i, j, k)] == 1]

    print(len(selection))
    i,j,k = selection[-1]

    outward_selection, inward_selection, accommodation_selection = None, None, None

    for option in outward_transport_options:
        if option.id == i:
            outward_selection = option
            break

    for option in inward_transport_options:
        if option.id == j:
            inward_selection = option
            break

    for option in accommodation_options:
        if option.id == k:
            accommodation_selection = option
            break

    return templates.TemplateResponse(
        request=request,
        name="solution.html",
        context={
            "solution": ModelSolution(
                **{
                    "cost": pulp.value(model.objective),
                    "outward_transport_selection": outward_selection,
                    "inward_transport_selection": inward_selection,
                    "accommodation_selection": accommodation_selection,
                }
            )
        },
    )
