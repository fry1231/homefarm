from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)

    pins = relationship("Pin", back_populates="board")


class Pin(Base):
    __tablename__ = "pins"

    id = Column(Integer, primary_key=True, index=True)
    analog = Column(Boolean)
    number = Column(Integer, unique=True)
    is_readable = Column(Boolean)

    equipment_name = Column(String)
    equipment_desc = Column(String)
    tsdb_tag = Column(String, unique=True)
    required_state = Column(Boolean)

    board = relationship("Board", back_populates="pins")

