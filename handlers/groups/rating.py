import asyncio

from aiogram import Dispatcher
from aiogram.dispatcher.filters import IsReplyFilter
from aiogram.types import Message
from aiogram.utils.exceptions import ChatNotFound
from async_lru import alru_cache

from filters import IsGroup
from loader import db, bot
from utils.misc import rate_limit
from utils.misc.middleware_helpers import override
from utils.misc.rating import caching_rating, get_rating


async def reset_rating_handler(m: Message):
    db.drop_table('RatingUsers')
    db.create_table_rating_users()
    await m.reply('Готово')


@rate_limit(limit=30, key='rating',
            text='Вы не можете так часто начислять рейтинг. (<i>Сообщение автоматически удалится</i>')
@override(user_id=362089194)
async def add_rating_handler(m: Message):
    helper_id = m.reply_to_message.from_user.id  # айди хелпера
    user_id = m.from_user.id  # айди юзера, который поставил + или -
    message_id = m.reply_to_message.message_id

    if m.bot.id == helper_id or user_id == helper_id:
        return await m.delete()

    cached = caching_rating(helper_id, user_id, message_id)
    if not cached:
        return await m.delete()

    mention_reply = m.reply_to_message.from_user.get_mention(m.reply_to_message.from_user.first_name, True)
    mention_from = m.from_user.get_mention(m.from_user.first_name)

    if helper_id == 362089194 and m.text in ['-', '👎', '➖']:
        await m.answer_photo(
            photo='https://memepedia.ru/wp-content/uploads/2019/02/uno-meme-1.jpg',
            caption='Вы не можете это сделать. Ваш удар был направлен против вас'
        )
        helper_id = m.from_user.id
        mention_reply = m.from_user.get_mention(m.from_user.first_name)
    ratings = {
        '+': 1, '➕': 1, '👍': 1, "спасибо": 1, "дякую": 1, "спасибо большое": 2,
        '-': -1, '➖': -1, '👎': -1, "пошел нахуй": -2, "иди нахуй": -2,
    }
    selected_rating = ratings.get(m.text)
    rating_user = get_rating(helper_id, selected_rating)

    if m.text in ['+', '➕', '👍', 'спасибо', 'дякую', 'спасибо большое']:
        text = f'{mention_from} <b>повысил рейтинг на {selected_rating} пользователю</b> {mention_reply} 😳 \n' \
               f'<b>Текущий рейтинг: {rating_user}</b>'
    else:
        text = f'{mention_from} <b>понизил рейтинг на {selected_rating} пользователю</b> {mention_reply} 😳 \n' \
               f'<b>Текущий рейтинг: {rating_user}</b>'

    await m.answer(text)


@alru_cache(maxsize=10)
async def get_profile(chat_id) -> str:
    await asyncio.sleep(0.1)
    try:
        chat = await bot.get_chat(chat_id)
    except ChatNotFound:
        return 'Отсутствует'
    return chat.full_name


@rate_limit(limit=30, key='top_helpers')
@override(user_id=362089194)
async def get_top_helpers(m: Message):
    helpers = db.get_top_by_rating()
    emoji_for_top = [
        '🦕', '🐙', '🐮', '🐻', '🐼', '🐰', '🦊', '🦁', '🙈', '🐤', '🐸'
    ]

    helpers = [(user_id, rating) for user_id, rating in helpers if rating > 0]

    tops = '\n'.join(
        [
            f'<b>{number}) {emoji_for_top[number - 1]} '
            f'{await get_profile(user_id)} '
            f'( {rating} )'
            f'</b>'
            for number, (user_id, rating) in enumerate(helpers, 1)
        ]
    )
    text = f'Топ Хелперов:\n{tops}'
    await m.answer(text)


def register_ratng_handlers(dp: Dispatcher):
    dp.register_message_handler(reset_rating_handler,
                                IsGroup(),
                                text='/reset_rating', user_id=362089194
                                )
    dp.register_message_handler(get_top_helpers, commands=['top_helpers'])
    dp.register_message_handler(
        add_rating_handler,
        IsGroup(),
        IsReplyFilter(True),
        text=[
            '+', '➕', '👍', '-', '➖', '👎',
            'спасибо', 'дякую', 'спасибо большое',
            "пошел нахуй", "иди нахуй"
        ]
    )
