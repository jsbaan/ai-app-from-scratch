"""
This file initializes the database connection and creates the SQLAlchemy objects we need later on.

SQLAlchemy is a toolkit to easily connect and interact with a SQL database, like our postgres db. It is also an Object
Relational Mapper (ORM) that maps user-defined python classes to db tables and instances of those classes (objects)
like a chat history to rows in those tables (https://docs.sqlalchemy.org/en/13/orm/tutorial.html).
It creates SQL queries for us, and uses psycopg2, a popular lower-level
python postgresql "driver" (connection & communication tool) under the hood.

Based on https://fastapi.tiangolo.com/tutorial/sql-databases/
"""

from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger("uvicorn.error")


# The Pydantic Settings model that reads environment variables in a case-insensitive way and sets default values
class Settings(BaseSettings):
    postgres_username: str = "myuser"
    postgres_password: str = "mypassword"
    postgres_host: str = "localhost"
    postgres_database: str = "postgres"
    postgres_port: int = 5432


# Load, convert and validate environment variables according to the schema above
settings = Settings()

# The url to connect to our postgres database using environment variables that can be set by Docker run/compose
SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.postgres_username}:{settings.postgres_password}@{settings.postgres_host}/{settings.postgres_database}"

# The "engine" is the lowest-level object in SQLAlchemy to manage connections with the db
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# `SessionLocal` is a class that we will instantiate later to create a database `Session` object.
# The `Session` object is the database "handle", i.e., the thing we use to reference/interact with the db
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# The SQLAlchemy system that describes db tables and maps our classes to it is called Declerative.
# The below declarative base class `Base` maintains a catalog of the classes and tables we will define later.
# Each class that we wish to map to a db table should inherent from this Base class.
Base = declarative_base()
