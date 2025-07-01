#!/usr/bin/env python3
"""
Lamoda Parser Agent

Парсер для извлечения товаров с Lamoda.
Поддерживает несколько стратегий парсинга и домены .ru, .kz, .by
"""

import asyncio
import json
import re
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse, parse_qs, quote

import httpx
from bs4 import BeautifulSoup

# Конфигурация доменов
LAMODA_DOMAINS = {
    "ru": {"host": "https://www.lamoda.ru", "currency": "₽"},
    "kz": {"host": "https://www.lamoda.kz", "currency": "₸"},
    "by": {"host": "https://www.lamoda.by", "currency": "р."}
}

@dataclass
class Product:
    sku: str
    name: str
    brand: str
    price: float
    old_price: Optional[float]
    url: str
    image_url: str  # Основное изображение для обратной совместимости
    image_urls: List[str]  # Список всех изображений товара


class LamodaParser:
    def __init__(self, domain: str = "ru"):
        if domain not in LAMODA_DOMAINS:
            raise ValueError(f"Unsupported domain: {domain}")
        
        self.domain = domain
        self.base_url = LAMODA_DOMAINS[domain]["host"]
        self.currency = LAMODA_DOMAINS[domain]["currency"]
        
        # Более реалистичные заголовки для обхода блокировок
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8,kk;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        # Создаем сессию для повторного использования соединений
        self.session = None

    async def _get_session(self):
        """Получить или создать HTTP сессию"""
        if self.session is None:
            timeout = httpx.Timeout(30.0, connect=10.0)
            self.session = httpx.AsyncClient(
                headers=self.headers,
                timeout=timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self.session

    async def _make_request(self, url: str, **kwargs) -> Optional[httpx.Response]:
        """Выполнить HTTP запрос с обработкой ошибок"""
        session = await self._get_session()
        
        try:
            # Добавляем случайную задержку для имитации человеческого поведения
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            response = await session.get(url, **kwargs)
            
            if response.status_code == 429:  # Too Many Requests
                print(f"Rate limited, waiting...")
                await asyncio.sleep(random.uniform(5, 10))
                return await self._make_request(url, **kwargs)
            
            if response.status_code in [200, 301, 302]:
                return response
            else:
                print(f"HTTP {response.status_code} for {url}")
                return None
            
        except Exception as e:
            print(f"Request failed for {url}: {e}")
            return None

    def _extract_price(self, text: str) -> Optional[float]:
        """Улучшенное извлечение цены из текста с учетом структуры Lamoda"""
        if not text:
            return None
        
        # Очищаем от HTML тегов и лишних символов
        text = re.sub(r'<[^>]+>', '', text)
        text = text.strip()
        
        # Убираем валютные символы но сохраняем контекст
        clean_text = text.replace('₸', '').replace('₽', '').replace('р.', '').strip()
        
        # Паттерн для цен с пробелами (стандартный формат Lamoda)
        # Например: "15 990", "2 350", "125 000"
        price_pattern = r'\b(\d{1,3}(?:\s+\d{3})*)\b'
        
        matches = re.findall(price_pattern, clean_text)
        
        if matches:
            # Берем первое совпадение как основную цену
            price_str = matches[0].replace(' ', '')
            try:
                price = float(price_str)
                # Проверяем разумность цены (от 100 до 10 млн тенге/рублей)
                if 100 <= price <= 10000000:
                    return price
            except ValueError:
                pass
        
        # Fallback: ищем любые числа без пробелов
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

    def _extract_prices_from_element(self, element) -> Optional[Dict[str, Optional[float]]]:
        """Точное извлечение цен из элемента карточки товара на основе реальной структуры Lamoda"""
        try:
            price_info = {
                'current_price': None,
                'old_price': None
            }
            
            # Современные селекторы на основе реальной структуры Lamoda
            price_selectors = {
                'new_price': [
                    '.x-product-card-description__price-new',
                    'span[class*="price-new"]', 
                    'span[class*="price_new"]',
                    '.product-card__price_new'
                ],
                'old_price': [
                    '.x-product-card-description__price-old',
                    '.x-product-card-description__price-second-old',
                    'span[class*="price-old"]',
                    'span[class*="price_old"]',
                    '.product-card__price_old'
                ],
                'single_price': [
                    '.x-product-card-description__price-single',
                    'span[class*="price-single"]',
                    'span[class*="price_single"]',
                    '.product-card__price:not([class*="old"]):not([class*="new"])'
                ]
            }
            
            # Извлекаем новую (актуальную) цену
            for selector in price_selectors['new_price']:
                price_elem = element.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    if price_text and ('₸' in price_text or '₽' in price_text or 'р.' in price_text):
                        price = self._extract_price(price_text)
                        if price:
                            price_info['current_price'] = price
                            break
            
            # Извлекаем старую цену  
            for selector in price_selectors['old_price']:
                old_price_elem = element.select_one(selector)
                if old_price_elem:
                    old_price_text = old_price_elem.get_text(strip=True)
                    if old_price_text and ('₸' in old_price_text or '₽' in old_price_text or 'р.' in old_price_text):
                        old_price = self._extract_price(old_price_text)
                        if old_price:
                            price_info['old_price'] = old_price
                            break
            
            # Если актуальной цены нет, ищем единственную цену
            if not price_info['current_price']:
                for selector in price_selectors['single_price']:
                    price_elem = element.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        if price_text and ('₸' in price_text or '₽' in price_text or 'р.' in price_text):
                            price = self._extract_price(price_text)
                            if price:
                                price_info['current_price'] = price
                                break
            
            # Fallback: ищем любые элементы с ценами в тексте
            if not price_info['current_price']:
                element_text = element.get_text()
                all_price_matches = re.findall(r'(\d{1,3}(?:\s+\d{3})*)\s*[₸₽]', element_text)
                
                if all_price_matches:
                    prices = []
                    for price_str in all_price_matches:
                        try:
                            price = float(price_str.replace(' ', ''))
                            if 100 <= price <= 10000000:
                                prices.append(price)
                        except ValueError:
                            continue
                    
                    if prices:
                        prices.sort()
                        price_info['current_price'] = prices[0]  # Минимальная цена
                        if len(prices) > 1:
                            price_info['old_price'] = prices[-1]  # Максимальная цена
            
            # Проверяем логичность цен
            if price_info['current_price'] and price_info['old_price']:
                # Старая цена должна быть больше новой
                if price_info['old_price'] <= price_info['current_price']:
                    price_info['old_price'] = None
            
            return price_info if price_info['current_price'] else None
            
        except Exception as e:
            print(f"❌ Error extracting prices: {e}")
            return None

    async def _try_real_search(self, query: str, limit: int = 20, page: int = 1) -> List[Product]:
        """Реальный поиск по Lamoda используя структуру из примера"""
        try:
            # Используем реальный URL формат как в примере
            search_url = f"{self.base_url}/catalogsearch/result/"
            params = {
                'q': query,
                'submit': 'y'
            }
            
            if page > 1:
                params['p'] = page
            
            print(f"Searching: {search_url} with query: {query}")
            
            response = await self._make_request(search_url, params=params)
            if not response:
                print("Failed to get response")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Анализируем структуру страницы
            products = self._parse_lamoda_products(soup, limit)
            
            if products:
                print(f"Successfully parsed {len(products)} products")
                return products
            else:
                print("No products found in HTML")
                return []
            
        except Exception as e:
            print(f"Real search failed: {e}")
            return []

    def _parse_lamoda_products(self, soup: BeautifulSoup, limit: int) -> List[Product]:
        """Парсинг товаров из HTML страницы Lamoda на основе реальной структуры"""
        products = []
        
        print("🔍 Analyzing page content...")
        
        # Сначала пытаемся извлечь данные из JSON на странице
        print("🔍 Trying JSON extraction...")
        json_products = self._extract_json_from_scripts(soup, limit)
        if json_products:
            products.extend(json_products)
            print(f"✅ Found {len(json_products)} products from JSON")
        
        # Если JSON не дал результатов, пробуем HTML парсинг
        if not products:
            product_blocks = self._find_product_blocks(soup)
            
            if product_blocks:
                print(f"🔍 Found {len(product_blocks)} product blocks in HTML")
                
                for i, block in enumerate(product_blocks[:limit]):
                    # Пытаемся парсить современную карточку
                    product = self._parse_modern_product_card(block, i)
                    if product:
                        products.append(product)
                        print(f"✅ Parsed from HTML: {product.brand} - {product.name} - {product.price}₸" + 
                              (f" (was {product.old_price}₸)" if product.old_price else ""))
                        
                    if len(products) >= limit:
                        break
        
        # Если всё ещё нет товаров, используем fallback regex парсинг
        if not products:
            print("🔍 Fallback to regex text parsing...")
            products = self._parse_from_regex_fallback(soup, limit)
        
        # Удаляем дубликаты (по SKU, а не по бренду и названию)
        unique_products: list[Product] = []
        seen_skus: set[str] = set()
        for prod in products:
            # Используем SKU как основной критерий уникальности
            if prod.sku not in seen_skus:
                seen_skus.add(prod.sku)
                unique_products.append(prod)

        print(f"📈 Final result after deduplication: {len(unique_products)} products (was {len(products)})")
        return unique_products[:limit]

    def _parse_from_regex_fallback(self, soup: BeautifulSoup, limit: int) -> List[Product]:
        """Fallback regex парсинг из текста страницы"""
        products = []
        page_text = soup.get_text()
        
        # На основе веб-результатов, структура Lamoda такая:
        # "цена₸ старая_цена₸ итоговая_цена ₸ Бренд Название"
        # Пример: "22 70017 29013 832 ₸ PUMA Шорты спортивные ESS 2 COLOR"
        currency_symbol = self.currency
        
        # Обновленные паттерны на основе реальной структуры
        price_patterns = [
            # Основной паттерн: множественные цены + бренд + название
            rf'(\d{{1,3}}(?:\s+\d{{3}})*)\s*(\d{{1,3}}(?:\s+\d{{3}})*)\s*(\d{{1,3}}(?:\s+\d{{3}})*)\s*{re.escape(currency_symbol)}\s+([A-Z][A-Za-z\s&\.]+?)\s+([\w\s\-а-яё\.,"\'()]+?)(?=\d{{1,3}}(?:\s+\d{{3}})*\s*(?:\d{{1,3}}(?:\s+\d{{3}})*\s*)*{re.escape(currency_symbol)}|$)',
            # Паттерн с двумя ценами
            rf'(\d{{1,3}}(?:\s+\d{{3}})*)\s*(\d{{1,3}}(?:\s+\d{{3}})*)\s*{re.escape(currency_symbol)}\s+([A-Z][A-Za-z\s&\.]+?)\s+([\w\s\-а-яё\.,"\'()]+?)(?=\d{{1,3}}(?:\s+\d{{3}})*\s*(?:\d{{1,3}}(?:\s+\d{{3}})*\s*)*{re.escape(currency_symbol)}|$)',
            # Простой паттерн: цена + бренд + название  
            rf'(\d{{1,3}}(?:\s+\d{{3}})*)\s*{re.escape(currency_symbol)}\s+([A-Z][A-Za-z\s&\.]+?)\s+([\w\s\-а-яё\.,"\'()]+?)(?=\d{{1,3}}(?:\s+\d{{3}})*\s*{re.escape(currency_symbol)}|$)',
        ]
        
        print(f"🔍 Searching for products with currency: {currency_symbol}")
        
        for pattern_idx, pattern in enumerate(price_patterns):
            matches = re.findall(pattern, page_text, re.MULTILINE | re.IGNORECASE)
            
            if matches:
                print(f"✅ Found {len(matches)} matches with pattern {pattern_idx + 1}")
                
                for i, match in enumerate(matches[:limit]):
                    try:
                        # Разбираем match в зависимости от паттерна
                        if len(match) == 5:  # Паттерн с 3 ценами
                            price_str_1, price_str_2, price_str_3, brand_raw, name_raw = match
                            # Берем минимальную цену как актуальную
                            prices = [float(p.replace(' ', '')) for p in [price_str_1, price_str_2, price_str_3]]
                            price = min(prices)
                            old_price = max(prices) if max(prices) > min(prices) else None
                        elif len(match) == 4:  # Паттерн с 2 ценами
                            price_str_1, price_str_2, brand_raw, name_raw = match
                            price1 = float(price_str_1.replace(' ', ''))
                            price2 = float(price_str_2.replace(' ', ''))
                            price = min(price1, price2)
                            old_price = max(price1, price2) if price1 != price2 else None
                        else:  # Простой паттерн с 1 ценой
                            price_str, brand_raw, name_raw = match
                            price = float(price_str.replace(' ', ''))
                            old_price = None
                        
                        # Проверяем разумность цены
                        if price < 100 or price > 999999:
                            continue
                        
                        # Очищаем бренд
                        brand = self._clean_brand(brand_raw.strip())
                        if not brand or len(brand) < 2:
                            continue
                        
                        # Очищаем название
                        name = self._clean_name(name_raw.strip())
                        if not name or len(name) < 3:
                            continue
                        
                        # Генерируем SKU
                        sku = f"LMD{self.domain.upper()}{len(products) + 1:04d}"
                        
                        # Пропускаем товары без реальных URL в regex парсинге
                        continue
                        
                    except Exception as e:
                        print(f"❌ Error parsing match {i}: {e}")
                        continue
                
                if products:
                    break  # Если нашли товары, не пробуем другие паттерны
        
        return products

    def _clean_brand(self, brand_raw: str) -> str:
        """Очистка названия бренда"""
        # Известные бренды
        known_brands = [
            'Nike', 'Adidas', 'Puma', 'Reebok', 'Jordan', 'Converse', 'New Balance', 
            'Vans', 'Under Armour', 'Asics', 'Mizuno', 'Skechers', 'Fila', 'Kappa', 
            'Umbro', 'Diadora', 'Calvin Klein', 'Tommy Hilfiger', 'Lacoste', 'Hugo Boss',
            'Demix', 'Outventure', 'Baon', 'Befree', 'Mango', 'Zara', 'H&M', 'Uniqlo',
            'Euphoria', 'Profit', 'Terranova', 'Pepe Jeans', 'Marco Tozzi', 'Tamaris',
            'Founds', 'Nume', 'Shoiberg', 'T.Taccardi', 'Abricot', 'Pierre Cardin'
        ]
        
        # Ищем точное совпадение
        brand_words = brand_raw.split()
        for word in brand_words:
            for known_brand in known_brands:
                if word.lower() == known_brand.lower():
                    return known_brand
        
        # Ищем частичное совпадение
        for known_brand in known_brands:
            if known_brand.lower() in brand_raw.lower():
                return known_brand
        
        # Возвращаем первое слово как бренд
        first_word = brand_words[0] if brand_words else brand_raw
        return first_word.strip()

    def _clean_name(self, name_raw: str) -> str:
        """Очистка названия товара"""
        # Удаляем лишние символы и числа в конце
        name = re.sub(r'\s+\d+\s*$', '', name_raw)  # Убираем числа в конце
        name = re.sub(r'\s{2,}', ' ', name)  # Убираем множественные пробелы
        name = name.strip()
        
        # Ограничиваем длину
        if len(name) > 80:
            name = name[:80].strip()
        
        return name

    def _find_product_images(self, soup: BeautifulSoup, brand: str, name: str) -> tuple[str, List[str]]:
        """Поиск изображений товара на странице"""
        image_url = ""
        image_urls = []
        
        try:
            brand_lower = brand.lower()
            # Ограничимся первыми несколькими словами названия для поиска в alt
            name_tokens = [t.lower() for t in name.split()[:3]]

            img_tags = soup.find_all('img')

            candidate_urls: list[str] = []  # Изображения, которые совпали по alt/brand/name
            fallback_urls: list[str] = []   # Все подходящие изображения (на случай отсутствия совпадений)

            for img in img_tags:
                src = img.get('src') or img.get('data-src') or img.get('data-original')
                if not src:
                    continue

                # Нормализуем URL
                if src.startswith('//'):
                    full_url = 'https:' + src
                elif src.startswith('/'):
                    full_url = urljoin(self.base_url, src)
                else:
                    full_url = src

                if not full_url or 'lmcdn.ru' not in full_url:
                    continue

                if not any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    continue

                # Проверяем alt-текст, чтобы понять принадлежит ли изображение бренду/товару
                alt_text = (img.get('alt') or '').lower()

                matches_brand = brand_lower in alt_text if brand_lower else False
                matches_name = any(tok in alt_text for tok in name_tokens) if name_tokens else False

                if (matches_brand or matches_name) and full_url not in candidate_urls:
                    candidate_urls.append(full_url)
                elif full_url not in fallback_urls:
                    fallback_urls.append(full_url)

            # Если нашли совпадения по alt/brand/name – используем их, иначе fallback
            final_urls = candidate_urls if candidate_urls else fallback_urls

            if final_urls:
                image_url = final_urls[0]
                image_urls.extend(final_urls)
        
        except Exception as e:
            print(f"❌ Error finding images: {e}")
        
        return image_url, image_urls

    def _extract_json_from_scripts(self, soup: BeautifulSoup, limit: int) -> List[Product]:
        """Извлечение товаров из JSON данных в скриптах страницы"""
        products = []

        def _find_products_array(text: str) -> Optional[str]:
            """Найти и вернуть JSON-строку массива products с балансировкой скобок"""
            key = '"products"'
            start_key = text.find(key)
            if start_key == -1:
                return None
            # ищем первую открывающую квадратную скобку после ключа
            array_start = text.find('[', start_key)
            if array_start == -1:
                return None
            depth = 0
            for idx in range(array_start, len(text)):
                ch = text[idx]
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        return text[array_start:idx + 1]
            return None
        
        try:
            # Ищем различные паттерны со встроенными JSON данными
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if not script.string:
                    continue
                    
                script_content = script.string.strip()

                # 1) Попытка найти products через helper (поддержка __NUXT__)
                if '"products"' in script_content:
                    products_json_str = _find_products_array(script_content)
                    if products_json_str:
                        try:
                            products_data = json.loads(products_json_str)
                            extracted = self._extract_products_from_lamoda_json(products_data, limit)
                            if extracted:
                                products.extend(extracted)
                                if len(products) >= limit:
                                    return products[:limit]
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON decode error (products array): {e}")
                            # fallthrough to regex strategies
                
                # Паттерны для поиска JSON с товарами (старые методы)
                json_patterns = [
                    # Основной паттерн для Lamoda
                    r'"products"\s*:\s*(\[[\s\S]*?\])',
                    r'window\.__INITIAL_STATE__\s*=\s*({[\s\S]*?});',
                    r'window\.dataLayer\s*=\s*(\[[\s\S]*?\]);',
                    r'window\.__NEXT_DATA__\s*=\s*({[\s\S]*?});',
                    # Дополнительные паттерны
                    r'catalogsearch.*?"products"\s*:\s*(\[[\s\S]*?\])',
                    r'"catalog"\s*:\s*{[\s\S]*?"items"\s*:\s*(\[[\s\S]*?\])',
                ]
                
                for pattern in json_patterns:
                    matches = re.findall(pattern, script_content, re.DOTALL)
                    
                    for match in matches:
                        try:
                            # Если это массив товаров
                            if match.strip().startswith('['):
                                products_data = json.loads(match)
                                extracted = self._extract_products_from_lamoda_json(products_data, limit - len(products))
                                if extracted:
                                    products.extend(extracted)
                                    if len(products) >= limit:
                                        return products[:limit]
                                    
                            # Если это объект с товарами
                            else:
                                data = json.loads(match)
                                extracted = self._find_products_in_object(data, limit - len(products))
                                if extracted:
                                    products.extend(extracted)
                                    if len(products) >= limit:
                                        return products[:limit]
                                
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON decode error: {e}")
                            continue
                        except Exception as e:
                            print(f"❌ Error processing JSON: {e}")
                            continue
                
                if len(products) >= limit:
                    break
        
        except Exception as e:
            print(f"❌ Error extracting JSON from scripts: {e}")
        
        return products[:limit]

    def _extract_products_from_lamoda_json(self, products_data: list, limit: int) -> List[Product]:
        """Извлечение товаров из JSON массива Lamoda"""
        products = []
        
        for item in products_data[:limit]:
            try:
                product = self._parse_lamoda_product_json(item)
                if product:
                    products.append(product)
            except Exception as e:
                print(f"❌ Error parsing product JSON: {e}")
                continue
        
        return products

    def _parse_lamoda_product_json(self, item: dict) -> Optional[Product]:
        """Парсинг одного товара из JSON структуры Lamoda"""
        try:
            # Извлекаем основные данные
            sku = item.get('sku', '')
            name = item.get('name', '')
            

            
            # Бренд из объекта brand
            brand = "Unknown"
            if 'brand' in item and isinstance(item['brand'], dict):
                brand = item['brand'].get('name', 'Unknown')
            
            # Цена
            price = item.get('price_amount', 0)
            if isinstance(price, str):
                try:
                    price = float(price)
                except ValueError:
                    price = 0
            
            # Старая цена
            old_price = item.get('old_price_amount')
            if old_price and isinstance(old_price, str):
                try:
                    old_price = float(old_price)
                except ValueError:
                    old_price = None
            
            # URL товара - проверяем разные поля
            url = ""
            
            # Сначала проверяем прямое поле url
            if 'url' in item and item['url']:
                candidate_url = item['url']
                if candidate_url.startswith('/'):
                    url = f"{self.base_url}{candidate_url}"
                elif candidate_url.startswith('http'):
                    url = candidate_url
            
            # Если нет, строим URL из SKU + seo_tail (правильный формат Lamoda)
            if not url and sku:
                seo_tail = item.get('seo_tail', '')
                if seo_tail:
                    # Формат: /p/{sku}/{seo_tail}/
                    url = f"{self.base_url}/p/{sku.lower()}/{seo_tail}/"
                else:
                    # Только SKU
                    url = f"{self.base_url}/p/{sku.lower()}/"
            
            # Fallback: используем только seo_tail если нет SKU
            if not url:
                seo_tail = item.get('seo_tail', '')
                if seo_tail and len(seo_tail) > 5:
                    if seo_tail.startswith('/'):
                        url = f"{self.base_url}{seo_tail}"
                    else:
                        url = f"{self.base_url}/p/{seo_tail}/"
            

            
            # Если URL не найден, пропускаем товар
            if not url:
                print(f"⚠️ Skipping product {sku} - no URL found")
                return None
            
            # Изображения
            image_url = ""
            image_urls = []
            
            # Основное изображение
            thumbnail = item.get('thumbnail', '')
            if thumbnail:
                if thumbnail.startswith('/'):
                    image_url_raw = f"https://a.lmcdn.ru{thumbnail}"
                else:
                    image_url_raw = thumbnail
                image_url = image_url_raw
                image_urls.append(image_url)
            
            # Дополнительные изображения из галереи
            gallery = item.get('gallery', [])
            if isinstance(gallery, list):
                for img_path in gallery:
                    if img_path and img_path.startswith('/'):
                        full_img_url = f"https://a.lmcdn.ru{img_path}"
                        if full_img_url not in image_urls:
                            image_urls.append(full_img_url)
            
            # Проверяем минимальные требования
            if not sku or not name or price <= 0:

                return None
            

            
            return Product(
                sku=sku,
                name=name,
                brand=brand,
                price=price,
                old_price=old_price,
                url=url,
                image_url=image_url,
                image_urls=image_urls
            )
            
        except Exception as e:
            print(f"❌ Error parsing Lamoda product JSON: {e}")
            return None

    def _find_products_in_object(self, data: dict, limit: int) -> List[Product]:
        """Рекурсивный поиск товаров в JSON объекте"""
        products = []
        
        def search_recursive(obj, path=""):
            nonlocal products
            
            if len(products) >= limit:
                return
                
            if isinstance(obj, dict):
                # Ищем ключи которые могут содержать товары
                product_keys = ['products', 'items', 'catalog', 'results', 'data']
                for key in product_keys:
                    if key in obj and isinstance(obj[key], list):
                        extracted = self._extract_products_from_lamoda_json(obj[key], limit - len(products))
                        products.extend(extracted)
                        if len(products) >= limit:
                            return
                
                # Рекурсивно проверяем другие ключи
                for key, value in obj.items():
                    if key not in product_keys and len(products) < limit:
                        search_recursive(value, f"{path}.{key}")
                        
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if len(products) >= limit:
                        break
                    search_recursive(item, f"{path}[{i}]")
        
        search_recursive(data)
        return products

    def _find_product_blocks(self, soup: BeautifulSoup) -> List:
        """Найти блоки товаров в HTML"""
        # Попробуем различные селекторы, начиная с наиболее специфичных
        selectors = [
            # Селекторы для современного Lamoda
            'a[href*="/p/"]',  # Прямые ссылки на товары
            'div[class*="product"] a[href]',  # Ссылки внутри блоков товаров
            'article a[href]',  # Ссылки в article элементах
            '.product-card a[href]',  # Старые селекторы
            '.product-card',
            '.product-item',
            '.catalog-item',
            '.item-card',
            # Селекторы на основе классов
            '[class*="product"]',
            '[class*="item"]',
            '[class*="card"]',
            # Структурные селекторы
            'article',
            '.grid-item',
            'li[class*="item"]',
            # Fallback селекторы
            'div[data-*]',
        ]
        
        for selector in selectors:
            blocks = soup.select(selector)
            if blocks and len(blocks) > 3:  # Должно быть хотя бы несколько товаров
                print(f"Found product blocks with selector: {selector}")
                return blocks
        
        return []

    def _parse_modern_product_card(self, element, index: int) -> Optional[Product]:
        """Парсинг современной карточки товара Lamoda"""
        try:
            # Различные стратегии извлечения данных
            product_data = {
                'name': None,
                'brand': None,
                'price': None,
                'old_price': None,
                'url': None,
                'image_url': None,
                'image_urls': []
            }
            
            # Стратегия 1: Извлечение названия
            name_selectors = [
                'h3[class*="title"]',
                'div[class*="title"]',
                'span[class*="title"]',
                '[data-testid*="title"]',
                '[data-testid*="name"]',
                'h1, h2, h3, h4',
                '.product-card__product-name',  # Старый селектор
            ]
            
            for selector in name_selectors:
                name_elem = element.select_one(selector)
                if name_elem:
                    name_text = name_elem.get_text(strip=True)
                    if name_text and len(name_text) > 3 and name_text != "Product":
                        product_data['name'] = name_text[:100]  # Ограничиваем длину
                        break
            
            # Стратегия 2: Извлечение бренда
            brand_selectors = [
                'span[class*="brand"]',
                'div[class*="brand"]',
                '[data-testid*="brand"]',
                '.product-card__brand-name',  # Старый селектор
            ]
            
            for selector in brand_selectors:
                brand_elem = element.select_one(selector)
                if brand_elem:
                    brand_text = brand_elem.get_text(strip=True)
                    if brand_text and len(brand_text) > 1 and brand_text != "Unknown":
                        product_data['brand'] = brand_text
                        break
            
            # Если бренд не найден, пытаемся извлечь из названия
            if not product_data['brand'] and product_data['name']:
                known_brands = ['Nike', 'Adidas', 'Puma', 'Reebok', 'Jordan', 'Converse', 
                               'New Balance', 'Vans', 'Under Armour', 'Asics', 'Mizuno',
                               'Skechers', 'Fila', 'Kappa', 'Umbro', 'Diadora', 'Calvin Klein',
                               'Tommy Hilfiger', 'Lacoste', 'Polo Ralph Lauren', 'Hugo Boss']
                
                name_upper = product_data['name'].upper()
                for brand in known_brands:
                    if brand.upper() in name_upper:
                        product_data['brand'] = brand
                        break
            
            # Стратегия 3: Извлечение цены с улучшенными селекторами
            price_info = self._extract_prices_from_element(element)
            if price_info:
                product_data['price'] = price_info['current_price']
                product_data['old_price'] = price_info['old_price']
            
            # Стратегия 4: Извлечение URL
            # Улучшенная логика поиска ссылки
            url_selectors = [
                'a[href*="/p/"]',  # Прямые ссылки на товары
                'a[href]',  # Любые ссылки
            ]
            
            found_url = None
            for selector in url_selectors:
                link_elem = element.select_one(selector)
                if link_elem and link_elem.get('href'):
                    href = link_elem['href']
                    # Проверяем что это реальная ссылка на товар
                    if href.startswith('/p/') or '/p/' in href:
                        if href.startswith('/'):
                            found_url = urljoin(self.base_url, href)
                        elif href.startswith('http'):
                            found_url = href
                        break
            
            # Если не нашли ссылку в элементе, ищем в родительских элементах
            if not found_url:
                parent = element.parent
                for _ in range(3):  # Ищем на 3 уровня вверх
                    if parent and parent.name:
                        parent_link = parent.find('a', href=True)
                        if parent_link:
                            href = parent_link['href']
                            if href.startswith('/p/') or '/p/' in href:
                                if href.startswith('/'):
                                    found_url = urljoin(self.base_url, href)
                                elif href.startswith('http'):
                                    found_url = href
                                break
                        parent = parent.parent
                    else:
                        break
            
            product_data['url'] = found_url
            
            # Стратегия 5: Извлечение изображений
            img_selectors = [
                'img[src*="lmcdn"]',
                'img[data-src*="lmcdn"]',
                'img[class*="image"]',
                'img[class*="picture"]',
                'img',
            ]
            
            found_images = set()
            for selector in img_selectors:
                img_elems = element.select(selector)
                for img in img_elems:
                    src = (img.get('src') or img.get('data-src') or 
                          img.get('data-lazy-src') or img.get('data-original'))
                    if src:
                        # Нормализуем URL
                        if src.startswith('//'):
                            full_url = 'https:' + src
                        elif src.startswith('/'):
                            full_url = urljoin(self.base_url, src)
                        else:
                            full_url = src
                        
                        # Проверяем что это изображение товара
                        if (full_url and 
                            ('lmcdn.ru' in full_url or 'lamoda' in full_url) and
                            any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and
                            full_url not in found_images):
                            found_images.add(full_url)
            
            product_data['image_urls'] = list(found_images)
            if product_data['image_urls']:
                product_data['image_url'] = product_data['image_urls'][0]
            
            # Генерируем SKU
            sku = f"LMD{self.domain.upper()}{index + 1:04d}"
            if product_data['url']:
                # Пытаемся извлечь SKU из URL
                sku_match = re.search(r'/([A-Z0-9]+)/?(?:\?|$)', product_data['url'])
                if sku_match:
                    sku = sku_match.group(1)
            
            # Проверяем минимальные требования
            if not product_data['price'] or not product_data['url']:
                return None
            
            # Устанавливаем значения по умолчанию
            if not product_data['name']:
                product_data['name'] = "Product"
            if not product_data['brand']:
                product_data['brand'] = "Unknown"
            if not product_data['image_url']:
                product_data['image_url'] = ""
            
            return Product(
                sku=sku,
                name=product_data['name'],
                brand=product_data['brand'],
                price=product_data['price'],
                old_price=product_data['old_price'],
                url=product_data['url'],
                image_url=product_data['image_url'],
                image_urls=product_data['image_urls']
            )
            
        except Exception as e:
            print(f"❌ Error in modern parser for element {index}: {e}")
            return None

    def _parse_legacy_product_card(self, card, index: int) -> Optional[Product]:
        """Парсинг старой структуры карточки товара (оригинальный код)"""
        return self._parse_product_card(card, index)
    
    def _parse_flexible_product_block(self, block, index: int) -> Optional[Product]:
        """Гибкий парсинг любого блока с товаром"""
        return self._parse_product_block(block, index)

    def _parse_product_card(self, card, index: int) -> Optional[Product]:
        """Парсинг отдельной карточки товара с новой структурой"""
        try:
            # Извлекаем бренд
            brand_elem = card.select_one('.product-card__brand-name')
            brand = brand_elem.get_text(strip=True) if brand_elem else "Unknown"
            
            # Извлекаем название товара
            name_elem = card.select_one('.product-card__product-name')
            name = name_elem.get_text(strip=True) if name_elem else "Product"
            
            # Извлекаем цены с улучшенной логикой
            price_info = self._extract_prices_from_element(card)
            
            if not price_info or not price_info['current_price']:
                print(f"No price found for product {index}")
                return None
            
            price = price_info['current_price']
            old_price = price_info['old_price']
            
            # Извлекаем ссылку - улучшенная логика
            url = ""
            url_selectors = [
                '.product-card__hit-area[href]',
                'a[href*="/p/"]',
                'a[href]'
            ]
            
            for selector in url_selectors:
                link_elem = card.select_one(selector)
                if link_elem and link_elem.get('href'):
                    href = link_elem['href']
                    # Проверяем что это реальная ссылка на товар
                    if href.startswith('/p/') or '/p/' in href or (href.startswith('/') and len(href) > 5):
                        if href.startswith('/'):
                            url = urljoin(self.base_url, href)
                        elif href.startswith('http'):
                            url = href
                        break
            
            # Извлекаем изображения
            image_url = ""
            image_urls = []
            
            # Ищем основное изображение
            img_elem = card.select_one('.product-card__pic-img')
            if img_elem:
                src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
                if src:
                    if src.startswith('//'):
                        image_url = 'https:' + src
                    elif src.startswith('/'):
                        image_url = urljoin(self.base_url, src)
                    else:
                        image_url = src
                    
                    # Добавляем основное изображение в список
                    if image_url:
                        image_urls.append(image_url)
            
            # Ищем дополнительные изображения
            all_imgs = card.select('img')
            for img in all_imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                if src:
                    # Нормализуем URL
                    if src.startswith('//'):
                        full_url = 'https:' + src
                    elif src.startswith('/'):
                        full_url = urljoin(self.base_url, src)
                    else:
                        full_url = src
                    
                    # Добавляем только если это изображение товара и его еще нет в списке
                    if (full_url and 
                        full_url not in image_urls and 
                        ('lmcdn.ru' in full_url or 'lamoda' in full_url) and
                        any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp'])):
                        image_urls.append(full_url)
            
            # Генерируем SKU
            sku = f"LMD{self.domain.upper()}{index + 1:04d}"
            if url:
                # Пробуем извлечь SKU из URL
                sku_match = re.search(r'/([A-Z0-9]+)/', url)
                if sku_match:
                    sku = sku_match.group(1)
            
            # Проверяем разумность цены и наличие URL
            if price > 1000000:
                print(f"Price too high for product {index}: {price}")
                return None
            
            if not url:
                print(f"No valid URL found for product {index}")
                return None
            
            return Product(
                sku=sku,
                name=name.strip(),
                brand=brand.strip(),
                price=price,
                old_price=old_price,
                url=url,
                image_url=image_url,
                image_urls=image_urls
            )
            
        except Exception as e:
            print(f"Error parsing product card {index}: {e}")
            return None

    def _parse_product_block(self, block, index: int) -> Optional[Product]:
        """Парсинг отдельного блока товара"""
        try:
            # Сначала пробуем парсить как карточку товара
            if hasattr(block, 'select_one'):
                # Проверяем, есть ли специфичные элементы карточки
                if (block.select_one('.product-card__brand-name') or 
                    block.select_one('.product-card__product-name') or
                    block.select_one('.product-card__price')):
                    return self._parse_product_card(block, index)
            
            # Извлекаем текст из блока
            text = block.get_text(strip=True)
            
            # Улучшенный поиск цен в тексте
            price_matches = re.findall(r'(\d+(?:\s+\d+)*)\s*₸', text)
            if not price_matches:
                # Попробуем найти цены без валютного символа
                price_matches = re.findall(r'(\d+(?:\s+\d+){1,2})', text)
            
            if not price_matches:
                return None
            
            # Берем первую найденную цену (обычно это актуальная цена)
            price_str = price_matches[0]
            price = float(price_str.replace(' ', ''))
            
            # Ищем старую цену (если есть несколько цен)
            old_price = None
            if len(price_matches) > 1:
                old_price_str = price_matches[1]
                old_price_val = float(old_price_str.replace(' ', ''))
                if old_price_val > price:
                    old_price = old_price_val
            
            # Улучшенное извлечение бренда и названия
            brand, name = self._extract_brand_and_name(text)
            
            # Ищем ссылку - улучшенная логика
            url = ""
            url_selectors = [
                'a[href*="/p/"]',
                'a[href]'
            ]
            
            for selector in url_selectors:
                link = block.select_one(selector)
                if link and link.get('href'):
                    href = link['href']
                    # Проверяем что это реальная ссылка на товар
                    if href.startswith('/p/') or '/p/' in href or (href.startswith('/') and len(href) > 5):
                        if href.startswith('/'):
                            url = urljoin(self.base_url, href)
                        elif href.startswith('http'):
                            url = href
                        break
            
            # Ищем изображение
            image_url = ""
            image_urls = []
            
            # Ищем основное изображение  
            img = block.find('img')
            if img:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                if src:
                    if src.startswith('//'):
                        image_url = 'https:' + src
                    elif src.startswith('/'):
                        image_url = urljoin(self.base_url, src)
                    else:
                        image_url = src
                    
                    # Добавляем основное изображение в список
                    if image_url:
                        image_urls.append(image_url)
            
            # Ищем дополнительные изображения
            all_imgs = block.find_all('img')
            for img in all_imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                if src:
                    # Нормализуем URL
                    if src.startswith('//'):
                        full_url = 'https:' + src
                    elif src.startswith('/'):
                        full_url = urljoin(self.base_url, src)
                    else:
                        full_url = src
                    
                    # Добавляем только если это изображение товара и его еще нет в списке
                    if (full_url and 
                        full_url not in image_urls and 
                        ('lmcdn.ru' in full_url or 'lamoda' in full_url) and
                        any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp'])):
                        image_urls.append(full_url)
            
            # Генерируем SKU из ссылки или используем индекс
            sku = f"LMD{self.domain.upper()}{index + 1:04d}"
            if url:
                # Пробуем извлечь SKU из URL
                sku_match = re.search(r'/([A-Z0-9]+)/', url)
                if sku_match:
                    sku = sku_match.group(1)
            
            # Проверяем разумность цены и наличие URL
            if price > 1000000:
                return None
            
            if not url:
                print(f"No valid URL found for product block {index}")
                return None
            
            return Product(
                sku=sku,
                name=name.strip(),
                brand=brand.strip(),
                price=price,
                old_price=old_price,
                url=url,
                image_url=image_url,
                image_urls=image_urls
            )
            
        except Exception as e:
            print(f"Error parsing product block {index}: {e}")
            return None

    def _extract_brand_and_name(self, text: str) -> tuple[str, str]:
        """Извлечь бренд и название из текста"""
        # Очищаем текст от лишних символов
        text = re.sub(r'[₸₽]', '', text)
        text = re.sub(r'\d+(?:\s+\d+)*', '', text)  # Убираем цены
        text = ' '.join(text.split())  # Нормализуем пробелы
        
        brand = "Unknown"
        name = "Product"
        
        # Известные бренды
        known_brands = [
            'Nike', 'Adidas', 'Puma', 'Reebok', 'Jordan', 'Converse', 
            'New Balance', 'Vans', 'Under Armour', 'Asics', 'Mizuno',
            'Skechers', 'Fila', 'Kappa', 'Umbro', 'Diadora'
        ]
        
        # Ищем бренд в тексте
        text_lower = text.lower()
        for brand_name in known_brands:
            if brand_name.lower() in text_lower:
                brand = brand_name
                # Находим позицию бренда и берем текст после него как название
                brand_pos = text_lower.find(brand_name.lower())
                if brand_pos != -1:
                    name_part = text[brand_pos + len(brand_name):].strip()
                    if name_part:
                        # Берем первые несколько слов как название
                        name_words = name_part.split()[:5]
                        if name_words:
                            name = ' '.join(name_words)
                break
        
        # Если бренд не найден, пробуем извлечь из начала текста
        if brand == "Unknown":
            words = text.split()
            if words:
                # Первое слово может быть брендом
                first_word = words[0]
                if len(first_word) > 2 and first_word.isalpha():
                    brand = first_word
                    if len(words) > 1:
                        name = ' '.join(words[1:6])  # Берем следующие 5 слов
        
        # Очищаем название от лишних символов
        name = re.sub(r'[^\w\s\-]', '', name).strip()
        if not name or len(name) < 3:
            name = "Product"
        
        return brand, name

    def _parse_from_text(self, text: str, limit: int) -> List[Product]:
        """Парсинг товаров из текста страницы (fallback метод)"""
        products = []
        
        # Множественные паттерны для поиска товаров
        patterns = [
            # Паттерн 1: Цена + валюта + бренд + название
            r'(\d{2,6}(?:\s+\d{3})*)\s*₸\s*([A-Za-z]+)\s+([А-Яа-я\s\w\-]{10,80})',
            # Паттерн 2: Бренд + название + цена
            r'([A-Za-z]+)\s+([А-Яа-я\s\w\-]{10,80})\s+(\d{2,6}(?:\s+\d{3})*)\s*₸',
            # Паттерн 3: Только цены от 1000 до 999999 тенге
            r'(\d{4,6})\s*₸',
        ]
        
        # Сначала пробуем структурированные паттерны  
        for pattern in patterns[:2]:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            
            if matches:
                print(f"Found {len(matches)} matches with pattern")
                for i, match in enumerate(matches[:limit]):
                    try:
                        if len(match) == 3:
                            if pattern.startswith(r'(\d{2,6}'):  # Паттерн 1: цена первая
                                price_str, brand, name = match
                            else:  # Паттерн 2: цена последняя
                                brand, name, price_str = match
                            
                            # Очищаем цену от пробелов и проверяем разумность
                            price = float(price_str.replace(' ', ''))
                            if price < 1000 or price > 999999:  # Разумные пределы цен в тенге
                                continue
                            
                            # Очищаем название и бренд
                            name = re.sub(r'\s+', ' ', name.strip())
                            name = name[:80]  # Ограничиваем длину
                            brand = brand.strip()
                            
                            if len(name) < 5 or len(brand) < 2:  # Минимальная длина
                                continue
                            
                            sku = f"TXT{self.domain.upper()}{i + 1:04d}"
                            
                            # Пропускаем товары без реальных URL
                            continue
                            
                    except Exception as e:
                        print(f"Error parsing text match {i}: {e}")
                        continue
                
                if products:
                    return products
        
        # Fallback: ищем просто цены и пытаемся найти рядом товары
        print("Using fallback price-only parsing")
        price_matches = re.findall(patterns[2], text)
        
        if price_matches:
            # Разбиваем текст на сегменты около цен
            segments = re.split(r'\d{4,6}\s*₸', text)
            
            for i, price_str in enumerate(price_matches[:limit]):
                try:
                    price = float(price_str)
                    if price < 1000 or price > 999999:
                        continue
                    
                    # Берем текст до или после цены
                    segment = ""
                    if i < len(segments) - 1:
                        segment = segments[i] + " " + segments[i + 1]
                    elif i < len(segments):
                        segment = segments[i]
                    
                    # Извлекаем бренд и название из сегмента
                    brand, name = self._extract_brand_and_name(segment)
                    
                    if name == "Product" or brand == "Unknown":
                        name = f"Товар #{i + 1}"
                        brand = "Generic"
                    
                    sku = f"TXT{self.domain.upper()}{i + 1:04d}"
                    
                    # Пропускаем товары без реальных URL
                    continue
                    
                except Exception as e:
                    print(f"Error parsing fallback match {i}: {e}")
                    continue
        
        return products

    async def afetch_search(self, query: str, limit: int = 20, page: int = 1) -> List[Product]:
        """Асинхронный поиск товаров"""
        try:
            print(f"Searching for '{query}' on {self.domain} domain")
            
            # Стратегия 1: Реальный поиск
            products = await self._try_real_search(query, limit, page)
            if products:
                print(f"Found {len(products)} products via real search")
                return products
            
            # Стратегия 2: Демо режим как fallback
            print("Real search failed, using demo mode...")
            return self._generate_demo_products(query, limit)
                
        except Exception as e:
            print(f"Search failed: {e}")
            # В случае ошибки тоже возвращаем демо данные
            return self._generate_demo_products(query, limit)

    def _generate_demo_products(self, query: str, limit: int) -> List[Product]:
        """Генерировать демо товары для тестирования API"""
        demo_products = []
        
        # Базовые товары для разных запросов
        product_templates = {
            'nike': [
                {'name': 'Nike Air Max 270', 'brand': 'Nike', 'price': 12990, 'old_price': 15990},
                {'name': 'Nike React Infinity Run', 'brand': 'Nike', 'price': 9990, 'old_price': None},
                {'name': 'Nike Air Force 1', 'brand': 'Nike', 'price': 8990, 'old_price': 10990},
            ],
            'adidas': [
                {'name': 'Adidas Ultraboost 22', 'brand': 'Adidas', 'price': 14990, 'old_price': None},
                {'name': 'Adidas Stan Smith', 'brand': 'Adidas', 'price': 6990, 'old_price': 8990},
                {'name': 'Adidas Gazelle', 'brand': 'Adidas', 'price': 7990, 'old_price': None},
            ],
            'puma': [
                {'name': 'Puma Suede Classic', 'brand': 'Puma', 'price': 5990, 'old_price': None},
                {'name': 'Puma RS-X', 'brand': 'Puma', 'price': 8990, 'old_price': 11990},
                {'name': 'Puma Future Rider', 'brand': 'Puma', 'price': 6990, 'old_price': None},
            ]
        }
        
        # Выбираем шаблоны на основе запроса
        templates = []
        query_lower = query.lower()
        
        for brand, products in product_templates.items():
            if brand in query_lower:
                templates = products
                break
        
        # Если не нашли подходящий бренд, используем общие товары
        if not templates:
            templates = [
                {'name': f'Товар по запросу "{query}" #{i+1}', 'brand': 'Generic', 'price': 5000 + i * 1000, 'old_price': None}
                for i in range(3)
            ]
        
        # Генерируем товары
        for i, template in enumerate(templates[:limit]):
            sku = f"DEMO{query.upper()[:3]}{i+1:03d}"
            # Генерируем несколько демо изображений для товара
            main_image = f"https://a.lmcdn.ru/img600x866/demo/{sku.lower()}_1.jpg"
            demo_images = [
                main_image,
                f"https://a.lmcdn.ru/img600x866/demo/{sku.lower()}_2.jpg",
                f"https://a.lmcdn.ru/img600x866/demo/{sku.lower()}_3.jpg"
            ]
            
            demo_products.append(Product(
                sku=sku,
                name=template['name'],
                brand=template['brand'],
                price=float(template['price']),
                old_price=float(template['old_price']) if template['old_price'] else None,
                url=f"{self.base_url}/p/{sku.lower()}/demo-product-{i+1}/",
                image_url=main_image,
                image_urls=demo_images
            ))
        
        print(f"Generated {len(demo_products)} demo products")
        return demo_products

    def fetch_search(self, query: str, limit: int = 20, page: int = 1) -> List[Product]:
        """Синхронный поиск товаров"""
        return asyncio.run(self.afetch_search(query, limit, page))

    async def close(self):
        """Закрыть HTTP сессию"""
        if self.session:
            await self.session.aclose()
            self.session = None

    def __del__(self):
        """Деструктор для закрытия сессии"""
        if self.session:
            try:
                asyncio.create_task(self.close())
            except:
                pass


    
    def _generate_sku_from_url(self, url: str, index: int) -> str:
        """Генерирует SKU из URL товара"""
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
            return f"LMD{self.domain.upper()}{index + 1:04d}"
            
        except Exception:
            return f"LMD{self.domain.upper()}{index + 1:04d}"


# CLI интерфейс
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Lamoda Product Parser")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Max products to fetch")
    parser.add_argument("--domain", choices=list(LAMODA_DOMAINS.keys()), default="ru", help="Lamoda domain")
    parser.add_argument("--page", type=int, default=1, help="Page number")
    
    args = parser.parse_args()
    
    async def main():
        parser_instance = LamodaParser(domain=args.domain)
        try:
            products = await parser_instance.afetch_search(args.query, args.limit, args.page)
            
            if products:
                print(f"\nFound {len(products)} products:")
                for i, product in enumerate(products, 1):
                    print(f"\n{i}. {product.name}")
                    print(f"   Brand: {product.brand}")
                    print(f"   Price: {product.price} {LAMODA_DOMAINS[args.domain]['currency']}")
                    if product.old_price:
                        print(f"   Old Price: {product.old_price} {LAMODA_DOMAINS[args.domain]['currency']}")
                    print(f"   SKU: {product.sku}")
                    print(f"   URL: {product.url}")
                    if product.image_url:
                        print(f"   Image: {product.image_url}")
            else:
                print("No products found")
        finally:
            await parser_instance.close()
    
    asyncio.run(main()) 