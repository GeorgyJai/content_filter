"""Bulk import handlers for Telegram channel folders"""
import logging
import re
import asyncio
from typing import List, Dict, Optional
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from grpc_client import user_service_client
from folder_parser import TelegramFolderParser

logger = logging.getLogger(__name__)

router = Router()


async def get_internal_user_id(telegram_user_id: int) -> Optional[int]:
    """
    Get internal user_id from telegram user_id
    
    Args:
        telegram_user_id: Telegram user ID
        
    Returns:
        Internal user_id or None
    """
    try:
        # Try to get user profile which will return user_id
        user_data = await user_service_client.get_user_by_telegram_id(telegram_user_id)
        if user_data:
            return user_data.get("user_id")
        return None
    except Exception as e:
        logger.error(f"Failed to get internal user_id: {e}")
        return None


def is_folder_link(text: str) -> bool:
    """
    Check if text is a Telegram folder link
    
    Args:
        text: Text to check
        
    Returns:
        True if text is a folder link
    """
    # Telegram folder links format: https://t.me/addlist/XXXXX
    folder_pattern = r'https?://t\.me/addlist/[\w-]+'
    return bool(re.match(folder_pattern, text.strip()))


@router.message(Command("import_folder"))
async def cmd_import_folder(message: Message):
    """Handle /import_folder command"""
    help_text = (
        "📁 Импорт папки каналов\n\n"
        "Эта функция позволяет быстро добавить все каналы из папки Telegram.\n\n"
        "📝 Как использовать:\n"
        "1. Откройте папку каналов в Telegram\n"
        "2. Нажмите на название папки → 'Поделиться папкой'\n"
        "3. Скопируйте ссылку (формат: https://t.me/addlist/...)\n"
        "4. Отправьте ссылку мне\n\n"
        "💡 Все каналы из папки будут автоматически добавлены в ваши источники!"
    )
    
    await message.answer(help_text)


