import openai
import os
import json
from celery import shared_task
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models.item import Item
from app.db.models.outfit import Outfit, OutfitItem
from app.db.models.user import User



# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

@shared_task
def evaluate_outfit(outfit_id: int) -> dict:
    """Evaluate an outfit using AI and provide feedback."""
    try:
        db = next(get_db())
        outfit = db.get(Outfit, outfit_id)
        if not outfit:
            return {"error": "Outfit not found"}
        
        # Get all items in outfit
        items_data = []
        for outfit_item in outfit.outfit_items:
            item = outfit_item.item
            items_data.append({
                "name": item.name,
                "brand": item.brand,
                "color": item.color,
                "category": outfit_item.item_category,
                "style": item.style,
                "price": item.price
            })
        
        # Create prompt for AI evaluation
        prompt = f"""
        Analyze this outfit and provide a style evaluation:
        
        Outfit: {outfit.name}
        Style: {outfit.style}
        Items: {json.dumps(items_data, indent=2)}
        
        Please provide:
        1. Overall style score (0-100)
        2. Color harmony score (0-100) 
        3. Style consistency score (0-100)
        4. Brief feedback (2-3 sentences)
        5. Improvement suggestions (if any)
        
        Respond in JSON format.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional fashion stylist and outfit evaluator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        result = json.loads(response.choices[0].message.content)
        result["outfit_id"] = outfit_id
        return result
        
    except Exception as e:
        return {"error": str(e), "outfit_id": outfit_id}

@shared_task
def generate_outfit_from_catalog(
    user_id: int,
    style: str,
    occasion: str,
    budget: Optional[float] = None,
    preferred_colors: Optional[List[str]] = None,
    required_categories: Optional[List[str]] = None,
    collection: Optional[str] = None
) -> dict:
    """Generate a new outfit from available catalog items using AI."""
    try:
        db = next(get_db())
        
        # Get available items from catalog
        query = db.query(Item)
        
        if collection:
            query = query.filter(Item.collection == collection)
        
        if budget:
            query = query.filter(Item.price <= budget / 3)  # Rough budget per item
            
        available_items = query.all()
        
        if not available_items:
            return {"error": "No items available in catalog"}
        
        # Prepare items data for AI
        items_by_category = {}
        for item in available_items:
            category = item.category or "other"
            if category not in items_by_category:
                items_by_category[category] = []
            
            items_by_category[category].append({
                "id": item.id,
                "name": item.name,
                "brand": item.brand,
                "color": item.color,
                "price": item.price,
                "style": item.style,
                "image_url": item.image_url
            })
        
        # Create AI prompt for outfit generation
        prompt = f"""
        Create a stylish outfit for the following requirements:
        
        Style: {style}
        Occasion: {occasion}
        Budget: {budget or "No limit"}
        Preferred Colors: {preferred_colors or "Any"}
        Required Categories: {required_categories or "Any suitable"}
        
        Available items by category:
        {json.dumps(items_by_category, indent=2)}
        
        Please select items to create a cohesive outfit and respond with:
        1. selected_items: Array of item IDs
        2. outfit_name: Creative name for the outfit
        3. description: Why this combination works
        4. total_price: Sum of selected items prices
        5. style_notes: Styling tips
        
        Respond in JSON format. Select 3-6 items total.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional fashion stylist creating outfits from available items."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.8
        )
        
        ai_result = json.loads(response.choices[0].message.content)
        
        # Create the outfit in database
        user = db.get(User, user_id)
        if not user:
            return {"error": "User not found"}
        
        db_outfit = Outfit(
            name=ai_result.get("outfit_name", f"{style} Outfit"),
            style=style,
            description=ai_result.get("description", "AI Generated Outfit"),
            owner_id=str(user_id),
            collection=collection
        )
        
        # Add selected items to outfit
        selected_item_ids = ai_result.get("selected_items", [])
        category_mapping = {
            "top": "top",
            "tops": "top", 
            "shirt": "top",
            "tshirt": "top",
            "hoodie": "top",
            "sweater": "top",
            "jacket": "top",
            "coat": "top",
            "dress": "top",
            "bottom": "bottom",
            "bottoms": "bottom",
            "pants": "bottom",
            "jeans": "bottom", 
            "shorts": "bottom",
            "skirt": "bottom",
            "footwear": "footwear",
            "accessories": "accessory",
            "accessory": "accessory",
            "fragrances": "fragrance",
            "fragrance": "fragrance"
        }
        
        for item_id in selected_item_ids:
            item = db.get(Item, item_id)
            if item:
                item_category = category_mapping.get(item.category, "accessory")
                outfit_item = OutfitItem(
                    item_category=item_category,
                    item=item
                )
                db_outfit.outfit_items.append(outfit_item)
        
        db.add(db_outfit)
        db.commit()
        db.refresh(db_outfit)
        
        return {
            "outfit_id": db_outfit.id,
            "outfit_name": db_outfit.name,
            "description": db_outfit.description,
            "total_price": ai_result.get("total_price", 0),
            "style_notes": ai_result.get("style_notes", ""),
            "selected_items": selected_item_ids
        }
        
    except Exception as e:
        return {"error": str(e)}

