from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, nullable=True)
    
    # Хеширование пароля
    password_hash = Column(String, nullable=True)  # Может быть NULL для OAuth пользователей
    salt = Column(String, nullable=True)
    
    # OAuth идентификаторы
    yandex_id = Column(String, unique=True, nullable=True)
    vk_id = Column(String, unique=True, nullable=True)
    
    # Автоматические метки
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Soft Delete
    deleted_at = Column(DateTime, nullable=True)
    
    # Связь с токенами
    refresh_tokens = relationship("RefreshToken", back_populates="user", lazy="dynamic")
    access_tokens = relationship("AccessToken", back_populates="user", lazy="dynamic")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", lazy="dynamic")
    
    # Связь с запчастями (для проверки владения)
    parts = relationship("AutoPart", back_populates="owner", lazy="dynamic")
