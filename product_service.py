import requests


_STRAPI_URL = None
_STRAPI_TOKEN = None
_BASE_HEADERS = None
_JSON_HEADERS = None


def init_strapi_client(strapi_url: str, strapi_token: str):
    """
    Инициализирует клиент Strapi с переданными параметрами.
    Должна быть вызвана один раз перед использованием других функций.
    """
    global _STRAPI_URL, _STRAPI_TOKEN, _BASE_HEADERS, _JSON_HEADERS

    _STRAPI_URL = strapi_url
    _STRAPI_TOKEN = strapi_token
    _BASE_HEADERS = {"Authorization": f"Bearer {strapi_token}"}
    _JSON_HEADERS = {
        "Authorization": f"Bearer {strapi_token}",
        "Content-Type": "application/json"
    }


def get_fishes_from_strapi() -> list:
    """Отправляет запрос к API и в ответ получает
    список продуктов для продажи

    Returns:
        list: Свойства продуктов формата [{'id': 2, 'title': 'Масляная рыба х/к'}] и т.д.
    """
    response = requests.get(
        f"{_STRAPI_URL}/api/products",
        headers=_BASE_HEADERS,
        params={"populate": "*"}
    )

    response.raise_for_status()

    product_entities = response.json()
    return product_entities['data']


def get_description_from_strapi(document_id: str) -> str:
    """
    Получает данные о продукте из CMS Strapi и формирует текстовое описание для отображения.
    Args:
        document_id (str): Уникальный идентификатор продукта в системе Strapi.

    Returns:
        str: Форматированная строка с названием, ценой и описанием продукта.
    """
    response = requests.get(
        f"{_STRAPI_URL}/api/products/{document_id}",
        headers=_BASE_HEADERS,
        params={"populate": "*"}
    )

    response.raise_for_status()

    product_entities = response.json()
    product = product_entities['data']

    title = product.get('title', 'Без названия')
    price = product.get('price', 0)
    description = product.get('description', 'Описание отсутствует')

    message = f'{title}    Цена: {price} руб.\n\n'
    message += f'{description}'
    return message


def get_picture_bytes_from_strapi(document_id: str) -> bytes:
    """
    Получает URL изображения продукта из CMS Strapi по его идентификатору.

    Args:
        document_id (str): Уникальный идентификатор продукта в системе Strapi.

    Returns:
        bytes: Байты изображения продукта или None, если изображение не найдено.
    """
    response = requests.get(
        f"{_STRAPI_URL}/api/products/{document_id}",
        headers=_BASE_HEADERS,
        params={"populate": "*"}
    )

    response.raise_for_status()

    product_entities = response.json()

    pictures = product_entities['data'].get('picture', [])
    if not pictures:
        return None

    first_picture = pictures[0]
    picture_url = first_picture.get('url')

    if picture_url:
        if picture_url.startswith('/'):
            picture_url = f"{_STRAPI_URL}{picture_url}"

    image_response = requests.get(picture_url, headers=_BASE_HEADERS)
    image_response.raise_for_status()

    return image_response.content


def get_or_create_cart(tg_id: str) -> str:
    """
    Получает идентификатор корзины (documentId) пользователя по его Telegram ID.
    Args:
        tg_id (str): Уникальный идентификатор пользователя в Telegram.

    Returns:
        str: Уникальный идентификатор корзины (documentId) в формате строки.
    """
    response = requests.get(
        f"{_STRAPI_URL}/api/carts",
        headers=_JSON_HEADERS,
        params={
            "filters[tg_id][$eq]": tg_id,
        }
    )
    response.raise_for_status()
    cart_document_id = None

    if response.status_code == 200:
        carts_entities = response.json()
        if carts_entities.get('data') and len(carts_entities['data']) > 0:
            cart = carts_entities['data'][0]
            cart_document_id = cart['documentId']
            return cart_document_id

    if not cart_document_id:
        carts_entities = {
            "data": {
                "tg_id": tg_id,
            }
        }

        response = requests.post(
            f"{_STRAPI_URL}/api/carts",
            headers=_JSON_HEADERS,
            json=carts_entities
        )
        response.raise_for_status()

        cart = response.json()['data']
        cart_document_id = cart['documentId']
        return cart_document_id


