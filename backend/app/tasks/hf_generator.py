import json
import random
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models.item import Item
from app.db.models.outfit import Outfit, OutfitItem
from app.db.models.user import User

# Простые правила сочетания цветов
COLOR_HARMONY = {
    "white": ["black", "blue", "red", "green", "gray", "brown"],
    "black": ["white", "gray", "red", "blue", "yellow"],
    "blue": ["white", "gray", "brown", "beige", "navy"],
    "red": ["white", "black", "gray", "beige"],
    "green": ["white", "beige", "brown", "gray"],
    "gray": ["white", "black", "blue", "red", "yellow"],
    "brown": ["white", "beige", "green", "blue"],
    "beige": ["brown", "white", "blue", "red"],
    "yellow": ["black", "gray", "brown", "blue"],
    "navy": ["white", "beige", "gray", "red"],
    "pink": ["white", "gray", "black", "blue"],
    "purple": ["white", "gray", "black", "beige"]
}

# Стили и их характеристики
STYLE_RULES = {
    "casual": {
        "preferred_categories": ["tshirt", "jeans", "sneakers", "hoodie"],
        "colors": ["blue", "white", "gray", "black"],
        "avoid": ["formal", "suit", "tie"]
    },
    "formal": {
        "preferred_categories": ["shirt", "pants", "shoes", "jacket"],
        "colors": ["black", "white", "gray", "navy"],
        "avoid": ["sneakers", "tshirt", "shorts"]
    },
    "business": {
        "preferred_categories": ["shirt", "pants", "shoes", "blazer"],
        "colors": ["navy", "gray", "white", "black"],
        "avoid": ["sneakers", "shorts", "tshirt"]
    },
    "sporty": {
        "preferred_categories": ["tshirt", "shorts", "sneakers", "tracksuit"],
        "colors": ["blue", "red", "white", "black"],
        "avoid": ["formal", "dress", "heels"]
    }
}

# Поводы и подходящие стили
OCCASION_MAPPING = {
    "work": ["business", "formal"],
    "party": ["formal", "elegant"],
    "date": ["elegant", "casual"],
    "casual": ["casual", "sporty"],
    "formal event": ["formal", "elegant"],
    "business meeting": ["business", "formal"],
    "weekend": ["casual", "sporty"],
    "vacation": ["casual", "sporty"],
    "gym": ["sporty"],
    "shopping": ["casual"],
    "dinner": ["elegant", "formal"]
}

# Названия образов для разных стилей
OUTFIT_NAMES = {
    "casual": [
        "Городской комфорт",
        "Повседневный шик",
        "Комфортный стиль",
        "Casual Friday",
        "Расслабленный образ",
        "Свободный стиль"
    ],
    "formal": [
        "Деловая элегантность",
        "Классический костюм",
        "Строгий стиль",
        "Официальный образ",
        "Формальный шик",
        "Изысканность"
    ],
    "business": [
        "Офисный стиль",
        "Деловой дресс-код",
        "Профессиональный образ",
        "Корпоративный шик",
        "Рабочий костюм",
        "Business Professional"
    ],
    "sporty": [
        "Спортивный комфорт",
        "Активный день",
        "Спорт-шик",
        "Атлетический стиль",
        "Тренировочный образ",
        "Спортивная мода"
    ]
}

def check_color_harmony(items: List[Dict]) -> bool:
    """Проверяет гармонию цветов в образе"""
    if len(items) < 2:
        return True
    
    # Безопасно извлекаем цвета, обрабатывая None
    colors = []
    for item in items:
        color = item.get('color')
        if color and isinstance(color, str) and color.strip():
            colors.append(color.lower().strip())
    
    if not colors:
        return True  # Если нет цветов, считаем гармонию хорошей
    
    # Проверяем, что все цвета сочетаются между собой
    base_color = colors[0]
    if base_color in COLOR_HARMONY:
        compatible_colors = COLOR_HARMONY[base_color]
        for color in colors[1:]:
            if color not in compatible_colors and color != base_color:
                return False
    
    return True

def calculate_outfit_score(items: List[Dict], style: str) -> int:
    """Рассчитывает оценку образа от 0 до 100"""
    if not items:
        return 0
    
    score = 50  # Базовая оценка
    
    # Проверяем соответствие стилю
    if style in STYLE_RULES:
        style_rules = STYLE_RULES[style]
        preferred_cats = style_rules["preferred_categories"]
        
        for item in items:
            item_category = item.get('category') or ''
            if isinstance(item_category, str):
                item_category = item_category.lower()
                if any(cat in item_category for cat in preferred_cats):
                    score += 10
    
    # Проверяем гармонию цветов
    if check_color_harmony(items):
        score += 20
    
    # Проверяем количество вещей
    if 3 <= len(items) <= 6:
        score += 10
    
    return min(score, 100)

