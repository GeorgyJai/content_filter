"""Onboarding handlers for new users"""
import logging
import json
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from grpc_client import user_service_client

logger = logging.getLogger(__name__)

router = Router()


class OnboardingStates(StatesGroup):
    """States for onboarding flow"""
    waiting_for_interests = State()
    waiting_for_sources = State()
    waiting_for_schedule = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - begin onboarding"""
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    logger.info(f"New user started bot: {username} (ID: {user_id})")
    
    # Create user in database
    user_data = await user_service_client.create_user(
        username=username,
        platform="telegram"
    )
    
    if user_data:
        # Store internal user_id in FSM context
        await state.update_data(internal_user_id=user_data["user_id"])
        
        welcome_text = (
            "👋 Добро пожаловать в систему персонализированных дайджестов!\n\n"
            "Я помогу вам снизить информационную нагрузку и получать только "
            "самый важный и интересный контент из ваших источников.\n\n"
            "🎯 Что я умею:\n"
            "• Собирать контент из Telegram-каналов\n"
            "• Анализировать и суммировать публикации\n"
            "• Создавать персонализированные дайджесты\n"
            "• Учитывать ваши интересы и предпочтения\n\n"
            "Давайте начнем настройку!\n\n"
            "📝 Шаг 1/3: Опишите своими словами, какие темы вас интересуют.\n"
            "Например: 'технологии, искусственный интеллект, стартапы'"
        )
        
        await message.answer(welcome_text)
        await state.set_state(OnboardingStates.waiting_for_interests)
    else:
        await message.answer(
            "❌ Произошла ошибка при регистрации. Попробуйте позже или обратитесь к администратору."
        )


@router.message(OnboardingStates.waiting_for_interests)
async def process_interests(message: Message, state: FSMContext):
    """Process user interests"""
    interests = message.text.strip()
    
    if len(interests) < 5:
        await message.answer(
            "⚠️ Пожалуйста, опишите ваши интересы более подробно (минимум 5 символов)."
        )
        return
    
    # Get internal user_id from state
    data = await state.get_data()
    internal_user_id = data.get("internal_user_id")
    
    if not internal_user_id:
        await message.answer("❌ Ошибка: пользователь не найден. Начните заново с /start")
        await state.clear()
        return
    
    # Save interests to user profile
    preferences = {
        "interests": interests,
        "digest_interval_hours": 24,  # Default: once per day
        "detail_level": "interested"  # Default detail level
    }
    
    result = await user_service_client.update_preferences(
        user_id=internal_user_id,
        preferences_json=json.dumps(preferences, ensure_ascii=False)
    )
    
    if result:
        await state.update_data(interests=interests)
        
        sources_text = (
            "✅ Отлично! Ваши интересы сохранены.\n\n"
            "📱 Шаг 2/3: Добавьте Telegram-каналы, из которых хотите получать контент.\n\n"
            "Отправьте ссылку на канал или его @username.\n"
            "Например:\n"
            "• https://t.me/channel_name\n"
            "• @channel_name\n\n"
            "💡 Совет: Если у вас есть папка каналов в Telegram, вы можете импортировать "
            "все каналы сразу! Просто отправьте ссылку на папку (https://t.me/addlist/...)\n\n"
            "Вы можете добавить несколько каналов, отправляя их по одному.\n"
            "Когда закончите, нажмите кнопку 'Готово'."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово, перейти к расписанию", callback_data="sources_done")]
        ])
        
        await message.answer(sources_text, reply_markup=keyboard)
        await state.set_state(OnboardingStates.waiting_for_sources)
    else:
        await message.answer(
            "❌ Не удалось сохранить интересы. Попробуйте еще раз."
        )


@router.message(OnboardingStates.waiting_for_sources)
async def process_source(message: Message, state: FSMContext):
    """Process source URL"""
    source_text = message.text.strip()
    
    # Validate source format
    if not (source_text.startswith("https://t.me/") or source_text.startswith("@")):
        await message.answer(
            "⚠️ Пожалуйста, отправьте корректную ссылку на Telegram-канал:\n"
            "• https://t.me/channel_name\n"
            "• @channel_name"
        )
        return
    
    # Normalize URL
    if source_text.startswith("@"):
        source_url = f"https://t.me/{source_text[1:]}"
    else:
        source_url = source_text
    
    # Get internal user_id
    data = await state.get_data()
    internal_user_id = data.get("internal_user_id")
    
    if not internal_user_id:
        await message.answer("❌ Ошибка: пользователь не найден. Начните заново с /start")
        await state.clear()
        return
    
    # Add subscription
    result = await user_service_client.add_subscription(
        user_id=internal_user_id,
        source_url=source_url,
        platform_type="telegram"
    )
    
    if result and result.get("success"):
        # Track added sources count
        sources_count = data.get("sources_count", 0) + 1
        await state.update_data(sources_count=sources_count)
        
        await message.answer(
            f"✅ Канал добавлен! (Всего: {sources_count})\n\n"
            "Отправьте следующий канал или нажмите 'Готово'."
        )
    else:
        error_msg = result.get("message", "Неизвестная ошибка") if result else "Не удалось добавить канал"
        await message.answer(f"❌ {error_msg}")


@router.callback_query(F.data == "sources_done", OnboardingStates.waiting_for_sources)
async def sources_done(callback: CallbackQuery, state: FSMContext):
    """Finish adding sources and move to schedule setup"""
    data = await state.get_data()
    sources_count = data.get("sources_count", 0)
    
    if sources_count == 0:
        await callback.answer("⚠️ Добавьте хотя бы один канал!", show_alert=True)
        return
    
    schedule_text = (
        f"✅ Отлично! Добавлено каналов: {sources_count}\n\n"
        "⏰ Шаг 3/3: Настройте расписание доставки дайджестов.\n\n"
        "Как часто вы хотите получать дайджесты?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌅 Раз в день (утром)", callback_data="schedule_24")],
        [InlineKeyboardButton(text="🌗 Два раза в день", callback_data="schedule_12")],
        [InlineKeyboardButton(text="⏰ Каждые 8 часов", callback_data="schedule_8")],
        [InlineKeyboardButton(text="🔄 Каждые 4 часа", callback_data="schedule_4")]
    ])
    
    await callback.message.edit_text(schedule_text, reply_markup=keyboard)
    await state.set_state(OnboardingStates.waiting_for_schedule)
    await callback.answer()


@router.callback_query(F.data.startswith("schedule_"), OnboardingStates.waiting_for_schedule)
async def process_schedule(callback: CallbackQuery, state: FSMContext):
    """Process schedule selection"""
    interval_hours = int(callback.data.split("_")[1])
    
    # Get internal user_id and current preferences
    data = await state.get_data()
    internal_user_id = data.get("internal_user_id")
    interests = data.get("interests", "")
    
    if not internal_user_id:
        await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
        await state.clear()
        return
    
    # Update preferences with schedule
    preferences = {
        "interests": interests,
        "digest_interval_hours": interval_hours,
        "detail_level": "interested"
    }
    
    result = await user_service_client.update_preferences(
        user_id=internal_user_id,
        preferences_json=json.dumps(preferences, ensure_ascii=False)
    )
    
    if result:
        interval_text = {
            24: "раз в день",
            12: "два раза в день",
            8: "каждые 8 часов",
            4: "каждые 4 часа"
        }.get(interval_hours, f"каждые {interval_hours} часов")
        
        completion_text = (
            "🎉 Настройка завершена!\n\n"
            f"📊 Ваши настройки:\n"
            f"• Интересы: {interests[:100]}{'...' if len(interests) > 100 else ''}\n"
            f"• Источников: {data.get('sources_count', 0)}\n"
            f"• Расписание: {interval_text}\n\n"
            "✨ Система начнет собирать и анализировать контент.\n"
            "Первый дайджест вы получите в соответствии с выбранным расписанием.\n\n"
            "📱 Доступные команды:\n"
            "/settings - изменить настройки\n"
            "/add_source - добавить источник\n"
            "/import_folder - импортировать папку каналов\n"
            "/my_sources - список источников\n"
            "/help - справка"
        )
        
        await callback.message.edit_text(completion_text)
        await state.clear()
        await callback.answer("✅ Настройка завершена!")
        
        logger.info(f"User {internal_user_id} completed onboarding")
    else:
        await callback.answer("❌ Ошибка сохранения настроек", show_alert=True)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help information"""
    help_text = (
        "📖 Справка по командам:\n\n"
        "🔧 Основные команды:\n"
        "/start - начать работу с ботом\n"
        "/settings - изменить настройки\n"
        "/add_source - добавить новый источник\n"
        "/import_folder - импортировать папку каналов\n"
        "/bulk_add - массовое добавление каналов\n"
        "/my_sources - список ваших источников\n"
        "/help - эта справка\n\n"
        "ℹ️ О системе:\n"
        "Бот собирает контент из ваших источников, анализирует его "
        "с помощью искусственного интеллекта и создает персонализированные "
        "дайджесты с самым важным и интересным для вас контентом.\n\n"
        "💡 Система учитывает ваши интересы и обратную связь, "
        "постоянно улучшая качество подборок."
    )
    
    await message.answer(help_text)
