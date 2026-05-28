"""
Модуль для ранжирования контента
"""
import logging
from typing import List, Tuple
import numpy as np

from config import config
from database import db
from embedding_generator import embedding_generator

logger = logging.getLogger(__name__)


class ContentRanker:
    """Класс для ранжирования контента на основе релевантности"""
    
    def rank_content_for_user(
        self, 
        user_id: int, 
        content_ids: List[int], 
        limit: int = None
    ) -> List[Tuple[int, float, int]]:
        """
        Ранжирование контента для пользователя
        
        Args:
            user_id: ID пользователя
            content_ids: Список ID контента для ранжирования
            limit: Максимальное количество результатов
            
        Returns:
            Список кортежей (content_id, relevance_score, rank)
        """
        if not content_ids:
            logger.warning("Empty content_ids list provided")
            return []
        
        try:
            # Получение эмбеддинга интересов пользователя
            user_embedding = db.get_user_interests_embedding(user_id)
            
            if user_embedding is None:
                logger.warning(f"No interests embedding found for user {user_id}")
                # Возвращаем контент без ранжирования
                return [(cid, 0.5, idx + 1) for idx, cid in enumerate(content_ids[:limit])]
            
            # Получение контента
            content_items = db.get_content_by_ids(content_ids)
            
            if not content_items:
                logger.warning(f"No content found for provided IDs")
                return []
            
            # Вычисление релевантности для каждого элемента
            scored_items = []
            for item in content_items:
                if item['embedding'] is not None:
                    relevance = embedding_generator.calculate_cosine_similarity(
                        item['embedding'],
                        user_embedding
                    )
                    scored_items.append((item['content_id'], relevance))
                else:
                    # Контент без эмбеддинга получает низкую оценку
                    scored_items.append((item['content_id'], 0.0))
            
            # Сортировка по релевантности (от большего к меньшему)
            scored_items.sort(key=lambda x: x[1], reverse=True)
            
            # Применение лимита
            if limit:
                scored_items = scored_items[:limit]
            
            # Добавление ранга
            ranked_items = [
                (content_id, score, rank + 1)
                for rank, (content_id, score) in enumerate(scored_items)
            ]
            
            # Обновление оценок релевантности в БД
            for content_id, score, _ in ranked_items:
                db.update_content_relevance_score(content_id, score)
            
            logger.info(f"Ranked {len(ranked_items)} items for user {user_id}")
            return ranked_items
            
        except Exception as e:
            logger.error(f"Error ranking content: {e}")
            return []
    
    def calculate_relevance(
        self, 
        content_embedding: np.ndarray, 
        user_interests_embedding: np.ndarray
    ) -> float:
        """
        Вычисление релевантности контента для пользователя
        
        Args:
            content_embedding: Эмбеддинг контента
            user_interests_embedding: Эмбеддинг интересов пользователя
            
        Returns:
            Оценка релевантности (0-1)
        """
        try:
            similarity = embedding_generator.calculate_cosine_similarity(
                content_embedding,
                user_interests_embedding
            )
            
            # Нормализация в диапазон [0, 1]
            # Косинусное сходство в диапазоне [-1, 1]
            relevance = (similarity + 1) / 2
            
            return float(relevance)
            
        except Exception as e:
            logger.error(f"Error calculating relevance: {e}")
            return 0.5
    
    def find_similar_content(
        self, 
        content_id: int, 
        limit: int = None, 
        min_similarity: float = None
    ) -> List[Tuple[int, float]]:
        """
        Поиск похожего контента
        
        Args:
            content_id: ID контента для поиска похожих
            limit: Максимальное количество результатов
            min_similarity: Минимальная схожесть
            
        Returns:
            Список кортежей (content_id, similarity_score)
        """
        try:
            # Получение эмбеддинга исходного контента
            embedding = db.get_content_embedding(content_id)
            
            if embedding is None:
                logger.warning(f"No embedding found for content {content_id}")
                return []
            
            # Использование значений по умолчанию
            if limit is None:
                limit = config.DEFAULT_LIMIT
            if min_similarity is None:
                min_similarity = config.MIN_SIMILARITY
            
            # Векторный поиск
            similar_items = db.find_similar_content(
                embedding,
                limit=limit + 1,  # +1 чтобы исключить сам элемент
                min_similarity=min_similarity
            )
            
            # Исключение исходного элемента
            similar_items = [
                (cid, score) for cid, score in similar_items 
                if cid != content_id
            ][:limit]
            
            logger.info(f"Found {len(similar_items)} similar items for content {content_id}")
            return similar_items
            
        except Exception as e:
            logger.error(f"Error finding similar content: {e}")
            return []
    
    def update_user_interests_from_feedback(
        self, 
        user_id: int, 
        feedback_items: List[dict]
    ) -> np.ndarray:
        """
        Обновление эмбеддинга интересов пользователя на основе обратной связи
        
        Args:
            user_id: ID пользователя
            feedback_items: Список словарей с обратной связью
                           [{'content_id': int, 'reaction': str, 'embedding': np.ndarray}]
            
        Returns:
            Новый эмбеддинг интересов
        """
        try:
            # Получение текущего эмбеддинга интересов
            current_embedding = db.get_user_interests_embedding(user_id)
            
            if current_embedding is None:
                # Если нет текущего эмбеддинга, создаем на основе обратной связи
                logger.info(f"Creating initial interests embedding for user {user_id}")
                relevant_embeddings = [
                    item['embedding'] for item in feedback_items 
                    if item['reaction'] == 'relevant' and item.get('embedding') is not None
                ]
                
                if relevant_embeddings:
                    current_embedding = np.mean(relevant_embeddings, axis=0)
                else:
                    # Если нет релевантной обратной связи, используем нулевой вектор
                    current_embedding = np.zeros(config.EMBEDDING_DIM)
            
            # Вычисление взвешенного среднего на основе обратной связи
            weighted_sum = current_embedding.copy()
            total_weight = 1.0
            
            for item in feedback_items:
                if item.get('embedding') is None:
                    continue
                
                if item['reaction'] == 'relevant':
                    weight = config.FEEDBACK_WEIGHT * config.RELEVANT_BOOST
                    weighted_sum += weight * item['embedding']
                    total_weight += weight
                elif item['reaction'] == 'not_relevant':
                    weight = config.FEEDBACK_WEIGHT * abs(config.NOT_RELEVANT_PENALTY)
                    weighted_sum -= weight * item['embedding']
                    total_weight += weight
            
            # Нормализация
            new_embedding = weighted_sum / total_weight
            
            # Сохранение нового эмбеддинга
            db.save_user_interests_embedding(user_id, new_embedding)
            
            logger.info(f"Updated interests embedding for user {user_id} based on {len(feedback_items)} feedback items")
            return new_embedding
            
        except Exception as e:
            logger.error(f"Error updating user interests: {e}")
            return current_embedding if current_embedding is not None else np.zeros(config.EMBEDDING_DIM)


# Глобальный экземпляр ранжировщика
ranker = ContentRanker()
