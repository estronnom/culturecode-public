from telebot.async_telebot import AsyncTeleBot
import asyncio
import json
import logging

import constants
from markups import markup as mk

bot = AsyncTeleBot(constants.API_KEY, parse_mode=None)
logging.basicConfig(filename='exhib.log', encoding='utf-8', level=logging.INFO,
                    format='%(levelname)s:%(asctime)s:%(message)s')

with open('pictures.json') as fh:
    pictures = json.load(fh)

stack = {}
areas = {
    'larez': '\U0001FA86*ларец*\U0001FA86',
    'sunduk': '\U0001F5DD*сундук*\U0001F5DD',
    'tainik': '\U0001F30C*тайник*\U0001F30C',
    'albom': '\U00002601*альбом*\U00002601',
}
payment_options = ['cash', 'transfer', 'fundraise']
buttons = {
    'start': mk.createMarkup(1, ['Экспозиция', 'Купить билет'], ['exhibit_general', 'ticket_payment']),
    'areas': mk.createMarkup(1, ['Ларец \U0001FA86', 'Сундук \U0001F5DD', 'Тайник \U0001F30C', 'Альбом \U00002601'],
                             ['area_larez', 'area_sunduk', 'area_tainik', 'area_albom']),
    'payment': mk.createMarkup(1, ['Оплата наличными', 'Перевод по номеру телефона (СБП) или карты',
                                   'Оплата переводом на сбор средств в Тинькофф'], payment_options)
}
texts = {
    'start': 'Привет! Выбери опцию',
    'payment': f'Мы принимаем следующие способы оплаты...',
    'areas': 'Выбери зал',
    'back': '\U0001F519Назад\U0001F519',
    'cash': 'Для оплаты билета наличными подойдите, пожалуйста, к информационной стойке. Мур!',
    'transfer': 'Для оплаты переводом нужно отправить 300 рублей на любой следующий номер удобного Вам банка:\n\n'
                '*На Сбербанк:\n+79175411107\n5469380096528046\nВарвара Робертсовна Б.\n\nНа Тинькофф:\n+79660150299'
                '\n2200700165196162\nАлина Павловна Е.*\n\nПосле оплаты, пожалуйста, подойдите к информационному стенду'
                ' и покажите нам чек из банковского приложения.\nПриятного просмотра!',
    'fundraise': 'Вы можете перевести оплату за билет на сбор в Тинькофф-банке по ссылке:\n\n'
                 '*https://www.tinkoff.ru/cf/1YGnmLZPzsK*\n\nПосле оплаты, пожалуйста, подойдите к информационному'
                 ' стенду и покажите нам чек из банковского приложения. Приятного просмотра!'
}


def get_pictures_titles(area):
    pictures_buttons = []
    pictures_callback = []
    for index, obj in enumerate(pictures[area]['pieces']):
        pictures_buttons.append(obj['title'])
        pictures_callback.append(f"picture_{area}_{index}")
    pictures_buttons.append(texts['back'])
    pictures_callback.append('exhibit_general_back')
    return pictures_buttons, pictures_callback


async def send_audio_message(filename, chatid):
    try:
        with open(filename, 'rb') as file:
            voice_sent = await bot.send_voice(chatid, file)
            stack[chatid]['last_message'] = voice_sent.message_id
    except FileNotFoundError:
        error_sent = await bot.send_message(chatid,
                                            'Здесь должен быть аудиогид, однако он почему-то не отправился :(\n'
                                            'Обратитесь к администраторам выставки')
        stack[chatid]['last_message'] = error_sent.message_id


async def delete_audio_message(chatid):
    if stack[chatid].get('last_message', False):
        await bot.delete_message(chatid, stack[chatid]['last_message'])
        stack[chatid]['last_message'] = None


@bot.message_handler(commands=['start'])
async def start_handler(message):
    stack[message.chat.id] = {}
    await bot.send_message(message.chat.id, texts['start'], reply_markup=buttons['start'])
    logging.info(f'start:{message.chat.id}:{message.chat.first_name}')


@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    logging.info(f'callback:{call.from_user.id}:{call.from_user.first_name}:{call.data}')
    await delete_audio_message(call.from_user.id)
    if call.data.startswith('exhibit_general'):
        if call.data.endswith('back'):
            await bot.edit_message_text(texts['areas'], call.from_user.id,
                                        call.message.id, reply_markup=buttons['areas'])
        else:
            await bot.send_message(call.from_user.id, texts['areas'], reply_markup=buttons['areas'])
    elif call.data.startswith('ticket_payment'):
        if call.data.endswith('back'):
            await bot.edit_message_text(texts['payment'], call.from_user.id,
                                        call.message.id, reply_markup=buttons['payment'])
        else:
            await bot.send_message(call.from_user.id, texts['payment'], reply_markup=buttons['payment'])
    elif call.data in payment_options:
        await bot.edit_message_text(texts[call.data], call.from_user.id, call.message.id, parse_mode="Markdown",
                                    reply_markup=mk.createMarkup(1, [texts['back']], ['ticket_payment_back']),
                                    disable_web_page_preview=True)
    elif call.data.startswith('area'):
        area = call.data.split('_')[1]
        pictures_titles, callbacks = get_pictures_titles(area)
        await bot.edit_message_text(f"Зал {areas[area]}\n\n{pictures[area]['caption']}\n\nЗдесь представлены...",
                                    call.from_user.id, call.message.id,
                                    reply_markup=mk.createMarkup(1, pictures_titles, callbacks),
                                    parse_mode="Markdown")
        await send_audio_message(f'voice/{area}.ogg', call.from_user.id)
    elif call.data.startswith('picture'):
        area = call.data.split('_')[1]
        picture_id = int(call.data.split('_')[2])
        await bot.edit_message_text(f"*{pictures[area]['pieces'][picture_id]['title']}*\n"
                                    f"{pictures[area]['pieces'][picture_id]['caption']}", call.from_user.id,
                                    call.message.id,
                                    reply_markup=mk.createMarkup(1, [texts['back']], [f'area_{area}']),
                                    parse_mode="Markdown")
        await send_audio_message(f'voice/{area}_{picture_id + 1}.ogg', call.from_user.id)


def main():
    print('polling')
    asyncio.run(bot.infinity_polling())


if __name__ == '__main__':
    main()
