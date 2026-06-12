"""
SQLAlchemy ORM models — the database schema.
"""
from datetime import datetime

from sqlalchemy import (
    Column, Date, DateTime, Float, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Property(Base):
    """One property listing on one scrape date."""

    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_acct_no = Column(String(60), nullable=False, index=True)
    category = Column(String(100), index=True)
    classification = Column(String(100))
    tct_number = Column(String(120))
    address = Column(Text)
    city = Column(String(120), index=True)
    province = Column(String(100), index=True)
    region = Column(String(100), index=True)
    lot_area_sqm = Column(Float)
    floor_area_sqm = Column(Float)
    price_php = Column(Float)
    price_per_sqm = Column(Float)          # pre-computed for fast queries
    other_remarks = Column(Text)
    source = Column(String(50), default="BSP", index=True)
    date_scraped = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    # __table_args__ = (
    #     # Prevent duplicate ingestion of the same property on the same day
    #     UniqueConstraint("property_acct_no", "date_scraped", name="uq_property_date"),
    # )
    __table_args__ = (
                UniqueConstraint("property_acct_no","tct_number", name="uq_property_tct"),    #MORE UNIQUE
                    )



    def __repr__(self) -> str:
        return (
            f"<Property acct={self.property_acct_no!r} "
            f"price={self.price_php:,.0f} date={self.date_scraped}>"
        )


class ScrapeRun(Base):
    """Audit log of every pipeline execution."""

    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), index=True)
    date_scraped = Column(Date, index=True)
    records_extracted = Column(Integer, default=0)
    records_loaded = Column(Integer, default=0)
    status = Column(String(20), default="pending")   # pending | success | failed
    error_message = Column(Text)
    duration_seconds = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<ScrapeRun source={self.source!r} date={self.date_scraped} "
            f"status={self.status!r} loaded={self.records_loaded}>"
        )
