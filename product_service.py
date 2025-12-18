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


def get_or_create_cart(tg_id: str):

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



def add_cart_product(cart_documents_id: str, product_documents_id: str, quantity: float) -> dict:
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
