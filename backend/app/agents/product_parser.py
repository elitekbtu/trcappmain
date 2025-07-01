#!/usr/bin/env python3
"""
Modern Lamoda Product Parser

Парсер отдельных товаров по URL, адаптированный из старого парсера
но с современными селекторами и методами извлечения данных.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .parser_agent import Product


@dataclass
class ProductDetails:
    """Расширенные данные о товаре с дополнительными полями"""
    sku: str
    name: str
    brand: str
    price: float
    old_price: Optional[float]
    url: str
    image_url: str
    image_urls: List[str]
    # Дополнительные поля
    description: Optional[str] = None
    type: Optional[str] = None
    color: Optional[str] = None
    sizes: List[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None


class ModernLamodaParser:
    """Современный парсер товаров Lamoda по URL"""
    
    def __init__(self, domain: str = "kz"):
        self.domain = domain
        self.base_url = f"https://www.lamoda.{domain}"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self.session = None

    async def _get_session(self):
        """Получить или создать HTTP сессию"""
        if self.session is None:
            timeout = httpx.Timeout(30.0)
            self.session = httpx.AsyncClient(
                headers=self.headers,
                timeout=timeout,
                follow_redirects=True
            )
        return self.session

    async def parse_product_by_url(self, url: str) -> Optional[ProductDetails]:
        """Парсит товар Lamoda по URL"""
        try:
            print(f"🔍 Parsing product: {url}")
            
            session = await self._get_session()
            response = await session.get(url)
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code} for {url}")
                return None
            
            print(f"✅ Successfully fetched page (length: {len(response.text)})")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Пробуем различные методы извлечения данных
            product = self._parse_from_json(soup, url) or self._parse_from_html(soup, url)
            
            if product:
                print(f"✅ Successfully parsed: {product.name} by {product.brand}")
                return product
            else:
                print(f"❌ Failed to parse product from {url}")
                return None
                
        except Exception as e:
            print(f"❌ Error parsing {url}: {e}")
            return None

    def _parse_from_json(self, soup: BeautifulSoup, url: str) -> Optional[ProductDetails]:
        """Извлекает данные товара из JSON в скриптах"""
        try:
            scripts = soup.find_all('script')
            
            for script in scripts:
                if not script.string:
                    continue
                    
                content = script.string.strip()
                
                # Ищем JSON-LD структуру (schema.org)
                if '"@type": "Product"' in content:
                    product = self._parse_json_ld_product(content, url)
                    if product:
                        return product
                
                # Ищем __NUXT__ данные
                if 'var __NUXT__' in content:
                    product = self._parse_nuxt_data(content, url)
                    if product:
                        return product
            
            return None
            
        except Exception as e:
            print(f"❌ Error parsing JSON: {e}")
            return None

    def _parse_json_ld_product(self, content: str, url: str) -> Optional[ProductDetails]:
        """Парсит товар из JSON-LD структуры"""
        try:
            # Ищем JSON объект с продуктом
            json_match = re.search(r'\[?\{[^}]*"@type":\s*"Product"[^}]*\}[^}]*\}?\]?', content)
            if not json_match:
                return None
            
            # Очищаем от HTML entities
            json_str = json_match.group(0)
            json_str = json_str.replace('&quot;', '"').replace('&amp;', '&')
            
            # Убираем массив если есть
            if json_str.startswith('[') and json_str.endswith(']'):
                json_str = json_str[1:-1]
            
            data = json.loads(json_str)
            
            # Извлекаем данные
            brand = "Unknown"
            if 'brand' in data and isinstance(data['brand'], dict):
                brand = data['brand'].get('name', 'Unknown').replace('"', '')
            
            name = data.get('name', 'Unknown Product').replace('"', '')
            
            # Цена
            price = 0.0
            old_price = None
            
            if 'offers' in data and isinstance(data['offers'], dict):
                offers = data['offers']
                if 'price' in offers:
                    try:
                        price = float(offers['price'])
                    except (ValueError, TypeError):
                        pass
            
            # SKU
            sku = data.get('sku', self._generate_sku_from_url(url))
            
            # Изображения (пока пустые, будем искать в HTML)
            image_urls = []
            
            return ProductDetails(
                sku=sku,
                name=name,
                brand=brand,
                price=price,
                old_price=old_price,
                url=url,
                image_url="",
                image_urls=image_urls,
                description=data.get('description'),
                type=self._extract_type_from_name(name)
            )
            
        except Exception as e:
            print(f"❌ Error parsing JSON-LD: {e}")
            return None

    def _parse_nuxt_data(self, content: str, url: str) -> Optional[ProductDetails]:
        """Парсит товар из NUXT данных"""
        try:
            # Ищем payload в NUXT данных
            nuxt_match = re.search(r'var __NUXT__\s*=\s*({.*?});', content, re.DOTALL)
            if not nuxt_match:
                return None
            
            # Парсим JSON
            nuxt_data = json.loads(nuxt_match.group(1))
            
            # Ищем данные о товаре в различных местах
            payload = nuxt_data.get('payload', {})
            
            # Можем добавить логику для извлечения из NUXT данных
            # Пока возвращаем None, чтобы попробовать HTML парсинг
            return None
            
        except Exception as e:
            print(f"❌ Error parsing NUXT data: {e}")
            return None

    def _parse_from_html(self, soup: BeautifulSoup, url: str) -> Optional[ProductDetails]:
        """Парсит товар из HTML структуры с современными селекторами"""
        try:
            # Извлекаем название и бренд из h1
            h1_tag = soup.find('h1')
            if not h1_tag:
                return None
            
            h1_text = h1_tag.get_text(strip=True)
            print(f"Found h1: {h1_text}")
            
            # Пробуем разделить на бренд и название
            brand = "Unknown"
            name = h1_text
            
            # Если в h1 есть несколько строк, первая обычно бренд
            h1_lines = [line.strip() for line in h1_text.split('\n') if line.strip()]
            if len(h1_lines) >= 2:
                brand = h1_lines[0]
                name = ' '.join(h1_lines[1:])
            else:
                # Если одна строка, пытаемся разделить по известным брендам
                known_brands = ['Nike', 'Adidas', 'Puma', 'Reebok', 'Jordan', 'Converse', 
                               'New Balance', 'Vans', 'Under Armour', 'Asics', 'Mizuno',
                               'Skechers', 'Fila', 'Kappa', 'Umbro', 'Diadora', 'Calvin Klein',
                               'Tommy Hilfiger', 'Lacoste', 'Polo Ralph Lauren', 'Hugo Boss']
                
                for brand_name in known_brands:
                    if h1_text.startswith(brand_name):
                        brand = brand_name
                        name = h1_text[len(brand_name):].strip()
                        break
            
            # Улучшенное извлечение цены из структуры страницы товара
            price = 0.0
            old_price = None
            
            # Сначала пытаемся найти цены в специфичных элементах
            price_info = self._extract_detailed_prices(soup)
            if price_info:
                price = price_info.get('current_price', 0.0)
                old_price = price_info.get('old_price')
            
            # Найдем изображения
            image_urls = []
            
            all_imgs = soup.find_all('img')
            for img in all_imgs:
                src = img.get('src') or img.get('data-src')
                if src and 'lmcdn.ru' in src:
                    # Нормализуем URL
                    if src.startswith('//'):
                        full_url = 'https:' + src
                    elif src.startswith('/'):
                        full_url = 'https://a.lmcdn.ru' + src
                    else:
                        full_url = src
                    
                    if full_url not in image_urls:
                        image_urls.append(full_url)
            
            # Генерируем SKU
            sku = self._generate_sku_from_url(url)
            
            # Извлекаем тип товара
            product_type = self._extract_type_from_name(name)
            
            return ProductDetails(
                sku=sku,
                name=name,
                brand=brand,
                price=price,
                old_price=old_price,
                url=url,
                image_url=image_urls[0] if image_urls else "",
                image_urls=image_urls,
                type=product_type
            )
            
        except Exception as e:
            print(f"❌ Error parsing HTML: {e}")
            return None

    def _extract_detailed_prices(self, soup: BeautifulSoup) -> Optional[Dict[str, Optional[float]]]:
        """Детальное извлечение цен из страницы товара"""
        try:
            price_info = {
                'current_price': None,
                'old_price': None
            }
            
            # Селекторы для страницы товара (не каталога)
            price_selectors = {
                'current': [
                    '[data-testid="price-current"]',
                    '.price-current',
                    '.price__current',
                    '.product-price__current',
                    'span[class*="price"][class*="current"]',
                    'div[class*="price"][class*="current"]'
                ],
                'old': [
                    '[data-testid="price-old"]',
                    '.price-old',
                    '.price__old',
                    '.product-price__old',
                    'span[class*="price"][class*="old"]',
                    'div[class*="price"][class*="old"]'
                ],
                'single': [
                    '[data-testid="price"]',
                    '.price',
                    '.product-price',
                    'span[class*="price"]:not([class*="old"])',
                    'div[class*="price"]:not([class*="old"])'
                ]
            }
            
            # Пытаемся найти актуальную цену
            for selector in price_selectors['current']:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    if price_text and ('₸' in price_text or '₽' in price_text):
                        price = self._extract_price_from_text(price_text)
                        if price:
                            price_info['current_price'] = price
                            break
            
            # Пытаемся найти старую цену
            for selector in price_selectors['old']:
                old_price_elem = soup.select_one(selector)
                if old_price_elem:
                    old_price_text = old_price_elem.get_text(strip=True)
                    if old_price_text and ('₸' in old_price_text or '₽' in old_price_text):
                        old_price = self._extract_price_from_text(old_price_text)
                        if old_price:
                            price_info['old_price'] = old_price
                            break
            
            # Если актуальная цена не найдена, ищем единую цену
            if not price_info['current_price']:
                for selector in price_selectors['single']:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        if price_text and ('₸' in price_text or '₽' in price_text):
                            price = self._extract_price_from_text(price_text)
                            if price:
                                price_info['current_price'] = price
                                break
            
            # Fallback: поиск по всему тексту страницы
            if not price_info['current_price']:
                page_text = soup.get_text()
                price_matches = re.findall(r'(\d{1,3}(?:\s+\d{3})*)\s*[₸₽]', page_text)
                
                if price_matches:
                    prices = []
                    for price_str in price_matches:
                        try:
                            p = float(price_str.replace(' ', ''))
                            if 100 <= p <= 10000000:
                                prices.append(p)
                        except ValueError:
                            continue
                    
                    if prices:
                        prices.sort()
                        price_info['current_price'] = prices[0]
                        if len(prices) > 1:
                            # Берем вторую цену как старую, если она больше
                            potential_old_price = prices[1]
                            if potential_old_price > prices[0]:
                                price_info['old_price'] = potential_old_price
            
            return price_info if price_info['current_price'] else None
            
        except Exception as e:
            print(f"❌ Error extracting detailed prices: {e}")
            return None

    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """Извлечение цены из текста (аналог метода из parser_agent)"""
        if not text:
            return None
        
        # Очищаем от HTML тегов и лишних символов
        text = re.sub(r'<[^>]+>', '', text)
        text = text.strip()
        
        # Убираем валютные символы
        clean_text = text.replace('₸', '').replace('₽', '').replace('р.', '').strip()
        
        # Паттерн для цен с пробелами
        price_pattern = r'\b(\d{1,3}(?:\s+\d{3})*)\b'
        matches = re.findall(price_pattern, clean_text)
        
        if matches:
            price_str = matches[0].replace(' ', '')
            try:
                price = float(price_str)
                if 100 <= price <= 10000000:
                    return price
            except ValueError:
                pass
        
        # Fallback: числа без пробелов
        fallback_pattern = r'\b(\d{3,7})\b'
        fallback_matches = re.findall(fallback_pattern, clean_text)
        
        if fallback_matches:
            for match in fallback_matches:
                try:
                    price = float(match)
                    if 100 <= price <= 10000000:
                        return price
                except ValueError:
                    continue
        
        return None

    def _generate_sku_from_url(self, url: str) -> str:
        """Генерирует SKU из URL"""
        try:
            # Извлекаем код товара из URL
            # Формат: https://www.lamoda.kz/p/mp002xw0zg9n/clothes-terranova-bryuki/
            # Нужен артикул: mp002xw0zg9n
            path_parts = urlparse(url).path.strip('/').split('/')
            
            # Ищем часть после /p/
            if len(path_parts) >= 2 and path_parts[0] == 'p':
                article_code = path_parts[1]
                if len(article_code) >= 8 and article_code.replace('-', '').isalnum():
                    return article_code.upper()
            
            # Fallback - ищем любую длинную алфавитно-цифровую часть
            for part in path_parts:
                if len(part) >= 8 and part.replace('-', '').replace('_', '').isalnum():
                    return part.upper()
            
            # Последний fallback
            return f"PARSE{hash(url) % 100000:05d}"
            
        except Exception:
            return f"UNKNOWN{hash(url) % 100000:05d}"

    def _extract_type_from_name(self, name: str) -> str:
        """Извлекает тип товара из названия"""
        name_lower = name.lower()
        
        # Словарь типов товаров
        type_keywords = {
            'шорты': 'Шорты',
            'кроссовки': 'Кроссовки', 
            'футболка': 'Футболка',
            'платье': 'Платье',
            'брюки': 'Брюки',
            'джинсы': 'Джинсы',
            'куртка': 'Куртка',
            'свитер': 'Свитер',
            'рубашка': 'Рубашка',
            'юбка': 'Юбка',
            'сабо': 'Сабо',
            'кеды': 'Кеды',
            'ботинки': 'Ботинки',
            'сапоги': 'Сапоги'
        }
        
        for keyword, type_name in type_keywords.items():
            if keyword in name_lower:
                return type_name
        
        return "Товар"

    def to_product(self, product_details: ProductDetails) -> Product:
        """Конвертирует ProductDetails в стандартный Product"""
        return Product(
            sku=product_details.sku,
            name=product_details.name,
            brand=product_details.brand,
            price=product_details.price,
            old_price=product_details.old_price,
            url=product_details.url,
            image_url=product_details.image_url,
            image_urls=product_details.image_urls
        )

    async def close(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.aclose()
            self.session = None


# Пример использования
async def test_product_parser():
    """Тестирование парсера товаров"""
    parser = ModernLamodaParser(domain="kz")
    
    # Тестовые URL
    test_urls = [
        "https://www.lamoda.kz/p/rtlaek537801/",  # Nike шорты
    ]
    
    for url in test_urls:
        product = await parser.parse_product_by_url(url)
        if product:
            print(f"\n✅ SUCCESS:")
            print(f"   SKU: {product.sku}")
            print(f"   Name: {product.name}")
            print(f"   Brand: {product.brand}")
            print(f"   Price: {product.price}₸")
            if product.old_price:
                print(f"   Old Price: {product.old_price}₸")
            print(f"   Type: {product.type}")
            print(f"   Images: {len(product.image_urls)}")
        else:
            print(f"❌ FAILED to parse {url}")
    
    await parser.close()


if __name__ == "__main__":
    asyncio.run(test_product_parser()) 