from pymongo import MongoClient
import asyncio

class Database:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017")
        self.db = self.client["meme_bot"]
        self.memes = self.db["memes"]

    async def save_meme(self, meme):
        await asyncio.sleep(0)  # Для асинхронности
        self.memes.insert_one(meme)

    async def get_approved_memes(self, skip=0, limit=10):
        return list(self.memes.find({"status": "approved"}).skip(skip).limit(limit))

    async def get_pending_memes(self):
        return list(self.memes.find({"status": "pending"}))

    async def update_meme(self, meme_id, update):
        self.memes.update_one({"_id": meme_id}, update)

    async def delete_meme(self, meme_id):
        self.memes.delete_one({"_id": meme_id})