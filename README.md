# Fishy-Fishy-Fishy

Этот Telegram-бот предназначен для продажи рыбы и морепродуктов. Бот интегрирован с CMS Strapi V5 для управления товарами, корзинами и заказами. Пользователи могут:

Просматривать каталог товаров с фотографиями и описаниями
Добавлять товары в корзину
Управлять содержимым корзины (удалять товары, очищать корзину)
Оформлять заказы с указанием email
Получать подтверждение заказа с деталями покупки

## Запуск

Предварительные требования:
Python 3.8+

Установленный Redis (для хранения состояния диалога)

Strapi CMS (для управления товарами и заказами)

Telegram Bot Token (получить у @BotFather)

## Установка

Клонируйте репозиторий или скачайте файлы проекта

Установите зависимости:

```bash
pip install -r requirements.txt
```
или же
```bash
uv sync
```

Настройте переменные окружения (см. раздел 3)

Запустите бота:

```bash
python python_bot.py
```

## Переменные окружения

Создайте файл .env в корневой директории проекта со следующими переменными:

Обязательные:

`TG_BOT_TOKEN` - Токен вашего Telegram бота (получить у @BotFather)

`STRAPI_TOKEN` - API токен для доступа к Strapi CMS (получить в настройках в web интерфейсе)

`STRAPI_URL` - URL вашего Strapi сервера (пример: http://localhost:1337)

Необязательные (со значениями по умолчанию):

`DATABASE_HOST` - Хост Redis (по умолчанию: localhost)

`DATABASE_PORT` - Порт Redis (по умолчанию: 6379)

`DATABASE_PASSWORD` - Пароль Redis (по умолчанию: пустая строка)

### Примеры запуска

#### Локальный запуск с Strapi на той же машине

```bash
# Установите зависимости
pip install python-telegram-bot redis environs requests
```

#### Создайте .env файл с содержимым

```text
# TG_BOT_TOKEN=ваш_токен_бота
# STRAPI_TOKEN=ваш_strapi_токен
# STRAPI_URL=http://localhost:1337
# DATABASE_HOST=localhost
# DATABASE_PORT=6379
```

#### Запустите Redis сервер (если еще не запущен)

```bash
redis-server
```

#### Запустите бота

```bash
python python_bot.py
```

### Проверка работоспособности

После запуска бота:

Найдите вашего бота в Telegram по имени

Отправьте команду /start

Убедитесь, что отображается меню с товарами

Добавьте товар в корзину и проверьте оформление заказа

#### Требования к Strapi

Убедитесь, что в Strapi созданы следующие Content Types:

products (с полями: title, price, description, picture)

carts (с полями: tg_id, email, cart_products relation)

cart-products (с полями: quantity, cart relation, product relation)

orders (с полями: email, cart relation)
