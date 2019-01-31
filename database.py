from sqlalchemy import (Boolean, Column, Date, DateTime, Float, ForeignKey,
                        Integer, String, create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    __table_args__ = {'useexisting': True}
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    gender = Column(String(1), nullable=False)
    birth_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Fact(Base):
    __tablename__ = 'fact'
    __table_args__ = {'useexisting': True}
    id = Column(Integer, primary_key=True)
    subject = Column(String(255), nullable=False)
    verbtense = Column(String(255), nullable=False)
    clause = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey('user.id'), default=0)
    user = relationship(User)
    is_public = Column(Boolean, default=True)
    counter = Column(Integer, default=1)


class Notification(Base):
    __tablename__ = 'notifications'
    __table_args__ = {'useexisting': True}
    id = Column(Integer, primary_key=True)
    url = Column(String(255), nullable=False)
    title = Column(String(63), nullable=False)
    message = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    capitalize = Column(Boolean, default=False)


class Meal(Base):
    __tablename__ = 'meal'
    __table_args__ = {'useexisting': True}
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    time = Column(DateTime(timezone=True), server_default=func.now())


class Food(Base):
    __tablename__ = 'food'
    __table_args__ = {'useexisting': True}
    name = Column(String(255), nullable=False, primary_key=True)
    script = Column(String(255), nullable=False)
    ash = Column(Float)
    calcium = Column(Float)
    carbohydrate = Column(Float)
    cholesterol = Column(Float)
    copper = Column(Float)
    dietary_fibre = Column(Float)
    iron = Column(Float)
    magnesium = Column(Float)
    moisture = Column(Float)
    niacin = Column(Float)
    phosphorus = Column(Float)
    potassium = Column(Float)
    retinol = Column(Float)
    riboflavin = Column(Float)
    sodium = Column(Float)
    thiamin = Column(Float)
    total_energy = Column(Float)
    total_fat = Column(Float)
    total_monounsaturated = Column(Float)
    total_omega_3_polyunsaturated = Column(Float)
    total_omega_6_polyunsaturated = Column(Float)
    total_protein = Column(Float)
    total_saturated = Column(Float)
    total_sugars = Column(Float)
    vitamin_a = Column(Float)
    vitamin_c = Column(Float)
    zinc = Column(Float)
    beta_carotene = Column(Float)