def generate_outfit_from_selected_items(
    user_id: int,
    selected_item_ids: List[int],
    style: str,
    occasion: str,
    additional_categories: Optional[List[str]] = None
) -> dict:
    """Генерирует образ из выбранных пользователем вещей"""
    try:
        db = next(get_db())
        
        # Получаем выбранные товары
        selected_items = db.query(Item).filter(Item.id.in_(selected_item_ids)).all()
        if not selected_items:
            return {"error": "No selected items found"}
        
        selected_data = []
        used_categories = set()
        total_price = 0
        
        for item in selected_items:
            selected_data.append({
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "color": item.color,
                "price": item.price
            })
            used_categories.add(item.category or "other")
            total_price += item.price or 0
        
        # Добавляем дополнительные товары если нужно
        final_item_ids = selected_item_ids.copy()
        
        if additional_categories:
            needed_categories = set(additional_categories) - used_categories
            if needed_categories:
                additional_query = db.query(Item).filter(
                    Item.category.in_(list(needed_categories)),
                    ~Item.id.in_(selected_item_ids)
                )
                additional_items = additional_query.limit(3).all()
                
                for item in additional_items:
                    # Проверяем цветовую совместимость
                    new_item_data = {
                        "id": item.id,
                        "color": item.color,
                        "category": item.category,
                        "price": item.price
                    }
                    
                    test_items = selected_data + [new_item_data]
                    if check_color_harmony(test_items):
                        final_item_ids.append(item.id)
                        selected_data.append(new_item_data)
                        total_price += item.price or 0
                        break
        
        # Создаем образ в базе данных
        user = db.get(User, user_id)
        if not user:
            return {"error": "User not found"}
        
        # Генерируем название
        outfit_names = OUTFIT_NAMES.get(style, ["Стильный образ"])
        outfit_name = random.choice(outfit_names)
        
        # Создаем описание
        description = f"Образ в стиле {style} для {occasion}. Включает {len(final_item_ids)} предметов."
        
        db_outfit = Outfit(
            name=outfit_name,
            style=style,
            description=description,
            owner_id=str(user_id)
        )
        
        # Добавляем товары в образ
        category_mapping = {
            "top": "top", "tops": "top", "shirt": "top", "tshirt": "top", 
            "hoodie": "top", "sweater": "top", "jacket": "top", "coat": "top", "dress": "top",
            "bottom": "bottom", "bottoms": "bottom", "pants": "bottom", 
            "jeans": "bottom", "shorts": "bottom", "skirt": "bottom",
            "footwear": "footwear", "shoes": "footwear", "sneakers": "footwear",
            "accessories": "accessory", "accessory": "accessory",
            "fragrances": "fragrance", "fragrance": "fragrance"
        }
        
        for item_id in final_item_ids:
            item = db.get(Item, item_id)
            if item:
                item_category = category_mapping.get(item.category, "accessory")
                outfit_item = OutfitItem(item_category=item_category, item=item)
                db_outfit.outfit_items.append(outfit_item)
        
        db.add(db_outfit)
        db.commit()
        db.refresh(db_outfit)
        
        # Рассчитываем оценку образа
        score = calculate_outfit_score(selected_data, style)
        
        return {
            "outfit_id": db_outfit.id,
            "outfit_name": db_outfit.name,
            "description": db_outfit.description,
            "total_price": total_price,
            "style_notes": f"Оценка образа: {score}/100. Гармоничное сочетание в стиле {style}.",
            "selected_items": final_item_ids,
            "user_items_included": selected_item_ids,
            "suggested_additions": [id for id in final_item_ids if id not in selected_item_ids]
        }
        
    except Exception as e:
        return {"error": str(e)}

