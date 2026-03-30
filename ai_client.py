# ai_client.py
import json
import time
import requests
from typing import List, Tuple, Optional, Dict
from config import VEDAI_API_KEY, VEDAI_BASE_URL, TEMPERATURE, MAX_TOKENS

class OpenAICompatibleClient:
    """
    Универсальный клиент для любых OpenAI-compatible API
    (vedai.by, DeepSeek, OpenAI, Together, и др.)
    """

    def __init__(
        self, 
        api_key: str = None, 
        base_url: str = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None
    ):
        self.api_key = api_key or VEDAI_API_KEY
        self.base_url = base_url or VEDAI_BASE_URL.rstrip('/')
        self.model = model
        self.temperature = temperature if temperature is not None else TEMPERATURE
        self.max_tokens = max_tokens or MAX_TOKENS
        self.max_retries = 3
        self.retry_delay = 2

    def _build_prompt(self, question_text: str, options: List[Tuple[int, str]], is_multiple: bool) -> str:
        """Формирует строгий промт для получения только номеров ответов"""
        answer_type = "выберите ОДИН правильный ответ" if not is_multiple else "выберите ВСЕ правильные ответы"
        options_text = "\n".join([f"{idx}. {text}" for idx, text in options])

        prompt = f"""Ты — медицинский эксперт. Проанализируй вопрос и выбери правильный(е) ответ(ы).

Вопрос: {question_text}

Варианты ответа:
{options_text}

Инструкция: {answer_type}

Требования к ответу:
- Выдай ТОЛЬКО номера правильных ответов через запятую
- Без пробелов, без дополнительного текста, без объяснений
- Например: 1 или 1,3,5

Твой ответ:"""
        return prompt

    def _parse_response(self, response_text: str) -> List[int]:
        """Парсит ответ и извлекает только цифры-индексы"""
        response_text = response_text.strip()
        
        # Извлекаем только цифры и запятые из первой строки
        first_line = response_text.split('\n')[0]
        cleaned = ''.join(c for c in first_line if c.isdigit() or c == ',')
        
        if not cleaned:
            return []
            
        parts = [p.strip() for p in cleaned.split(',') if p.strip()]
        indices = []
        for part in parts:
            if part.isdigit():
                indices.append(int(part))
        return indices

    def get_answer(
        self, 
        question_text: str, 
        options: List[Tuple[int, str]], 
        is_multiple: bool
    ) -> Tuple[bool, List[int], str]:
        """
        Отправляет вопрос и получает ответ
        
        Returns:
            (success: bool, selected_indices: List[int], error_message: str)
        """
        if not self.api_key:
            return False, [], "API ключ не настроен"
        if not self.model:
            return False, [], "Модель не указана"

        prompt = self._build_prompt(question_text, options, is_multiple)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=45
                )

                if response.status_code == 200:
                    data = response.json()
                    ai_response = data['choices'][0]['message']['content']
                    indices = self._parse_response(ai_response)
                    return True, indices, ""
                    
                elif response.status_code == 429:
                    wait_time = self.retry_delay * (attempt + 1)
                    time.sleep(wait_time)
                    continue
                    
                else:
                    error_text = response.text[:300] if response.text else "No content"
                    return False, [], f"HTTP {response.status_code}: {error_text}"

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return False, [], "Таймаут запроса"
                
            except requests.exceptions.ConnectionError:
                return False, [], "Ошибка подключения к API"
                
            except Exception as e:
                return False, [], f"Неизвестная ошибка: {str(e)}"

        return False, [], "Превышено количество попыток"

    def test_connection(self) -> Tuple[bool, str]:
        """Проверяет работоспособность API с текущей моделью"""
        if not self.api_key:
            return False, "API ключ не настроен"
        if not self.model:
            return False, "Модель не указана"

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                },
                timeout=15
            )
            if response.status_code == 200:
                return True, f"✓ {self.model}"
            else:
                return False, f"✗ {self.model}: HTTP {response.status_code}"
        except Exception as e:
            return False, f"✗ {self.model}: {str(e)}"

