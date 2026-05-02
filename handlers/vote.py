import asyncio
import os
import time
from typing import Optional
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from db import db
from utils import format_vote_message

router = Router()

AUTO_CLOSE_HOURS = int(os.getenv("AUTO_CLOSE_HOURS", "16"))


async def get_non_bot_members(chat_id: int, bot: Bot, fallback: Optional[int] = None) -> int:
    bot_count = await db.get_bot_count(chat_id)
    total = None
    try:
        total = await bot.get_chat_member_count(chat_id)
    except Exception:
        total = None
    if total is not None:
        non_bots = max(0, total - bot_count)
        try:
            await db.set_non_bot_members(chat_id, non_bots)
        except Exception:
            pass
        return non_bots
    stored = await db.get_non_bot_members(chat_id)
    if stored is not None:
        return max(0, stored)
    if fallback is not None:
        return max(0, fallback)
    return 0


async def schedule_close(vote_id: int, created_at: int, bot: Bot):
    # compute remaining time
    elapsed = int(time.time()) - created_at
    delay = max(0, AUTO_CLOSE_HOURS*3600 - elapsed)
    await asyncio.sleep(delay)
    vote = await db.get_vote(vote_id)
    if not vote or vote.get("active") == 0:
        return
    # close: accept if yes > 50% of non-bot members
    yes_count, no_count = await db.get_vote_counts(vote_id)

    non_bots = await get_non_bot_members(vote["chat_id"], bot, fallback=yes_count + no_count)
    needed = (non_bots // 2) + 1 if non_bots > 0 else 1

    if yes_count >= needed:
        # accept rule
        await db.accept_rule(vote["rule_id"])
        # rebuild rules message from accepted rules
        rules_msg_id = await db.get_rules_message(vote["chat_id"])
        if rules_msg_id:
            accepted = await db.get_accepted_rules(vote["chat_id"])
            text = "Правила группы:\n"
            for r in accepted:
                text += f"- {r}\n"
            try:
                await bot.edit_message_text(chat_id=vote["chat_id"], message_id=rules_msg_id, text=text)
            except Exception:
                pass
    # mark vote inactive and edit vote message to indicate closed
    await db.close_vote(vote_id)
    try:
        await bot.edit_message_text(chat_id=vote["chat_id"], message_id=vote["vote_message_id"], text="Голосование закрыто.")
    except Exception:
        pass


@router.message(Command("vote"))
async def vote_cmd(message: Message, bot: Bot):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /vote <текст правила>")
        return
    rule_text = args[1].strip()
    rule_id = await db.create_rule(message.chat.id, rule_text)
    # create vote record
    vote_id = await db.create_vote(rule_id, message.chat.id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 За", callback_data=f"vote:{vote_id}:yes"), InlineKeyboardButton(text="👎 Против", callback_data=f"vote:{vote_id}:no")]
    ])

    non_bots = await get_non_bot_members(message.chat.id, bot)
    needed = (non_bots // 2) + 1 if non_bots > 0 else 1

    text = format_vote_message(rule_text, [], [], 0, 0, needed, vote_id)
    sent = await bot.send_message(message.chat.id, text, reply_markup=keyboard)
    await db.set_vote_message(vote_id, sent.message_id)

    # schedule auto-close
    asyncio.create_task(schedule_close(vote_id, int(time.time()), bot))

    await message.reply(f"Голосование создано: id={vote_id}")


@router.callback_query(lambda c: c.data and c.data.startswith("vote:"))
async def vote_callback(query: CallbackQuery, bot: Bot):
    parts = query.data.split(":")
    if len(parts) != 3:
        await query.answer()
        return
    vote_id = int(parts[1])
    choice = parts[2]
    if choice not in ("yes", "no"):
        await query.answer()
        return
    if query.from_user.is_bot:
        await query.answer("Боты не могут голосовать.")
        return

    vote = await db.get_vote(vote_id)
    if not vote or vote.get("active") != 1:
        await query.answer("Голосование закрыто.")
        return

    # record vote
    display_name = query.from_user.full_name
    username = query.from_user.username
    await db.add_or_update_vote(vote_id, query.from_user.id, username, display_name, choice)
    yes_count, no_count = await db.get_vote_counts(vote_id)
    yes_list, no_list = await db.get_voters_lists(vote_id)

    # get rule text
    rule_row = await db.fetchone("SELECT text FROM rules WHERE id = $1", vote["rule_id"])
    rule_text = rule_row[0] if rule_row else "(правило)"

    non_bots = await get_non_bot_members(vote["chat_id"], bot, fallback=yes_count + no_count)

    needed = (non_bots // 2) + 1 if non_bots > 0 else 1

    text = format_vote_message(rule_text, yes_list, no_list, yes_count, no_count, needed, vote_id)
    # if threshold reached now, accept immediately
    try:
        if yes_count >= needed:
            await db.accept_rule(vote["rule_id"])
            await db.close_vote(vote_id)

            # rebuild rules message
            rules_msg_id = await db.get_rules_message(vote["chat_id"])
            if rules_msg_id:
                accepted = await db.get_accepted_rules(vote["chat_id"])
                new_text = "Правила группы:\n"
                for r in accepted:
                    new_text += f"- {r}\n"
                try:
                    await bot.edit_message_text(chat_id=vote["chat_id"], message_id=rules_msg_id, text=new_text)
                except Exception:
                    pass

            # update vote message to indicate acceptance
            try:
                await bot.edit_message_text(chat_id=vote["chat_id"], message_id=vote["vote_message_id"], text="Правило принято и добавлено в список правил.")
            except Exception:
                pass

            await query.answer("Правило принято")
            return
    except Exception:
        # swallow errors but continue to update vote message
        pass

    try:
        await bot.edit_message_text(chat_id=vote["chat_id"], message_id=vote["vote_message_id"], text=text, reply_markup=query.message.reply_markup)
    except Exception:
        pass
    await query.answer("Голос учтён")


@router.message(Command("close_vote"))
async def close_vote_cmd(message: Message, bot: Bot):
    # admin only
    chat_id = message.chat.id
    user_id = message.from_user.id
    member = await bot.get_chat_member(chat_id, user_id)
    if member.status not in ("administrator", "creator"):
        await message.reply("Только админы могут закрывать голосования вручную.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /close_vote <vote_id>")
        return
    try:
        vote_id = int(args[1])
    except ValueError:
        await message.reply("Неверный id")
        return
    vote = await db.get_vote(vote_id)
    if not vote or vote.get("active") == 0:
        await message.reply("Голосование не найдено или уже закрыто.")
        return
    # close without consequence
    await db.close_vote(vote_id)
    try:
        await bot.edit_message_text(chat_id=vote["chat_id"], message_id=vote["vote_message_id"], text="Голосование закрыто администратором (результат не применяется).")
    except Exception:
        pass
    await message.reply("Голосование закрыто.")
