from sqlalchemy import Column, String, Date
from sqlalchemy.ext.declarative import declarative_base
from databases import Database

# Noua conexiune Railway:
DATABASE_URL = "mysql+aiomysql://root:iPbRZiKBUhJjdgTvQWvVHEEfbqOMVTtw@mainline.proxy.rlwy.net:21209/railway"

database = Database(DATABASE_URL)
Base = declarative_base()

class Subscription(Base):
    __tablename__ = "abonamente"
    numar_inmatriculare = Column(String, primary_key=True)
    nume = Column(String)
    prenume = Column(String)
    data_achizitie = Column(Date)
    data_expirare = Column(Date)
