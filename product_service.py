import requests
from environs import env


def get_fishes_from_strapi() -> list:
    """Отправляет запрос к API и в ответ получает
    список продуктов для продажи

    Returns:
        list: Свойства продуктов формата [{'id': 2, 'title': 'Масляная рыба х/к'}] и т.д.
    """
    env.read_env()
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')
    headers = {"Authorization": f"Bearer {strapi_token}"}

    response = requests.get(
        f"{strapi_url}/api/products",
        headers=headers,
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
    env.read_env()
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')
    headers = {"Authorization": f"Bearer {strapi_token}"}

    response = requests.get(
        f"{strapi_url}/api/products/{document_id}",
        headers=headers,
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
    env.read_env()
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')
    headers = {"Authorization": f"Bearer {strapi_token}"}

    response = requests.get(
        f"{strapi_url}/api/products/{document_id}",
        headers=headers,
        params={"populate": "*"}
    )

    response.raise_for_status()

    product_entities = response.json()

    pictures = product_entities['data'].get('picture', [])
    first_picture = pictures[0]
    picture_url = first_picture.get('url')

    if picture_url:
        if picture_url.startswith('/'):
            picture_url = f"{strapi_url}{picture_url}"
    image_response = requests.get(picture_url, headers=headers)
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
    env.read_env()
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')
    headers = {
        "Authorization": f"Bearer {strapi_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(
        f"{strapi_url}/api/carts",
        headers=headers,
        params={
            "filters[tg_id][$eq]": tg_id,
        }
    )
    response.raise_for_status()
    cart_documents_id = None

    if response.status_code == 200:
        carts_entities = response.json()
        if carts_entities.get('data') and len(carts_entities['data']) > 0:
            cart = carts_entities['data'][0]
            cart_documents_id = cart['documentId']
            return cart_documents_id

    if not cart_documents_id:
        carts_entities = {
            "data": {
                "tg_id": tg_id,
            }
        }

        response = requests.post(
            f"{strapi_url}/api/carts",
            headers=headers,
            json=carts_entities
        )
        response.raise_for_status()

        cart = response.json()['data']
        cart_documents_id = cart['documentId']
        return cart_documents_id


def add_cart_product(cart_documents_id: str, product_documents_id: str, quantity: float):
    """
    Добавляет продукт в существующую корзину пользователя через API Strapi v5.

    Функция создаёт новую запись в коллекции 'cart-products', устанавливая связь
    между корзиной и продуктом с указанным количеством. Использует формат связей Strapi v5
    с использованием ключа 'connect' для привязки существующих записей по их documentId.

    Args:
        cart_documents_id (str): Уникальный идентификатор корзины (documentId) в Strapi.
        product_documents_id (str): Уникальный идентификатор продукта (documentId) в Strapi.
        quantity (float): Количество добавляемого продукта.
    """
    env.read_env()
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')
    headers = {
        "Authorization": f"Bearer {strapi_token}",
        "Content-Type": "application/json"
    }

    cart_product = {
        "data": {
            "quantity": quantity,
            "cart": {
                "connect": [cart_documents_id]
            },
            "product": {
                "connect": [product_documents_id]
            }
        }
    }

    response = requests.post(
        f"{strapi_url}/api/cart-products",
        headers=headers,
        json=cart_product
    )
    response.raise_for_status()


def get_cart_content_with_details(cart_document_id: str) -> dict:
    """
    Получает содержимое корзины пользователя по его documentId и формирует текстовое описание.

    Args:
        cart_documents_id (str): Уникальный идентификатор корзины (documentId) в Strapi.
    """
    env.read_env()
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')
    headers = {
        "Authorization": f"Bearer {strapi_token}",
        "Content-Type": "application/json"
    }

    cart_response = requests.get(
        f"{strapi_url}/api/carts/{cart_document_id}",
        headers=headers,
        params={
            "populate": "*"
        }
    )

    cart_response.raise_for_status()
    cart_entyties = cart_response.json()["data"]

    items = []
    total_sum = 0

    for cart_product in cart_entyties.get('cart_products', []):
        product_document_id = cart_product.get('documentId')
        quantity = cart_product.get('quantity', 0)
        cart_product_id = cart_product.get('documentId')

        if product_document_id and quantity > 0:
            product_response = requests.get(
                f"{strapi_url}/api/cart-products/{product_document_id}",
                headers=headers,
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
    env.read_env()
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')
    headers = {
        "Authorization": f"Bearer {strapi_token}",
    }

    response = requests.delete(
        f"{strapi_url}/api/cart-products/{cart_product_id}",
        headers=headers
    )

    response.raise_for_status()
    return response.status_code == 200


def clear_cart(tg_id: str):
    """
    Очищает всю корзину пользователя.

    Args:
        tg_id (str): Telegram ID пользователя
    """
    env.read_env()
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')
    headers = {
        "Authorization": f"Bearer {strapi_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(
        f"{strapi_url}/api/carts",
        headers=headers,
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
                f"{strapi_url}/api/cart-products/{cart_product_id}",
                headers=headers
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
    env.read_env()
    strapi_url = env.str('STRAPI_URL', 'http://localhost:1337')
    strapi_token = env.str('STRAPI_TOKEN')
    headers = {
        "Authorization": f"Bearer {strapi_token}",
        "Content-Type": "application/json"
    }
    order_data = {
        "data": {
            "email": email,
            "cart": {
                "connect": [cart_document_id]
            }
        }
    }

    response = requests.post(
        f"{strapi_url}/api/orders",
        headers=headers,
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
