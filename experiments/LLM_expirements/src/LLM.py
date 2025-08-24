# LLM.py
import logging
import ollama

logger = logging.getLogger(__name__)


class LLM:
    """
    Класс для взаимодействия с локальной LLM через Ollama.
    Поддерживает разные модели, параметры генерации и логирование.
    """

    def __init__(self, model="llama3", temperature=0.1, max_tokens=None, keep_alive="5m"):
        """
        :param model: Название модели в Ollama (например, 'llama3', 'mistral', 'qwen')
        :param temperature: Контроль случайности (0.0 = детерминированно, 1.0 = креативно)
        :param max_tokens: Максимальное число токенов в ответе (None = по умолчанию)
        :param keep_alive: Время хранения модели в памяти (чтобы не перезагружать)
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.keep_alive = keep_alive

        self._validate_model()
        logger.info(f"LLM инициализирован: модель='{self.model}', temperature={self.temperature}")

    def _validate_model(self):
        """Проверяем, доступна ли модель в Ollama."""
        try:
            # ollama.list() возвращает объект с полем 'models' → список
            response = ollama.list()
            if "models" not in response:
                raise RuntimeError("Некорректный ответ от Ollama: отсутствует поле 'models'")

            # Извлекаем имена моделей: 'llama3:latest' → 'llama3'
            model_names = []
            for m in response["models"]:
                # Ключ может быть 'name' или 'model' — пробуем оба
                model_full_name = m.get("name") or m.get("model")
                if not model_full_name:
                    continue  # пропускаем, если нет имени
                model_clean = model_full_name.split(":")[0]  # берём имя до тега
                model_names.append(model_clean)

            if self.model not in model_names:
                available = ", ".join(set(model_names))  # уникальные
                raise RuntimeError(
                    f"Модель '{self.model}' не найдена. Доступные: {available}. "
                    f"Установи: ollama run {self.model}"
                )

            logger.info(f"Модель '{self.model}' найдена в Ollama.")

        except Exception as e:
            logger.critical("Ошибка при проверке моделей в Ollama: %s", e)
            raise RuntimeError(f"Не удалось подключиться к Ollama. Убедитесь, что сервис запущен: 'systemctl status ollama'")

    def ask(self, prompt: str) -> str:
        """
        Отправляет промпт в модель и возвращает ответ.

        :param prompt: Текст запроса
        :return: Ответ модели
        """
        logger.debug(f"Отправка промпта к модели '{self.model}' (температура={self.temperature})")
        logger.debug(f"Промпт (первые 200 символов): {prompt[:200]}...")

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
                keep_alive=self.keep_alive,
                stream=False,
            )
            answer = response["response"].strip()
            logger.info("Запрос к LLM успешен")
            return answer

        except Exception as e:
            logger.error("Ошибка при обращении к Ollama: %s", e)
            raise RuntimeError(f"Ошибка LLM: {e}")

    def ask_with_context(self, system_prompt: str, user_prompt: str) -> str:
        """
        Отправляет запрос с системным промптом (контекст) и пользовательским вводом.
        Полезно для точного управления поведением модели.

        :param system_prompt: Инструкция для модели (например, "Ты — юридический ассистент")
        :param user_prompt: Ввод пользователя (текст документа и задача)
        :return: Ответ модели
        """
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return self.ask(full_prompt)
