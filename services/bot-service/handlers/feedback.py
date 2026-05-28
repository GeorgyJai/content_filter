"""Feedback handlers for content rating and quality assessment"""
import logging
import json
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from grpc_client import user_service_client
from feedback_client import feedback_service_client

logger = logging.getLogger(__name__)

router = Router()


# ============================================
# Content Feedback Handlers
# ============================================

@router.callback_query(F.data.startswith("feedback_"))
async def process_content_feedback(callback: CallbackQuery):
    """
    Process content feedback (relevant/not_relevant)
    Format: feedback_relevant_123 or feedback_not_relevant_123
    """
    try:
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Неверный формат данных")
            return
        
        reaction = parts[1]  # relevant, not_relevant, saved, hidden
        content_id = int(parts[2])
        user_id = callback.from_user.id
        
        # Validate reaction type
        valid_reactions = ['relevant', 'not_relevant', 'saved', 'hidden']
        if reaction not in valid_reactions:
            await callback.answer("❌ Неверный тип реакции")
            return
        
        # Save feedback via gRPC (we'll need to implement this in user-service or create feedback-service)
        success = await save_feedback(user_id, content_id, reaction)
        
        if success:
            # Update user profile based on feedback
            await update_user_profile_from_feedback(user_id)
            
            # Provide user-friendly response
            reaction_messages = {
                'relevant': "✅ Отмечено как актуальное",
                'not_relevant': "❌ Отмечено как неактуальное",
                'saved': "💾 Сохранено",
                'hidden': "🙈 Скрыто"
            }
            
            await callback.answer(
                f"{reaction_messages.get(reaction, '✅')} Спасибо за обратную связь!"
            )
            
            # Update message to show feedback was recorded
            try:
                # Add checkmark or indicator to the message
                if callback.message.text:
                    updated_text = callback.message.text
                    if "✓" not in updated_text:
                        updated_text += f"\n\n✓ Ваша оценка: {reaction_messages.get(reaction, reaction)}"
                    
                    # Remove feedback buttons after rating
                    await callback.message.edit_text(
                        updated_text,
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.warning(f"Could not update message: {e}")
        else:
            await callback.answer("❌ Не удалось сохранить обратную связь")
            
    except ValueError:
        await callback.answer("❌ Неверный ID контента")
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        await callback.answer("❌ Произошла ошибка")


@router.message(Command("feedback"))
async def cmd_feedback_info(message: Message):
    """Show information about feedback system"""
    text = (
        "📊 <b>Система обратной связи</b>\n\n"
        "Ваши оценки помогают улучшить персонализацию дайджестов!\n\n"
        "<b>Типы оценок:</b>\n"
        "✅ <b>Актуально</b> - контент соответствует вашим интересам\n"
        "❌ <b>Неактуально</b> - контент не интересен\n"
        "💾 <b>Сохранить</b> - отметить для последующего чтения\n"
        "🙈 <b>Скрыть</b> - больше не показывать подобное\n\n"
        "<b>Как это работает:</b>\n"
        "• Система анализирует ваши оценки\n"
        "• Обновляет профиль интересов\n"
        "• Улучшает ранжирование контента\n"
        "• Показывает более релевантные материалы\n\n"
        "Чем больше оценок вы оставите, тем точнее будут дайджесты!"
    )
    
    await message.answer(text, parse_mode="HTML")


# ============================================
# Quality Rating Handlers (Release 3)
# ============================================

@router.callback_query(F.data.startswith("rate_quality_"))
async def process_quality_rating(callback: CallbackQuery):
    """
    Process quality rating for digest
    Format: rate_quality_8_123 (rating_digestId)
    """
    try:
        parts = callback.data.split("_")
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных")
            return
        
        rating = int(parts[2])  # 1-10
        digest_id = int(parts[3])
        user_id = callback.from_user.id
        
        # Validate rating
        if not (1 <= rating <= 10):
            await callback.answer("❌ Оценка должна быть от 1 до 10")
            return
        
        # Save quality rating
        success = await save_quality_rating(user_id, digest_id, rating)
        
        if success:
            # Provide motivational feedback based on rating
            if rating >= 8:
                emoji = "🌸"
                message = "Отлично! Ваш цифровой сад процветает!"
            elif rating >= 5:
                emoji = "🌿"
                message = "Хорошо! Продолжайте в том же духе!"
            else:
                emoji = "🥀"
                message = "Попробуем улучшить качество контента для вас"
            
            await callback.answer(
                f"{emoji} Спасибо! Ваша оценка: {rating}/10\n{message}"
            )
            
            # Update message
            try:
                if callback.message.text:
                    updated_text = callback.message.text
                    updated_text += f"\n\n{emoji} Ваша оценка качества: {rating}/10"
                    
                    await callback.message.edit_text(
                        updated_text,
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.warning(f"Could not update message: {e}")
        else:
            await callback.answer("❌ Не удалось сохранить оценку")
            
    except ValueError:
        await callback.answer("❌ Неверные данные")
    except Exception as e:
        logger.error(f"Error processing quality rating: {e}")
        await callback.answer("❌ Произошла ошибка")


@router.message(Command("garden"))
async def cmd_show_garden(message: Message):
    """Show digital garden (quality visualization)"""
    try:
        user_id = message.from_user.id
        
        # Get quality ratings statistics
        stats = await get_quality_statistics(user_id)
        
        if not stats or stats.get('total_ratings', 0) == 0:
            await message.answer(
                "🌱 <b>Ваш цифровой сад</b>\n\n"
                "Пока здесь пусто. Начните оценивать дайджесты, "
                "чтобы вырастить свой сад!\n\n"
                "Используйте кнопки оценки после получения дайджеста.",
                parse_mode="HTML"
            )
            return
        
        # Build garden visualization
        garden_text = "🌱 <b>Ваш цифровой сад</b>\n\n"
        
        # Overall statistics
        avg_rating = stats.get('average_rating', 0)
        total_ratings = stats.get('total_ratings', 0)
        
        garden_text += f"📊 Всего оценок: {total_ratings}\n"
        garden_text += f"⭐ Средняя оценка: {avg_rating:.1f}/10\n\n"
        
        # Weekly breakdown
        weekly_stats = stats.get('weekly_stats', [])
        if weekly_stats:
            garden_text += "<b>История по неделям:</b>\n"
            for week_data in weekly_stats[-8:]:  # Last 8 weeks
                week_num = week_data.get('week_number', 0)
                week_avg = week_data.get('average_rating', 0)
                
                # Choose plant emoji based on rating
                if week_avg >= 8:
                    plant = "🌸"
                elif week_avg >= 5:
                    plant = "🌿"
                else:
                    plant = "🥀"
                
                garden_text += f"{plant} Неделя {week_num}: {week_avg:.1f}/10\n"
        
        # Motivational message
        garden_text += "\n<b>Совет:</b>\n"
        if avg_rating >= 8:
            garden_text += "🎉 Отличная работа! Ваш сад процветает!"
        elif avg_rating >= 5:
            garden_text += "💪 Хорошо! Продолжайте оценивать контент для лучших результатов."
        else:
            garden_text += "🌱 Давайте улучшим качество! Попробуйте настроить интересы в /settings"
        
        await message.answer(garden_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing garden: {e}")
        await message.answer("❌ Не удалось загрузить ваш сад. Попробуйте позже.")


@router.message(Command("my_feedback"))
async def cmd_my_feedback(message: Message):
    """Show user's feedback history"""
    try:
        user_id = message.from_user.id
        
        # Get feedback statistics
        feedback_stats = await get_feedback_statistics(user_id)
        
        if not feedback_stats:
            await message.answer(
                "📊 <b>Ваша обратная связь</b>\n\n"
                "У вас пока нет оценок контента.\n"
                "Начните оценивать материалы в дайджестах!",
                parse_mode="HTML"
            )
            return
        
        text = "📊 <b>Ваша обратная связь</b>\n\n"
        
        relevant_count = feedback_stats.get('relevant', 0)
        not_relevant_count = feedback_stats.get('not_relevant', 0)
        saved_count = feedback_stats.get('saved', 0)
        hidden_count = feedback_stats.get('hidden', 0)
        total = relevant_count + not_relevant_count + saved_count + hidden_count
        
        if total > 0:
            text += f"<b>Всего оценок:</b> {total}\n\n"
            text += f"✅ Актуально: {relevant_count}\n"
            text += f"❌ Неактуально: {not_relevant_count}\n"
            text += f"💾 Сохранено: {saved_count}\n"
            text += f"🙈 Скрыто: {hidden_count}\n\n"
            
            # Calculate relevance rate
            if relevant_count + not_relevant_count > 0:
                relevance_rate = (relevant_count / (relevant_count + not_relevant_count)) * 100
                text += f"📈 Процент актуального контента: {relevance_rate:.1f}%\n\n"
            
            text += "Ваши оценки помогают улучшить персонализацию!"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing feedback: {e}")
        await message.answer("❌ Не удалось загрузить статистику. Попробуйте позже.")


# ============================================
# Helper Functions
# ============================================

async def save_feedback(user_id: int, content_id: int, reaction: str) -> bool:
    """Save feedback via gRPC"""
    try:
        result = await feedback_service_client.save_feedback(
            user_id=user_id,
            content_id=content_id,
            reaction=reaction
        )
        
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        return False


async def update_user_profile_from_feedback(user_id: int) -> bool:
    """Update user profile based on feedback history"""
    try:
        # This would trigger the ranking service to update user interests
        # based on their feedback history
        # Note: This is a placeholder - actual implementation would call ranking service
        
        logger.info(f"User profile update triggered for user {user_id}")
        
        # TODO: Implement actual gRPC call to ranking service
        # This would fetch recent feedback and call ranking service's UpdateUserInterestsFromFeedback
        return True
        
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        return False


async def save_quality_rating(user_id: int, digest_id: int, rating: int, comment: str = None) -> bool:
    """Save quality rating via gRPC"""
    try:
        result = await feedback_service_client.save_quality_rating(
            user_id=user_id,
            digest_id=digest_id,
            rating=rating,
            comment=comment
        )
        
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"Error saving quality rating: {e}")
        return False


async def get_quality_statistics(user_id: int) -> dict:
    """Get quality rating statistics for user"""
    try:
        stats = await feedback_service_client.get_quality_statistics(user_id=user_id)
        return stats
        
    except Exception as e:
        logger.error(f"Error getting quality statistics: {e}")
        return {}


async def get_feedback_statistics(user_id: int) -> dict:
    """Get feedback statistics for user"""
    try:
        stats = await feedback_service_client.get_feedback_statistics(user_id=user_id)
        return stats if stats else {
            'relevant': 0,
            'not_relevant': 0,
            'saved': 0,
            'hidden': 0
        }
        
        # TODO: Implement actual gRPC call
        return stats
        
    except Exception as e:
        logger.error(f"Error getting feedback statistics: {e}")
        return {}


def create_feedback_keyboard(content_id: int) -> InlineKeyboardMarkup:
    """Create inline keyboard for content feedback"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Актуально",
                callback_data=f"feedback_relevant_{content_id}"
            ),
            InlineKeyboardButton(
                text="❌ Неактуально",
                callback_data=f"feedback_not_relevant_{content_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="💾 Сохранить",
                callback_data=f"feedback_saved_{content_id}"
            ),
            InlineKeyboardButton(
                text="🙈 Скрыть",
                callback_data=f"feedback_hidden_{content_id}"
            )
        ]
    ])
    return keyboard


def create_quality_rating_keyboard(digest_id: int) -> InlineKeyboardMarkup:
    """Create inline keyboard for quality rating"""
    # Create two rows of 5 buttons each (1-5 and 6-10)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=str(i),
                callback_data=f"rate_quality_{i}_{digest_id}"
            ) for i in range(1, 6)
        ],
        [
            InlineKeyboardButton(
                text=str(i),
                callback_data=f"rate_quality_{i}_{digest_id}"
            ) for i in range(6, 11)
        ]
    ])
    return keyboard
