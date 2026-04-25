from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.part_service import PartService
from app.schemas.part import PartCreate, PartUpdate, PartPatch, PartResponse, PartsListResponse
from app.middleware.auth import require_auth

router = APIRouter(prefix="/parts", tags=["Auto Parts"])


@router.get("", response_model=PartsListResponse)
async def get_all_parts(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    # Требуется аутентификация
    user_id = require_auth(request)
    
    service = PartService(db)
    parts, meta = await service.get_parts(page, limit, user_id=user_id)
    return {"data": parts, "meta": meta}


@router.get("/{part_id}", response_model=PartResponse)
async def get_part(
    request: Request,
    part_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Требуется аутентификация
    user_id = require_auth(request)
    
    service = PartService(db)
    part = await service.get_part_by_id(part_id, user_id=user_id)
    if not part:
        raise HTTPException(status_code=404, detail="Запчасть не найдена или удалена")
    return part


@router.post("", response_model=PartResponse, status_code=201)
async def create_part(
    request: Request,
    part: PartCreate,
    db: AsyncSession = Depends(get_db)
):
    # Требуется аутентификация
    user_id = require_auth(request)
    
    service = PartService(db)
    try:
        return await service.create_part(part, user_id=user_id)
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail=f"Запчасть с артикулом '{part.part_number}' уже существует"
        )


@router.put("/{part_id}", response_model=PartResponse)
async def update_part(
    request: Request,
    part_id: int,
    part: PartUpdate,
    db: AsyncSession = Depends(get_db)
):
    # Требуется аутентификация
    user_id = require_auth(request)
    
    service = PartService(db)
    
    # Проверка владения
    existing_part = await service.get_part_by_id(part_id, user_id=None)
    if not existing_part:
        raise HTTPException(status_code=404, detail="Запчасть не найдена")
    
    if existing_part.owner_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Нет прав для редактирования этой запчасти"
        )
    
    try:
        updated = await service.update_part(part_id, part)
        if not updated:
            raise HTTPException(status_code=404, detail="Запчасть не найдена")
        return updated
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail=f"Запчасть с артикулом '{part.part_number}' уже существует"
        )


@router.patch("/{part_id}", response_model=PartResponse)
async def patch_part(
    request: Request,
    part_id: int,
    part: PartPatch,
    db: AsyncSession = Depends(get_db)
):
    # Требуется аутентификация
    user_id = require_auth(request)
    
    service = PartService(db)
    
    # Проверка владения
    existing_part = await service.get_part_by_id(part_id, user_id=None)
    if not existing_part:
        raise HTTPException(status_code=404, detail="Запчасть не найдена")
    
    if existing_part.owner_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Нет прав для редактирования этой запчасти"
        )
    
    try:
        updated = await service.patch_part(part_id, part)
        if not updated:
            raise HTTPException(status_code=404, detail="Запчасть не найдена")
        return updated
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail=f"Запчасть с артикулом '{part.part_number}' уже существует"
        )


@router.delete("/{part_id}", status_code=204)
async def delete_part(
    request: Request,
    part_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Требуется аутентификация
    user_id = require_auth(request)
    
    service = PartService(db)
    
    # Проверка владения
    existing_part = await service.get_part_by_id(part_id, user_id=None)
    if not existing_part:
        raise HTTPException(status_code=404, detail="Запчасть не найдена")
    
    if existing_part.owner_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Нет прав для удаления этой запчасти"
        )
    
    success = await service.delete_part(part_id)
    if not success:
        raise HTTPException(status_code=404, detail="Запчасть не найдена")
    return None
