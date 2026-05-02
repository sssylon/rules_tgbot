from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram import Bot

from db import db

router = Router()

@router.message(Command("send_rules"))
async def send_rules_handler(message: Message, bot: Bot):
    # check admin
    chat_id = message.chat.id
    user_id = message.from_user.id
    member = await bot.get_chat_member(chat_id, user_id)
    if member.status not in ("administrator", "creator"):
        await message.reply("Только админы могут установить сообщение с правилами.")
        return

    # build rules text from accepted rules if any
    accepted = await db.get_accepted_rules_with_ids(chat_id)
    if accepted:
        text = "Правила группы:\n"
        for i, (_, r) in enumerate(accepted, start=1):
            text += f"{i}. {r}\n"
    else:
        text = "Правила группы:\n(пока нет принятых правил)"

    # if rules message exists, edit it, otherwise send new
    existing_msg_id = await db.get_rules_message(chat_id)
    try:
        if existing_msg_id:
            await bot.edit_message_text(chat_id=chat_id, message_id=existing_msg_id, text=text)
            await message.reply("Сообщение с правилами обновлено.")
        else:
            sent = await bot.send_message(chat_id, text)
            await db.set_rules_message(chat_id, sent.message_id)
            await message.reply("Сообщение с правилами отправлено и установлено.")
    except Exception:
        # fallback: send new message and set
        sent = await bot.send_message(chat_id, text)
        await db.set_rules_message(chat_id, sent.message_id)
        await message.reply("Сообщение с правилами отправлено и установлено.")




@router.message(Command("add_rule"))
async def add_rule_cmd(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    member = await message.bot.get_chat_member(chat_id, user_id)
    if member.status not in ("administrator", "creator"):
        await message.reply("Только админы могут добавлять правила вручную.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /add_rule <текст правила>")
        return
    text = args[1].strip()
    rule_id = await db.add_accepted_rule(chat_id, text)
    # refresh rules message if exists
    rules_msg_id = await db.get_rules_message(chat_id)
    if rules_msg_id:
        accepted = await db.get_accepted_rules(chat_id)
        new_text = "Правила группы:\n"
        for i, r in enumerate(accepted, start=1):
            new_text += f"{i}. {r}\n"
        try:
            await message.bot.edit_message_text(chat_id=chat_id, message_id=rules_msg_id, text=new_text)
        except Exception:
            pass
    await message.reply(f"Правило добавлено (id={rule_id}).")


@router.message(Command("remove_rule"))
async def remove_rule_cmd(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    member = await message.bot.get_chat_member(chat_id, user_id)
    if member.status not in ("administrator", "creator"):
        await message.reply("Только админы могут удалять правила.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /remove_rule <номер>")
        return
    try:
        idx = int(args[1])
    except ValueError:
        await message.reply("Номер должен быть целым.")
        return
    accepted = await db.get_accepted_rules_with_ids(chat_id)
    if idx < 1 or idx > len(accepted):
        await message.reply("Неверный номер правила.")
        return
    rule_id = accepted[idx-1][0]
    await db.delete_rule_by_id(rule_id)
    # refresh rules message
    rules_msg_id = await db.get_rules_message(chat_id)
    if rules_msg_id:
        accepted2 = await db.get_accepted_rules(chat_id)
        new_text = "Правила группы:\n" if accepted2 else "Правила группы:\n(пока нет принятых правил)"
        for i, r in enumerate(accepted2, start=1):
            new_text += f"{i}. {r}\n"
        try:
            await message.bot.edit_message_text(chat_id=chat_id, message_id=rules_msg_id, text=new_text)
        except Exception:
            pass
    await message.reply("Правило удалено.")


@router.message(Command("edit_rule"))
async def edit_rule_cmd(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    member = await message.bot.get_chat_member(chat_id, user_id)
    if member.status not in ("administrator", "creator"):
        await message.reply("Только админы могут редактировать правила.")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("Использование: /edit_rule <номер> <новый текст>")
        return
    try:
        idx = int(args[1])
    except ValueError:
        await message.reply("Номер должен быть целым.")
        return
    new_text = args[2].strip()
    accepted = await db.get_accepted_rules_with_ids(chat_id)
    if idx < 1 or idx > len(accepted):
        await message.reply("Неверный номер правила.")
        return
    rule_id = accepted[idx-1][0]
    await db.update_rule_text(rule_id, new_text)
    # refresh message
    rules_msg_id = await db.get_rules_message(chat_id)
    if rules_msg_id:
        accepted2 = await db.get_accepted_rules(chat_id)
        new_text_all = "Правила группы:\n"
        for i, r in enumerate(accepted2, start=1):
            new_text_all += f"{i}. {r}\n"
        try:
            await message.bot.edit_message_text(chat_id=chat_id, message_id=rules_msg_id, text=new_text_all)
        except Exception:
            pass
    await message.reply("Правило обновлено.")


@router.message(Command("refresh_rules"))
async def refresh_rules_cmd(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    member = await message.bot.get_chat_member(chat_id, user_id)
    if member.status not in ("administrator", "creator"):
        await message.reply("Только админы могут обновлять сообщение с правилами.")
        return
    rules_msg_id = await db.get_rules_message(chat_id)
    accepted = await db.get_accepted_rules(chat_id)
    if not accepted:
        text = "Правила группы:\n(пока нет принятых правил)"
    else:
        text = "Правила группы:\n"
        for i, r in enumerate(accepted, start=1):
            text += f"{i}. {r}\n"
    if rules_msg_id:
        try:
            await message.bot.edit_message_text(chat_id=chat_id, message_id=rules_msg_id, text=text)
            await message.reply("Сообщение с правилами обновлено.")
            return
        except Exception:
            pass
    sent = await message.bot.send_message(chat_id, text)
    await db.set_rules_message(chat_id, sent.message_id)
    await message.reply("Сообщение с правилами отправлено и установлено.")


@router.message(Command("set_bot_count"))
async def set_bot_count(message: Message, bot: Bot):
    # admin only
    chat_id = message.chat.id
    user_id = message.from_user.id
    member = await bot.get_chat_member(chat_id, user_id)
    if member.status not in ("administrator", "creator"):
        await message.reply("Только админы могут устанавливать количество ботов.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /set_bot_count <число>")
        return
    try:
        n = int(args[1])
    except ValueError:
        await message.reply("Число должно быть целым.")
        return
    if n < 1:
        await message.reply("Значение должно быть >= 1")
        return
    await db.set_bot_count(chat_id, n)
    await message.reply(f"Количество ботов в чате установлено: {n}")
