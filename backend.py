from aiohttp import web
from aiohttp.web_middlewares import middleware
import aiohttp
import config
from database import Database
import logging
import time
from collections import defaultdict
import secrets
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO, filename="backend.log", filemode="a",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

db = Database()

# Создаём папку media, если её нет
MEDIA_DIR = "media"
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

# Хранилище для ограничения скорости
rate_limit = defaultdict(list)

@middleware
async def rate_limit_middleware(request, handler):
    user_id = request.query.get("user_id", "unknown")
    now = time.time()
    rate_limit[user_id] = [t for t in rate_limit[user_id] if now - t < 60]  # 60 секунд окно
    if len(rate_limit[user_id]) >= 10:  # Макс 10 запросов в минуту
        return await handle_error(request, "Слишком много запросов", 429)
    rate_limit[user_id].append(now)
    return await handler(request)

@middleware
async def csrf_middleware(request, handler):
    if request.method == "POST":
        csrf_token = request.headers.get("X-CSRF-Token")
        expected_token = request.app.get("csrf_token")
        if not csrf_token or csrf_token != expected_token:
            return await handle_error(request, "Недействительный CSRF-токен", 403)
    return await handler(request)

async def handle_error(request, message, status=400):
    logger.error(f"Ошибка в {request.path}: {message}")
    return web.json_response({"error": message}, status=status)

async def check_moderator(request):
    try:
        user_id = int(request.query.get("user_id"))
        return web.json_response({"isModerator": user_id in config.MODERATOR_IDS})
    except (ValueError, TypeError):
        return await handle_error(request, "Некорректный user_id", 400)

async def upload_meme(request):
    try:
        data = await request.post()
        title = data.get("title")
        if not title or len(title) > 100:
            return await handle_error(request, "Название мема обязательно и не длиннее 100 символов", 400)
        description = data.get("description", "")[:1000]
        tag = data.get("tag", "")[:50]
        is_adult = data.get("isAdult") == "true"
        user_id = int(data.get("userId"))
        media = data.get("media")

        if media:
            if media.size > 10 * 1024 * 1024:  # Лимит 10 МБ
                return await handle_error(request, "Файл слишком большой (макс. 10 МБ)", 400)
            allowed_types = ["image/jpeg", "image/png", "image/gif", "video/mp4"]
            if media.content_type not in allowed_types:
                return await handle_error(request, "Недопустимый формат файла", 400)

        meme = {
            "title": title,
            "description": description,
            "tag": tag,
            "isAdult": is_adult,
            "userId": user_id,
            "mediaUrl": await save_media(media) if media else None,
            "status": "pending",
            "likes": 0,
            "dislikes": 0,
            "comments": []
        }
        await db.save_meme(meme)
        return web.json_response({"message": "Мем отправлен на модерацию"})
    except ValueError:
        return await handle_error(request, "Некорректные данные", 400)
    except Exception as e:
        logger.error(f"Ошибка при загрузке мема: {e}")
        return await handle_error(request, "Внутренняя ошибка сервера", 500)

async def save_media(media):
    if not media:
        return None
    try:
        # Генерируем уникальное имя файла
        filename = f"{secrets.token_hex(16)}_{media.filename}"
        file_path = os.path.join(MEDIA_DIR, filename)
        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(media.file.read())
        # Возвращаем URL для доступа к файлу
        return f"/media/{filename}"
    except Exception as e:
        logger.error(f"Ошибка сохранения медиа: {e}")
        raise

async def get_memes(request):
    try:
        page = int(request.query.get("page", 1))
        limit = int(request.query.get("limit", 10))
        skip = (page - 1) * limit
        memes = await db.get_approved_memes(skip=skip, limit=limit)
        return web.json_response(memes)
    except ValueError:
        return await handle_error(request, "Некорректные параметры пагинации", 400)

async def get_moderation_memes(request):
    try:
        memes = await db.get_pending_memes()
        return web.json_response(memes)
    except Exception as e:
        logger.error(f"Ошибка при получении мемов для модерации: {e}")
        return await handle_error(request, "Внутренняя ошибка сервера", 500)

async def like_meme(request):
    try:
        meme_id = request.query["meme_id"]
        await db.update_meme(meme_id, {"$inc": {"likes": 1}})
        return web.json_response({"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка при лайке мема: {e}")
        return await handle_error(request, "Внутренняя ошибка сервера", 500)

async def dislike_meme(request):
    try:
        meme_id = request.query["meme_id"]
        await db.update_meme(meme_id, {"$inc": {"dislikes": 1}})
        return web.json_response({"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка при дизлайке мема: {e}")
        return await handle_error(request, "Внутренняя ошибка сервера", 500)

async def add_comment(request):
    try:
        meme_id = request.query["meme_id"]
        comment = request.query["comment"]
        if len(comment) > 500:
            return await handle_error(request, "Комментарий слишком длинный (макс. 500 символов)", 400)
        await db.update_meme(meme_id, {"$push": {"comments": comment}})
        return web.json_response({"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка при добавлении комментария: {e}")
        return await handle_error(request, "Внутренняя ошибка сервера", 500)

async def approve_meme(request):
    try:
        meme_id = request.query["meme_id"]
        await db.update_meme(meme_id, {"status": "approved"})
        return web.json_response({"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка при одобрении мема: {e}")
        return await handle_error(request, "Внутренняя ошибка сервера", 500)

async def reject_meme(request):
    try:
        meme_id = request.query["meme_id"]
        await db.delete_meme(meme_id)
        return web.json_response({"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка при отклонении мема: {e}")
        return await handle_error(request, "Внутренняя ошибка сервера", 500)

async def get_csrf_token(request):
    return web.json_response({"csrf_token": request.app["csrf_token"]})

app = web.Application(middlewares=[rate_limit_middleware, csrf_middleware])
app["csrf_token"] = secrets.token_urlsafe(32)

# Добавляем маршрут для доступа к медиафайлам
app.add_routes([
    web.get("/api/check_moderator", check_moderator),
    web.post("/api/upload_meme", upload_meme),
    web.get("/api/get_memes", get_memes),
    web.get("/api/get_moderation_memes", get_moderation_memes),
    web.post("/api/like_meme", like_meme),
    web.post("/api/dislike_meme", dislike_meme),
    web.post("/api/add_comment", add_comment),
    web.post("/api/approve_meme", approve_meme),
    web.post("/api/reject_meme", reject_meme),
    web.get("/api/csrf_token", get_csrf_token),
    web.static("/media", MEDIA_DIR),  # Статический маршрут для медиафайлов
])

if __name__ == "__main__":
    web.run_app(app, port=8080)