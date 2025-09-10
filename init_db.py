#!/usr/bin/env python3
"""
Database initialization script for Nintendo Deals Bot
"""

from models.database import engine
from models.models import Base

def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    init_database()