@shared_task  
def generate_outfit_variations(outfit_id: int, num_variations: int = 3) -> dict:
    """Generate variations of an existing outfit."""
    try:
        db = next(get_db())
        original_outfit = db.get(Outfit, outfit_id)
        
        if not original_outfit:
            return {"error": "Original outfit not found"}
        
        # Get current items
        current_items = []
        for outfit_item in original_outfit.outfit_items:
            item = outfit_item.item
            current_items.append({
                "id": item.id,
                "name": item.name,
                "category": outfit_item.item_category,
                "color": item.color,
                "style": item.style
            })
        
        # Get alternative items from catalog
        alternative_items = db.query(Item).filter(Item.id.notin_([item["id"] for item in current_items])).all()
        
        alternatives_by_category = {}
        for item in alternative_items:
            category = item.category or "other"
            if category not in alternatives_by_category:
                alternatives_by_category[category] = []
            
            alternatives_by_category[category].append({
                "id": item.id,
                "name": item.name,
                "brand": item.brand,
                "color": item.color,
                "price": item.price,
                "style": item.style
            })
        
        prompt = f"""
        Create {num_variations} variations of this outfit:
        
        Original outfit: {original_outfit.name}
        Style: {original_outfit.style}
        Current items: {json.dumps(current_items, indent=2)}
        
        Available alternatives: {json.dumps(alternatives_by_category, indent=2)}
        
        For each variation, keep the overall style but change 1-2 items. Respond with:
        {{
          "variations": [
            {{
              "name": "variation name",
              "description": "what changed and why",
              "selected_items": [item_ids],
              "changed_categories": ["which categories were changed"]
            }}
          ]
        }}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a fashion stylist creating outfit variations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.9
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        return {"error": str(e)}

@shared_task
def generate_seasonal_outfits(season: str, style: str, limit: int = 5) -> dict:
    """Generate seasonal outfit recommendations."""
    try:
        db = next(get_db())
        
        # Get items suitable for the season
        seasonal_keywords = {
            "winter": ["coat", "sweater", "boots", "warm", "wool"],
            "summer": ["tshirt", "shorts", "sandals", "light", "cotton"],
            "spring": ["jacket", "cardigan", "sneakers", "fresh"],
            "autumn": ["jacket", "boots", "layers", "cozy"]
        }
        
        keywords = seasonal_keywords.get(season, [])
        
        query = db.query(Item)
        if keywords:
            # Filter items that match seasonal keywords
            conditions = []
            for keyword in keywords:
                conditions.extend([
                    Item.name.ilike(f"%{keyword}%"),
                    Item.description.ilike(f"%{keyword}%"),
                    Item.clothing_type.ilike(f"%{keyword}%")
                ])
            
            if conditions:
                from sqlalchemy import or_
                query = query.filter(or_(*conditions))
        
        seasonal_items = query.limit(50).all()  # Limit for performance
        
        if not seasonal_items:
            return {"error": f"No items found for {season}"}
        
        # Group items by category
        items_by_category = {}
        for item in seasonal_items:
            category = item.category or "other"
            if category not in items_by_category:
                items_by_category[category] = []
            
            items_by_category[category].append({
                "id": item.id,
                "name": item.name,
                "brand": item.brand,
                "color": item.color,
                "price": item.price,
                "style": item.style
            })
        
        prompt = f"""
        Create {limit} seasonal outfit recommendations for {season}:
        
        Season: {season}
        Style: {style}
        Available items: {json.dumps(items_by_category, indent=2)}
        
        Create outfits that are:
        1. Appropriate for {season} weather
        2. Follow {style} aesthetic
        3. Use items from the available catalog
        
        Respond with:
        {{
          "seasonal_outfits": [
            {{
              "name": "outfit name",
              "description": "seasonal appropriateness",
              "selected_items": [item_ids],
              "weather_notes": "weather considerations"
            }}
          ]
        }}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"You are a fashion stylist specializing in {season} fashion."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.8
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        return {"error": str(e)}


