from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from fastapi import APIRouter
from app.core.config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN,
          default=DefaultBotProperties(parse_mode="HTML"))
dp  = Dispatcher()
router_bot = APIRouter(prefix="/bot", tags=["telegram-bot"])

main_router = Router()


@main_router.message(Command("start"))
async def start_handler(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🌸 Открыть магазин",
            web_app=WebAppInfo(url=settings.TELEGRAM_WEB_APP_URL)
        )
    ]])
    await message.answer(
        "Добро пожаловать в <b>Flower Shop</b>! 🌹\n"
        "Нажмите кнопку ниже чтобы просмотреть каталог и сделать заказ.",
        reply_markup=keyboard
    )


@main_router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "🌸 <b>Flower Shop Bot</b>\n\n"
        "/start — открыть магазин\n"
        "/help — показать это сообщение"
    )


dp.include_router(main_router)


@router_bot.post("/webhook")
async def telegram_webhook(update: dict):
    from aiogram.types import Update
    telegram_update = Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}


async def set_webhook(base_url: str):
    webhook_url = f"{base_url}/bot/webhook"
    await bot.set_webhook(webhook_url)
