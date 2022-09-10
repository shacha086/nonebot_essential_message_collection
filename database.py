from ast import operator
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy import *    
from .objects import *

ModelBase = declarative_base()

class Essences(ModelBase):
    __tablename__ = 'essences'
    message_id = Column(Integer, primary_key=True)
    group_id = Column(Integer)
    operator_id = Column(Integer)
    sender_id = Column(Integer)
    time = Column(Integer)
    message = Column(String())

class Pictures(ModelBase):
    __tablename__ = 'pictures'
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer)
    hash = Column(String())

engine = create_engine(f"sqlite:///{Object.db_path()}")
if not database_exists(engine.url):
    create_database(engine.url)
ModelBase.metadata.create_all(engine)
Session: sessionmaker = sessionmaker(bind=engine)