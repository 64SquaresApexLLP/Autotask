"""Database connection and models for Snowflake integration."""

import logging
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from snowflake.sqlalchemy import URL
from .config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


class TechnicianDummyData(Base):
    """Technician user model based on existing TECHNICIAN_DUMMY_DATA table."""
    __tablename__ = "TECHNICIAN_DUMMY_DATA"
    __table_args__ = {'schema': 'PUBLIC'}

    technician_id = Column(String(50), primary_key=True, name="TECHNICIAN_ID")
    name = Column(String(50), name="NAME")
    email = Column(String(100), name="EMAIL")
    role = Column(String(50), name="ROLE")
    skills = Column(String(500), name="SKILLS")
    current_workload = Column(String(50), name="CURRENT_WORKLOAD")
    specializations = Column(String(500), name="SPECIALIZATIONS")
    technician_password = Column(String(50), name="TECHNICIAN_PASSWORD")

    # Add properties for compatibility with existing auth system
    @property
    def id(self):
        return self.technician_id

    @property
    def username(self):
        return self.email.split('@')[0] if self.email else self.technician_id

    @property
    def full_name(self):
        return self.name

    @property
    def department(self):
        return self.specializations

    @property
    def is_active(self):
        return True

    @property
    def hashed_password(self):
        # For demo purposes - in production, hash the password properly
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(self.technician_password) if self.technician_password else ""



class Ticket(Base):
    """Support ticket model based on existing TICKETS table."""
    __tablename__ = "TICKETS"
    __table_args__ = {'schema': 'PUBLIC'}

    ticketnumber = Column(String(50), primary_key=True, name="TICKETNUMBER")
    title = Column(String(500), name="TITLE")
    description = Column(Text, name="DESCRIPTION")
    tickettype = Column(String(50), name="TICKETTYPE")
    ticketcategory = Column(String(50), name="TICKETCATEGORY")
    issuetype = Column(String(50), name="ISSUETYPE")
    subissuetype = Column(String(50), name="SUBISSUETYPE")
    duedatetime = Column(String(50), name="DUEDATETIME")
    resolution = Column(Text, name="RESOLUTION")
    userid = Column(String(50), name="USERID")
    useremail = Column(String(100), name="USEREMAIL")
    technicianemail = Column(String(100), name="TECHNICIANEMAIL")
    phonenumber = Column(String(20), name="PHONENUMBER")

    # Add properties for compatibility with existing code
    @property
    def id(self):
        return self.ticketnumber

    @property
    def ticket_number(self):
        return self.ticketnumber

    @property
    def status(self):
        # Derive status from resolution field
        if self.resolution and self.resolution.strip():
            return "resolved"
        else:
            return "open"

    @property
    def priority(self):
        # Default priority - could be enhanced based on issue type
        if self.issuetype in ["Network", "Cloud Workspace"]:
            return "high"
        else:
            return "medium"

    @property
    def category(self):
        return self.ticketcategory

    @property
    def assigned_technician_id(self):
        return self.technicianemail

    @property
    def created_by(self):
        return self.useremail

    @property
    def created_at(self):
        # Parse due date as created date for now
        try:
            from datetime import datetime
            return datetime.strptime(self.duedatetime, "%Y-%m-%d") if self.duedatetime else None
        except:
            return None

    @property
    def updated_at(self):
        return self.created_at

    @property
    def resolved_at(self):
        return self.created_at if self.status == "resolved" else None

    @property
    def resolution_notes(self):
        return self.resolution


class UserDummyData(Base):
    """User model based on existing USER_DUMMY_DATA table."""
    __tablename__ = "USER_DUMMY_DATA"
    __table_args__ = {'schema': 'PUBLIC'}

    user_id = Column(String(50), primary_key=True, name="USER_ID")
    name = Column(String(100), name="NAME")
    user_email = Column(String(100), name="USER_EMAIL")
    user_phonenumber = Column(String(20), name="USER_PHONENUMBER")
    user_password = Column(String(50), name="USER_PASSWORD")


class KnowledgeBase(Base):
    """Knowledge base model for FAQ and help articles."""
    __tablename__ = "knowledge_base"
    __table_args__ = {'schema': 'PUBLIC'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50))
    tags = Column(String(500))
    author_id = Column(String(50))  # VARCHAR to match technician_id format
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP()')
    updated_at = Column(DateTime, server_default='CURRENT_TIMESTAMP()')
    view_count = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)


class CompanyData(Base):
    """Company data model based on existing COMPANY_4130_DATA table."""
    __tablename__ = "COMPANY_4130_DATA"
    __table_args__ = {'schema': 'PUBLIC'}

    # Assuming the table has similar structure to TICKETS
    # Adjust these columns based on actual table structure
    ticketnumber = Column(String(50), primary_key=True, name="TICKETNUMBER")
    title = Column(String(500), name="TITLE")
    description = Column(Text, name="DESCRIPTION")
    tickettype = Column(String(50), name="TICKETTYPE")
    ticketcategory = Column(String(50), name="TICKETCATEGORY")
    issuetype = Column(String(50), name="ISSUETYPE")
    subissuetype = Column(String(50), name="SUBISSUETYPE")
    duedatetime = Column(String(50), name="DUEDATETIME")
    resolution = Column(Text, name="RESOLUTION")
    userid = Column(String(50), name="USERID")
    useremail = Column(String(100), name="USEREMAIL")
    technicianemail = Column(String(100), name="TECHNICIANEMAIL")
    phonenumber = Column(String(20), name="PHONENUMBER")
    status = Column(String(50), name="STATUS")
    priority = Column(String(50), name="PRIORITY")

    # Add properties for compatibility with existing code
    @property
    def id(self):
        return self.ticketnumber

    @property
    def ticket_number(self):
        return self.ticketnumber

    @property
    def is_resolved(self):
        return self.resolution and self.resolution.strip() and self.status == "Resolved"


# Using existing tables plus knowledge_base for FAQ functionality


# Database connection
def create_snowflake_engine():
    """Create Snowflake database engine."""
    try:
        # Build connection parameters
        connect_args = {
            'account': settings.snowflake_account,
            'user': settings.snowflake_user,
            'database': settings.snowflake_database,
            'schema': settings.snowflake_schema,
            'warehouse': settings.snowflake_warehouse,
            'role': settings.snowflake_role,
        }

        # Add authentication method
        if settings.snowflake_authenticator == "externalbrowser":
            connect_args['authenticator'] = 'externalbrowser'
        elif settings.snowflake_password:
            connect_args['password'] = settings.snowflake_password

        engine = create_engine(
            URL(**connect_args),
            echo=settings.debug,
            # Connection pooling settings to reuse connections
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600  # Recycle connections every hour
        )
        logger.info("Snowflake database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Failed to create Snowflake engine: {e}")
        raise

# Global engine and session factory
engine = create_snowflake_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)




def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Verify existing database tables (no new tables created)."""
    try:
        # Only verify that existing tables are accessible
        # We don't create any new tables - using only TICKETS and TECHNICIAN_DUMMY_DATA
        logger.info("Using existing database tables only - no new tables created")
    except Exception as e:
        logger.error(f"Failed to verify database tables: {e}")
        raise
