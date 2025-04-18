from sqlalchemy import Column, String, Date
from sqlalchemy.ext.declarative import declarative_base
from databases import Database

DATABASE_URL = "mysql+aiomysql://sql7773773:QL5qYji5K5@sql7.freesqldatabase.com:3306/sql7773773"

database = Database(DATABASE_URL)
Base = declarative_base()

class Subscription(Base):
    __tablename__ = "abonamente"
    numar_inmatriculare = Column(String, primary_key=True)
    nume = Column(String)
    prenume = Column(String)
    data_achizitie = Column(Date)
    data_expirare = Column(Date)