def add_cart_product(cart_document_id: str, product_document_id: str, quantity: float):
    """
    Добавляет продукт в существующую корзину пользователя через API Strapi v5.

    Функция создаёт новую запись в коллекции 'cart-products', устанавливая связь
    между корзиной и продуктом с указанным количеством. Использует формат связей Strapi v5
    с использованием ключа 'connect' для привязки существующих записей по их documentId.

    Args:
        cart_document_id (str): Уникальный идентификатор корзины (documentId) в Strapi.
        product_document_id (str): Уникальный идентификатор продукта (documentId) в Strapi.
        quantity (float): Количество добавляемого продукта.
    """
    cart_product = {
        "data": {
            "quantity": quantity,
            "cart": {
                "connect": [cart_document_id]
            },
            "product": {
                "connect": [product_document_id]
            }
        }
    }

    response = requests.post(
        f"{_STRAPI_URL}/api/cart-products",
        headers=_JSON_HEADERS,
        json=cart_product
    )
    response.raise_for_status()


def get_cart_content_with_details(cart_document_id: str) -> dict:
    """
    Получает содержимое корзины пользователя по его documentId и формирует текстовое описание.

    Args:
        cart_document_id (str): Уникальный идентификатор корзины (documentId) в Strapi.
    """
    cart_response = requests.get(
        f"{_STRAPI_URL}/api/carts/{cart_document_id}",
        headers=_JSON_HEADERS,
        params={
            "populate": "*"
        }
    )

    cart_response.raise_for_status()
    cart_entities = cart_response.json()["data"]

    items = []
    total_sum = 0

    for cart_product in cart_entities.get('cart_products', []):
        product_document_id = cart_product.get('documentId')
        quantity = cart_product.get('quantity', 0)
        cart_product_id = cart_product.get('documentId')

        if product_document_id and quantity > 0:
            product_response = requests.get(
                f"{_STRAPI_URL}/api/cart-products/{product_document_id}",
                headers=_JSON_HEADERS,
                params={"populate": "*"}
            )
            product_response.raise_for_status()
            product_data = product_response.json()["data"]["product"]

            title = product_data.get('title', 'Неизвестный товар')
            price = float(product_data.get('price', 0))
            item_total = price * quantity

            items.append({
                'title': title,
                'quantity': quantity,
                'price': price,
                'total': item_total,
                'cart_product_id': cart_product_id
            })

            total_sum += item_total

    return {
        'items': items,
        'total_sum': total_sum
    }


def delete_cart_product(cart_product_id: str):
    """
    Удаляет продукт из корзины по ID записи cart-product.

    Args:
        cart_product_id (str): Уникальный идентификатор записи в корзине (documentId cart-product).
    """
    response = requests.delete(
        f"{_STRAPI_URL}/api/cart-products/{cart_product_id}",
        headers=_BASE_HEADERS
    )

    response.raise_for_status()
    return response.status_code == 200


def clear_cart(tg_id: str):
    """
    Очищает всю корзину пользователя.

    Args:
        tg_id (str): Telegram ID пользователя
    """
    response = requests.get(
        f"{_STRAPI_URL}/api/carts",
        headers=_JSON_HEADERS,
        params={"filters[tg_id][$eq]": tg_id, "populate": "cart_products"}
    )
    response.raise_for_status()

    carts = response.json()["data"]
    if not carts:
        return True

    cart = carts[0]
    cart_products = cart.get('cart_products', [])

    for cart_product in cart_products:
        cart_product_id = cart_product.get('documentId')
        if cart_product_id:
            requests.delete(
                f"{_STRAPI_URL}/api/cart-products/{cart_product_id}",
                headers=_BASE_HEADERS
            )

    return True


def create_order(cart_document_id: str, email: str) -> dict:
    """
    Создает заказ (Order) в Strapi, связывая его с корзиной.
    Args:
        cart_document_id (str): Уникальный идентификатор корзины (documentId) в Strapi.
        email (str): Email пользователя.
    Returns:
        dict: Созданный заказ
    """
    order_data = {
        "data": {
            "email": email,
            "cart": {
                "connect": [cart_document_id]
            }
        }
    }

    response = requests.post(
        f"{_STRAPI_URL}/api/orders",
        headers=_JSON_HEADERS,
        json=order_data
    )

    response.raise_for_status()
    return response.json()['data']


def update_cart_with_email(cart_document_id: str, email: str):
    """
    Обновляет корзину пользователя, добавляя email.
    (Оставлено для обратной совместимости)

    Args:
        cart_document_id (str): Уникальный идентификатор корзины (documentId) в Strapi.
        email (str): Email пользователя.
    """
    return create_order(cart_document_id, email)
