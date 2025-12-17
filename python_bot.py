import logging
import redis
from io import BytesIO
from environs import env
from product_service import (
    get_fishes_from_strapi,
    get_description_from_strapi,
    get_picture_bytes_from_strapi
    )

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler


_database = None
logger = logging.getLogger(__name__)


def start(update, context):
    fishes = get_fishes_from_strapi()
    buttons = []
    for fish in fishes:
        fish_document_id = fish['documentId']
        fish_title = fish['title']

        button = InlineKeyboardButton(
            fish_title,
            callback_data=str(fish_document_id)
        )
        buttons.append([button])

    reply_markup = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.message.reply_text('Выбери рыбку', reply_markup=reply_markup)
    else:
        update.message.reply_text('Выбери рыбку', reply_markup=reply_markup)
    return "HANDLE_MENU"


def show_product_description(update, context):
    """
    Обрабатывает нажатие на кнопку с выбором продукта в телеграм-боте и отображает его описание.

    Returns:
        str: Состояние диалога 'HANDLE_MENU', указывающее, что после отображения
             описания бот должен перейти в режим обработки меню.
    """
    query = update.callback_query
    query.answer()

    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )

    fish_document_id = query.data
    fish_description = get_description_from_strapi(fish_document_id)

    image_bytes = get_picture_bytes_from_strapi(fish_document_id)

    keyboard = [[InlineKeyboardButton('Назад', callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if image_bytes:
        image_file = BytesIO(image_bytes)
        image_file.name = f'product_image_{fish_document_id}.jpg'

        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_file,
            caption=fish_description,
            reply_markup=reply_markup
        )
    else:
        query.message.reply_text(fish_description, reply_markup=reply_markup)
    return "HANDLE_DESCRIPTION"


def handle_users_reply(update, context):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    """
    db = get_database_connection()

    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id

        if user_reply == "back_to_menu":
            context.bot.delete_message(
                chat_id=chat_id,
                message_id=update.callback_query.message.message_id
            )

            next_state = start(update, context)
            db.set(chat_id, next_state)
            return
    else:
        return

    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id)
        if user_state is None:
            user_state = 'START'
        else:
            try:
                if isinstance(user_state, bytes):
                    user_state = user_state.decode('utf-8')
            except (AttributeError, UnicodeDecodeError):
                user_state = 'START'

    states_functions = {
        'START': start,
        'HANDLE_MENU': show_product_description,
        'HANDLE_DESCRIPTION': lambda update, context: None,
    }

    state_handler = states_functions.get(user_state, start)

    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        logger.error(f'Ошибка установки статуса в БД {err}')


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = env.str('DATABASE_PASSWORD', '')
        database_host = env.str('DATABASE_HOST', 'localhost')
        database_port = env.str('DATABASE_PORT', 6379)
        _database = redis.Redis(
            host=database_host,
            port=int(database_port),
            password=database_password,
            decode_responses=True
        )
    return _database


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )

    env.read_env()

    tg_bot_token = env.str('TG_BOT_TOKEN')

    logger.info('Бот запущен')

    updater = Updater(tg_bot_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
