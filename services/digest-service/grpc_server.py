"""
gRPC сервер для Digest Service
"""

import logging
import grpc
from concurrent import futures
from datetime import datetime

import sys
sys.path.append('/app')
from shared.proto import digest_service_pb2, digest_service_pb2_grpc

from database import db_manager
from digest_generator import digest_generator
from config import config

logger = logging.getLogger(__name__)


class DigestServiceServicer(digest_service_pb2_grpc.DigestServiceServicer):
    """Реализация gRPC сервиса для генерации дайджестов"""
    
    def GenerateDigest(self, request, context):
        """
        Генерация дайджеста для пользователя
        
        Args:
            request: GenerateDigestRequest
            context: gRPC context
            
        Returns:
            DigestResponse
        """
        try:
            user_id = request.user_id
            logger.info(f"Received GenerateDigest request for user_id={user_id}")
            
            # Генерируем дайджест
            digest_data = digest_generator.generate_digest(
                user_id=user_id
            )
            
            if not digest_data:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(f"Failed to generate digest for user {user_id}")
                return digest_service_pb2.DigestResponse()
            
            # Форматируем текст дайджеста
            formatted_text = digest_generator.format_digest_text(digest_data)
            
            # Формируем ответ
            response = digest_service_pb2.DigestResponse(
                digest_id=digest_data.get('digest_id', 0),
                formatted_text=formatted_text
            )
            
            # Добавляем элементы дайджеста
            for item in digest_data.get('items', []):
                digest_item = digest_service_pb2.DigestItem(
                    content_id=item['content_id'],
                    annotation=item['annotation'],
                    rank=digest_data['items'].index(item) + 1,
                    source_name=item.get('source_name', ''),
                    original_url=item.get('original_url', '')
                )
                response.items.append(digest_item)
            
            logger.info(f"Digest generated successfully: digest_id={response.digest_id}, items={len(response.items)}")
            return response
            
        except Exception as e:
            logger.error(f"Error in GenerateDigest: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return digest_service_pb2.DigestResponse()
    
    def GetDigest(self, request, context):
        """
        Получение существующего дайджеста по ID
        
        Args:
            request: GetDigestRequest
            context: gRPC context
            
        Returns:
            DigestResponse
        """
        try:
            digest_id = request.digest_id
            logger.info(f"Received GetDigest request for digest_id={digest_id}")
            
            session = db_manager.get_session()
            digest_data = db_manager.get_digest(session, digest_id)
            session.close()
            
            if not digest_data:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Digest {digest_id} not found")
                return digest_service_pb2.DigestResponse()
            
            # Форматируем текст дайджеста
            formatted_text = digest_generator.format_digest_text(digest_data)
            
            # Формируем ответ
            response = digest_service_pb2.DigestResponse(
                digest_id=digest_data['digest_id'],
                formatted_text=formatted_text
            )
            
            # Добавляем элементы дайджеста
            for item in digest_data.get('items', []):
                digest_item = digest_service_pb2.DigestItem(
                    content_id=item['content_id'],
                    annotation=item['annotation'],
                    rank=item['rank'],
                    source_name=item.get('source_name', ''),
                    original_url=item.get('original_url', '')
                )
                response.items.append(digest_item)
            
            logger.info(f"Digest retrieved successfully: digest_id={digest_id}, items={len(response.items)}")
            return response
            
        except Exception as e:
            logger.error(f"Error in GetDigest: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return digest_service_pb2.DigestResponse()


def serve():
    """Запуск gRPC сервера"""
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=config.GRPC_MAX_WORKERS),
        options=[
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
        ]
    )
    
    digest_service_pb2_grpc.add_DigestServiceServicer_to_server(
        DigestServiceServicer(), server
    )
    
    server_address = f'[::]:{config.GRPC_PORT}'
    server.add_insecure_port(server_address)
    
    logger.info(f"Starting Digest Service gRPC server on {server_address}")
    server.start()
    
    return server


if __name__ == '__main__':
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = serve()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(0)
