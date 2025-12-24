import logging
import redis
from io import BytesIO
from environs import env

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

import product_service

logger = logging.getLogger(__name__)


def create_redis_client():
    """Создает подключение к Redis"""
    database_password = env.str('DATABASE_PASSWORD', '')
    database_host = env.str('DATABASE_HOST', 'localhost')
    database_port = env.str('DATABASE_PORT', 6379)
    return redis.Redis(
        host=database_host,
        port=int(database_port),
        password=database_password,
        decode_responses=True
    )


def create_handlers(strapi_url, strapi_token, redis_client):
    """Создает все обработчики с замыканием зависимостей"""
    def start(update, context):
        fishes = product_service.get_fishes_from_strapi(strapi_url, strapi_token)

        buttons = []
        for fish in fishes:
            fish_document_id = fish['documentId']
            fish_title = fish['title']

            button = InlineKeyboardButton(
                fish_title,
                callback_data=str(fish_document_id)
            )
            buttons.append([button])
        buttons.append([InlineKeyboardButton('Моя Корзина', callback_data='view_cart')])

        reply_markup = InlineKeyboardMarkup(buttons)

        if update.callback_query:
            query = update.callback_query
            query.answer()
            query.message.reply_text('Выбери рыбку', reply_markup=reply_markup)
        else:
            update.message.reply_text('Выбери рыбку', reply_markup=reply_markup)
        return "HANDLE_MENU"

    def show_cart(update, context, edit=False):
        query = update.callback_query

        if query:
            query.answer("Загружаем корзину...", show_alert=False)

            if not edit:
                try:
                    context.bot.delete_message(
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id
                    )
                except Exception as e:
                    logger.warning(f"Не удалось удалить сообщение: {e}")

        tg_id = str(query.message.chat_id) if query else str(update.message.chat_id)

        cart_document_id = product_service.get_or_create_cart(strapi_url, strapi_token, tg_id)

        try:
            cart_content = product_service.get_cart_content_with_details(
                strapi_url, strapi_token, cart_document_id
            )
        except Exception as e:
            logger.error(f"Ошибка получения корзины: {e}")
            cart_content = {'items': [], 'total_sum': 0}

        if not cart_content['items']:
            cart_message = "🛒 *Ваша корзина пуста*"
            keyboard = [
                [InlineKeyboardButton('Назад к выбору', callback_data='back_to_menu')]
            ]
        else:
            lines = ["🛒 *Ваша корзина:*\n"]

            for i, item in enumerate(cart_content['items'], 1):
                lines.append(
                    f"{i}. *{item['title']}*\n"
                    f"   Количество: {item['quantity']} × {item['price']} руб. = {item['total']} руб."
                )

            lines.append(f"\n*Итого:* {cart_content['total_sum']} руб.")
            cart_message = "\n".join(lines)

            keyboard = []
            for item in cart_content['items']:
                keyboard.append([
                    InlineKeyboardButton(
                        f"❌ Удалить {item['title']}",
                        callback_data=f"remove_{item['cart_product_id']}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton('Очистить корзину', callback_data='clear_cart'),
                InlineKeyboardButton('Оплатить', callback_data='pay')
            ])
            keyboard.append([
                InlineKeyboardButton('Назад к выбору', callback_data='back_to_menu')
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if query and edit:
            query.edit_message_text(
                text=cart_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            context.bot.send_message(
                chat_id=query.message.chat_id if query else update.message.chat_id,
                text=cart_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        return "HANDLE_CART"

    def show_product_description(update, context):
        query = update.callback_query
        query.answer()

        if query.data == 'view_cart':
            return show_cart(update, context)

        try:
            context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

        fish_document_id = query.data
        fish_description = product_service.get_description_from_strapi(
            strapi_url, strapi_token, fish_document_id
        )

        image_bytes = product_service.get_picture_bytes_from_strapi(
            strapi_url, strapi_token, fish_document_id
        )

        context.user_data['current_product'] = fish_document_id

        keyboard = [
            [InlineKeyboardButton('Добавить в корзину', callback_data=f'buy_{fish_document_id}')],
            [InlineKeyboardButton('Моя Корзина', callback_data='view_cart')],
            [InlineKeyboardButton('Назад', callback_data='back_to_menu')]
        ]

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

    def handle_description(update, context):
        query = update.callback_query
        button_callback = query.data

        if button_callback == 'back_to_menu':
            try:
                context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {e}")
            return start(update, context)

        elif button_callback.startswith('buy_'):
            product_document_id = button_callback.split('_')[1]
            tg_id = str(query.message.chat_id)

            cart_document_id = product_service.get_or_create_cart(
                strapi_url, strapi_token, tg_id
            )
            product_service.add_cart_product(
                strapi_url, strapi_token, 
                cart_document_id, product_document_id, 1.0
            )
            query.answer("Товар добавлен в корзину!", show_alert=False)
            return "HANDLE_DESCRIPTION"
        elif button_callback == 'view_cart':
            return show_cart(update, context)

        return "HANDLE_DESCRIPTION"

    def handle_cart(update, context):
        query = update.callback_query
        button_callback = query.data

        if button_callback == 'back_to_menu':
            try:
                context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {e}")
            return start(update, context)

        elif button_callback.startswith('remove_'):
            cart_product_id = button_callback.split('_')[1]

            try:
                product_service.delete_cart_product(
                    strapi_url, strapi_token, cart_product_id
                )
                query.answer("✅ Товар удален из корзины", show_alert=False)
            except Exception as e:
                logger.error(f"Ошибка удаления товара: {e}")
                query.answer("Ошибка удаления товара", show_alert=True)
                return "HANDLE_CART"
            return show_cart(update, context, edit=True)

        elif button_callback == 'clear_cart':
            tg_id = str(query.message.chat_id)

            try:
                product_service.clear_cart(strapi_url, strapi_token, tg_id)
                query.answer("✅ Корзина очищена", show_alert=False)
            except Exception as e:
                logger.error(f"Ошибка очистки корзины: {e}")
                query.answer("❌ Ошибка очистки корзины", show_alert=True)
                return "HANDLE_CART"
            return show_cart(update, context, edit=False)

        elif button_callback == 'pay':
            query.answer("Переходим к оплате...", show_alert=False)

            try:
                context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {e}")

            context.bot.send_message(
                chat_id=query.message.chat_id,
                text="*Оформление заказа*\n\n"
                     "Для оформления заказа, пожалуйста, укажите ваш email:\n"
                     "(Пример: example@email.com)",
                parse_mode="Markdown"
            )
            return "WAITING_EMAIL"

        query.answer()
        return "HANDLE_CART"

    def waiting_for_email(update, context):
        if update.message:
            email = update.message.text.strip()

            if '@' not in email or '.' not in email:
                update.message.reply_text(
                    "❌ Пожалуйста, введите корректный email адрес.\n"
                    "Пример: example@email.com"
                )
                return "WAITING_EMAIL"

            tg_id = str(update.message.chat_id)
            try:
                cart_document_id = product_service.get_or_create_cart(
                    strapi_url, strapi_token, tg_id
                )
                logger.info(f"Cart document ID: {cart_document_id}")

                cart_content = product_service.get_cart_content_with_details(
                    strapi_url, strapi_token, cart_document_id
                )
                logger.info(f"Cart content: {cart_content}")

                order = product_service.create_order(
                    strapi_url, strapi_token, cart_document_id, email
                )
                logger.info(f"Order created: {order}")

                items_list = ""
                if cart_content['items']:
                    items_list = "\n".join([
                        f"   • {item['title']} - {item['quantity']} шт. × {item['price']} руб."
                        for item in cart_content['items']
                    ])
                    items_list = f"\n*Состав заказа:*\n{items_list}\n\n"

                success_message = (
                    "✅ *Заказ успешно оформлен!*\n\n"
                    f"Ваш email: `{email}`\n"
                    f"Номер заказа: `{order.get('documentId')}`\n"
                    f"Сумма заказа: *{cart_content['total_sum']} руб.*\n"
                    f"Товаров в заказе: *{len(cart_content['items'])}*\n"
                    f"{items_list}"
                    "Спасибо за покупку!"
                )

                for item in cart_content['items']:
                    product_service.delete_cart_product(
                        strapi_url, strapi_token, item['cart_product_id']
                    )

                update.message.reply_text(
                    success_message,
                    parse_mode="Markdown"
                )
                return start(update, context)

            except Exception as e:
                logger.error(f"Ошибка при оформлении заказа: {e}", exc_info=True)
                update.message.reply_text(
                    f"❌ Произошла ошибка при оформлении заказа: {str(e)}"
                )
                return start(update, context)
        elif update.callback_query:
            query = update.callback_query
            query.answer()
            query.edit_message_text(
                text="❌ Оформление заказа отменено.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('Вернуться в меню', callback_data='back_to_menu')]
                ])
            )
            return "HANDLE_MENU"
        return "WAITING_EMAIL"

    def handle_users_reply(update, context):
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
                redis_client.set(chat_id, next_state)
                return
        else:
            return

        if user_reply == '/start':
            user_state = 'START'
        else:
            user_state = redis_client.get(chat_id)
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
            'HANDLE_DESCRIPTION': handle_description,
            'HANDLE_CART': handle_cart,
            'WAITING_EMAIL': waiting_for_email,
        }

        state_handler = states_functions.get(user_state, start)

        try:
            next_state = state_handler(update, context)
            redis_client.set(chat_id, next_state)
        except Exception as err:
            logger.error(f'Ошибка установки статуса в БД {err}')

    return handle_users_reply


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        level=logging.INFO
    )

    env.read_env()

    tg_bot_token = env.str('TG_BOT_TOKEN')
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')

    logger.info('Бот запущен')

    updater = Updater(tg_bot_token)

    redis_client = create_redis_client()

    main_handler = create_handlers(strapi_url, strapi_token, redis_client)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(main_handler))
    dispatcher.add_handler(MessageHandler(Filters.text, main_handler))
    dispatcher.add_handler(CommandHandler('start', main_handler))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
