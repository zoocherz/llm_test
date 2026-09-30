from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
import io
import pandas as pd

from app.db.database import get_db
from app.models.models import Task, TestCase, TestRun, TestResult
from app.models.schemas import (
    TaskCreate, TaskUpdate, TaskResponse,
    TestCaseCreate, TestCaseUpdate, TestCaseResponse,
    TestRunCreate, TestRunResponse, TestResultResponse,
    ExportFormat
)
from app.services.test_runner import TestRunner

router = APIRouter(prefix="/tasks", tags=["tasks"])


# === Task Endpoints ===

@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка задач"""
    query = select(Task)
    
    if is_active is not None:
        query = query.where(Task.is_active == is_active)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание новой задачи"""
    task = Task(**task_data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id:int}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение задачи по ID"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.put("/{task_id:int}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление задачи"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id:int}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление задачи"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.delete(task)
    await db.commit()
    return None


# === TestCase Endpoints ===

@router.get("/{task_id:int}/test-cases", response_model=List[TestCaseResponse])
async def get_test_cases(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение тест-кейсов для задачи"""
    result = await db.execute(
        select(TestCase).where(TestCase.task_id == task_id)
    )
    return list(result.scalars().all())


@router.post("/{task_id:int}/test-cases", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_test_case(
    task_id: int,
    test_case_data: TestCaseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание тест-кейса для задачи"""
    # Проверяем существование задачи
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    if not task_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")
    
    test_case = TestCase(**test_case_data.model_dump(), task_id=task_id)
    db.add(test_case)
    await db.commit()
    await db.refresh(test_case)
    return test_case


@router.delete("/test-cases/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_case(
    test_case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление тест-кейса"""
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    test_case = result.scalar_one_or_none()
    
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    await db.delete(test_case)
    await db.commit()
    return None


# === TestRun Endpoints ===

@router.post("/run", response_model=TestRunResponse)
async def run_test(
    test_run_data: TestRunCreate,
    judge_model: str = "gpt-4o-mini",
    db: AsyncSession = Depends(get_db)
):
    """Запуск теста"""
    # Создаём запись о запуске
    test_run = TestRun(**test_run_data.model_dump())
    db.add(test_run)
    await db.commit()
    await db.refresh(test_run)
    
    # Запускаем тест в фоне (для простоты синхронно)
    runner = TestRunner(db)
    try:
        completed_run = await runner.run_test(test_run, judge_model=judge_model)
        return completed_run
    except Exception as e:
        test_run.status = "failed"
        test_run.completed_at = datetime.utcnow()
        await db.merge(test_run)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@router.get("/runs", response_model=List[TestRunResponse])
async def get_test_runs(
    task_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получение истории запусков тестов"""
    query = select(TestRun)
    
    if task_id is not None:
        query = query.where(TestRun.task_id == task_id)
    
    if status_filter is not None:
        query = query.where(TestRun.status == status_filter)
    
    query = query.order_by(TestRun.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/runs/{run_id}", response_model=TestRunResponse)
async def get_test_run(
    run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение деталей запуска теста"""
    result = await db.execute(select(TestRun).where(TestRun.id == run_id))
    test_run = result.scalar_one_or_none()
    
    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")
    
    return test_run


@router.get("/runs/{run_id}/results", response_model=List[TestResultResponse])
async def get_test_run_results(
    run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение результатов запуска теста"""
    result = await db.execute(
        select(TestResult).where(TestResult.test_run_id == run_id)
    )
    return list(result.scalars().all())


@router.get("/runs/{run_id}/export")
async def export_results(
    run_id: int,
    format: ExportFormat = ExportFormat.CSV,
    db: AsyncSession = Depends(get_db)
):
    """Экспорт результатов теста в CSV или Excel"""
    results_result = await db.execute(
        select(TestResult, TestCase)
        .join(TestCase, TestResult.test_case_id == TestCase.id)
        .where(TestResult.test_run_id == run_id)
    )
    results = results_result.all()
    
    if not results:
        raise HTTPException(status_code=404, detail="No results found")
    
    # Формируем данные для экспорта
    data = []
    for result, test_case in results:
        data.append({
            "Test Case": test_case.name,
            "Provider Used": result.provider_used,
            "Response Time (s)": result.response_time,
            "Cost ($)": result.cost,
            "Judge Score": result.judge_score,
            "Judge Feedback": result.judge_feedback,
            "Model Response": result.model_response,
            "Error": result.error_message,
        })
    
    df = pd.DataFrame(data)
    
    if format == ExportFormat.CSV:
        output = io.StringIO()
        df.to_csv(output, index=False)
        content = output.getvalue().encode('utf-8-sig')
        media_type = "text/csv"
        filename = f"test_run_{run_id}.csv"
    else:  # Excel
        output = io.BytesIO()
        df.to_excel(output, index=False)
        content = output.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"test_run_{run_id}.xlsx"
    
    from fastapi.responses import StreamingResponse
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
