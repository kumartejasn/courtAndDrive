
from sqlalchemy import (create_engine, Table, Column, Integer, 
                        String, MetaData, Text, ForeignKey)

DATABASE_URL = "sqlite:///./court_queries.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()


queries = Table(
    "queries",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("case_type", String),
    Column("case_number", String),
    Column("case_year", String),
    Column("status", String), 
    Column("raw_response_html", Text, nullable=True),
)


cases = Table(
    "cases",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("case_identifier", String, unique=True, index=True),
    Column("parties", Text),
    Column("filing_date", String),
    Column("next_hearing_date", String),
)


orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True),
   
    Column("case_id", Integer, ForeignKey("cases.id")),
    Column("pdf_url", String, unique=True),
    Column("order_date", String),
)



metadata.create_all(engine)