@router.message(F.text.regexp(r'https?://t\.me/addlist/[\w-]+'))
async def process_folder_link(message: Message, state: FSMContext):
    """Process Telegram folder link"""
    folder_link = message.text.strip()
    
    logger.info(f"Processing folder link from user {message.from_user.id}: {folder_link}")
    
    # Send processing message
    processing_msg = await message.answer(
        "⏳ Обрабатываю ссылку на папку...\n"
        "Это может занять несколько секунд."
    )
    
    try:
        # Get internal user_id
        internal_user_id = await get_internal_user_id(message.from_user.id)
        
        if not internal_user_id:
            # Try to get from FSM state
            data = await state.get_data()
            internal_user_id = data.get("internal_user_id")
        
        if not internal_user_id:
            await processing_msg.edit_text(
                "❌ Ошибка: пользователь не найден в системе.\n"
                "Пожалуйста, начните с команды /start"
            )
            return
        
        # Parse folder and get channels
        parser = TelegramFolderParser()
        await parser.initialize()
        
        try:
            channels = await parser.parse_folder_link(folder_link)
            
            if not channels:
                await processing_msg.edit_text(
                    "❌ Не удалось получить список каналов из папки.\n\n"
                    "Возможные причины:\n"
                    "• Ссылка недействительна или устарела\n"
                    "• Папка пустая\n"
                    "• Нет доступа к папке\n\n"
                    "Попробуйте создать новую ссылку на папку."
                )
                return
            
            # Update processing message
            await processing_msg.edit_text(
                f"📋 Найдено каналов: {len(channels)}\n"
                f"⏳ Добавляю в ваши источники..."
            )
            
            # Add channels to user subscriptions
            added_count = 0
            failed_count = 0
            failed_channels = []
            
            for channel in channels:
                try:
                    result = await user_service_client.add_subscription(
                        user_id=internal_user_id,
                        source_url=channel['url'],
                        platform_type='telegram'
                    )
                    
                    if result and result.get("success"):
                        added_count += 1
                    else:
                        failed_count += 1
                        failed_channels.append(channel['title'])
                    
                    # Small delay to avoid overwhelming the service
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to add channel {channel['url']}: {e}")
                    failed_count += 1
                    failed_channels.append(channel['title'])
            
            # Prepare result message
            result_text = f"✅ Импорт завершен!\n\n"
            result_text += f"📊 Статистика:\n"
            result_text += f"• Всего каналов: {len(channels)}\n"
            result_text += f"• Успешно добавлено: {added_count}\n"
            
            if failed_count > 0:
                result_text += f"• Не удалось добавить: {failed_count}\n\n"
                
                if failed_channels:
                    result_text += "❌ Не добавлены:\n"
                    for title in failed_channels[:5]:  # Show first 5
                        result_text += f"• {title}\n"
                    
                    if len(failed_channels) > 5:
                        result_text += f"• ... и еще {len(failed_channels) - 5}\n"
            
            result_text += f"\n💡 Используйте /my_sources для просмотра всех источников"
            
            await processing_msg.edit_text(result_text)
            
            logger.info(
                f"Folder import completed for user {internal_user_id}: "
                f"{added_count} added, {failed_count} failed"
            )
            
        finally:
            await parser.shutdown()
    
    except Exception as e:
        logger.error(f"Error processing folder link: {e}", exc_info=True)
        await processing_msg.edit_text(
            "❌ Произошла ошибка при обработке папки.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )


@router.message(Command("bulk_add"))
async def cmd_bulk_add(message: Message):
    """Handle /bulk_add command - alternative way to add multiple channels"""
    help_text = (
        "📝 Массовое добавление каналов\n\n"
        "Вы можете добавить несколько каналов одновременно.\n\n"
        "Отправьте список каналов (по одному на строку):\n"
        "```\n"
        "https://t.me/channel1\n"
        "@channel2\n"
        "https://t.me/channel3\n"
        "```\n\n"
        "💡 Или используйте /import_folder для импорта целой папки!"
    )
    
    await message.answer(help_text, parse_mode="Markdown")


@router.message(F.text.contains("\n") & F.text.regexp(r'(https?://t\.me/|@)\w+'))
async def process_bulk_channels(message: Message, state: FSMContext):
    """Process multiple channel links sent as a list"""
    lines = message.text.strip().split('\n')
    
    # Filter valid channel links
    channels = []
    for line in lines:
        line = line.strip()
        if line.startswith('https://t.me/') or line.startswith('@'):
            # Skip folder links
            if '/addlist/' not in line:
                channels.append(line)
    
    if not channels:
        await message.answer(
            "⚠️ Не найдено корректных ссылок на каналы.\n"
            "Используйте формат:\n"
            "• https://t.me/channel_name\n"
            "• @channel_name"
        )
        return
    
    if len(channels) > 50:
        await message.answer(
            "⚠️ Слишком много каналов за раз (максимум 50).\n"
            "Пожалуйста, разделите на несколько сообщений."
        )
        return
    
    # Get internal user_id
    data = await state.get_data()
    internal_user_id = data.get("internal_user_id")
    
    if not internal_user_id:
        internal_user_id = await get_internal_user_id(message.from_user.id)
    
    if not internal_user_id:
        await message.answer(
            "❌ Ошибка: пользователь не найден в системе.\n"
            "Пожалуйста, начните с команды /start"
        )
        return
    
    # Send processing message
    processing_msg = await message.answer(
        f"⏳ Добавляю {len(channels)} каналов...\n"
        "Это может занять некоторое время."
    )
    
    # Add channels
    added_count = 0
    failed_count = 0
    
    for channel_text in channels:
        try:
            # Normalize URL
            if channel_text.startswith('@'):
                source_url = f"https://t.me/{channel_text[1:]}"
            else:
                source_url = channel_text
            
            result = await user_service_client.add_subscription(
                user_id=internal_user_id,
                source_url=source_url,
                platform_type='telegram'
            )
            
            if result and result.get("success"):
                added_count += 1
            else:
                failed_count += 1
            
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Failed to add channel {channel_text}: {e}")
            failed_count += 1
    
    # Send result
    result_text = (
        f"✅ Обработка завершена!\n\n"
        f"📊 Результат:\n"
        f"• Успешно добавлено: {added_count}\n"
        f"• Не удалось добавить: {failed_count}\n\n"
        f"💡 Используйте /my_sources для просмотра всех источников"
    )
    
    await processing_msg.edit_text(result_text)
    
    logger.info(
        f"Bulk add completed for user {internal_user_id}: "
        f"{added_count} added, {failed_count} failed"
    )
