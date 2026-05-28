"""
gRPC сервер для Ranking Service
"""
import logging
import sys
import os
from concurrent import futures
import grpc
import numpy as np

# Добавление пути к proto файлам
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared/proto'))

import ranking_service_pb2
import ranking_service_pb2_grpc

from embedding_generator import embedding_generator
from ranker import ranker
from database import db
from config import config

logger = logging.getLogger(__name__)


class RankingServiceServicer(ranking_service_pb2_grpc.RankingServiceServicer):
    """Реализация gRPC сервиса ранжирования"""
    
    def GenerateEmbedding(self, request, context):
        """Генерация эмбеддинга для текста"""
        try:
            logger.info(f"Generating embedding for text (length: {len(request.text)})")
            
            embedding = embedding_generator.generate_embedding(request.text)
            
            return ranking_service_pb2.EmbeddingResponse(
                embedding=embedding.tolist(),
                success=True,
                message="Embedding generated successfully"
            )
        except Exception as e:
            logger.error(f"Error in GenerateEmbedding: {e}")
            return ranking_service_pb2.EmbeddingResponse(
                embedding=[],
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def GenerateBatchEmbeddings(self, request, context):
        """Генерация эмбеддингов для списка текстов"""
        try:
            logger.info(f"Generating batch embeddings for {len(request.texts)} texts")
            
            embeddings = embedding_generator.generate_batch_embeddings(list(request.texts))
            
            embedding_vectors = [
                ranking_service_pb2.EmbeddingVector(values=emb.tolist())
                for emb in embeddings
            ]
            
            return ranking_service_pb2.BatchEmbeddingsResponse(
                embeddings=embedding_vectors,
                success=True,
                message=f"Generated {len(embeddings)} embeddings"
            )
        except Exception as e:
            logger.error(f"Error in GenerateBatchEmbeddings: {e}")
            return ranking_service_pb2.BatchEmbeddingsResponse(
                embeddings=[],
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def RankContentForUser(self, request, context):
        """Ранжирование контента для пользователя"""
        try:
            logger.info(f"Ranking content for user {request.user_id}, {len(request.content_ids)} items")
            
            limit = request.limit if request.limit > 0 else None
            
            ranked_items = ranker.rank_content_for_user(
                user_id=request.user_id,
                content_ids=list(request.content_ids),
                limit=limit
            )
            
            ranked_content = [
                ranking_service_pb2.RankedContent(
                    content_id=content_id,
                    relevance_score=score,
                    rank=rank
                )
                for content_id, score, rank in ranked_items
            ]
            
            return ranking_service_pb2.RankedContentResponse(
                items=ranked_content,
                success=True,
                message=f"Ranked {len(ranked_content)} items"
            )
        except Exception as e:
            logger.error(f"Error in RankContentForUser: {e}")
            return ranking_service_pb2.RankedContentResponse(
                items=[],
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def CalculateRelevance(self, request, context):
        """Вычисление релевантности между эмбеддингами"""
        try:
            content_embedding = np.array(request.content_embedding)
            user_interests_embedding = np.array(request.user_interests_embedding)
            
            relevance = ranker.calculate_relevance(
                content_embedding,
                user_interests_embedding
            )
            
            return ranking_service_pb2.RelevanceResponse(
                relevance_score=relevance,
                success=True,
                message="Relevance calculated successfully"
            )
        except Exception as e:
            logger.error(f"Error in CalculateRelevance: {e}")
            return ranking_service_pb2.RelevanceResponse(
                relevance_score=0.0,
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def FindSimilarContent(self, request, context):
        """Поиск похожего контента"""
        try:
            logger.info(f"Finding similar content for content_id {request.content_id}")
            
            limit = request.limit if request.limit > 0 else config.DEFAULT_LIMIT
            min_similarity = request.min_similarity if request.min_similarity > 0 else config.MIN_SIMILARITY
            
            similar_items = ranker.find_similar_content(
                content_id=request.content_id,
                limit=limit,
                min_similarity=min_similarity
            )
            
            similar_content = [
                ranking_service_pb2.SimilarContent(
                    content_id=content_id,
                    similarity_score=score
                )
                for content_id, score in similar_items
            ]
            
            return ranking_service_pb2.SimilarContentResponse(
                items=similar_content,
                success=True,
                message=f"Found {len(similar_content)} similar items"
            )
        except Exception as e:
            logger.error(f"Error in FindSimilarContent: {e}")
            return ranking_service_pb2.SimilarContentResponse(
                items=[],
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def UpdateUserInterestsFromFeedback(self, request, context):
        """Обновление интересов пользователя на основе обратной связи"""
        try:
            logger.info(f"Updating interests for user {request.user_id} with {len(request.feedback_items)} feedback items")
            
            # Преобразование feedback items
            feedback_items = []
            for item in request.feedback_items:
                feedback_dict = {
                    'content_id': item.content_id,
                    'reaction': item.reaction,
                    'embedding': np.array(item.content_embedding) if item.content_embedding else None
                }
                feedback_items.append(feedback_dict)
            
            new_embedding = ranker.update_user_interests_from_feedback(
                user_id=request.user_id,
                feedback_items=feedback_items
            )
            
            return ranking_service_pb2.UpdateInterestsResponse(
                new_interests_embedding=new_embedding.tolist(),
                success=True,
                message="User interests updated successfully"
            )
        except Exception as e:
            logger.error(f"Error in UpdateUserInterestsFromFeedback: {e}")
            return ranking_service_pb2.UpdateInterestsResponse(
                new_interests_embedding=[],
                success=False,
                message=f"Error: {str(e)}"
            )


def serve():
    """Запуск gRPC сервера"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ranking_service_pb2_grpc.add_RankingServiceServicer_to_server(
        RankingServiceServicer(), server
    )
    
    server.add_insecure_port(f'[::]:{config.GRPC_PORT}')
    server.start()
    
    logger.info(f"Ranking Service gRPC server started on port {config.GRPC_PORT}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(0)
        db.close_all()
