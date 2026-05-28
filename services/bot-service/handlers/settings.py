"""Settings and subscription management handlers"""
import logging
import json
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from grpc_client import user_service_client

logger = logging.getLogger(__name__)

router = Router()


class SettingsStates(StatesGroup):
    """States for settings management"""
    waiting_for_new_interests = State()
    waiting_for_new_source = State()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Show settings menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Изменить интересы", callback_data="settings_interests")],
        [InlineKeyboardButton(text="⏰ Изменить расписание", callback_data="settings_schedule")],
        [InlineKeyboardButton(text="📊 Уровень детализации", callback_data="settings_detail")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="settings_close")]
    ])
    
    await message.answer(
        "⚙️ Настройки\n\nВыберите, что хотите изменить:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "settings_interests")
async def settings_interests(callback: CallbackQuery, state: FSMContext):
    """Change interests"""
    await callback.message.edit_text(
        "🎯 Изменение интересов\n\n"
        "Опишите ваши интересы заново.\n"
        "Например: 'технологии, наука, бизнес'"
    )
    await state.set_state(SettingsStates.waiting_for_new_interests)
    await callback.answer()


@router.message(SettingsStates.waiting_for_new_interests)
async def process_new_interests(message: Message, state: FSMContext):
    """Process new interests"""
    interests = message.text.strip()
    
    if len(interests) < 5:
        await message.answer("⚠️ Опишите интересы более подробно (минимум 5 символов).")
        return
    
    # Get user profile to preserve other settings
    user_id = message.from_user.id
    # Note: In production, we'd need to map telegram user_id to internal user_id
    # For now, assuming they match or we have a mapping
    
    profile = await user_service_client.get_user_profile(user_id)
    
    if profile:
        # Parse existing preferences
        try:
            preferences = json.loads(profile.get("preferences_json", "{}"))
        except json.JSONDecodeError:
            preferences = {}
        
        # Update interests
        preferences["interests"] = interests
        
        result = await user_service_client.update_preferences(
            user_id=user_id,
            preferences_json=json.dumps(preferences, ensure_ascii=False)
        )
        
        if result:
            await message.answer(
                f"✅ Интересы обновлены!\n\n"
                f"Новые интересы: {interests}"
            )
            await state.clear()
        else:
            await message.answer("❌ Не удалось обновить интересы. Попробуйте позже.")
    else:
        await message.answer(
            "❌ Профиль не найден. Пожалуйста, начните с команды /start"
        )
        await state.clear()


@router.callback_query(F.data == "settings_schedule")
async def settings_schedule(callback: CallbackQuery):
    """Change schedule"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌅 Раз в день", callback_data="set_schedule_24")],
        [InlineKeyboardButton(text="🌗 Два раза в день", callback_data="set_schedule_12")],
        [InlineKeyboardButton(text="⏰ Каждые 8 часов", callback_data="set_schedule_8")],
        [InlineKeyboardButton(text="🔄 Каждые 4 часа", callback_data="set_schedule_4")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_back")]
    ])
    
    await callback.message.edit_text(
        "⏰ Изменение расписания\n\n"
        "Как часто вы хотите получать дайджесты?",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_schedule_"))
async def process_schedule_change(callback: CallbackQuery):
    """Process schedule change"""
    interval_hours = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Get current profile
    profile = await user_service_client.get_user_profile(user_id)
    
    if profile:
        try:
            preferences = json.loads(profile.get("preferences_json", "{}"))
        except json.JSONDecodeError:
            preferences = {}
        
        preferences["digest_interval_hours"] = interval_hours
        
        result = await user_service_client.update_preferences(
            user_id=user_id,
            preferences_json=json.dumps(preferences, ensure_ascii=False)
        )
        
        if result:
            interval_text = {
                24: "раз в день",
                12: "два раза в день",
                8: "каждые 8 часов",
                4: "каждые 4 часа"
            }.get(interval_hours, f"каждые {interval_hours} часов")
            
            await callback.message.edit_text(
                f"✅ Расписание обновлено!\n\n"
                f"Новое расписание: {interval_text}"
            )
            await callback.answer("✅ Сохранено!")
        else:
            await callback.answer("❌ Ошибка сохранения", show_alert=True)
    else:
        await callback.answer("❌ Профиль не найден", show_alert=True)


@router.callback_query(F.data == "settings_detail")
async def settings_detail(callback: CallbackQuery):
    """Change detail level"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Подробно", callback_data="set_detail_very_interested")],
        [InlineKeyboardButton(text="📄 Средне", callback_data="set_detail_interested")],
        [InlineKeyboardButton(text="📝 Кратко", callback_data="set_detail_maybe")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_back")]
    ])
    
    await callback.message.edit_text(
        "📊 Уровень детализации\n\n"
        "Выберите, насколько подробными должны быть резюме публикаций:\n\n"
        "📖 Подробно - полное описание (200-300 слов)\n"
        "📄 Средне - основные моменты (100-150 слов)\n"
        "📝 Кратко - только суть (50-100 слов)",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_detail_"))
async def process_detail_change(callback: CallbackQuery):
    """Process detail level change"""
    detail_level = callback.data.split("set_detail_")[1]
    user_id = callback.from_user.id
    
    profile = await user_service_client.get_user_profile(user_id)
    
    if profile:
        try:
            preferences = json.loads(profile.get("preferences_json", "{}"))
        except json.JSONDecodeError:
            preferences = {}
        
        preferences["detail_level"] = detail_level
        
        result = await user_service_client.update_preferences(
            user_id=user_id,
            preferences_json=json.dumps(preferences, ensure_ascii=False)
        )
        
        if result:
            detail_text = {
                "very_interested": "Подробно",
                "interested": "Средне",
                "maybe": "Кратко"
            }.get(detail_level, detail_level)
            
            await callback.message.edit_text(
                f"✅ Уровень детализации обновлен!\n\n"
                f"Новый уровень: {detail_text}"
            )
            await callback.answer("✅ Сохранено!")
        else:
            await callback.answer("❌ Ошибка сохранения", show_alert=True)
    else:
        await callback.answer("❌ Профиль не найден", show_alert=True)


@router.callback_query(F.data == "settings_back")
async def settings_back(callback: CallbackQuery):
    """Return to settings menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Изменить интересы", callback_data="settings_interests")],
        [InlineKeyboardButton(text="⏰ Изменить расписание", callback_data="settings_schedule")],
        [InlineKeyboardButton(text="📊 Уровень детализации", callback_data="settings_detail")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="settings_close")]
    ])
    
    await callback.message.edit_text(
        "⚙️ Настройки\n\nВыберите, что хотите изменить:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "settings_close")
async def settings_close(callback: CallbackQuery):
    """Close settings menu"""
    await callback.message.delete()
    await callback.answer()


@router.message(Command("add_source"))
async def cmd_add_source(message: Message, state: FSMContext):
    """Add new source"""
    await message.answer(
        "📱 Добавление нового источника\n\n"
        "Отправьте ссылку на Telegram-канал:\n"
        "• https://t.me/channel_name\n"
        "• @channel_name"
    )
    await state.set_state(SettingsStates.waiting_for_new_source)


@router.message(SettingsStates.waiting_for_new_source)
async def process_add_source(message: Message, state: FSMContext):
    """Process new source addition"""
    source_text = message.text.strip()
    
    if not (source_text.startswith("https://t.me/") or source_text.startswith("@")):
        await message.answer(
            "⚠️ Пожалуйста, отправьте корректную ссылку на Telegram-канал"
        )
        return
    
    # Normalize URL
    if source_text.startswith("@"):
        source_url = f"https://t.me/{source_text[1:]}"
    else:
        source_url = source_text
    
    user_id = message.from_user.id
    
    result = await user_service_client.add_subscription(
        user_id=user_id,
        source_url=source_url,
        platform_type="telegram"
    )
    
    if result and result.get("success"):
        await message.answer(
            f"✅ Источник добавлен!\n\n"
            f"URL: {source_url}\n\n"
            "Контент из этого канала будет включен в следующий дайджест."
        )
        await state.clear()
    else:
        error_msg = result.get("message", "Неизвестная ошибка") if result else "Не удалось добавить источник"
        await message.answer(f"❌ {error_msg}")


@router.message(Command("my_sources"))
async def cmd_my_sources(message: Message):
    """Show user's sources"""
    user_id = message.from_user.id
    
    subscriptions = await user_service_client.get_subscriptions(user_id)
    
    if not subscriptions:
        await message.answer(
            "📭 У вас пока нет добавленных источников.\n\n"
            "Используйте /add_source для добавления."
        )
        return
    
    sources_text = "📚 Ваши источники:\n\n"
    
    for i, sub in enumerate(subscriptions, 1):
        platform_emoji = {
            "telegram": "📱",
            "vk": "🔵",
            "youtube": "📺"
        }.get(sub["platform_type"], "📄")
        
        sources_text += f"{i}. {platform_emoji} {sub['source_url']}\n"
    
    sources_text += f"\n📊 Всего источников: {len(subscriptions)}"
    
    await message.answer(sources_text)
