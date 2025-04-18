from sqlalchemy import create_engine, MetaData, Table, Column, String, Date, Integer
from sqlalchemy.orm import declarative_base
from databases import Database
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://abonamente_user:JhoMGJk2pZi5TifSzZEPQPuRncST01iS@dpg-d011uuk9c44c73cpso90-a.oregon-postgres.render.com/abonamente")  # înlocuiește cu URL-ul tău

database = Database(DATABASE_URL)
Base = declarative_base()

class Subscription(Base):
    __tablename__ = "abonamente"
    plate = Column(String, primary_key=True)
    owner = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)

# Doar pentru crearea tabelei o dată:
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
