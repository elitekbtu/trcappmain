from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List

class ProductOut(BaseModel):
    sku: str = Field(..., description="Артикул товара")
    name: str = Field(..., description="Название товара")
    brand: str = Field(..., description="Бренд")
    price: float = Field(..., description="Текущая цена")
    old_price: Optional[float] = Field(None, description="Старая цена, если есть")
    url: str = Field(..., description="Полная ссылка на товар")
    image_url: str = Field(..., description="Ссылка на обложку товара")
    image_urls: List[str] = Field(default_factory=list, description="Список всех изображений товара")

    class Config:
        schema_extra = {
            "example": {
                "sku": "NI002ABCDEF1",
                "name": "Кроссовки Air Max",
                "brand": "Nike",
                "price": 12990.0,
                "old_price": 15990.0,
                "url": "https://www.lamoda.ru/p/ni002abcdef1/shoes-nike-krossovki/",
                "image_url": "https://a.lmcdn.ru/img600x866/M/P/MP002XM123ABC_1.jpg",
                "image_urls": [
                    "https://a.lmcdn.ru/img600x866/M/P/MP002XM123ABC_1.jpg",
                    "https://a.lmcdn.ru/img600x866/M/P/MP002XM123ABC_2.jpg",
                    "https://a.lmcdn.ru/img600x866/M/P/MP002XM123ABC_3.jpg"
                ]
            }
        }


class SearchResponse(BaseModel):
    products: list[ProductOut] = Field(..., description="Список найденных товаров")
    total_found: int = Field(..., description="Общее количество найденных товаров")
    page: int = Field(..., description="Текущая страница")
    limit: int = Field(..., description="Лимит товаров на странице")
    domain: str = Field(..., description="Домен Lamoda")


class DomainInfo(BaseModel):
    domains: List[str] = Field(..., description="Список поддерживаемых доменов")
    details: dict = Field(..., description="Детали по каждому домену")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Статус сервиса")
    message: str = Field(..., description="Сообщение о статусе")
    supported_domains: List[str] = Field(..., description="Поддерживаемые домены")


# NEW: Схемы для парсинга по URL
class ProductParseRequest(BaseModel):
    """Запрос на парсинг товара по URL"""
    url: HttpUrl = Field(..., description="URL товара Lamoda")
    save_to_db: bool = Field(True, description="Сохранять ли товар в базу данных")

    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.lamoda.kz/p/rtlaek537801/",
                "save_to_db": True
            }
        }


class ProductDetailsOut(BaseModel):
    """Расширенная информация о товаре"""
    sku: str = Field(..., description="Артикул товара")
    name: str = Field(..., description="Название товара")
    brand: str = Field(..., description="Бренд")
    price: float = Field(..., description="Текущая цена")
    old_price: Optional[float] = Field(None, description="Старая цена, если есть")
    url: str = Field(..., description="Полная ссылка на товар")
    image_url: str = Field(..., description="Ссылка на обложку товара")
    image_urls: List[str] = Field(default_factory=list, description="Список всех изображений товара")
    # Дополнительные поля
    type: Optional[str] = Field(None, description="Тип товара")
    description: Optional[str] = Field(None, description="Описание товара")


class ProductParseResponse(BaseModel):
    """Ответ на парсинг товара по URL"""
    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение о результате")
    product: Optional[ProductDetailsOut] = Field(None, description="Данные товара")
    item_id: Optional[int] = Field(None, description="ID товара в базе данных (если сохранен)")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Товар RTLAEK537801 добавлен в базу данных с 5 изображениями",
                "product": {
                    "sku": "RTLAEK537801",
                    "name": "Nike Шорты спортивные NK ONE DF MR 3IN BR SHORT",
                    "brand": "Nike",
                    "price": 37300.0,
                    "old_price": None,
                    "url": "https://www.lamoda.kz/p/rtlaek537801/",
                    "image_url": "https://a.lmcdn.ru/img600x866/R/T/RTLAEK537801_28489916_1_v1_2x.jpg",
                    "image_urls": [
                        "https://a.lmcdn.ru/img600x866/R/T/RTLAEK537801_28489916_1_v1_2x.jpg",
                        "https://a.lmcdn.ru/img600x866/R/T/RTLAEK537801_28489917_2_v1_2x.jpg"
                    ],
                    "type": "Шорты",
                    "description": None
                },
                "item_id": 123
            }
        }


