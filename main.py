import json
import os

import telegram
from dev_nhentai import NHentai
from dev_nhentai.entities.doujin import Doujin
from telegram import InlineKeyboardButton, ParseMode, InputMediaPhoto
from telegram.ext import Updater, MessageHandler, Filters, CallbackQueryHandler, CommandHandler


def escape_markdown(text):
    to_escape = ['_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!']
    for char in to_escape:
        if char in text:
            text = text.replace(char, "\\" + char)
    return text


def get_identifier(chat_id, message_id):
    return str(chat_id) + "SEP" + str(message_id)


def get_description(data, page, hidden):
    if not isinstance(data, Doujin):
        doujin = data
    else:
        doujin = data.to_dict()
    print(doujin)
    if not hidden:
        text = f"[{escape_markdown(doujin['title']['english'])}]({escape_markdown(doujin['url'])})"
        text += f"\nArtists: "
        if doujin['artists'] is not None:
            for artist in doujin['artists']:
                text += f"[{escape_markdown(artist['name'])}]({escape_markdown(artist['url'])}) "
        else:
            text += "Unknown"
        text += f"\nTags: "
        for tag in doujin['tags']:
            text += f"[{escape_markdown(tag['name'])}]({escape_markdown(tag['url'])}) "
    else:
        text = f"[{escape_markdown(doujin['title']['pretty'])}]({escape_markdown(doujin['url'])})"
    text += f"\nPage: {page}/{doujin['total_pages']}"
    print(text)
    return text


def command_fetch(update, context):
    print(update)
    fetch(update, context, context.args[0])


def fetch(update, context, id=None):
    if id is None:
        id = update.message.text
    nhentai = NHentai()
    doujin: Doujin = nhentai.get_doujin(id=id)
    print(doujin)
    if doujin is None:
        print("NOT FOUND")
        return
    markup = telegram.InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("Prev", callback_data="prev"),
            InlineKeyboardButton("Hide", callback_data="hide"),
            InlineKeyboardButton("Next", callback_data="next")
        ],
    ])
    desc = get_description(doujin, 1, False)
    photo = doujin.images[0].src
    print(desc)
    print(photo)

    message_id = update.message.reply_photo(caption=desc, reply_markup=markup, photo=photo,
                                            parse_mode=ParseMode.MARKDOWN_V2)
    identifier = get_identifier(update.message.chat.id, message_id.message_id)
    print(identifier)
    with open("shits.json", "r") as file:
        doujins = json.load(file)
    doujins[identifier] = {
        "data": doujin.to_dict(),
        "page": 1,
        "hide_data": False,
    }
    print(doujins)
    with open("shits.json", "w") as file:
        json.dump(doujins, file, indent=4, default=str)


def flip_page(update, context, next):
    query = update.callback_query
    query.answer()
    identifier = get_identifier(query.message.chat.id, query.message.message_id)
    print(identifier)
    with open("shits.json", "r") as file:
        messages = json.load(file)
    doujin = messages[identifier]
    markup = telegram.InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("Prev", callback_data="prev"),
            InlineKeyboardButton("Show", callback_data="hide") if doujin["hide_data"] else InlineKeyboardButton("Hide",
                                                                                                                callback_data="hide"),
            InlineKeyboardButton("Next", callback_data="next")
        ],
    ])
    if next:
        print(doujin["page"])
        if doujin["page"] == doujin["data"]["total_pages"]:
            return
        doujin["page"] += 1
        print("next")
    else:
        if doujin["page"] == 1:
            return
        doujin["page"] -= 1
    text = get_description(doujin["data"], doujin["page"], doujin["hide_data"])
    photo = doujin["data"]["images"][int(doujin["page"])]["src"]
    query.edit_message_media(
        InputMediaPhoto(photo, caption=text, parse_mode=ParseMode.MARKDOWN_V2),
        reply_markup=markup)
    with open("shits.json", "w") as file:
        json.dump(messages, file, indent=4)



def switch_hide(update, context):
    query = update.callback_query
    identifier = get_identifier(query.message.chat.id, query.message.message_id)
    print(identifier)
    with open("shits.json", "r") as file:
        messages = json.load(file)
    doujin = messages[identifier]
    doujin["hide_data"] = not doujin["hide_data"]
    markup = telegram.InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("Prev", callback_data="prev"),
            InlineKeyboardButton("Show", callback_data="hide") if doujin["hide_data"] else InlineKeyboardButton("Hide",
                                                                                                                callback_data="hide"),
            InlineKeyboardButton("Next", callback_data="next")
        ],
    ])
    text = get_description(doujin["data"], doujin["page"], doujin["hide_data"])
    query.edit_message_caption(caption=text,
                               reply_markup=markup, parse_mode=ParseMode.MARKDOWN_V2)
    with open("shits.json", "w") as file:
        json.dump(messages, file, indent=4)
    query.answer()


def button_pressed(update, context):
    query = update.callback_query
    if query.data == "next":
        flip_page(update, context, next=True)
    elif query.data == "prev":
        flip_page(update, context, next=False)
    else:
        switch_hide(update, context)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG,
    # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    updater = Updater(token='', use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.regex(r"^\d{1,7}$"), fetch))
    dispatcher.add_handler(CommandHandler("fetch", command_fetch))
    dispatcher.add_handler(CallbackQueryHandler(button_pressed))
    if not os.path.exists("shits.json"):
        with open("shits.json", "w") as file:
            file.write("{}")

    updater.start_polling()
