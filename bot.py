import os
import json
import asyncio
import random
from datetime import datetime, date
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
DATA_FILE = "friends.json"

WEEKLY_PROMPTS = [
    "Давно не писала ей 🌸 Самое время!",
    "Вдруг она скучает по тебе? 💌",
    "Напомни ей что ты существуешь ✨",
    "Хорошее время написать привет 🎀",
    "Она точно обрадуется твоему сообщению 💅",
    "Просто напиши «привет, думала о тебе» 🦋",
]

def load_friends():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_friends(friends):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(friends, f, ensure_ascii=False, indent=2)

def days_until_birthday(birthday_str):
    today = date.today()
    bday = datetime.strptime(birthday_str, "%d.%m").date()
    next_bday = bday.replace(year=today.year)
    if next_bday < today:
        next_bday = next_bday.replace(year=today.year + 1)
    return (next_bday - today).days

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🎀 *Pink Circle Bot*\n\n"
        f"Твой чат ID: `{chat_id}`\n\n"
        f"Сохрани этот ID — он нужен для настройки!\n\n"
        f"*Команды:*\n"
        f"/add Имя ДД.ММ — добавить подругу\n"
        f"/list — список всех подруг\n"
        f"/remove Имя — удалить подругу\n"
        f"/check — проверить ближайшие дни рождения\n"
        f"/who — кому написать на этой неделе",
        parse_mode="Markdown"
    )

async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        args = ctx.args
        if len(args) < 2:
            await update.message.reply_text("Используй: /add Имя ДД.ММ\nНапример: /add Маша 15.03")
            return
        name = args[0]
        birthday = args[1]
        datetime.strptime(birthday, "%d.%m")  # проверка формата
        friends = load_friends()
        friends = [f for f in friends if f["name"].lower() != name.lower()]
        friends.append({"name": name, "birthday": birthday})
        save_friends(friends)
        days = days_until_birthday(birthday)
        await update.message.reply_text(
            f"🌸 *{name}* добавлена!\n"
            f"День рождения: {birthday}\n"
            f"До него: {days} дней ✨",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Используй ДД.ММ, например 15.03")

async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    friends = load_friends()
    if not friends:
        await update.message.reply_text("Пока никого нет 🌙 Добавь подруг командой /add")
        return
    sorted_friends = sorted(friends, key=lambda f: days_until_birthday(f["birthday"]))
    text = "🎀 *Твои подруги:*\n\n"
    for f in sorted_friends:
        days = days_until_birthday(f["birthday"])
        emoji = "🎂" if days <= 7 else "🌸" if days <= 30 else "💜"
        text += f"{emoji} *{f['name']}* — {f['birthday']} ({days} дн)\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_remove(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Используй: /remove Имя")
        return
    name = ctx.args[0]
    friends = load_friends()
    new_friends = [f for f in friends if f["name"].lower() != name.lower()]
    if len(new_friends) == len(friends):
        await update.message.reply_text(f"Не нашла подругу с именем {name} 🤔")
        return
    save_friends(new_friends)
    await update.message.reply_text(f"💔 *{name}* удалена из списка", parse_mode="Markdown")

async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    friends = load_friends()
    if not friends:
        await update.message.reply_text("Список пуст! Добавь подруг командой /add")
        return
    upcoming = [f for f in friends if days_until_birthday(f["birthday"]) <= 30]
    upcoming.sort(key=lambda f: days_until_birthday(f["birthday"]))
    if not upcoming:
        await update.message.reply_text("В ближайшие 30 дней дней рождений нет 🌙")
        return
    text = "🎂 *Ближайшие дни рождения:*\n\n"
    for f in upcoming:
        days = days_until_birthday(f["birthday"])
        if days == 0:
            text += f"🎉 *{f['name']}* — СЕГОДНЯ! Скорее поздравляй!\n"
        elif days <= 7:
            text += f"⚡ *{f['name']}* — через {days} дн ({f['birthday']})\n"
        else:
            text += f"🌸 *{f['name']}* — через {days} дн ({f['birthday']})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_who(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    friends = load_friends()
    if not friends:
        await update.message.reply_text("Список пуст! Добавь подруг командой /add")
        return
    f = random.choice(friends)
    prompt = random.choice(WEEKLY_PROMPTS)
    await update.message.reply_text(
        f"💌 *На этой неделе напиши:*\n\n"
        f"🌸 *{f['name']}*\n"
        f"{prompt}",
        parse_mode="Markdown"
    )

async def daily_check(bot: Bot):
    friends = load_friends()
    if not friends or not CHAT_ID:
        return
    messages = []
    for f in friends:
        days = days_until_birthday(f["birthday"])
        if days == 14:
            messages.append(f"🌸 До дня рождения *{f['name']}* осталось 2 недели ({f['birthday']})!\nСамое время подумать о подарке 🎁")
        elif days == 7:
            messages.append(f"⚡ До дня рождения *{f['name']}* осталась 1 неделя ({f['birthday']})!\nУже пора придумать что подарить 🎀")
        elif days == 0:
            messages.append(f"🎂 Сегодня день рождения у *{f['name']}*!\nСкорее поздравляй! 🎉✨")
    for msg in messages:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")

async def weekly_nudge(bot: Bot):
    friends = load_friends()
    if not friends or not CHAT_ID:
        return
    f = random.choice(friends)
    prompt = random.choice(WEEKLY_PROMPTS)
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"💌 *Кому написать на этой неделе:*\n\n🌸 *{f['name']}*\n{prompt}",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("who", cmd_who))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_check, "cron", hour=10, minute=0, args=[app.bot])
    scheduler.add_job(weekly_nudge, "cron", day_of_week="mon", hour=10, minute=0, args=[app.bot])
    scheduler.start()

    print("🎀 Pink Circle Bot запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
