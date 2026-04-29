from typing import List

from pydantic import BaseModel


class GroupedBookieOut(BaseModel):
    bookie: str
    mercados: List[str]


class GroupedEventOut(BaseModel):
    deporte: str
    competicion: str
    partido: str
    bookies: List[GroupedBookieOut]


class GroupedEventsResponse(BaseModel):
    total: int
    groups: List[GroupedEventOut]