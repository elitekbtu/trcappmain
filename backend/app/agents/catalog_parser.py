#!/usr/bin/env python3
"""High-level Lamoda catalog parser.

1. Получает список товаров из страницы поиска (каталога) Lamoda
   с помощью `LamodaParser` (по ключевому слову).
2. Берёт реальные URL каждого товара и дополнительно парсит
   каждую карточку при помощи `ModernLamodaParser`,
   тем самым извлекая расширенные и более точные данные.

Использование как CLI:
    python -m app.agents.catalog_parser "nike кроссовки" --limit 20 --domain kz

Пример вызова как корутины:
    results = await parse_catalog_items("шорты спортивные", domain="kz", limit=15)

`parse_catalog_items` возвращает список `ProductDetails` (см. product_parser)."""
from __future__ import annotations

import asyncio
from typing import List, Optional

from .parser_agent import LamodaParser, Product
from .product_parser import ModernLamodaParser, ProductDetails

__all__ = ["parse_catalog_items"]


async def _parse_single_item(parser: ModernLamodaParser, url: str, sem: asyncio.Semaphore) -> Optional[ProductDetails]:
    """Внутренний хелпер для ограниченного параллельного парсинга карточек."""
    async with sem:
        try:
            return await parser.parse_product_by_url(url)
        except Exception as exc:
            print(f"[item-error] {url}: {exc}")
            return None


async def parse_catalog_items(query: str, *, domain: str = "kz", limit: int = 20, concurrency: int = 5) -> List[ProductDetails]:
    """Полный цикл парсинга: каталог → карточки товаров.

    Args:
        query: Поисковый запрос (например, "nike кроссовки").
        domain: Домен Lamoda (`kz`, `ru`, `by`).
        limit: Максимум товаров для детального парсинга.
        concurrency: Количество одновременных запросов к карточкам.
    """
    # 1. Получаем список товаров из каталога
    search_parser = LamodaParser(domain=domain)
    try:
        catalog_products: List[Product] = await search_parser.afetch_search(query, limit=limit)
    finally:
        await search_parser.close()

    if not catalog_products:
        print("Found 0 products via real search")
        return []

    print(f"Found {len(catalog_products)} products via real search")

    # 2. Формируем список URL карточек (пропускаем пустые и фейковые)
    product_urls = []
    for p in catalog_products:
        if p.url and p.url.startswith('http') and '/p/' in p.url:
            product_urls.append(p.url)
    
    if not product_urls:
        print("No products have valid URLs for detailed parsing")
        print("Found products from catalog search (for reference only):")
        for i, p in enumerate(catalog_products[:5], 1):
            print(f"  {i}. {p.brand} - {p.name} - {p.price}₸ (URL: {p.url or 'NO URL'})")
        return []

    print(f"Products with valid URLs: {len(product_urls)}/{len(catalog_products)}")
    # 3. Детальное парсирование карточек
    item_parser = ModernLamodaParser(domain=domain)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    try:
        tasks = [_parse_single_item(item_parser, url, semaphore) for url in product_urls]
        details: List[Optional[ProductDetails]] = await asyncio.gather(*tasks)
    finally:
        await item_parser.close()

    # 4. Фильтруем неуспехи и обрезаем до лимита
    return [d for d in details if d][:limit]


# CLI интерфейс --------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    from dataclasses import asdict
    import json

    cli = argparse.ArgumentParser(description="Lamoda catalog → item parser")
    cli.add_argument("query", help="Поисковый запрос, напр. 'nike кроссовки'")
    cli.add_argument("--domain", choices=["kz", "ru", "by"], default="kz", help="Домен Lamoda")
    cli.add_argument("--limit", type=int, default=20, help="Максимум товаров")
    cli.add_argument("--concurrency", type=int, default=5, help="Одновременные запросы к карточкам")
    args = cli.parse_args()

    async def _main():
        results = await parse_catalog_items(args.query, domain=args.domain, limit=args.limit, concurrency=args.concurrency)
        print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2))

    asyncio.run(_main()) 