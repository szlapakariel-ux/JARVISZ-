from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True) # Telegram ID
    first_name = Column(String)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    checkins = relationship("CheckIn", back_populates="user")
    energy_logs = relationship("EnergyLog", back_populates="user")
    journal_entries = relationship("JournalEntry", back_populates="user")

class CheckIn(Base):
    __tablename__ = 'checkins'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    type = Column(String) # 'morning', 'evening'
    sleep_score = Column(Integer, nullable=True)
    body_battery = Column(Integer, nullable=True)
    mood_score = Column(Integer) # 1-5
    
    # Emotional/Physical Check-in (The 2 words technique)
    emotion_word = Column(String, nullable=True)
    sensation_word = Column(String, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="checkins")

class EnergyLog(Base):
    __tablename__ = 'energy_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    level = Column(Integer) # 0-100 (Body Battery or subjective)
    source = Column(String) # 'manual', 'garmin'
    context = Column(String, nullable=True) # e.g. "After work", "Woke up"
    
    user = relationship("User", back_populates="energy_logs")

class JournalEntry(Base):
    __tablename__ = 'journal_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    content = Column(Text)
    tags = Column(String, nullable=True) # JSON or comma-separated
    
    user = relationship("User", back_populates="journal_entries")

class KPIEvent(Base):
    __tablename__ = 'kpi_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    event_type = Column(String) # 'frustration', 'timer_set', 'task_breakdown', 'interaction'
    meta_data = Column(String, nullable=True) # JSON extra info
    
    user = relationship("User", back_populates="kpi_events")

User.kpi_events = relationship("KPIEvent", back_populates="user")
