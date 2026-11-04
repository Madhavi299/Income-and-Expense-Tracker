from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def initialize_database(bind=engine):
    Base.metadata.create_all(bind=bind)
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    with bind.begin() as connection:
        if "role" not in columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
            )
        if "is_active" not in columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE")
            )
    Base.metadata.create_all(bind=bind)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
