"""Auto-extracted routes module — shops.

Extracted from server.py (2026-05-30 refactor). Registered via
`attach_shop_routes(api_router, ...)`. The factory takes shared deps as
keyword args; route bodies close over them.
"""
from typing import List, Optional, Dict
from datetime import datetime, timezone
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)


async def _auto_price_or_400(db, item_payload: Dict, shop_doc: Dict) -> int:
    """Resolve the auto-priced item's retail price from the goods market.

    Falls back to the shop's `nation` if `source_nation` is empty. Raises
    HTTP 400 with a helpful message if the goods market can't satisfy the
    request (good missing from catalogue, city without a contract, etc.).
    """
    from economy_service import EconomyService
    good_slug = item_payload.get("source_good_slug")
    city_slug = item_payload.get("source_city_slug")
    nation = item_payload.get("source_nation") or shop_doc.get("nation") or ""
    markup_pct = item_payload.get("markup_pct")
    if not good_slug or not city_slug or not nation:
        raise HTTPException(
            status_code=400,
            detail="Auto-priced items require source_good_slug, source_city_slug, "
                   "and source_nation (or a shop with a nation set).",
        )
    price = await EconomyService(db).resolve_item_auto_price(
        nation=nation, city_slug=city_slug, good_slug=good_slug, markup_pct=markup_pct,
    )
    if price is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No active market price for {good_slug} in {city_slug} ({nation}). "
                "An active trade contract supplying this city must exist."
            ),
        )
    return int(price)


