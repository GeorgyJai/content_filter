"""VK Callback API webhook handler."""
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import structlog

from config import config
from rabbitmq_publisher import RabbitMQPublisher

logger = structlog.get_logger()


class VKWebhookHandler:
    """Handler for VK Callback API webhooks."""
    
    def __init__(self, publisher: RabbitMQPublisher):
        """
        Initialize webhook handler.
        
        Args:
            publisher: RabbitMQ publisher instance
        """
        self.publisher = publisher
    
    def verify_signature(self, request_body: str, signature: str) -> bool:
        """
        Verify VK request signature.
        
        Args:
            request_body: Raw request body
            signature: Signature from request headers
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not config.VK_SECRET_KEY:
            logger.warning("vk_secret_key_not_configured")
            return True  # Skip verification if secret key not set
        
        expected_signature = hmac.new(
            config.VK_SECRET_KEY.encode('utf-8'),
            request_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def extract_media_urls(self, attachments: List[Dict[str, Any]]) -> List[str]:
        """
        Extract media URLs from post attachments.
        
        Args:
            attachments: List of VK attachments
            
        Returns:
            List of media URLs
        """
        media_urls = []
        
        for attachment in attachments:
            att_type = attachment.get('type')
            
            if att_type == 'photo':
                photo = attachment.get('photo', {})
                # Get largest photo size
                sizes = photo.get('sizes', [])
                if sizes:
                    largest = max(sizes, key=lambda x: x.get('width', 0) * x.get('height', 0))
                    media_urls.append(largest.get('url', ''))
            
            elif att_type == 'video':
                video = attachment.get('video', {})
                # VK doesn't provide direct video URLs in callback
                owner_id = video.get('owner_id')
                video_id = video.get('id')
                if owner_id and video_id:
                    media_urls.append(f"https://vk.com/video{owner_id}_{video_id}")
            
            elif att_type == 'link':
                link = attachment.get('link', {})
                url = link.get('url', '')
                if url:
                    media_urls.append(url)
            
            elif att_type == 'doc':
                doc = attachment.get('doc', {})
                url = doc.get('url', '')
                if url:
                    media_urls.append(url)
        
        return media_urls
    
    def process_wall_post(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process VK wall post and convert to standard format.
        
        Args:
            post: VK wall post object
            
        Returns:
            Formatted message for RabbitMQ or None if processing failed
        """
        try:
            owner_id = post.get('owner_id')
            post_id = post.get('id')
            text = post.get('text', '')
            date = post.get('date', 0)
            from_id = post.get('from_id', owner_id)
            
            # Extract media URLs
            attachments = post.get('attachments', [])
            media_urls = self.extract_media_urls(attachments)
            
            # Get signer info if post is signed
            signer_id = post.get('signer_id')
            
            # Construct post URL
            post_url = f"https://vk.com/wall{owner_id}_{post_id}"
            
            # Format message
            message = {
                "message_type": "raw_content",
                "platform": "vk",
                "source_id": abs(owner_id),  # Convert to positive for community ID
                "source_url": f"https://vk.com/public{abs(owner_id)}" if owner_id < 0 else f"https://vk.com/id{owner_id}",
                "content": {
                    "post_id": f"{owner_id}_{post_id}",
                    "text": text,
                    "author_id": from_id,
                    "signer_id": signer_id,
                    "published_at": datetime.fromtimestamp(date).isoformat(),
                    "media_urls": media_urls,
                    "original_url": post_url,
                    "likes_count": post.get('likes', {}).get('count', 0),
                    "reposts_count": post.get('reposts', {}).get('count', 0),
                    "views_count": post.get('views', {}).get('count', 0),
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(
                "wall_post_processed",
                post_id=f"{owner_id}_{post_id}",
                text_length=len(text),
                media_count=len(media_urls)
            )
            
            return message
            
        except Exception as e:
            logger.error("process_wall_post_failed", error=str(e), post=post)
            return None
    
    async def handle_callback(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle VK Callback API event.
        
        Args:
            data: Callback data from VK
            
        Returns:
            Response for VK
        """
        event_type = data.get('type')
        
        # Handle confirmation
        if event_type == 'confirmation':
            logger.info("confirmation_requested", group_id=data.get('group_id'))
            return {"response": config.VK_CONFIRMATION_TOKEN}
        
        # Handle wall post
        if event_type == 'wall_post_new':
            post = data.get('object')
            if post:
                message = self.process_wall_post(post)
                if message:
                    success = self.publisher.publish(message)
                    if success:
                        logger.info("wall_post_published", post_id=message['content']['post_id'])
                    else:
                        logger.error("wall_post_publish_failed", post_id=message['content']['post_id'])
            
            return {"response": "ok"}
        
        # Handle wall repost
        if event_type == 'wall_repost':
            post = data.get('object')
            if post:
                message = self.process_wall_post(post)
                if message:
                    message['content']['is_repost'] = True
                    success = self.publisher.publish(message)
                    if success:
                        logger.info("wall_repost_published", post_id=message['content']['post_id'])
            
            return {"response": "ok"}
        
        # Log unhandled event types
        logger.info("unhandled_event_type", event_type=event_type)
        return {"response": "ok"}


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="VK Collector Service",
        description="Collects content from VK communities via Callback API",
        version="1.0.0"
    )
    
    # Initialize publisher
    publisher = RabbitMQPublisher()
    handler = VKWebhookHandler(publisher)
    
    @app.post("/vk_callback")
    async def vk_callback(request: Request):
        """
        VK Callback API endpoint.
        
        Receives events from VK communities.
        """
        try:
            # Get request body
            body = await request.body()
            body_str = body.decode('utf-8')
            
            # Verify signature if secret key is configured
            signature = request.headers.get('X-VK-Signature', '')
            if config.VK_SECRET_KEY and not handler.verify_signature(body_str, signature):
                logger.warning("invalid_signature", signature=signature)
                raise HTTPException(status_code=403, detail="Invalid signature")
            
            # Parse JSON
            data = await request.json()
            
            # Handle callback
            response = await handler.handle_callback(data)
            
            return JSONResponse(content=response)
            
        except Exception as e:
            logger.error("callback_handler_error", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "vk-collector"}
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        publisher.close()
    
    return app