# NEW: Схемы для массового парсинга
class BatchParseRequest(BaseModel):
    """Запрос на массовый парсинг товаров по URL"""
    urls: List[HttpUrl] = Field(..., min_items=1, max_items=10, description="Список URL товаров Lamoda (максимум 10)")
    save_to_db: bool = Field(True, description="Сохранять ли товары в базу данных")

    class Config:
        schema_extra = {
            "example": {
                "urls": [
                    "https://www.lamoda.kz/p/rtlaek537801/",
                    "https://www.lamoda.kz/p/another-product/"
                ],
                "save_to_db": True
            }
        }


class BatchParseResult(BaseModel):
    """Результат парсинга одного товара в массовом парсинге"""
    url: str = Field(..., description="URL товара")
    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение о результате")
    product: Optional[ProductDetailsOut] = Field(None, description="Данные товара")
    item_id: Optional[int] = Field(None, description="ID товара в базе данных (если сохранен)")
    error: Optional[str] = Field(None, description="Ошибка, если произошла")


class BatchParseResponse(BaseModel):
    """Ответ на массовый парсинг товаров"""
    total_requested: int = Field(..., description="Общее количество запрошенных товаров")
    successful: int = Field(..., description="Количество успешно распарсенных товаров")
    failed: int = Field(..., description="Количество неуспешных попыток")
    results: List[BatchParseResult] = Field(..., description="Результаты для каждого URL")
    summary: str = Field(..., description="Краткое описание результатов")

    class Config:
        schema_extra = {
            "example": {
                "total_requested": 2,
                "successful": 1,
                "failed": 1,
                "results": [
                    {
                        "url": "https://www.lamoda.kz/p/rtlaek537801/",
                        "success": True,
                        "message": "Товар успешно добавлен",
                        "product": {
                            "sku": "RTLAEK537801",
                            "name": "Nike Шорты спортивные",
                            "brand": "Nike",
                            "price": 37300.0,
                            "old_price": None,
                            "url": "https://www.lamoda.kz/p/rtlaek537801/",
                            "image_url": "https://a.lmcdn.ru/img600x866/...",
                            "image_urls": ["https://a.lmcdn.ru/img600x866/..."],
                            "type": "Шорты"
                        },
                        "item_id": 123
                    },
                    {
                        "url": "https://www.lamoda.kz/p/invalid/",
                        "success": False,
                        "message": "Не удалось распарсить товар",
                        "error": "Товар не найден"
                    }
                ],
                "summary": "Успешно распарсено 1 из 2 товаров"
            }
        }


# NEW: Схемы для массового поиска и добавления
class BatchSearchRequest(BaseModel):
    """Запрос на поиск и массовое добавление товаров"""
    query: str = Field(..., min_length=1, description="Поисковый запрос")
    limit: int = Field(20, ge=1, le=50, description="Максимум товаров для добавления")
    domain: str = Field("kz", description="Домен Lamoda (ru/kz/by)")
    save_to_db: bool = Field(True, description="Сохранять ли найденные товары в базу данных")

    class Config:
        schema_extra = {
            "example": {
                "query": "nike кроссовки",
                "limit": 10,
                "domain": "kz",
                "save_to_db": True
            }
        }


class BatchSearchResponse(BaseModel):
    """Ответ на массовый поиск и добавление товаров"""
    query: str = Field(..., description="Поисковый запрос")
    total_found: int = Field(..., description="Общее количество найденных товаров")
    requested_limit: int = Field(..., description="Запрошенный лимит")
    successful: int = Field(..., description="Количество успешно добавленных товаров")
    failed: int = Field(..., description="Количество неуспешных попыток")
    products: List[ProductDetailsOut] = Field(..., description="Список добавленных товаров")
    summary: str = Field(..., description="Краткое описание результатов")

    class Config:
        schema_extra = {
            "example": {
                "query": "nike кроссовки",
                "total_found": 15,
                "requested_limit": 10,
                "successful": 8,
                "failed": 2,
                "products": [],
                "summary": "По запросу 'nike кроссовки' найдено 15 товаров, успешно добавлено 8 из 10 запрошенных"
            }
        } 