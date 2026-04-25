from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.part import AutoPart
from app.schemas.part import PartCreate, PartUpdate, PartPatch
from datetime import datetime
from typing import Optional, Tuple, List


class PartService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_parts(
        self,
        page: int = 1,
        limit: int = 10,
        user_id: Optional[int] = None
    ) -> Tuple[List[AutoPart], dict]:
        # Soft Delete: выбираем только где deleted_at is NULL
        query = select(AutoPart).where(AutoPart.deleted_at == None)
        
        # Если передан user_id, фильтруем только его запчасти
        if user_id:
            query = query.where(AutoPart.owner_id == user_id)

        # Подсчет общего количества для пагинации
        count_query = select(func.count()).select_from(AutoPart).where(AutoPart.deleted_at == None)
        if user_id:
            count_query = count_query.where(AutoPart.owner_id == user_id)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Пагинация
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        parts = result.scalars().all()

        total_pages = (total + limit - 1) // limit if total > 0 else 0

        return parts, {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }

    async def get_part_by_id(self, part_id: int, user_id: Optional[int] = None):
        query = select(AutoPart).where(
            AutoPart.id == part_id,
            AutoPart.deleted_at == None
        )
        
        # Если передан user_id, проверяем владение
        if user_id:
            query = query.where(AutoPart.owner_id == user_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_part(self, part_data: PartCreate, user_id: int):
        new_part = AutoPart(
            **part_data.model_dump(),
            owner_id=user_id
        )
        self.db.add(new_part)
        try:
            await self.db.commit()
            await self.db.refresh(new_part)
            return new_part
        except IntegrityError:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def update_part(self, part_id: int, part_data: PartUpdate):
        # Сначала проверяем существование (с учетом soft delete)
        part = await self.get_part_by_id(part_id)
        if not part:
            return None

        try:
            for key, value in part_data.model_dump().items():
                setattr(part, key, value)

            part.updated_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(part)
            return part
        except IntegrityError:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def patch_part(self, part_id: int, part_data: PartPatch):
        part = await self.get_part_by_id(part_id)
        if not part:
            return None

        try:
            update_data = part_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(part, key, value)

            part.updated_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(part)
            return part
        except IntegrityError:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def delete_part(self, part_id: int):
        # Soft Delete: обновляем поле deleted_at вместо удаления
        part = await self.get_part_by_id(part_id)
        if not part:
            return False

        try:
            part.deleted_at = datetime.now()
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            raise
