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
