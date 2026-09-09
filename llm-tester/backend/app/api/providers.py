from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from app.db.database import get_db
from app.models.models import Provider, ProviderType
from app.models.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    TestStatistics
)

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=List[ProviderResponse])
async def get_providers(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка провайдеров"""
    query = select(Provider)
    
    if is_active is not None:
        query = query.where(Provider.is_active == is_active)
    
    query = query.offset(skip).limit(limit).order_by(Provider.priority.asc())
    
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/types", response_model=List[str])
async def get_provider_types():
    """Получение доступных типов провайдеров"""
    return [t.value for t in ProviderType]


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider_data: ProviderCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание нового провайдера"""
    # Проверяем уникальность имени
    existing = await db.execute(
        select(Provider).where(Provider.name == provider_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider with this name already exists"
        )
    
    provider = Provider(**provider_data.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    
    return provider


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение провайдера по ID"""
    result = await db.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    return provider


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: int,
    provider_data: ProviderUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление провайдера"""
    result = await db.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    update_data = provider_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)
    
    await db.commit()
    await db.refresh(provider)
    
    return provider


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление провайдера"""
    result = await db.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    await db.delete(provider)
    await db.commit()
    
    return None


@router.post("/{provider_id}/test", response_model=dict)
async def test_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Тестирование подключения к провайдеру"""
    from app.services.providers.factory import ProviderFactory
    
    result = await db.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    llm_provider = ProviderFactory.create(
        provider_type=provider.provider_type,
        api_key=provider.api_key,
        base_url=provider.base_url
    )
    
    is_valid, error = await llm_provider.validate_connection()
    
    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "is_valid": is_valid,
        "error": error
    }


@router.get("/pool/validate", response_model=List[dict])
async def validate_pool(
    db: AsyncSession = Depends(get_db)
):
    """Проверка всех активных провайдеров в пуле"""
    from app.services.providers.pool_manager import PoolManager
    
    pool_manager = PoolManager(db)
    results = await pool_manager.validate_all_providers()
    
    return [
        {
            "provider_id": p.id,
            "provider_name": p.name,
            "provider_type": p.provider_type.value,
            "is_valid": is_valid,
            "error": error
        }
        for p, is_valid, error in results
    ]
