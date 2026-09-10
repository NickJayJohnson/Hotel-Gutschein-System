import random
import string
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./hotel_gutscheine.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Datenbank-Modelle
class Kunde(Base):
    __tablename__ = "kunden"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)

class Gutschein(Base):
    __tablename__ = "gutscheine"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    original_wert = Column(Float)
    rest_wert = Column(Float)
    empfaenger_name = Column(String, nullable=True)
    absender_name = Column(String, nullable=True)
    widmung = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def code_generieren(laenge=8):
    zeichen = string.ascii_uppercase + string.digits
    return ''.join(random.choices(zeichen, k=laenge))
