#!/usr/bin/env python3
"""
Telegram бот для управления Transmission через Docker
"""
import os
import logging
import asyncio
from io import BytesIO
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from transmission_client import TransmissionClient

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

# ID разрешенного пользователя
ALLOWED_USER_ID = 800891816

# Инициализация клиента Transmission
transmission = TransmissionClient(
    host=os.getenv('TRANSMISSION_HOST', '192.168.1.1'),
    port=int(os.getenv('TRANSMISSION_PORT', '8190')),
    username=os.getenv('TRANSMISSION_USERNAME', 'torr'),
    password=os.getenv('TRANSMISSION_PASSWORD', 'h3YTeVcPfyx5NXH'),
    path=os.getenv('TRANSMISSION_PATH', '/transmission/rpc')
)


def format_size(size_bytes):
    """Форматирует размер в байтах в читаемый формат"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_speed(speed_bytes):
    """Форматирует скорость в байтах/сек в читаемый формат"""
    return format_size(speed_bytes) + "/s"


async def check_user_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Проверяет, имеет ли пользователь доступ к боту
    
    Returns:
        True если доступ разрешен, False иначе
    """
    user_id = update.effective_user.id
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return False
    return True


def format_torrent_info(torrent):
    """Форматирует информацию о торренте"""
    name = torrent.name
    status = torrent.status
    percent_done = torrent.percent_done * 100
    downloaded = torrent.downloaded_ever
    total_size = torrent.total_size
    download_rate = torrent.rate_download
    upload_rate = torrent.rate_upload
    peers_connected = torrent.peers_connected
    peers_getting_from_us = torrent.peers_getting_from_us
    peers_sending_to_us = torrent.peers_sending_to_us
    
    status_text = {
        'stopped': '⏸ Остановлен',
        'check_wait': '⏳ Ожидает проверки',
        'check': '🔍 Проверяется',
        'download_wait': '⏳ Ожидает загрузки',
        'downloading': '⬇️ Загружается',
        'seed_wait': '⏳ Ожидает раздачи',
        'seeding': '⬆️ Раздается'
    }.get(status, f'❓ {status}')
    
    info = f"📦 **{name}**\n"
    info += f"Статус: {status_text}\n"
    info += f"Прогресс: {percent_done:.1f}%\n"
    info += f"Загружено: {format_size(downloaded)} / {format_size(total_size)}\n"
    info += f"Скорость загрузки: {format_speed(download_rate)}\n"
    info += f"Скорость отдачи: {format_speed(upload_rate)}\n"
    info += f"Пиры: {peers_connected} (отдаем: {peers_getting_from_us}, получаем: {peers_sending_to_us})\n"
    
    return info


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if not await check_user_access(update, context):
        return
    
    welcome_text = """
🤖 **Бот для управления Transmission**

Доступные команды:
/start - Показать это сообщение
/all - Показать все загрузки
/active - Показать только активные загрузки
/pause - Поставить все загрузки на паузу
/resume - Продолжить все загрузки
/help - Показать справку

📎 **Отправьте .torrent файл** для автоматической загрузки
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    if not await check_user_access(update, context):
        return
    
    help_text = """
📖 **Справка по использованию бота**

**Доступные команды:**

