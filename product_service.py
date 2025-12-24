import requests


def create_headers(strapi_token):
    """Создает заголовки для запросов"""
    return {
        "Authorization": f"Bearer {strapi_token}",
        "Content-Type": "application/json"
    }


def get_fishes_from_strapi(strapi_url, strapi_token):
    """Отправляет запрос к API и в ответ получает список продуктов"""
    headers = {"Authorization": f"Bearer {strapi_token}"}
    response = requests.get(
        f"{strapi_url}/api/products",
        headers=headers,
        params={"populate": "*"}
    )
    response.raise_for_status()
    product_entities = response.json()
    return product_entities['data']


def get_description_from_strapi(strapi_url, strapi_token, document_id):
    """Получает данные о продукте из CMS Strapi"""
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


def get_picture_bytes_from_strapi(strapi_url, strapi_token, document_id):
    """Получает URL изображения продукта из CMS Strapi"""
    headers = {"Authorization": f"Bearer {strapi_token}"}
    response = requests.get(
        f"{strapi_url}/api/products/{document_id}",
        headers=headers,
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
            picture_url = f"{strapi_url}{picture_url}"

    image_response = requests.get(picture_url, headers=headers)
    image_response.raise_for_status()
    return image_response.content


def get_or_create_cart(strapi_url, strapi_token, tg_id):
    """Получает идентификатор корзины пользователя по его Telegram ID"""
    headers = create_headers(strapi_token)

    response = requests.get(
        f"{strapi_url}/api/carts",
        headers=headers,
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
            f"{strapi_url}/api/carts",
            headers=headers,
            json=carts_entities
        )
        response.raise_for_status()

        cart = response.json()['data']
        cart_document_id = cart['documentId']
        return cart_document_id


def add_cart_product(strapi_url, strapi_token, cart_document_id, product_document_id, quantity):
    """Добавляет продукт в существующую корзину пользователя"""
    headers = create_headers(strapi_token)

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
        f"{strapi_url}/api/cart-products",
        headers=headers,
        json=cart_product
    )
    response.raise_for_status()


def get_cart_content_with_details(strapi_url, strapi_token, cart_document_id):
    """Получает содержимое корзины пользователя"""
    headers = create_headers(strapi_token)

    cart_response = requests.get(
        f"{strapi_url}/api/carts/{cart_document_id}",
        headers=headers,
        params={"populate": "*"}
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


def delete_cart_product(strapi_url, strapi_token, cart_product_id):
    """Удаляет продукт из корзины"""
    headers = {"Authorization": f"Bearer {strapi_token}"}
    response = requests.delete(
        f"{strapi_url}/api/cart-products/{cart_product_id}",
        headers=headers
    )
    response.raise_for_status()
    return response.status_code == 200


def clear_cart(strapi_url, strapi_token, tg_id):
    """Очищает всю корзину пользователя"""
    headers = create_headers(strapi_token)

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
            delete_cart_product(strapi_url, strapi_token, cart_product_id)

    return True


def create_order(strapi_url, strapi_token, cart_document_id, email):
    """Создает заказ в Strapi"""
    headers = create_headers(strapi_token)

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