def generate_random_outfit(
    user_id: int,
    style: str,
    occasion: str,
    budget: Optional[float] = None,
    collection: Optional[str] = None
) -> dict:
    """Генерирует случайный образ из каталога"""
    try:
        db = next(get_db())
        
        # Получаем товары из каталога
        query = db.query(Item)
        
        if collection:
            query = query.filter(Item.collection == collection)
        
        # Сначала попробуем с бюджетом, если есть
        if budget:
            budget_query = query.filter(Item.price <= budget)
            budget_items = budget_query.all()
            if len(budget_items) >= 3:
                all_items = budget_items
            else:
                # Если с бюджетом мало товаров, берем все доступные
                all_items = query.all()
        else:
            all_items = query.all()
        
        if len(all_items) < 3:
            return {"error": "Not enough items in catalog for random generation"}
        
        # Группируем по категориям
        items_by_category = {}
        for item in all_items:
            category = item.category or "other"
            if category not in items_by_category:
                items_by_category[category] = []
            
            items_by_category[category].append({
                "id": item.id,
                "name": item.name,
                "color": item.color,
                "price": item.price,
                "category": category
            })
        
        # Логика выбора по стилю
        selected_items = []
        total_price = 0
        used_categories = set()
        
        # Приоритетные категории для стиля
        style_rules = STYLE_RULES.get(style, {})
        preferred_categories = style_rules.get("preferred_categories", [])
        preferred_colors = style_rules.get("colors", list(COLOR_HARMONY.keys()))
        
        # Выбираем 1-2 базовых предмета
        for pref_cat in preferred_categories[:2]:
            if pref_cat in items_by_category and pref_cat not in used_categories:
                candidates = [item for item in items_by_category[pref_cat] 
                            if item.get("color") and isinstance(item["color"], str) and item["color"].lower() in preferred_colors]
                # Если нет товаров с предпочтенными цветами, берем любые из категории
                if not candidates:
                    candidates = items_by_category[pref_cat]
                
                if candidates:
                    item = random.choice(candidates)
                    selected_items.append(item)
                    total_price += item["price"] or 0
                    used_categories.add(pref_cat)
        
        # Добавляем совместимые предметы
        remaining_budget = (budget or 10000) - total_price
        attempts = 0
        
        while len(selected_items) < 5 and attempts < 20:
            attempts += 1
            
            # Выбираем случайную категорию
            available_categories = [cat for cat in items_by_category.keys() 
                                  if cat not in used_categories]
            if not available_categories:
                break
                
            category = random.choice(available_categories)
            candidates = items_by_category[category]
            
            # Фильтруем по бюджету только если остался разумный бюджет
            if budget and remaining_budget > 0:
                budget_candidates = [item for item in candidates 
                                   if (item["price"] or 0) <= remaining_budget]
                # Если есть товары в бюджете, используем их, иначе игнорируем бюджет
                if budget_candidates:
                    candidates = budget_candidates
            
            if not candidates:
                continue
            
            # Выбираем товар
            item = random.choice(candidates)
            
            # Проверяем цветовую совместимость
            test_items = selected_items + [item]
            if check_color_harmony(test_items):
                selected_items.append(item)
                total_price += item["price"] or 0
                used_categories.add(category)
                remaining_budget = (budget or 10000) - total_price
        
        # Создаем образ в базе данных
        user = db.get(User, user_id)
        if not user:
            return {"error": "User not found"}
        
        # Генерируем креативное название
        outfit_names = OUTFIT_NAMES.get(style, ["Случайный образ"])
        outfit_name = random.choice(outfit_names)
        
        # Создаем описание с изюминкой
        surprises = [
            "неожиданное цветовое сочетание",
            "интересный микс текстур",
            "современная интерпретация классики",
            "смелое стилевое решение",
            "креативный подход к базовым вещам"
        ]
        surprise = random.choice(surprises)
        
        description = f"Случайный образ в стиле {style} с {surprise}. Идеально для {occasion}!"
        
        db_outfit = Outfit(
            name=outfit_name,
            style=style,
            description=description,
            owner_id=str(user_id),
            collection=collection
        )
        
        # Добавляем товары в образ
        category_mapping = {
            "top": "top", "tops": "top", "shirt": "top", "tshirt": "top", 
            "hoodie": "top", "sweater": "top", "jacket": "top", "coat": "top", "dress": "top",
            "bottom": "bottom", "bottoms": "bottom", "pants": "bottom", 
            "jeans": "bottom", "shorts": "bottom", "skirt": "bottom",
            "footwear": "footwear", "shoes": "footwear", "sneakers": "footwear",
            "accessories": "accessory", "accessory": "accessory",
            "fragrances": "fragrance", "fragrance": "fragrance"
        }
        
        final_item_ids = [item["id"] for item in selected_items]
        
        for item_id in final_item_ids:
            item = db.get(Item, item_id)
            if item:
                item_category = category_mapping.get(item.category, "accessory")
                outfit_item = OutfitItem(item_category=item_category, item=item)
                db_outfit.outfit_items.append(outfit_item)
        
        db.add(db_outfit)
        db.commit()
        db.refresh(db_outfit)
        
        # Рассчитываем оценку
        score = calculate_outfit_score(selected_items, style)
        
        return {
            "outfit_id": db_outfit.id,
            "outfit_name": db_outfit.name,
            "description": db_outfit.description,
            "total_price": total_price,
            "style_notes": f"Оценка образа: {score}/100. Гармония цветов и стиля.",
            "surprise_factor": f"Изюминка этого образа: {surprise}",
            "selected_items": final_item_ids
        }
        
    except Exception as e:
        return {"error": str(e)} 