from typing import List, Optional
from datetime import datetime
import asyncio

from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session

from app.agents.parser_agent import LamodaParser, LAMODA_DOMAINS
from app.agents.product_parser import ModernLamodaParser
from app.agents.catalog_parser import parse_catalog_items
from app.core.database import get_db
from app.core.security import get_current_user
from app.db.models.user import User
from app.db.models.item import Item
from app.db.models.item_image import ItemImage
from .schemas import (
    ProductOut, 
    DomainInfo, 
    HealthResponse, 
    ProductParseRequest,
    ProductParseResponse,
    ProductDetailsOut,
    BatchParseRequest,
    BatchParseResponse,
    BatchParseResult,
    BatchSearchRequest,
    BatchSearchResponse
)

router = APIRouter(prefix="/lamoda", tags=["lamoda"])


@router.get("/search", response_model=List[ProductOut])
async def lamoda_search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    limit: int = Query(20, ge=1, le=100, description="Максимум товаров"),
    domain: str = Query("ru", description="Домен Lamoda (ru/kz/by)"),
    page: int = Query(1, ge=1, le=50, description="Номер страницы")
):
    """Вернуть результаты поиска Lamoda по ключевому слову *q*.

    Парсинг выполняется на лету. При ошибке Lamoda (например, блокировка
    по IP) вернётся HTTP 502.
    
    Args:
        q: Поисковый запрос (например, "nike кроссовки")
        limit: Максимальное количество товаров (1-100)
        domain: Домен Lamoda - ru, kz или by
        page: Номер страницы для пагинации
    """
    # Validate domain
    if domain not in LAMODA_DOMAINS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported domain: {domain}. Use one of: {list(LAMODA_DOMAINS.keys())}"
        )
    
    try:
        parser = LamodaParser(domain=domain)
        products = await parser.afetch_search(q, limit=limit, page=page)
        
        if not products:
            return []
            
        # Convert Product dataclass to dict manually
        result = []
        for product in products:
            # Получаем список изображений, если он доступен
            image_urls = getattr(product, 'image_urls', [])
            # Если список пустой, но есть основное изображение, добавляем его
            if not image_urls and product.image_url:
                image_urls = [product.image_url]
            
            result.append({
                "sku": product.sku,
                "name": product.name,
                "brand": product.brand,
                "price": product.price,
                "old_price": product.old_price,
                "url": product.url,
                "image_url": product.image_url,
                "image_urls": image_urls
            })
        
        return result
        
    except Exception as exc:
        # Log the error for debugging
        print(f"Lamoda search error: {exc}")
        raise HTTPException(
            status_code=502, 
            detail=f"Failed to fetch products from Lamoda: {str(exc)}"
        ) from exc


