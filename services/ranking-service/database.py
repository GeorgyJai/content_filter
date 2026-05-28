"""
Модуль для работы с базой данных
"""
import logging
from typing import List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import numpy as np

from config import config

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с PostgreSQL + pgvector"""
    
    def __init__(self):
        """Инициализация пула подключений"""
        self.pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        logger.info("Database connection pool initialized")
    
    def get_connection(self):
        """Получить соединение из пула"""
        return self.pool.getconn()
    
    def return_connection(self, conn):
        """Вернуть соединение в пул"""
        self.pool.putconn(conn)
    
    def close_all(self):
        """Закрыть все соединения"""
        self.pool.closeall()
        logger.info("All database connections closed")
    
    def get_content_embedding(self, content_id: int) -> Optional[np.ndarray]:
        """
        Получить эмбеддинг контента по ID
        
        Args:
            content_id: ID контента
            
        Returns:
            Numpy array с эмбеддингом или None
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT embedding FROM content_units WHERE content_id = %s",
                    (content_id,)
                )
                result = cur.fetchone()
                if result and result[0]:
                    # Преобразование pgvector в numpy array
                    return np.array(result[0])
                return None
        except Exception as e:
            logger.error(f"Error getting content embedding: {e}")
            return None
        finally:
            self.return_connection(conn)
    
    def save_content_embedding(self, content_id: int, embedding: np.ndarray) -> bool:
        """
        Сохранить эмбеддинг контента
        
        Args:
            content_id: ID контента
            embedding: Векторное представление
            
        Returns:
            True если успешно
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Преобразование numpy array в список для pgvector
                embedding_list = embedding.tolist()
                cur.execute(
                    "UPDATE content_units SET embedding = %s WHERE content_id = %s",
                    (embedding_list, content_id)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving content embedding: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)
    
    def get_user_interests_embedding(self, user_id: int) -> Optional[np.ndarray]:
        """
        Получить эмбеддинг интересов пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Numpy array с эмбеддингом или None
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT preferences->>'interests_embedding' as embedding
                    FROM user_profiles
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
                result = cur.fetchone()
                if result and result[0]:
                    # Преобразование JSON списка в numpy array
                    import json
                    embedding_list = json.loads(result[0])
                    return np.array(embedding_list)
                return None
        except Exception as e:
            logger.error(f"Error getting user interests embedding: {e}")
            return None
        finally:
            self.return_connection(conn)
    
    def save_user_interests_embedding(self, user_id: int, embedding: np.ndarray) -> bool:
        """
        Сохранить эмбеддинг интересов пользователя
        
        Args:
            user_id: ID пользователя
            embedding: Векторное представление интересов
            
        Returns:
            True если успешно
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                import json
                embedding_list = embedding.tolist()
                embedding_json = json.dumps(embedding_list)
                
                cur.execute(
                    """
                    UPDATE user_profiles
                    SET preferences = COALESCE(preferences, '{}'::jsonb) || 
                        jsonb_build_object('interests_embedding', %s::jsonb)
                    WHERE user_id = %s
                    """,
                    (embedding_json, user_id)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving user interests embedding: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)
    
    def get_content_by_ids(self, content_ids: List[int]) -> List[dict]:
        """
        Получить контент по списку ID
        
        Args:
            content_ids: Список ID контента
            
        Returns:
            Список словарей с данными контента
        """
        if not content_ids:
            return []
        
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT content_id, embedding, relevance_score
                    FROM content_units
                    WHERE content_id = ANY(%s)
                    """,
                    (content_ids,)
                )
                results = cur.fetchall()
                # Преобразование embedding в numpy array
                for result in results:
                    if result['embedding']:
                        result['embedding'] = np.array(result['embedding'])
                return results
        except Exception as e:
            logger.error(f"Error getting content by IDs: {e}")
            return []
        finally:
            self.return_connection(conn)
    
    def find_similar_content(
        self, 
        embedding: np.ndarray, 
        limit: int = 10, 
        min_similarity: float = 0.5
    ) -> List[Tuple[int, float]]:
        """
        Найти похожий контент используя векторный поиск
        
        Args:
            embedding: Векторное представление для поиска
            limit: Максимальное количество результатов
            min_similarity: Минимальная схожесть (0-1)
            
        Returns:
            Список кортежей (content_id, similarity_score)
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                embedding_list = embedding.tolist()
                cur.execute(
                    """
                    SELECT content_id, 
                           1 - (embedding <=> %s::vector) as similarity
                    FROM content_units
                    WHERE embedding IS NOT NULL
                      AND 1 - (embedding <=> %s::vector) >= %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding_list, embedding_list, min_similarity, embedding_list, limit)
                )
                results = cur.fetchall()
                return [(row[0], float(row[1])) for row in results]
        except Exception as e:
            logger.error(f"Error finding similar content: {e}")
            return []
        finally:
            self.return_connection(conn)
    
    def get_feedback_for_user(self, user_id: int, limit: int = 100) -> List[dict]:
        """
        Получить последнюю обратную связь пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей
            
        Returns:
            Список словарей с обратной связью
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT f.content_id, f.reaction, c.embedding
                    FROM feedback f
                    JOIN content_units c ON f.content_id = c.content_id
                    WHERE f.user_id = %s AND c.embedding IS NOT NULL
                    ORDER BY f.created_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit)
                )
                results = cur.fetchall()
                # Преобразование embedding в numpy array
                for result in results:
                    if result['embedding']:
                        result['embedding'] = np.array(result['embedding'])
                return results
        except Exception as e:
            logger.error(f"Error getting feedback: {e}")
            return []
        finally:
            self.return_connection(conn)
    
    def update_content_relevance_score(self, content_id: int, score: float) -> bool:
        """
        Обновить оценку релевантности контента
        
        Args:
            content_id: ID контента
            score: Оценка релевантности
            
        Returns:
            True если успешно
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE content_units SET relevance_score = %s WHERE content_id = %s",
                    (score, content_id)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating relevance score: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)


# Глобальный экземпляр базы данных
db = Database()
