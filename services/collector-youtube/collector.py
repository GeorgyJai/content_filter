"""YouTube content collector with optional transcription."""
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import structlog
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import config
from rabbitmq_publisher import RabbitMQPublisher
from database import VideoTracker

logger = structlog.get_logger()


class YouTubeCollector:
    """Collector for YouTube content with polling and optional transcription."""
    
    def __init__(self):
        """Initialize YouTube collector."""
        self.youtube = build('youtube', config.YOUTUBE_API_VERSION, developerKey=config.YOUTUBE_API_KEY)
        self.publisher = RabbitMQPublisher()
        self.tracker = VideoTracker()
        self.transcriber = None
        
        # Initialize transcriber if enabled
        if config.ENABLE_TRANSCRIPTION:
            try:
                import whisper
                self.transcriber = whisper.load_model(config.WHISPER_MODEL)
                logger.info("whisper_model_loaded", model=config.WHISPER_MODEL)
            except ImportError:
                logger.warning("whisper_not_installed", message="Transcription disabled")
                config.ENABLE_TRANSCRIPTION = False
            except Exception as e:
                logger.error("whisper_load_failed", error=str(e))
                config.ENABLE_TRANSCRIPTION = False
        
        # Create temp directory for downloads
        os.makedirs(config.TEMP_DOWNLOAD_DIR, exist_ok=True)
    
    def get_channel_videos(self, channel_id: str, max_results: int = None) -> List[Dict[str, Any]]:
        """
        Get recent videos from a YouTube channel.
        
        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of videos to retrieve
            
        Returns:
            List of video data dictionaries
        """
        if max_results is None:
            max_results = config.MAX_RESULTS_PER_CHANNEL
        
        try:
            # Search for videos from the channel
            request = self.youtube.search().list(
                part="snippet",
                channelId=channel_id,
                order="date",
                type="video",
                maxResults=max_results
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                video_id = item['id'].get('videoId')
                if video_id:
                    videos.append({
                        'video_id': video_id,
                        'channel_id': channel_id,
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'published_at': item['snippet']['publishedAt'],
                        'channel_title': item['snippet']['channelTitle'],
                        'thumbnail_url': item['snippet']['thumbnails'].get('high', {}).get('url', '')
                    })
            
            logger.info(
                "channel_videos_fetched",
                channel_id=channel_id,
                video_count=len(videos)
            )
            return videos
            
        except HttpError as e:
            logger.error("youtube_api_error", error=str(e), channel_id=channel_id)
            return []
        except Exception as e:
            logger.error("get_channel_videos_failed", error=str(e), channel_id=channel_id)
            return []
    
    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video details dictionary or None
        """
        try:
            request = self.youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                return None
            
            item = response['items'][0]
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            
            return {
                'video_id': video_id,
                'title': snippet['title'],
                'description': snippet['description'],
                'channel_id': snippet['channelId'],
                'channel_title': snippet['channelTitle'],
                'published_at': snippet['publishedAt'],
                'thumbnail_url': snippet['thumbnails'].get('high', {}).get('url', ''),
                'duration': content_details.get('duration', ''),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'tags': snippet.get('tags', [])
            }
            
        except Exception as e:
            logger.error("get_video_details_failed", error=str(e), video_id=video_id)
            return None
    
    def download_audio(self, video_id: str) -> Optional[str]:
        """
        Download audio from YouTube video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Path to downloaded audio file or None
        """
        try:
            import yt_dlp
            
            output_path = os.path.join(config.TEMP_DOWNLOAD_DIR, f"{video_id}.mp3")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(config.TEMP_DOWNLOAD_DIR, f"{video_id}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            
            if os.path.exists(output_path):
                logger.info("audio_downloaded", video_id=video_id, path=output_path)
                return output_path
            else:
                logger.error("audio_file_not_found", video_id=video_id)
                return None
                
        except ImportError:
            logger.error("yt_dlp_not_installed")
            return None
        except Exception as e:
            logger.error("download_audio_failed", error=str(e), video_id=video_id)
            return None
    
    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text or None
        """
        if not self.transcriber:
            return None
        
        try:
            result = self.transcriber.transcribe(
                audio_path,
                language=config.TRANSCRIPTION_LANGUAGE
            )
            transcript = result["text"]
            
            logger.info(
                "audio_transcribed",
                audio_path=audio_path,
                text_length=len(transcript)
            )
            return transcript
            
        except Exception as e:
            logger.error("transcribe_audio_failed", error=str(e), audio_path=audio_path)
            return None
    
    def cleanup_audio(self, audio_path: str) -> None:
        """
        Remove downloaded audio file.
        
        Args:
            audio_path: Path to audio file
        """
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info("audio_cleaned_up", path=audio_path)
        except Exception as e:
            logger.error("cleanup_audio_failed", error=str(e), path=audio_path)
    
    def process_video(self, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a YouTube video and create message for RabbitMQ.
        
        Args:
            video_data: Video data dictionary
            
        Returns:
            Formatted message for RabbitMQ or None
        """
        video_id = video_data['video_id']
        
        # Check if already processed
        if self.tracker.is_processed(video_id):
            logger.info("video_already_processed", video_id=video_id)
            return None
        
        try:
            # Get detailed video information
            details = self.get_video_details(video_id)
            if not details:
                logger.warning("video_details_not_found", video_id=video_id)
                return None
            
            # Prepare content text
            content_text = f"{details['title']}\n\n{details['description']}"
            
            # Optionally transcribe video
            transcript = None
            if config.ENABLE_TRANSCRIPTION:
                logger.info("starting_transcription", video_id=video_id)
                audio_path = self.download_audio(video_id)
                if audio_path:
                    transcript = self.transcribe_audio(audio_path)
                    self.cleanup_audio(audio_path)
                    
                    if transcript:
                        content_text += f"\n\n[Транскрипция]\n{transcript}"
            
            # Create message
            message = {
                "message_type": "raw_content",
                "platform": "youtube",
                "source_id": details['channel_id'],
                "source_url": f"https://www.youtube.com/channel/{details['channel_id']}",
                "content": {
                    "video_id": video_id,
                    "text": content_text,
                    "title": details['title'],
                    "description": details['description'],
                    "transcript": transcript,
                    "author": details['channel_title'],
                    "published_at": details['published_at'],
                    "original_url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail_url": details['thumbnail_url'],
                    "duration": details['duration'],
                    "view_count": details['view_count'],
                    "like_count": details['like_count'],
                    "comment_count": details['comment_count'],
                    "tags": details['tags']
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(
                "video_processed",
                video_id=video_id,
                title=details['title'],
                has_transcript=transcript is not None
            )
            
            return message
            
        except Exception as e:
            logger.error("process_video_failed", error=str(e), video_id=video_id)
            return None
    
    async def poll_channel(self, channel_id: str) -> int:
        """
        Poll a YouTube channel for new videos.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Number of new videos processed
        """
        logger.info("polling_channel", channel_id=channel_id)
        
        # Get recent videos
        videos = self.get_channel_videos(channel_id)
        
        processed_count = 0
        for video_data in videos:
            message = self.process_video(video_data)
            if message:
                # Publish to RabbitMQ
                if self.publisher.publish(message):
                    # Mark as processed
                    self.tracker.mark_processed(
                        video_data['video_id'],
                        channel_id,
                        video_data['title'],
                        video_data['published_at']
                    )
                    processed_count += 1
        
        logger.info(
            "channel_poll_completed",
            channel_id=channel_id,
            processed_count=processed_count
        )
        
        return processed_count
    
    async def poll_channels(self, channel_ids: List[str]) -> None:
        """
        Poll multiple YouTube channels.
        
        Args:
            channel_ids: List of YouTube channel IDs
        """
        logger.info("polling_channels", channel_count=len(channel_ids))
        
        total_processed = 0
        for channel_id in channel_ids:
            try:
                count = await self.poll_channel(channel_id)
                total_processed += count
            except Exception as e:
                logger.error("poll_channel_failed", error=str(e), channel_id=channel_id)
        
        logger.info("polling_completed", total_processed=total_processed)
    
    async def run_polling_loop(self, channel_ids: List[str]) -> None:
        """
        Run continuous polling loop.
        
        Args:
            channel_ids: List of YouTube channel IDs to monitor
        """
        logger.info(
            "starting_polling_loop",
            channel_count=len(channel_ids),
            interval_seconds=config.POLL_INTERVAL_SECONDS
        )
        
        while True:
            try:
                await self.poll_channels(channel_ids)
                logger.info("waiting_for_next_poll", seconds=config.POLL_INTERVAL_SECONDS)
                await asyncio.sleep(config.POLL_INTERVAL_SECONDS)
            except KeyboardInterrupt:
                logger.info("polling_loop_interrupted")
                break
            except Exception as e:
                logger.error("polling_loop_error", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def close(self) -> None:
        """Close all connections."""
        self.publisher.close()
        self.tracker.close()
        logger.info("collector_closed")
