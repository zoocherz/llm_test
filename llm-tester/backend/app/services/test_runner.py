from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Task, TestCase, TestRun, TestResult, Provider
from app.services.providers.pool_manager import PoolManager
from app.services.judge import JudgeService
from app.services.providers.base import LLMError


class TestRunner:
    """Сервис для запуска тестов"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.pool_manager = PoolManager(db_session)
        self.judge_service = JudgeService(db_session)
    
    async def run_test(
        self,
        test_run: TestRun,
        judge_model: str = "gpt-4o-mini"
    ) -> TestRun:
        """Запуск теста для всех тест-кейсов задачи"""
        
        # Получаем задачу и тест-кейсы
        task_result = await self.db.execute(
            select(Task).where(Task.id == test_run.task_id)
        )
        task = task_result.scalar_one_or_none()
        
        if not task:
            raise ValueError(f"Task {test_run.task_id} not found")
        
        test_cases_result = await self.db.execute(
            select(TestCase).where(TestCase.task_id == task.id)
        )
        test_cases = list(test_cases_result.scalars().all())
        
        if not test_cases:
            raise ValueError(f"No test cases found for task {task.id}")
        
        # Обновляем статус
        test_run.status = "running"
        test_run.started_at = datetime.utcnow()
        await self.db.merge(test_run)
        await self.db.commit()
        
        total_cost = 0.0
        total_time = 0.0
        judge_scores = []
        
        # Выполняем каждый тест-кейс
        for test_case in test_cases:
            try:
                result = await self._run_single_test_case(
                    test_run=test_run,
                    test_case=test_case,
                    task=task,
                    judge_model=judge_model
                )
                
                total_cost += result.cost
                total_time += result.response_time
                
                if result.judge_score is not None:
                    judge_scores.append(result.judge_score)
                
            except Exception as e:
                # Создаём запись с ошибкой
                error_result = TestResult(
                    test_run_id=test_run.id,
                    test_case_id=test_case.id,
                    provider_used="N/A",
                    model_response="",
                    response_time=0.0,
                    cost=0.0,
                    error_message=str(e),
                    fallback_count=0,
                    judge_score=0.0,
                    judge_feedback=f"Test failed: {str(e)}"
                )
                self.db.add(error_result)
        
        # Обновляем статистику запуска
        test_run.completed_at = datetime.utcnow()
        test_run.status = "completed"
        test_run.total_cost = total_cost
        test_run.total_time = total_time
        test_run.average_judge_score = sum(judge_scores) / len(judge_scores) if judge_scores else None
        
        await self.db.merge(test_run)
        await self.db.commit()
        
        return test_run
    
    async def _run_single_test_case(
        self,
        test_run: TestRun,
        test_case: TestCase,
        task: Task,
        judge_model: str
    ) -> TestResult:
        """Запуск одного тест-кейса"""
        
        # Определяем модель для тестирования
        model_name = test_run.model_name
        
        # Если указан конкретный провайдер
        if test_run.provider_id:
            provider_result = await self.db.execute(
                select(Provider).where(Provider.id == test_run.provider_id)
            )
            provider = provider_result.scalar_one_or_none()
            
            if not provider:
                raise ValueError(f"Provider {test_run.provider_id} not found")
            
            # Используем конкретного провайдера
            from app.services.providers.factory import ProviderFactory
            llm_provider = ProviderFactory.create(
                provider_type=provider.provider_type,
                api_key=provider.api_key,
                base_url=provider.base_url
            )
            
            try:
                response = await llm_provider.generate(
                    prompt=test_case.prompt,
                    model=model_name,
                    input_text=test_case.input_text,
                    input_images=test_case.input_images,
                )
                
                provider_used = provider.name
                fallback_count = 0
                
            except LLMError as e:
                raise Exception(f"Provider {provider.name} failed: {e.message}")
        else:
            # Используем пул провайдеров
            response, provider_used, fallback_count = await self.pool_manager.generate_with_fallback(
                prompt=test_case.prompt,
                model=model_name,
                input_text=test_case.input_text,
                input_images=test_case.input_images,
            )
        
        # Оценка судьёй
        judge_result = await self.judge_service.evaluate(
            judge_prompt=task.judge_prompt,
            test_prompt=test_case.prompt,
            model_response=response.content,
            input_text=test_case.input_text,
            expected_output=test_case.expected_output,
            output_schema=task.output_schema,
            model_name=judge_model,
        )
        
        # Создаём результат
        result = TestResult(
            test_run_id=test_run.id,
            test_case_id=test_case.id,
            provider_used=provider_used,
            model_response=response.content,
            response_time=response.response_time,
            cost=response.cost,
            tokens_used=response.tokens_used,
            fallback_count=fallback_count,
            judge_score=judge_result["score"],
            judge_feedback=judge_result.get("feedback", ""),
            judge_raw_response=judge_result.get("raw_response", "")
        )
        
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        
        return result