@router.post("/parse-url", response_model=ProductParseResponse)
async def parse_product_by_url(
    request: ProductParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Парсит товар Lamoda по URL
    
    Принимает URL товара и возвращает распарсенные данные.
    Опционально сохраняет товар в базу данных.
    
    Поддерживает URL вида:
    - https://www.lamoda.kz/p/rtlaek537801/
    - https://www.lamoda.ru/p/he002emklgv2/clothes-hebymango-futbolka/
    """
    return await _parse_single_product(request.url, request.save_to_db, db, current_user)


@router.post("/parse-urls", response_model=BatchParseResponse)
async def parse_multiple_products_by_urls(
    request: BatchParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Массовый парсинг товаров Lamoda по списку URL
    
    Принимает список URL товаров и возвращает результаты парсинга для каждого.
    Опционально сохраняет товары в базу данных.
    
    Максимум 10 URL за один запрос для предотвращения перегрузки.
    """
    results = []
    successful_count = 0
    failed_count = 0
    
    # Создаем задачи для параллельного выполнения
    tasks = []
    for url in request.urls:
        task = _parse_single_product(str(url), request.save_to_db, db, current_user)
        tasks.append((str(url), task))
    
    # Выполняем парсинг с ограничением на одновременные подключения
    semaphore = asyncio.Semaphore(3)  # Максимум 3 одновременных запроса
    
    async def parse_with_semaphore(url: str, task):
        async with semaphore:
            try:
                result = await task
                return BatchParseResult(
                    url=url,
                    success=result.success,
                    message=result.message,
                    product=result.product,
                    item_id=result.item_id,
                    error=None if result.success else result.message
                )
            except Exception as e:
                return BatchParseResult(
                    url=url,
                    success=False,
                    message=f"Ошибка при парсинге: {str(e)}",
                    product=None,
                    item_id=None,
                    error=str(e)
                )
    
    # Запускаем все задачи параллельно
    parse_tasks = [parse_with_semaphore(url, task) for url, task in tasks]
    results = await asyncio.gather(*parse_tasks)
    
    # Подсчитываем статистику
    for result in results:
        if result.success:
            successful_count += 1
        else:
            failed_count += 1
    
    summary = f"Успешно распарсено {successful_count} из {len(request.urls)} товаров"
    if failed_count > 0:
        summary += f", {failed_count} ошибок"
    
    return BatchParseResponse(
        total_requested=len(request.urls),
        successful=successful_count,
        failed=failed_count,
        results=results,
        summary=summary
    )


@router.post("/batch-search", response_model=BatchSearchResponse)
async def batch_search_and_add(
    request: BatchSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Поиск товаров по запросу и массовое добавление в каталог
    
    Выполняет поиск товаров на Lamoda по ключевому слову и 
    автоматически добавляет найденные товары в базу данных.
    
    Максимум 50 товаров за один запрос.
    """
    # Validate domain
    if request.domain not in LAMODA_DOMAINS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported domain: {request.domain}. Use one of: {list(LAMODA_DOMAINS.keys())}"
        )
    
    try:
        # Новый улучшенный поиск: сначала каталог, затем карточки
        products = await parse_catalog_items(
            request.query,
            domain=request.domain,
            limit=request.limit,
            concurrency=5,
        )
        
        if not products:
            return BatchSearchResponse(
                query=request.query,
                total_found=0,
                requested_limit=request.limit,
                successful=0,
                failed=0,
                products=[],
                summary=f"По запросу '{request.query}' товары не найдены"
            )
        
        added_products = []
        successful_count = 0
        failed_count = 0
        
        # Если нужно сохранять в БД, добавляем товары
        if request.save_to_db:
            for product in products:
                try:
                    # Проверяем, есть ли уже товар с таким SKU
                    existing_item = db.query(Item).filter(Item.source_sku == product.sku).first()
                    
                    if existing_item:
                        # Обновляем существующий товар
                        existing_item.name = product.name
                        existing_item.brand = product.brand
                        existing_item.price = product.price
                        existing_item.old_price = product.old_price
                        existing_item.image_url = product.image_url
                        existing_item.source_url = product.url
                        existing_item.updated_at = datetime.utcnow()
                        existing_item.source = "lamoda"
                        
                        db.commit()
                        db.refresh(existing_item)
                        item_id = existing_item.id
                    else:
                        # Создаем новый товар
                        new_item = Item(
                            name=product.name,
                            brand=product.brand,
                            price=product.price,
                            old_price=product.old_price,
                            image_url=product.image_url,
                            source_url=product.url,
                            source_sku=product.sku,
                            source="lamoda",
                            created_at=datetime.utcnow()
                        )
                        
                        db.add(new_item)
                        db.commit()
                        db.refresh(new_item)
                        item_id = new_item.id
                        
                        # Сохраняем изображения
                        for img_url in product.image_urls:
                            if img_url:
                                new_image = ItemImage(
                                    item_id=new_item.id,
                                    image_url=img_url
                                )
                                db.add(new_image)
                        
                        db.commit()
                    
                    # Добавляем в результат
                    added_products.append(ProductDetailsOut(
                        sku=product.sku,
                        name=product.name,
                        brand=product.brand,
                        price=product.price,
                        old_price=product.old_price,
                        url=product.url,
                        image_url=product.image_url,
                        image_urls=product.image_urls,
                        type=getattr(product, 'type', None),
                        description=getattr(product, 'description', None)
                    ))
                    successful_count += 1
                    
                except Exception as e:
                    print(f"Ошибка добавления товара {product.sku}: {e}")
                    failed_count += 1
                    continue
        else:
            # Если не сохраняем в БД, просто возвращаем найденные товары
            for product in products:
                added_products.append(ProductDetailsOut(
                    sku=product.sku,
                    name=product.name,
                    brand=product.brand,
                    price=product.price,
                    old_price=product.old_price,
                    url=product.url,
                    image_url=product.image_url,
                    image_urls=product.image_urls,
                    type=getattr(product, 'type', None),
                    description=getattr(product, 'description', None)
                ))
                successful_count += 1
        
        # Формируем summary
        if request.save_to_db:
            summary = f"По запросу '{request.query}' найдено {len(products)} товаров, успешно добавлено {successful_count}"
            if failed_count > 0:
                summary += f", {failed_count} ошибок"
        else:
            summary = f"По запросу '{request.query}' найдено {len(products)} товаров (без сохранения в БД)"
        
        return BatchSearchResponse(
            query=request.query,
            total_found=len(products),
            requested_limit=request.limit,
            successful=successful_count,
            failed=failed_count,
            products=added_products,
            summary=summary
        )
        
    except Exception as exc:
        print(f"Batch search error: {exc}")
        raise HTTPException(
            status_code=502, 
            detail=f"Failed to search and add products from Lamoda: {str(exc)}"
        ) from exc


async def _parse_single_product(
    url: str, 
    save_to_db: bool, 
    db: Session, 
    current_user: User
) -> ProductParseResponse:
    """Внутренняя функция для парсинга одного товара"""
    try:
        # Определяем домен из URL
        url_str = str(url)
        domain = "kz"
        if ".ru/" in url_str:
            domain = "ru"
        elif ".by/" in url_str:
            domain = "by"
        
        # Инициализируем парсер
        parser = ModernLamodaParser(domain=domain)
        
        # Парсим товар
        product_details = await parser.parse_product_by_url(url_str)
        
        if not product_details:
            await parser.close()
            return ProductParseResponse(
                success=False,
                message="Не удалось распарсить товар по указанному URL"
            )
        
        # Конвертируем в стандартный Product
        product = parser.to_product(product_details)
        
        item_id = None
        
        # Сохраняем в базу данных если требуется
        if save_to_db:
            try:
                # Проверяем, есть ли уже товар с таким SKU
                existing_item = db.query(Item).filter(Item.source_sku == product.sku).first()
                
                if existing_item:
                    # Обновляем существующий товар
                    existing_item.name = product.name
                    existing_item.brand = product.brand
                    existing_item.price = product.price
                    existing_item.old_price = product.old_price
                    existing_item.image_url = product.image_url
                    existing_item.source_url = product.url
                    existing_item.updated_at = datetime.utcnow()
                    existing_item.source = "lamoda"
                    
                    db.commit()
                    db.refresh(existing_item)
                    item_id = existing_item.id
                    message = f"Товар {product.sku} обновлен в базе данных"
                else:
                    # Создаем новый товар
                    new_item = Item(
                        name=product.name,
                        brand=product.brand,
                        price=product.price,
                        old_price=product.old_price,
                        image_url=product.image_url,
                        source_url=product.url,
                        source_sku=product.sku,
                        source="lamoda",
                        created_at=datetime.utcnow()
                    )
                    
                    db.add(new_item)
                    db.commit()
                    db.refresh(new_item)
                    item_id = new_item.id
                    
                    # Сохраняем изображения
                    for img_url in product.image_urls:
                        if img_url:  # Проверяем что URL не пустой
                            new_image = ItemImage(
                                item_id=new_item.id,
                                image_url=img_url
                            )
                            db.add(new_image)
                    
                    db.commit()
                    message = f"Товар {product.sku} добавлен в базу данных с {len(product.image_urls)} изображениями"
                
            except Exception as db_error:
                print(f"Ошибка сохранения в БД: {db_error}")
                db.rollback()
                message = f"Товар распарсен, но произошла ошибка при сохранении в БД: {str(db_error)}"
        else:
            message = "Товар успешно распарсен (не сохранен в БД)"
        
        await parser.close()
        
        return ProductParseResponse(
            success=True,
            message=message,
            product=ProductDetailsOut(
                sku=product.sku,
                name=product.name,
                brand=product.brand,
                price=product.price,
                old_price=product.old_price,
                url=product.url,
                image_url=product.image_url,
                image_urls=product.image_urls,
                type=getattr(product_details, 'type', None),
            ),
            item_id=item_id
        )
        
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return ProductParseResponse(
            success=False,
            message=f"Ошибка при парсинге товара: {str(e)}"
        )


@router.get("/domains", response_model=DomainInfo)
async def get_supported_domains():
    """Получить список поддерживаемых доменов Lamoda"""
    return DomainInfo(
        domains=list(LAMODA_DOMAINS.keys()),
        details=LAMODA_DOMAINS
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка работоспособности парсера"""
    return HealthResponse(
        status="ok",
        message="Lamoda parser is working",
        supported_domains=list(LAMODA_DOMAINS.keys())
    ) 