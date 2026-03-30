# ai_client.py
import json
import time
import requests
from typing import List, Tuple, Optional, Dict
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


class DeepSeekClient:
    """Клиент для работы с DeepSeek API"""

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.model = model or DEEPSEEK_MODEL
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.max_retries = 3
        self.retry_delay = 2

    def _build_prompt(self, question_text: str, options: List[Tuple[int, str]], is_multiple: bool) -> str:
        """
        Формирует промт для AI

        Args:
            question_text: текст вопроса
            options: список вариантов (индекс, текст)
            is_multiple: True если несколько правильных ответов

        Returns:
            готовый промт для AI
        """
        # Тип ответа
        answer_type = "выберите ОДИН правильный ответ" if not is_multiple else "выберите ВСЕ правильные ответы"

        # Формируем варианты
        options_text = "\n".join([f"{idx}. {text}" for idx, text in options])

        prompt = f"""Ты — медицинский эксперт. Проанализируй вопрос и выбери правильный(е) ответ(ы).

Вопрос: {question_text}

Варианты ответа:
{options_text}

Инструкция: {answer_type}

Требования к ответу:
- Выдай ТОЛЬКО номера правильных ответов через запятую
- Без пробелов, без дополнительного текста
- Например: 1 или 1,3,5

Твой ответ:"""

        return prompt

    def _parse_response(self, response_text: str) -> List[int]:
        """
        Парсит ответ AI и извлекает номера ответов

        Args:
            response_text: текст ответа от AI

        Returns:
            список индексов выбранных ответов
        """
        # Убираем пробелы и запятые
        response_text = response_text.strip().replace(' ', '')

        # Если есть запятые — разбиваем
        if ',' in response_text:
            parts = response_text.split(',')
        else:
            parts = [response_text]

        # Извлекаем только цифры
        indices = []
        for part in parts:
            # Убираем все нечисловые символы
            digits = ''.join(filter(str.isdigit, part))
            if digits:
                try:
                    indices.append(int(digits))
                except ValueError:
                    pass

        return indices

    def get_answer(self, question_text: str, options: List[Tuple[int, str]], is_multiple: bool) -> Tuple[bool, List[int], str]:
        """
        Отправляет вопрос AI и получает ответ

        Args:
            question_text: текст вопроса
            options: список вариантов (индекс, текст)
            is_multiple: True если несколько правильных ответов

        Returns:
            (успех, список индексов, сообщение об ошибке)
        """
        if not self.api_key:
            return False, [], "API ключ не настроен"

        prompt = self._build_prompt(question_text, options, is_multiple)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 100
        }

        # Повторные попытки при ошибках
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.base_url + "/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    ai_response = data['choices'][0]['message']['content']
                    indices = self._parse_response(ai_response)
                    return True, indices, ""
                elif response.status_code == 429:
                    # Rate limit — ждём и пробуем снова
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    return False, [], error_msg

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return False, [], "Таймаут запроса"
            except Exception as e:
                return False, [], f"Ошибка: {str(e)}"

        return False, [], "Превышено количество попыток"

    def test_connection(self) -> Tuple[bool, str]:
        """
        Проверяет работоспособность API

        Returns:
            (успех, сообщение)
        """
        if not self.api_key:
            return False, "API ключ не настроен"

        try:
            response = requests.post(
                self.base_url + "/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Привет"}],
                    "max_tokens": 10
                },
                timeout=10
            )

            if response.status_code == 200:
                return True, "Подключение успешно"
            else:
                return False, f"Ошибка: HTTP {response.status_code}"

        except Exception as e:
            return False, f"Ошибка: {str(e)}"


def build_prompt(question_text: str, options: List[Tuple[int, str]], is_multiple: bool) -> str:
    """Утилита для формирования промта (если нужно использовать отдельно)"""
    client = DeepSeekClient()
    return client._build_prompt(question_text, options, is_multiple)