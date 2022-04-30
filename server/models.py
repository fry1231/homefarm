from pydantic import BaseModel


class States(BaseModel):
    ledstate: int
