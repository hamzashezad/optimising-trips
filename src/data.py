import json
from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel


class TransportOption(BaseModel):
    id: str
    dep: datetime
    arr: datetime
    type: Literal["air", "train"]
    cost: float


class AccommodationOption(BaseModel):
    id: str
    checkin: time
    checkout: time
    cost_per_night: float
    internal_cost: float
    breakfast_included: bool


with open("./data/accommodation_options.json", "r") as f:
    data = json.load(f)
    accommodation_options = [AccommodationOption(**item) for item in data]

with open("./data/outward_transport_options.json", "r") as f:
    data = json.load(f)
    outward_transport_options = [TransportOption(**item) for item in data]

with open("./data/inward_transport_options.json", "r") as f:
    data = json.load(f)
    inward_transport_options = [TransportOption(**item) for item in data]
