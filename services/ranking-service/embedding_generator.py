"""
Модуль для генерации векторных представлений (embeddings)
"""
import logging
from typing import List
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

from config import config

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Класс для генерации эмбеддингов с использованием BERT"""
    
    def __init__(self):
        """Инициализация модели и токенизатора"""
        logger.info(f"Loading model: {config.MODEL_NAME}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
            self.model = AutoModel.from_pretrained(config.MODEL_NAME)
            
            # Перевод модели в режим оценки
            self.model.eval()
            
            # Использование GPU если доступен
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            
            logger.info(f"Model loaded successfully on device: {self.device}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Генерация эмбеддинга для текста
        
        Args:
            text: Входной текст
            
        Returns:
            Numpy array размерности (768,)
        """
        if not text or not text.strip():
            logger.warning("Empty text provided, returning zero vector")
            return np.zeros(config.EMBEDDING_DIM)
        
        try:
            # Токенизация
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=config.MAX_LENGTH,
                truncation=True,
                padding=True
            )
            
            # Перенос на устройство
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Генерация эмбеддинга
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Используем [CLS] токен как представление всего текста
            embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return np.zeros(config.EMBEDDING_DIM)
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Генерация эмбеддингов для списка текстов (батч-обработка)
        
        Args:
            texts: Список текстов
            
        Returns:
            Список numpy arrays
        """
        if not texts:
            return []
        
        try:
            # Токенизация батча
            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                max_length=config.MAX_LENGTH,
                truncation=True,
                padding=True
            )
            
            # Перенос на устройство
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Генерация эмбеддингов
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Извлечение [CLS] токенов для всех текстов
            embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            
            return [embedding for embedding in embeddings]
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [np.zeros(config.EMBEDDING_DIM) for _ in texts]
    
    def calculate_cosine_similarity(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray
    ) -> float:
        """
        Вычисление косинусного сходства между двумя эмбеддингами
        
        Args:
            embedding1: Первый эмбеддинг
            embedding2: Второй эмбеддинг
            
        Returns:
            Косинусное сходство (от -1 до 1)
        """
        try:
            # Нормализация векторов
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Косинусное сходство
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0


# Глобальный экземпляр генератора эмбеддингов
embedding_generator = EmbeddingGenerator()
