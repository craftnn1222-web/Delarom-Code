import os, asyncio
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

env = dotenv_values("/app/backend/.env")


async def main():
    db = AsyncIOMotorClient(env["MONGO_URL"])[env["DB_NAME"]]
    for e in ["craftnn1222@gmail.com", "rep_tester_round2@delarom.com"]:
        u = await db.users.find_one({"email": e}, {"_id": 0, "password": 0, "hashed_password": 0})
        print({k: u.get(k) for k in ("id", "username", "email", "role", "currency", "status")} if u else None)
        if u:
            ch = await db.characters.find({"user_id": u["id"]}, {"_id": 0, "id": 1, "name": 1}).to_list(10)
            print(ch)
    print("goods", await db.goods.count_documents({}))
    print("grain", await db.goods.find_one({"slug": "grain"}, {"_id": 0, "slug": 1, "default_base_cost": 1}))
    print("companies", await db.trade_companies.count_documents({}))
    print("producers", await db.city_producers.count_documents({}))
    print("inv duncroft grain", await db.producer_inventory.find_one({"owner_key": "ammeonon:duncroft", "good_slug": "grain"}, {"_id": 0}))


asyncio.run(main())
