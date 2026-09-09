from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.providers.base import LLMResponse
from app.services.providers.pool_manager import PoolManager


class JudgeService:
    """Сервис для оценки результатов тестов с помощью LLM-судьи"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.pool_manager = PoolManager(db_session)
    
    async def evaluate(
        self,
        judge_prompt: str,
        test_prompt: str,
        model_response: str,
        input_text: Optional[str] = None,
        expected_output: Optional[str] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        model_name: str = "gpt-4o-mini",  # Модель судьи
        **kwargs
    ) -> Dict[str, Any]:
        """
        Оценка результата теста с помощью LLM-судьи.
        
        Возвращает:
        - score: float (0.0 - 1.0)
        - feedback: str (комментарий судьи)
        - raw_response: str (сырой ответ)
        """
        
        # Формируем промт для судьи
        evaluation_prompt = self._build_judge_prompt(
            judge_prompt=judge_prompt,
            test_prompt=test_prompt,
            model_response=model_response,
            input_text=input_text,
            expected_output=expected_output,
            output_schema=output_schema
        )
        
        try:
            # Вызываем LLM через пул провайдеров
            response, provider_used, fallback_count = await self.pool_manager.generate_with_fallback(
                prompt=evaluation_prompt,
                model=model_name,
                max_tokens=1024,
                temperature=0.3,  # Более детерминированный ответ
                **kwargs
            )
            
            # Парсим оценку из ответа
            score, feedback = self._parse_judge_response(response.content)
            
            return {
                "score": score,
                "feedback": feedback,
                "raw_response": response.content,
                "provider_used": provider_used,
                "response_time": response.response_time,
                "cost": response.cost,
                "tokens_used": response.tokens_used,
            }
            
        except Exception as e:
            return {
                "score": 0.0,
                "feedback": f"Judge evaluation failed: {str(e)}",
                "raw_response": "",
                "error": str(e),
            }
    
    def _build_judge_prompt(
        self,
        judge_prompt: str,
        test_prompt: str,
        model_response: str,
        input_text: Optional[str] = None,
        expected_output: Optional[str] = None,
        output_schema: Optional[Dict[str, Any]] = None
    ) -> str:
        """Построение промта для судьи"""
        
        parts = [
            "You are an expert evaluator of LLM outputs.",
            "",
            "=== TASK DESCRIPTION ===",
            judge_prompt,
            "",
            "=== ORIGINAL PROMPT ===",
            test_prompt,
        ]
        
        if input_text:
            parts.extend([
                "",
                "=== INPUT DATA ===",
                input_text,
            ])
        
        parts.extend([
            "",
            "=== MODEL RESPONSE ===",
            model_response,
        ])
        
        if expected_output:
            parts.extend([
                "",
                "=== EXPECTED OUTPUT (for reference) ===",
                expected_output,
            ])
        
        if output_schema:
            parts.extend([
                "",
                "=== EXPECTED OUTPUT SCHEMA ===",
                str(output_schema),
            ])
        
        parts.extend([
            "",
            "=== EVALUATION INSTRUCTIONS ===",
            "Evaluate the model response based on the criteria above.",
            "Provide a score from 0.0 to 1.0, where:",
            "- 1.0: Perfect response that fully meets all requirements",
            "- 0.7-0.9: Good response with minor issues",
            "- 0.4-0.6: Acceptable but has significant problems",
            "- 0.1-0.3: Poor response with major issues",
            "- 0.0: Completely fails to meet requirements",
            "",
            "Format your response as:",
            "Score: <number between 0.0 and 1.0>",
            "Feedback: <your detailed feedback>",
            "",
            "Your evaluation:",
        ])
        
        return "\n".join(parts)
    
    def _parse_judge_response(self, response_text: str) -> tuple[float, str]:
        """Парсинг ответа судьи для извлечения оценки и комментария"""
        
        score = 0.0
        feedback = ""
        
        lines = response_text.strip().split("\n")
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Ищем строку с оценкой
            if line_lower.startswith("score:"):
                try:
                    score_str = line.split(":")[1].strip()
                    # Извлекаем число из строки
                    import re
                    numbers = re.findall(r"\d+\.?\d*", score_str)
                    if numbers:
                        score = float(numbers[0])
                        score = max(0.0, min(1.0, score))  # Ограничиваем от 0 до 1
                except (ValueError, IndexError):
                    pass
            
            # Ищем строку с комментарием
            elif line_lower.startswith("feedback:"):
                feedback = line.split(":", 1)[1].strip()
                # Если комментарий продолжается на следующих строках
                if i + 1 < len(lines):
                    remaining_lines = []
                    for next_line in lines[i + 1:]:
                        if next_line.lower().strip().startswith("score:"):
                            break
                        remaining_lines.append(next_line)
                    if remaining_lines:
                        feedback += "\n" + "\n".join(remaining_lines)
        
        # Если не нашли явного формата, используем эвристики
        if feedback == "":
            # Предполагаем что весь текст после первой строки это feedback
            feedback = "\n".join(lines[1:]) if len(lines) > 1 else response_text
        
        return score, feedback
