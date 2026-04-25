from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Хеш токена (не храним в открытом виде)
    token_hash = Column(String, nullable=False)
    
    # Срок действия
    expires_at = Column(DateTime, nullable=False)
    
    # Флаг отзыва
    is_revoked = Column(Boolean, default=False)
    
    # Метаданные
    created_at = Column(DateTime, server_default=func.now())
    user_agent = Column(String, nullable=True)  # Для логирования устройства
    
    # Связь с пользователем
    user = relationship("User", back_populates="refresh_tokens")
