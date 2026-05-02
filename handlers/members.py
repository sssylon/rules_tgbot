from aiogram import Router, F
from aiogram.types import Message
from db import db

router = Router()

@router.message(F.new_chat_members | F.left_chat_member)
async def track_joins_and_leaves(message: Message):
    chat_id = message.chat.id
    # new members
    if message.new_chat_members:
        for u in message.new_chat_members:
            if not u.is_bot:
                await db.incr_non_bot_members(chat_id, 1)
    # left
    if message.left_chat_member:
        u = message.left_chat_member
        if not u.is_bot:
            await db.incr_non_bot_members(chat_id, -1)
