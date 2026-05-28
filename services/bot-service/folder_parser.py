"""Telegram folder parser using Telethon"""
import logging
import re
from typing import List, Dict, Optional
from telethon import TelegramClient
from telethon.tl.functions.chatlists import GetChatlistUpdatesRequest
from telethon.tl.types import Channel, Chat
from telethon.errors import (
    SessionPasswordNeededError,
    FloodWaitError,
    ChatlistInvalidError,
    InviteHashInvalidError
)
import asyncio

from config import settings

logger = logging.getLogger(__name__)


class TelegramFolderParser:
    """Parser for Telegram folder links to extract channel list"""
    
    def __init__(self):
        self.client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Telethon client"""
        if self._initialized:
            return
        
        try:
            # Check if Telethon credentials are configured
            if not hasattr(settings, 'telegram_api_id') or not settings.telegram_api_id:
                logger.warning("Telegram API credentials not configured for folder parsing")
                return
            
            # Initialize Telegram client for bot
            self.client = TelegramClient(
                'bot_folder_parser',
                settings.telegram_api_id,
                settings.telegram_api_hash
            )
            
            await self.client.start(bot_token=settings.bot_token)
            
            self._initialized = True
            logger.info("Telegram folder parser initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize folder parser: {e}")
            self._initialized = False
    
    def extract_folder_slug(self, folder_link: str) -> Optional[str]:
        """
        Extract folder slug from Telegram folder link
        
        Args:
            folder_link: Telegram folder link (https://t.me/addlist/XXXXX)
            
        Returns:
            Folder slug or None
        """
        pattern = r'https?://t\.me/addlist/([\w-]+)'
        match = re.search(pattern, folder_link)
        
        if match:
            return match.group(1)
        
        return None
    
    async def parse_folder_link(self, folder_link: str) -> List[Dict[str, str]]:
        """
        Parse Telegram folder link and extract channel list
        
        Args:
            folder_link: Telegram folder link
            
        Returns:
            List of channels with their info
        """
        if not self._initialized:
            logger.error("Folder parser not initialized")
            return []
        
        try:
            slug = self.extract_folder_slug(folder_link)
            if not slug:
                logger.error(f"Invalid folder link format: {folder_link}")
                return []
            
            logger.info(f"Parsing folder with slug: {slug}")
            
            # Try to get folder info using the invite link
            # Note: Telegram's folder API is limited, so we'll use an alternative approach
            # We'll try to resolve the link and get the dialogs
            
            channels = await self._parse_folder_alternative(folder_link, slug)
            
            logger.info(f"Parsed {len(channels)} channels from folder")
            return channels
            
        except ChatlistInvalidError:
            logger.error("Invalid chatlist/folder")
            return []
        except InviteHashInvalidError:
            logger.error("Invalid invite hash")
            return []
        except FloodWaitError as e:
            logger.warning(f"Flood wait error: need to wait {e.seconds} seconds")
            return []
        except Exception as e:
            logger.error(f"Error parsing folder link: {e}", exc_info=True)
            return []
    
    async def _parse_folder_alternative(self, folder_link: str, slug: str) -> List[Dict[str, str]]:
        """
        Alternative method to parse folder using invite link resolution
        
        This is a workaround since Telegram's folder API is limited for bots.
        In production, you might need to use a user account or implement
        a different approach.
        
        Args:
            folder_link: Original folder link
            slug: Extracted slug
            
        Returns:
            List of channels
        """
        channels = []
        
        try:
            # For now, we'll return an empty list with a note that this requires
            # a user account or special permissions
            # 
            # In a real implementation, you would:
            # 1. Use a user account (not bot) to access folder links
            # 2. Or implement a web scraping approach
            # 3. Or ask users to manually share the channel list
            
            logger.warning(
                "Folder parsing with bot account has limitations. "
                "Consider using a user account for full functionality."
            )
            
            # Placeholder: In production, implement proper folder parsing
            # This might require:
            # - Using Telethon with user account
            # - Implementing web scraping
            # - Using Telegram's official API if available
            
            return channels
            
        except Exception as e:
            logger.error(f"Error in alternative folder parsing: {e}")
            return []
    
    async def get_channel_info(self, channel_username: str) -> Optional[Dict[str, str]]:
        """
        Get channel information by username
        
        Args:
            channel_username: Channel username (without @)
            
        Returns:
            Channel info dict or None
        """
        if not self._initialized:
            return None
        
        try:
            entity = await self.client.get_entity(channel_username)
            
            if isinstance(entity, Channel):
                return {
                    'title': entity.title,
                    'username': entity.username or '',
                    'url': f"https://t.me/{entity.username}" if entity.username else '',
                    'id': entity.id,
                    'participants_count': getattr(entity, 'participants_count', 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting channel info for {channel_username}: {e}")
            return None
    
    async def parse_channels_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        Parse channel usernames/links from text and get their info
        
        This is a fallback method when folder API is not available.
        Users can manually paste channel list.
        
        Args:
            text: Text containing channel links or usernames
            
        Returns:
            List of channel info dicts
        """
        if not self._initialized:
            return []
        
        channels = []
        
        # Extract channel usernames and links
        # Pattern for @username or https://t.me/username
        patterns = [
            r'@(\w+)',
            r'https?://t\.me/(\w+)'
        ]
        
        usernames = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            usernames.update(matches)
        
        # Get info for each channel
        for username in usernames:
            try:
                info = await self.get_channel_info(username)
                if info:
                    channels.append(info)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error processing channel {username}: {e}")
                continue
        
        return channels
    
    async def shutdown(self):
        """Shutdown the Telethon client"""
        try:
            if self.client and self._initialized:
                await self.client.disconnect()
                self._initialized = False
                logger.info("Folder parser shut down")
        except Exception as e:
            logger.error(f"Error shutting down folder parser: {e}")


# Simplified version that doesn't require Telethon for basic functionality
class SimpleFolderParser:
    """
    Simplified folder parser that extracts channel info from folder links
    without requiring full Telethon integration.
    
    This is a fallback implementation that guides users to manually
    share their channel list.
    """
    
    @staticmethod
    def is_folder_link(text: str) -> bool:
        """Check if text is a folder link"""
        pattern = r'https?://t\.me/addlist/[\w-]+'
        return bool(re.match(pattern, text.strip()))
    
    @staticmethod
    def extract_channels_from_text(text: str) -> List[str]:
        """
        Extract channel URLs from text
        
        Args:
            text: Text containing channel links
            
        Returns:
            List of channel URLs
        """
        channels = []
        
        # Pattern for Telegram channel links
        pattern = r'https://t\.me/(\w+)'
        matches = re.findall(pattern, text)
        
        for match in matches:
            if match and match != 'addlist':  # Exclude folder links
                channels.append(f"https://t.me/{match}")
        
        # Also handle @username format
        username_pattern = r'@(\w+)'
        username_matches = re.findall(username_pattern, text)
        
        for username in username_matches:
            channels.append(f"https://t.me/{username}")
        
        return list(set(channels))  # Remove duplicates
