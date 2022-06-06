from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)

    things = relationship("Thing", back_populates="board")


class Thing(Base):
    __tablename__ = "things"

    id = Column(Integer, primary_key=True, index=True)
    analog = Column(Boolean)
    pin = Column(Integer, unique=True)
    is_writable = Column(Boolean)

    equipment_name = Column(String)
    equipment_desc = Column(String)
    tsdb_tag = Column(String, unique=True)
    schedule_id = Column(Integer, ForeignKey('schedules.id'))

    board = relationship("Board", back_populates="things")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    desc = Column(String)
    hour = Column(Integer)
    list_of_tuple_minutes = Column(String)


class Triggers(Base):
    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True, index=True)
    on = Column(Integer, ForeignKey("things.id"), nullable=False)
    do = Column(Integer, ForeignKey("things.id"), nullable=False)
    set = Column(Integer, nullable=False)
    for_seconds = Column(Integer)
    until_sensor_id = Column(Integer, ForeignKey("things.id"))
    until_sensor_val = Column(Integer)