🔹 /start - Показать приветственное сообщение со списком команд
🔹 /help - Показать эту справку
🔹 /all - Показать все торренты (включая завершенные и остановленные)
🔹 /active - Показать только активные загрузки (загружающиеся, раздающиеся, проверяющиеся)
🔹 /pause - Поставить все загрузки на паузу
🔹 /resume - Продолжить все загрузки
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def show_all_torrents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все торренты"""
    if not await check_user_access(update, context):
        return
    
    try:
        torrents = transmission.get_all_torrents()
        
        if not torrents:
            await update.message.reply_text("📭 Нет загрузок")
            return
        
        message = f"📋 **Все загрузки ({len(torrents)}):**\n\n"
        
        for i, torrent in enumerate(torrents, 1):
            message += f"{i}. {format_torrent_info(torrent)}\n"
        
        # Telegram ограничивает длину сообщения до 4096 символов
        if len(message) > 4096:
            # Разбиваем на части
            parts = []
            current_part = "📋 **Все загрузки:**\n\n"
            
            for i, torrent in enumerate(torrents, 1):
                torrent_text = f"{i}. {format_torrent_info(torrent)}\n"
                if len(current_part) + len(torrent_text) > 4000:
                    parts.append(current_part)
                    current_part = torrent_text
                else:
                    current_part += torrent_text
            
            if current_part:
                parts.append(current_part)
            
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Ошибка при получении списка торрентов: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def show_active_torrents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать только активные торренты"""
    if not await check_user_access(update, context):
        return
    
    try:
        torrents = transmission.get_active_torrents()
        
        if not torrents:
            await update.message.reply_text("📭 Нет активных загрузок")
            return
        
        message = f"⚡ **Активные загрузки ({len(torrents)}):**\n\n"
        
        for i, torrent in enumerate(torrents, 1):
            message += f"{i}. {format_torrent_info(torrent)}\n"
        
        # Telegram ограничивает длину сообщения до 4096 символов
        if len(message) > 4096:
            parts = []
            current_part = "⚡ **Активные загрузки:**\n\n"
            
            for i, torrent in enumerate(torrents, 1):
                torrent_text = f"{i}. {format_torrent_info(torrent)}\n"
                if len(current_part) + len(torrent_text) > 4000:
                    parts.append(current_part)
                    current_part = torrent_text
                else:
                    current_part += torrent_text
            
            if current_part:
                parts.append(current_part)
            
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Ошибка при получении активных торрентов: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def pause_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поставить все загрузки на паузу"""
    if not await check_user_access(update, context):
        return
    
    try:
        count = transmission.pause_all()
        await update.message.reply_text(f"⏸ Остановлено загрузок: {count}")
    except Exception as e:
        logger.error(f"Ошибка при остановке загрузок: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def resume_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Продолжить все загрузки"""
    if not await check_user_access(update, context):
        return
    
    try:
        count = transmission.resume_all()
        await update.message.reply_text(f"▶️ Продолжено загрузок: {count}")
    except Exception as e:
        logger.error(f"Ошибка при продолжении загрузок: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def handle_torrent_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик torrent файлов"""
    if not await check_user_access(update, context):
        return
    
    try:
        file = await update.message.document.get_file()
        torrent_data = BytesIO()
        await file.download_to_memory(torrent_data)
        torrent_data.seek(0)
        
        # Добавляем торрент в Transmission
        torrent = transmission.add_torrent(torrent_data)
        
        await update.message.reply_text(
            f"✅ Торрент добавлен!\n\n"
            f"📦 {torrent.name}\n"
            f"Статус: Загрузка начата"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении торрента: {e}")
        await update.message.reply_text(f"❌ Ошибка при добавлении торрента: {str(e)}")


async def post_init(application: Application) -> None:
    """Отправляет сообщение о запуске бота разрешенному пользователю"""
    async def send_startup_message():
        """Отправляет сообщение о запуске после небольшой задержки"""
        await asyncio.sleep(2)  # Небольшая задержка для инициализации бота
        try:
            await application.bot.send_message(
                chat_id=ALLOWED_USER_ID,
                text="✅ **Бот успешно запущен!**\n\nБот готов к работе. Используйте /help для просмотра всех доступных команд.",
                parse_mode='Markdown'
            )
            logger.info(f"Сообщение о запуске отправлено пользователю {ALLOWED_USER_ID}")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о запуске: {e}")
    
    # Запускаем задачу в фоне
    asyncio.create_task(send_startup_message())


def main():
    """Главная функция запуска бота"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    #token = "6653784804:AAERhdcErWtm98dFE8qT5iSTuHqIsNXQhjY"
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не установлен!")
        raise ValueError("TELEGRAM_BOT_TOKEN должен быть установлен в переменных окружения")
    
    # Создаем приложение
    application = Application.builder().token(token).post_init(post_init).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("all", show_all_torrents))
    application.add_handler(CommandHandler("active", show_active_torrents))
    application.add_handler(CommandHandler("pause", pause_all))
    application.add_handler(CommandHandler("resume", resume_all))
    
    # Обработчик torrent файлов
    application.add_handler(
        MessageHandler(
            filters.Document.FileExtension("torrent"),
            handle_torrent_file
        )
    )
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