def attach_shop_routes(
    api_router: APIRouter,
    *,
    db, User, get_current_user, Shop, ShopCreate, Item, ItemCreate, Transaction, TransactionType, EquipRequest, UnequipRequest, PurchaseRequest,
):
    # ==================== WALLET/CURRENCY ROUTES ====================

    @api_router.get("/wallet")
    async def get_wallet(current_user: User = Depends(get_current_user)):
        return {"balance": current_user.currency}

    @api_router.get("/wallet/transactions", response_model=List[Transaction])
    async def get_transactions(current_user: User = Depends(get_current_user)):
        transactions = await db.transactions.find(
            {"user_id": current_user.id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    
        for trans in transactions:
            if isinstance(trans.get('created_at'), str):
                trans['created_at'] = datetime.fromisoformat(trans['created_at'])
    
        return transactions

    # ==================== SHOP ROUTES ====================

    @api_router.post("/shops", response_model=Shop)
    async def create_shop(shop_data: ShopCreate, current_user: User = Depends(get_current_user)):
        # Check if user already has a shop
        existing = await db.shops.find_one({"owner_id": current_user.id})
        if existing:
            raise HTTPException(status_code=400, detail="You already have a shop")
    
        shop = Shop(
            owner_id=current_user.id,
            owner_username=current_user.username,
            **shop_data.model_dump()
        )
    
        shop_doc = shop.model_dump()
        shop_doc['created_at'] = shop_doc['created_at'].isoformat()
    
        await db.shops.insert_one(shop_doc)
        return shop

    @api_router.get("/shops", response_model=List[Shop])
    async def get_shops(nation: Optional[str] = None):
        query = {}
        if nation:
            query['nation'] = nation
    
        shops = await db.shops.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
        for shop in shops:
            if isinstance(shop.get('created_at'), str):
                shop['created_at'] = datetime.fromisoformat(shop['created_at'])
        return shops

    @api_router.get("/shops/my-shop", response_model=Shop)
    async def get_my_shop(current_user: User = Depends(get_current_user)):
        shop_doc = await db.shops.find_one({"owner_id": current_user.id}, {"_id": 0})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="You don't have a shop yet")
        if isinstance(shop_doc.get('created_at'), str):
            shop_doc['created_at'] = datetime.fromisoformat(shop_doc['created_at'])
        return Shop(**shop_doc)

    @api_router.get("/shops/{shop_id}", response_model=Shop)
    async def get_shop(shop_id: str):
        shop_doc = await db.shops.find_one({"id": shop_id}, {"_id": 0})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")
        if isinstance(shop_doc.get('created_at'), str):
            shop_doc['created_at'] = datetime.fromisoformat(shop_doc['created_at'])
        return Shop(**shop_doc)

    @api_router.post("/shops/{shop_id}/items", response_model=Item)
    async def add_item(shop_id: str, item_data: ItemCreate, current_user: User = Depends(get_current_user)):
        shop_doc = await db.shops.find_one({"id": shop_id})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")
        if shop_doc['owner_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
        payload = item_data.model_dump()
        # Economy auto-pricing — if opted in, override `price` from goods catalogue.
        if payload.get("is_auto_priced"):
            payload["price"] = await _auto_price_or_400(db, payload, shop_doc)
            payload["last_repriced_at"] = datetime.now(timezone.utc).isoformat()

        item = Item(shop_id=shop_id, **payload)
        item_doc = item.model_dump()
        item_doc['created_at'] = item_doc['created_at'].isoformat()
    
        await db.items.insert_one(item_doc)
        return item

    @api_router.get("/shops/{shop_id}/items", response_model=List[Item])
    async def get_shop_items(shop_id: str):
        items = await db.items.find({"shop_id": shop_id}, {"_id": 0}).to_list(100)
        for item in items:
            if isinstance(item.get('created_at'), str):
                item['created_at'] = datetime.fromisoformat(item['created_at'])
        return items

    @api_router.get("/shops/{shop_id}/customers")
    async def get_shop_customers(
        shop_id: str,
        limit: int = 30,
        current_user: User = Depends(get_current_user),
    ):
        """Recent NPC walk-in customers for a shop. Any authed user can
        peek — it's flavour data. Shop owners see it on their dashboard."""
        from npc_economy import recent_shop_customers
        shop_doc = await db.shops.find_one({"id": shop_id}, {"_id": 0, "id": 1})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")
        return await recent_shop_customers(db, shop_id, limit=limit)

    @api_router.get("/shops/{shop_id}/alerts")
    async def get_shop_alerts(shop_id: str, current_user: User = Depends(get_current_user)):
        """Unseen low-stock (sold-out) alerts for the owner's shop."""
        shop_doc = await db.shops.find_one({"id": shop_id}, {"_id": 0})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")
        if shop_doc.get("owner_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only view your own shop's alerts")
        return await db.shop_alerts.find(
            {"shop_id": shop_id, "seen": False}, {"_id": 0},
        ).sort("created_at", -1).to_list(50)

    @api_router.post("/shops/{shop_id}/alerts/seen")
    async def mark_shop_alerts_seen(shop_id: str, current_user: User = Depends(get_current_user)):
        """Dismiss all unseen alerts for this shop."""
        shop_doc = await db.shops.find_one({"id": shop_id}, {"_id": 0})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")
        if shop_doc.get("owner_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only manage your own shop's alerts")
        res = await db.shop_alerts.update_many(
            {"shop_id": shop_id, "seen": False}, {"$set": {"seen": True}},
        )
        return {"cleared": res.modified_count}



    @api_router.delete("/items/{item_id}")
    async def delete_shop_item(item_id: str, current_user: User = Depends(get_current_user)):
        """Delete an item from the user's shop."""
        # Find the item
        item_doc = await db.items.find_one({"id": item_id})
        if not item_doc:
            raise HTTPException(status_code=404, detail="Item not found")
    
        # Find the shop to verify ownership
        shop_doc = await db.shops.find_one({"id": item_doc['shop_id']})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")
    
        # Verify the user owns this shop
        if shop_doc['owner_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only delete items from your own shop")
    
        # Delete the item
        await db.items.delete_one({"id": item_id})
    
        return {"message": f"Item '{item_doc['name']}' has been removed from your shop"}


    @api_router.put("/items/{item_id}")
    async def update_shop_item(item_id: str, item_data: ItemCreate, current_user: User = Depends(get_current_user)):
        """Update an item in the user's shop."""
        # Find the item
        item_doc = await db.items.find_one({"id": item_id})
        if not item_doc:
            raise HTTPException(status_code=404, detail="Item not found")
    
        # Find the shop to verify ownership
        shop_doc = await db.shops.find_one({"id": item_doc['shop_id']})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")
    
        # Verify the user owns this shop
        if shop_doc['owner_id'] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only update items in your own shop")
    
        # Update the item
        update_data = {
            "name": item_data.name,
            "description": item_data.description,
            "price": item_data.price,
            "stock": item_data.stock,
            "item_type": item_data.item_type,
            "equipment_slot": item_data.equipment_slot,
            "stat_bonuses": item_data.stat_bonuses or {},
            "source_good_slug": item_data.source_good_slug,
            "source_city_slug": item_data.source_city_slug,
            "source_nation": item_data.source_nation,
            "markup_pct": item_data.markup_pct,
            "is_auto_priced": item_data.is_auto_priced,
            "auto_restock": item_data.auto_restock,
            "restock_target": item_data.restock_target,
        }
        # Economy auto-pricing — recompute if the owner opted in.
        if item_data.is_auto_priced:
            update_data["price"] = await _auto_price_or_400(
                db, item_data.model_dump(), shop_doc,
            )
            update_data["last_repriced_at"] = datetime.now(timezone.utc).isoformat()
    
        await db.items.update_one({"id": item_id}, {"$set": update_data})
    
        # Get updated item
        updated_item = await db.items.find_one({"id": item_id}, {"_id": 0})
        if isinstance(updated_item.get('created_at'), str):
            updated_item['created_at'] = datetime.fromisoformat(updated_item['created_at'])
    
        return updated_item


    @api_router.post("/items/{item_id}/refresh-price")
    async def refresh_item_price(item_id: str, current_user: User = Depends(get_current_user)):
        """Re-derive the auto-priced item's `price` from the current goods market.

        Use this after a faction adjusts production cost or after a world
        event has shifted market prices.
        """
        item_doc = await db.items.find_one({"id": item_id}, {"_id": 0})
        if not item_doc:
            raise HTTPException(status_code=404, detail="Item not found")
        shop_doc = await db.shops.find_one({"id": item_doc.get("shop_id")}, {"_id": 0})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")
        if shop_doc.get("owner_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        if not item_doc.get("is_auto_priced"):
            raise HTTPException(status_code=400, detail="This item is not auto-priced; set is_auto_priced=true first.")
        new_price = await _auto_price_or_400(db, item_doc, shop_doc)
        await db.items.update_one(
            {"id": item_id},
            {"$set": {
                "price": new_price,
                "last_repriced_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return {"id": item_id, "price": new_price}


    @api_router.post("/shops/{shop_id}/refresh-prices")
    async def refresh_shop_prices(shop_id: str, current_user: User = Depends(get_current_user)):
        """Bulk refresh every auto-priced item in this shop. Returns counts."""
        shop_doc = await db.shops.find_one({"id": shop_id}, {"_id": 0})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")
        if shop_doc.get("owner_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        items = await db.items.find(
            {"shop_id": shop_id, "is_auto_priced": True}, {"_id": 0},
        ).to_list(500)
        updated = 0
        skipped = 0
        for it in items:
            try:
                new_price = await _auto_price_or_400(db, it, shop_doc)
                await db.items.update_one(
                    {"id": it["id"]},
                    {"$set": {
                        "price": new_price,
                        "last_repriced_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                updated += 1
            except HTTPException:
                skipped += 1
        return {"updated": updated, "skipped": skipped, "total_auto_priced": len(items)}


    @api_router.post("/items/{item_id}/purchase")
    async def purchase_item(item_id: str, payload: PurchaseRequest, current_user: User = Depends(get_current_user)):
        item_doc = await db.items.find_one({"id": item_id})
        if not item_doc:
            raise HTTPException(status_code=404, detail="Item not found")

        if item_doc['stock'] <= 0:
            raise HTTPException(status_code=400, detail="Item out of stock")

        # Verify character belongs to user
        char_doc = await db.characters.find_one({"id": payload.character_id, "user_id": current_user.id})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found or not yours")

        # Get shop owner
        shop_doc = await db.shops.find_one({"id": item_doc['shop_id']})
        if not shop_doc:
            raise HTTPException(status_code=404, detail="Shop not found")

        # ── Reputation-driven pricing ─────────────────────────────
        # Buyer's Renown in the shop's city shifts the price ±25%.
        # Legend (+76+): friend's price. Hunted (-76-): pay dear or don't sell.
        from reputation_web_service import ReputationWebService
        rep = ReputationWebService(db)
        city_slug = (shop_doc.get("city_slug") or shop_doc.get("nation", "")).lower()
        stance = await rep.guard_stance(payload.character_id, city_slug)
        if stance == "arrest":
            raise HTTPException(
                status_code=403,
                detail=(
                    "The shopkeeper eyes you coldly and closes the counter — "
                    "you are Hunted in this city and no one will trade with you."
                ),
            )
        price_mod = await rep.shop_price_modifier(payload.character_id, city_slug)
        final_price = max(1, int(round(int(item_doc['price']) * price_mod)))

        if current_user.currency < final_price:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        # Deduct from buyer
        await db.users.update_one({"id": current_user.id}, {"$inc": {"currency": -final_price}})

        # Add to seller
        await db.users.update_one({"id": shop_doc['owner_id']}, {"$inc": {"currency": final_price}})

        # Decrease stock
        await db.items.update_one({"id": item_id}, {"$inc": {"stock": -1}})

        # Low-stock alert for the shop owner when a purchase clears the shelf.
        if int(item_doc.get('stock', 0)) - 1 <= 0:
            try:
                from npc_economy import _emit_out_of_stock_alert
                await _emit_out_of_stock_alert(
                    db, item_doc['shop_id'], item_id, item_doc.get('name', 'item'),
                )
            except Exception as e:  # pragma: no cover — best-effort
                logger.warning(f"out-of-stock alert failed: {e}")

        # Renown nudge — buying from a city's shops modestly raises your standing
        # (unless the shop is NPC-owned in a city where you're already Legend).
        try:
            if city_slug:
                await rep.adjust(
                    payload.character_id, "city", city_slug,
                    delta=1,
                    reason=f"Bought {item_doc.get('name','goods')} in {city_slug}",
                )
        except Exception as e:  # pragma: no cover — best-effort
            logger.warning(f"purchase rep-nudge failed: {e}")

        # Add item to character's inventory
        inventory_item = {
            "id": str(uuid.uuid4()),
            "item_id": item_id,
            "name": item_doc['name'],
            "description": item_doc['description'],
            "item_type": item_doc.get('item_type', 'equipment'),
            "equipment_slot": item_doc.get('equipment_slot'),
            "stat_bonuses": item_doc.get('stat_bonuses', {}),
            "acquired_from": "shop_purchase",
            "acquired_at": datetime.now(timezone.utc).isoformat()
        }
        await db.characters.update_one(
            {"id": payload.character_id},
            {"$push": {"inventory": inventory_item}}
        )

        # Create transactions
        buyer_trans = Transaction(
            user_id=current_user.id,
            amount=-final_price,
            transaction_type=TransactionType.SHOP_PURCHASE,
            description=f"Purchased {item_doc['name']} from {shop_doc['name']} for {char_doc['name']}",
            related_id=item_id
        )
        buyer_doc = buyer_trans.model_dump()
        buyer_doc['created_at'] = buyer_doc['created_at'].isoformat()
        await db.transactions.insert_one(buyer_doc)

        seller_trans = Transaction(
            user_id=shop_doc['owner_id'],
            amount=final_price,
            transaction_type=TransactionType.SHOP_SALE,
            description=f"Sold {item_doc['name']} to {current_user.username}",
            related_id=item_id
        )
        seller_doc = seller_trans.model_dump()
        seller_doc['created_at'] = seller_doc['created_at'].isoformat()
        await db.transactions.insert_one(seller_doc)

        return {
            "message": "Purchase successful!",
            "item": item_doc['name'],
            "list_price": item_doc['price'],
            "price_paid": final_price,
            "price_modifier_pct": int(round((price_mod - 1.0) * 100)),
            "new_balance": current_user.currency - final_price,
        }


    # ==================== EQUIPMENT/INVENTORY ROUTES ====================

    @api_router.post("/characters/{character_id}/equip-item")
    async def equip_item(character_id: str, payload: EquipRequest, current_user: User = Depends(get_current_user)):
        """Equip an item from inventory to an equipment slot"""
        char_doc = await db.characters.find_one({"id": character_id, "user_id": current_user.id})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found or not yours")
    
        # Find the item in inventory
        inventory = char_doc.get('inventory', [])
        item_to_equip = None
        item_index = None
    
        for i, inv_item in enumerate(inventory):
            if inv_item['id'] == payload.inventory_item_id:
                item_to_equip = inv_item
                item_index = i
                break
    
        if not item_to_equip:
            raise HTTPException(status_code=404, detail="Item not found in inventory")
    
        equipment_slot = item_to_equip.get('equipment_slot')
        if not equipment_slot:
            raise HTTPException(status_code=400, detail="Item is not equippable")
    
        # Check if slot is valid
        valid_slots = ["weapon", "head", "chest", "legs", "boots", "gloves", "ring", "necklace"]
        if equipment_slot not in valid_slots:
            raise HTTPException(status_code=400, detail="Invalid equipment slot")
    
        equipped = char_doc.get('equipped', {})
    
        # If slot already has an item, unequip it to inventory first
        if equipped.get(equipment_slot):
            old_item = equipped[equipment_slot]
            inventory.append(old_item)
    
        # Equip the new item
        equipped[equipment_slot] = item_to_equip
    
        # Remove from inventory
        inventory.pop(item_index)
    
        # Update database
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"equipped": equipped, "inventory": inventory}}
        )
    
        return {
            "message": f"{item_to_equip['name']} equipped to {equipment_slot}",
            "equipped": equipped,
            "inventory": inventory
        }

    @api_router.post("/characters/{character_id}/unequip-item")
    async def unequip_item(character_id: str, payload: UnequipRequest, current_user: User = Depends(get_current_user)):
        """Unequip an item from an equipment slot back to inventory"""
        char_doc = await db.characters.find_one({"id": character_id, "user_id": current_user.id})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found or not yours")
    
        equipped = char_doc.get('equipped', {})
    
        if payload.equipment_slot not in equipped or not equipped.get(payload.equipment_slot):
            raise HTTPException(status_code=400, detail="No item equipped in that slot")
    
        # Move item from equipped to inventory
        item = equipped[payload.equipment_slot]
        equipped[payload.equipment_slot] = None
    
        inventory = char_doc.get('inventory', [])
        inventory.append(item)
    
        # Update database
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"equipped": equipped, "inventory": inventory}}
        )
    
        return {
            "message": f"{item['name']} unequipped from {payload.equipment_slot}",
            "equipped": equipped,
            "inventory": inventory
        }

    @api_router.get("/characters/{character_id}/stats")
    async def get_character_stats(character_id: str, current_user: User = Depends(get_current_user)):
        """Get character stats including bonuses from equipped gear"""
        char_doc = await db.characters.find_one({"id": character_id, "user_id": current_user.id}, {"_id": 0})
        if not char_doc:
            raise HTTPException(status_code=404, detail="Character not found or not yours")
    
        # Base stats
        base_stats = {
            "strength": char_doc.get('strength', 10),
            "magic": char_doc.get('magic', 10),
            "agility": char_doc.get('agility', 10),
            "endurance": char_doc.get('endurance', 10),
            "charisma": char_doc.get('charisma', 10),
            "luck": char_doc.get('luck', 10)
        }
    
        # Calculate bonuses from equipped gear
        gear_bonuses = {stat: 0 for stat in base_stats.keys()}
        equipped = char_doc.get('equipped', {})
    
        for slot, item in equipped.items():
            if item and item.get('stat_bonuses'):
                for stat, bonus in item['stat_bonuses'].items():
                    if stat in gear_bonuses:
                        gear_bonuses[stat] += bonus
    
        # Total stats
        total_stats = {stat: base_stats[stat] + gear_bonuses[stat] for stat in base_stats.keys()}
    
        return {
            "base_stats": base_stats,
            "gear_bonuses": gear_bonuses,
            "total_stats": total_stats,
            "equipped": equipped
        }

