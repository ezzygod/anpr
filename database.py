from sqlalchemy import Table, Column, String, DateTime, MetaData
from databases import Database

# Conexiune Railway
DATABASE_URL = "mysql+aiomysql://root:iPbRZiKBUhJjdgTvQWvVHEEfbqOMVTtw@mainline.proxy.rlwy.net:21209/railway"

database = Database(DATABASE_URL)
metadata = MetaData()

Subscription = Table(
    "abonamente",
    metadata,
    Column("numar_inmatriculare", String, primary_key=True),
    Column("nume", String),
    Column("prenume", String),
    Column("data_achizitie", DateTime),
    Column("data_expirare", DateTime),
)