def generate_outfit_from_selected_items(
    user_id: int,
    selected_item_ids: List[int],
    style: str,
    occasion: str,
    additional_categories: Optional[List[str]] = None
) -> dict:
    """Generate outfit from user-selected items plus additional suggestions."""
    try:
        db = next(get_db())
        
        # Get selected items
        selected_items = db.query(Item).filter(Item.id.in_(selected_item_ids)).all()
        if not selected_items:
            return {"error": "No selected items found"}
        
        # Prepare selected items data
        selected_data = []
        used_categories = set()
        for item in selected_items:
            selected_data.append({
                "id": item.id,
                "name": item.name,
                "brand": item.brand,
                "color": item.color,
                "category": item.category,
                "style": item.style,
                "price": item.price
            })
            used_categories.add(item.category)
        
        # Get additional items if needed
        additional_items = []
        if additional_categories:
            needed_categories = set(additional_categories) - used_categories
            if needed_categories:
                additional_query = db.query(Item).filter(
                    Item.category.in_(list(needed_categories)),
                    ~Item.id.in_(selected_item_ids)
                )
                additional_items = additional_query.limit(20).all()
        
        additional_data = []
        for item in additional_items:
            additional_data.append({
                "id": item.id,
                "name": item.name,
                "brand": item.brand,
                "color": item.color,
                "category": item.category,
                "style": item.style,
                "price": item.price
            })
        
        # Create AI prompt
        prompt = f"""
        Create a stylish outfit based on user-selected items and suggest additional pieces:
        
        User selected items (MUST include all of these):
        {json.dumps(selected_data, indent=2)}
        
        Style: {style}
        Occasion: {occasion}
        
        Available additional items to choose from:
        {json.dumps(additional_data, indent=2)}
        
        Please create an outfit that:
        1. INCLUDES ALL user-selected items
        2. Suggests 1-3 additional items from available list to complete the look
        3. Ensures style consistency and color harmony
        
        Respond with:
        {{
          "selected_items": [all_item_ids_including_user_selected_and_additional],
          "outfit_name": "creative outfit name",
          "description": "why this combination works well",
          "total_price": sum_of_all_items_prices,
          "style_notes": "styling tips and recommendations",
          "user_items_included": [user_selected_item_ids],
          "suggested_additions": [additional_item_ids]
        }}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional stylist helping users complete their outfit with selected items."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        ai_result = json.loads(response.choices[0].message.content)
        
        # Create outfit in database
        user = db.get(User, user_id)
        if not user:
            return {"error": "User not found"}
        
        db_outfit = Outfit(
            name=ai_result.get("outfit_name", f"{style} Outfit"),
            style=style,
            description=ai_result.get("description", "Generated from selected items"),
            owner_id=str(user_id)
        )
        
        # Add all items to outfit
        final_item_ids = ai_result.get("selected_items", selected_item_ids)
        category_mapping = {
            "top": "top", "tops": "top", "shirt": "top", "tshirt": "top", "hoodie": "top",
            "sweater": "top", "jacket": "top", "coat": "top", "dress": "top",
            "bottom": "bottom", "bottoms": "bottom", "pants": "bottom", "jeans": "bottom",
            "shorts": "bottom", "skirt": "bottom",
            "footwear": "footwear",
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
        
        return {
            "outfit_id": db_outfit.id,
            "outfit_name": db_outfit.name,
            "description": db_outfit.description,
            "total_price": ai_result.get("total_price", 0),
            "style_notes": ai_result.get("style_notes", ""),
            "selected_items": final_item_ids,
            "user_items_included": ai_result.get("user_items_included", selected_item_ids),
            "suggested_additions": ai_result.get("suggested_additions", [])
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
    """Generate completely random outfit from catalog."""
    try:
        db = next(get_db())
        
        # Get random items from catalog
        query = db.query(Item)
        
        if collection:
            query = query.filter(Item.collection == collection)
        
        if budget:
            query = query.filter(Item.price <= budget / 3)  # Rough budget per item
        
        # Get random selection
        import random
        all_items = query.all()
        
        if len(all_items) < 3:
            return {"error": "Not enough items in catalog for random generation"}
        
        # Randomly select 20-30 items for AI to choose from
        sample_size = min(30, len(all_items))
        random_items = random.sample(all_items, sample_size)
        
        # Group by category
        items_by_category = {}
        for item in random_items:
            category = item.category or "other"
            if category not in items_by_category:
                items_by_category[category] = []
            
            items_by_category[category].append({
                "id": item.id,
                "name": item.name,
                "brand": item.brand,
                "color": item.color,
                "price": item.price,
                "style": item.style
            })
        
        prompt = f"""
        Create a completely random stylish outfit for:
        
        Style: {style}
        Occasion: {occasion}
        Budget: {budget or "No limit"}
        
        Random items to choose from:
        {json.dumps(items_by_category, indent=2)}
        
        Create a surprising but harmonious combination that the user might not have thought of.
        Be creative and bold with your choices while maintaining style coherence.
        
        Respond with:
        {{
          "selected_items": [item_ids],
          "outfit_name": "creative and fun outfit name",
          "description": "why this random combination is amazing",
          "total_price": sum_of_prices,
          "style_notes": "how to style this unexpected combination",
          "surprise_factor": "what makes this outfit unexpectedly great"
        }}
        
        Select 3-6 items total for a complete look.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a creative fashion stylist who loves making unexpected but amazing outfit combinations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=1.0  # Higher temperature for more creativity
        )
        
        ai_result = json.loads(response.choices[0].message.content)
        
        # Create outfit in database
        user = db.get(User, user_id)
        if not user:
            return {"error": "User not found"}
        
        db_outfit = Outfit(
            name=ai_result.get("outfit_name", f"Random {style} Look"),
            style=style,
            description=ai_result.get("description", "Randomly generated outfit"),
            owner_id=str(user_id),
            collection=collection
        )
        
        # Add items to outfit
        selected_item_ids = ai_result.get("selected_items", [])
        category_mapping = {
            "top": "top", "tops": "top", "shirt": "top", "tshirt": "top", "hoodie": "top",
            "sweater": "top", "jacket": "top", "coat": "top", "dress": "top",
            "bottom": "bottom", "bottoms": "bottom", "pants": "bottom", "jeans": "bottom",
            "shorts": "bottom", "skirt": "bottom",
            "footwear": "footwear",
            "accessories": "accessory", "accessory": "accessory",
            "fragrances": "fragrance", "fragrance": "fragrance"
        }
        
        for item_id in selected_item_ids:
            item = db.get(Item, item_id)
            if item:
                item_category = category_mapping.get(item.category, "accessory")
                outfit_item = OutfitItem(item_category=item_category, item=item)
                db_outfit.outfit_items.append(outfit_item)
        
        db.add(db_outfit)
        db.commit()
        db.refresh(db_outfit)
        
        return {
            "outfit_id": db_outfit.id,
            "outfit_name": db_outfit.name,
            "description": db_outfit.description,
            "total_price": ai_result.get("total_price", 0),
            "style_notes": ai_result.get("style_notes", ""),
            "surprise_factor": ai_result.get("surprise_factor", ""),
            "selected_items": selected_item_ids
        }
        
    except Exception as e:
        return {"error": str(e)}

