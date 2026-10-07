from to_do_list_fast_api.database import Base, engine
from to_do_list_fast_api.models import User, Todo
from sqlalchemy import inspect

try:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("PostgreSQL connection successful!")
    print("Created/existing tables in PostgreSQL:", tables)
except Exception as e:
    print("Database connection error:", e)
