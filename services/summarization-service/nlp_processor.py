"""
NLP Processor для суммаризации, анализа тональности и генерации эмбеддингов
"""

import torch
import numpy as np
from transformers import (
    MBartTokenizer, 
    MBartForConditionalGeneration,
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AutoModel
)
from typing import List, Dict, Tuple, Optional
import structlog
from config import settings

logger = structlog.get_logger()


class NLPProcessor:
    """Обработчик NLP задач: суммаризация, анализ тональности, эмбеддинги"""
    
    def __init__(self):
        """Инициализация моделей"""
        self.device = self._get_device()
        logger.info("nlp_processor_initializing", device=str(self.device))
        
        # Загрузка моделей
        self._load_summarization_model()
        self._load_sentiment_model()
        self._load_embedding_model()
        
        logger.info("nlp_processor_initialized", 
                   summarization_model=settings.summarization_model,
                   sentiment_model=settings.sentiment_model,
                   embedding_model=settings.embedding_model)
    
    def _get_device(self) -> torch.device:
        """Определение устройства для вычислений"""
        if settings.use_gpu and torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")
    
    def _load_summarization_model(self):
        """Загрузка модели суммаризации"""
        try:
            logger.info("loading_summarization_model", model=settings.summarization_model)
            self.summarization_tokenizer = MBartTokenizer.from_pretrained(
                settings.summarization_model,
                cache_dir=settings.model_cache_dir
            )
            self.summarization_model = MBartForConditionalGeneration.from_pretrained(
                settings.summarization_model,
                cache_dir=settings.model_cache_dir
            )
            self.summarization_model.to(self.device)
            self.summarization_model.eval()
            logger.info("summarization_model_loaded")
        except Exception as e:
            logger.error("failed_to_load_summarization_model", error=str(e))
            raise
    
    def _load_sentiment_model(self):
        """Загрузка модели анализа тональности"""
        try:
            logger.info("loading_sentiment_model", model=settings.sentiment_model)
            self.sentiment_tokenizer = AutoTokenizer.from_pretrained(
                settings.sentiment_model,
                cache_dir=settings.model_cache_dir
            )
            self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(
                settings.sentiment_model,
                cache_dir=settings.model_cache_dir
            )
            self.sentiment_model.to(self.device)
            self.sentiment_model.eval()
            
            # Маппинг меток тональности
            self.sentiment_labels = {0: "negative", 1: "neutral", 2: "positive"}
            logger.info("sentiment_model_loaded")
        except Exception as e:
            logger.error("failed_to_load_sentiment_model", error=str(e))
            raise
    
    def _load_embedding_model(self):
        """Загрузка модели для генерации эмбеддингов"""
        try:
            logger.info("loading_embedding_model", model=settings.embedding_model)
            self.embedding_tokenizer = AutoTokenizer.from_pretrained(
                settings.embedding_model,
                cache_dir=settings.model_cache_dir
            )
            self.embedding_model = AutoModel.from_pretrained(
                settings.embedding_model,
                cache_dir=settings.model_cache_dir
            )
            self.embedding_model.to(self.device)
            self.embedding_model.eval()
            logger.info("embedding_model_loaded")
        except Exception as e:
            logger.error("failed_to_load_embedding_model", error=str(e))
            raise
    
    def summarize(
        self, 
        text: str, 
        max_length: Optional[int] = None,
        min_length: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Суммаризация текста
        
        Args:
            text: Текст для суммаризации
            max_length: Максимальная длина резюме (слова)
            min_length: Минимальная длина резюме (слова)
            
        Returns:
            Словарь с резюме и метаданными
        """
        try:
            if not text or len(text.strip()) == 0:
                return {
                    "summary": "",
                    "original_length": 0,
                    "summary_length": 0,
                    "compression_ratio": 0.0,
                    "success": False,
                    "message": "Empty text provided"
                }
            
            # Параметры по умолчанию
            max_length = max_length or settings.default_max_length
            min_length = min_length or settings.default_min_length
            
            # Подсчет слов в оригинале
            original_word_count = len(text.split())
            
            # Если текст слишком короткий, возвращаем его как есть
            if original_word_count <= min_length:
                return {
                    "summary": text,
                    "original_length": original_word_count,
                    "summary_length": original_word_count,
                    "compression_ratio": 1.0,
                    "success": True,
                    "message": "Text too short for summarization"
                }
            
            # Ограничение длины текста
            if original_word_count > settings.max_text_length:
                words = text.split()[:settings.max_text_length]
                text = " ".join(words)
                logger.warning("text_truncated", 
                             original_length=original_word_count,
                             truncated_length=settings.max_text_length)
            
            # Токенизация
            inputs = self.summarization_tokenizer(
                text,
                max_length=1024,
                padding="max_length",
                truncation=True,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Генерация резюме
            with torch.no_grad():
                summary_ids = self.summarization_model.generate(
                    inputs["input_ids"],
                    max_length=max_length,
                    min_length=min_length,
                    num_beams=settings.num_beams,
                    length_penalty=settings.length_penalty,
                    early_stopping=True
                )
            
            # Декодирование
            summary = self.summarization_tokenizer.decode(
                summary_ids[0],
                skip_special_tokens=True
            )
            
            summary_word_count = len(summary.split())
            compression_ratio = summary_word_count / original_word_count if original_word_count > 0 else 0
            
            logger.info("text_summarized",
                       original_length=original_word_count,
                       summary_length=summary_word_count,
                       compression_ratio=round(compression_ratio, 2))
            
            return {
                "summary": summary,
                "original_length": original_word_count,
                "summary_length": summary_word_count,
                "compression_ratio": compression_ratio,
                "success": True,
                "message": "Summarization successful"
            }
            
        except Exception as e:
            logger.error("summarization_failed", error=str(e))
            return {
                "summary": "",
                "original_length": 0,
                "summary_length": 0,
                "compression_ratio": 0.0,
                "success": False,
                "message": f"Summarization error: {str(e)}"
            }
    
    def adaptive_summarize(self, text: str, interest_level: str) -> Dict[str, any]:
        """
        Адаптивная суммаризация с учетом уровня интереса
        
        Args:
            text: Текст для суммаризации
            interest_level: Уровень интереса (very_interested, interested, maybe, not_interested)
            
        Returns:
            Словарь с резюме и метаданными
        """
        # Маппинг уровней интереса на длину резюме
        length_map = {
            "very_interested": settings.very_interested_length,
            "interested": settings.interested_length,
            "maybe": settings.maybe_length,
            "not_interested": settings.not_interested_length
        }
        
        max_length = length_map.get(interest_level, settings.default_max_length)
        min_length = max(10, max_length // 3)  # Минимум - треть от максимума
        
        logger.info("adaptive_summarization",
                   interest_level=interest_level,
                   max_length=max_length)
        
        return self.summarize(text, max_length=max_length, min_length=min_length)
    
    def analyze_sentiment(self, text: str) -> Dict[str, any]:
        """
        Анализ тональности текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            Словарь с результатами анализа тональности
        """
        try:
            if not text or len(text.strip()) == 0:
                return {
                    "sentiment_score": 0.0,
                    "sentiment_label": "neutral",
                    "confidence": 0.0,
                    "success": False,
                    "message": "Empty text provided"
                }
            
            # Токенизация
            inputs = self.sentiment_tokenizer(
                text,
                max_length=512,
                padding=True,
                truncation=True,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Предсказание
            with torch.no_grad():
                outputs = self.sentiment_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # Получение результатов
            confidence, predicted_class = torch.max(predictions, dim=1)
            confidence = confidence.item()
            predicted_class = predicted_class.item()
            
            sentiment_label = self.sentiment_labels.get(predicted_class, "neutral")
            
            # Преобразование в шкалу от -1 до 1
            # negative (0) -> -1, neutral (1) -> 0, positive (2) -> 1
            sentiment_score = (predicted_class - 1) * confidence
            
            logger.info("sentiment_analyzed",
                       sentiment_label=sentiment_label,
                       sentiment_score=round(sentiment_score, 2),
                       confidence=round(confidence, 2))
            
            return {
                "sentiment_score": sentiment_score,
                "sentiment_label": sentiment_label,
                "confidence": confidence,
                "success": True,
                "message": "Sentiment analysis successful"
            }
            
        except Exception as e:
            logger.error("sentiment_analysis_failed", error=str(e))
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "confidence": 0.0,
                "success": False,
                "message": f"Sentiment analysis error: {str(e)}"
            }
    
    def generate_embedding(self, text: str) -> Dict[str, any]:
        """
        Генерация векторного представления текста
        
        Args:
            text: Текст для генерации эмбеддинга
            
        Returns:
            Словарь с эмбеддингом и метаданными
        """
        try:
            if not text or len(text.strip()) == 0:
                return {
                    "embedding": [0.0] * 768,
                    "dimension": 768,
                    "success": False,
                    "message": "Empty text provided"
                }
            
            # Токенизация
            inputs = self.embedding_tokenizer(
                text,
                max_length=512,
                padding=True,
                truncation=True,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Генерация эмбеддинга
            with torch.no_grad():
                outputs = self.embedding_model(**inputs)
            
            # Используем [CLS] токен как представление всего текста
            embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]
            
            # Нормализация
            embedding = embedding / np.linalg.norm(embedding)
            
            logger.info("embedding_generated", dimension=len(embedding))
            
            return {
                "embedding": embedding.tolist(),
                "dimension": len(embedding),
                "success": True,
                "message": "Embedding generation successful"
            }
            
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            return {
                "embedding": [0.0] * 768,
                "dimension": 768,
                "success": False,
                "message": f"Embedding generation error: {str(e)}"
            }
    
    def extract_topics(self, text: str, max_topics: int = 5) -> Dict[str, any]:
        """
        Извлечение ключевых тем из текста (упрощенная версия)
        
        Args:
            text: Текст для анализа
            max_topics: Максимальное количество тем
            
        Returns:
            Словарь с темами и их релевантностью
        """
        try:
            if not text or len(text.strip()) == 0:
                return {
                    "topics": [],
                    "topic_scores": [],
                    "success": False,
                    "message": "Empty text provided"
                }
            
            # Упрощенное извлечение тем через ключевые слова
            # В production версии можно использовать более сложные методы
            # (например, LDA, BERT-based topic modeling)
            
            # Список общих тем для русского языка
            topic_keywords = {
                "технологии": ["технология", "компьютер", "программирование", "AI", "искусственный интеллект", "робот"],
                "политика": ["политика", "правительство", "выборы", "закон", "президент", "парламент"],
                "экономика": ["экономика", "бизнес", "финансы", "рынок", "инвестиции", "деньги"],
                "наука": ["наука", "исследование", "ученый", "открытие", "эксперимент"],
                "спорт": ["спорт", "футбол", "хоккей", "олимпиада", "чемпионат", "команда"],
                "культура": ["культура", "искусство", "музыка", "кино", "театр", "выставка"],
                "здоровье": ["здоровье", "медицина", "врач", "лечение", "болезнь", "вакцина"],
                "образование": ["образование", "школа", "университет", "студент", "учитель", "обучение"]
            }
            
            text_lower = text.lower()
            topic_scores = {}
            
            for topic, keywords in topic_keywords.items():
                score = sum(1 for keyword in keywords if keyword in text_lower)
                if score > 0:
                    topic_scores[topic] = score
            
            # Сортировка по релевантности
            sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[:max_topics]
            
            if not sorted_topics:
                return {
                    "topics": ["общее"],
                    "topic_scores": [1.0],
                    "success": True,
                    "message": "No specific topics detected, using general category"
                }
            
            topics = [topic for topic, _ in sorted_topics]
            max_score = max(score for _, score in sorted_topics)
            scores = [score / max_score for _, score in sorted_topics]
            
            logger.info("topics_extracted", topics=topics, count=len(topics))
            
            return {
                "topics": topics,
                "topic_scores": scores,
                "success": True,
                "message": "Topic extraction successful"
            }
            
        except Exception as e:
            logger.error("topic_extraction_failed", error=str(e))
            return {
                "topics": [],
                "topic_scores": [],
                "success": False,
                "message": f"Topic extraction error: {str(e)}"
            }
    
    def process_content(self, text: str, interest_level: Optional[str] = None) -> Dict[str, any]:
        """
        Полная обработка контента: суммаризация, анализ тональности, эмбеддинги, темы
        
        Args:
            text: Текст для обработки
            interest_level: Уровень интереса для адаптивной суммаризации
            
        Returns:
            Словарь со всеми результатами обработки
        """
        logger.info("processing_content", text_length=len(text), interest_level=interest_level)
        
        # Суммаризация
        if interest_level:
            summary_result = self.adaptive_summarize(text, interest_level)
        else:
            summary_result = self.summarize(text)
        
        # Анализ тональности
        sentiment_result = self.analyze_sentiment(text)
        
        # Генерация эмбеддинга (используем резюме для более компактного представления)
        summary_text = summary_result.get("summary", text)
        embedding_result = self.generate_embedding(summary_text)
        
        # Извлечение тем
        topics_result = self.extract_topics(text)
        
        return {
            "summary": summary_result.get("summary", ""),
            "summary_length": summary_result.get("summary_length", 0),
            "compression_ratio": summary_result.get("compression_ratio", 0.0),
            "sentiment_score": sentiment_result.get("sentiment_score", 0.0),
            "sentiment_label": sentiment_result.get("sentiment_label", "neutral"),
            "embedding": embedding_result.get("embedding", []),
            "topics": topics_result.get("topics", []),
            "topic_scores": topics_result.get("topic_scores", []),
            "success": all([
                summary_result.get("success", False),
                sentiment_result.get("success", False),
                embedding_result.get("success", False),
                topics_result.get("success", False)
            ])
        }
