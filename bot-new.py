#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import sqlite3
import logging
import json
import requests
from requests.models import Response
import os
import random

from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext, \
    ConversationHandler, jobqueue
from telegram.utils import helpers

Token = os.getenv("API_KEY")
Resume_channel = os.getenv("RESUME_CHANNEL")
Files_channel = os.getenv("FILES_CHANNEL")
host_url = "http://127.0.0.1:8000/"
authorizeText = "You are not authorized to use this bot!" \
                "\nPlease /authorize yourself first!\nIf you're authorized, please /start again."

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, context):
    user = update.message.from_user
    if context.user_data == {}:
        context.user_data['turn'] = 0
        context.user_data['authorized'] = False
        context.user_data['userName_'] = ""
        context.user_data['userTOKEN'] = ""
        context.user_data['projectID'] = None
        context.user_data['userID'] = None
        context.user_data['requested_projects'] = []
        context.user_data['selectedCategories'] = {}
        response = requests.post(url=f"{host_url}api/v1/login", json={
            "username": user['id'],
        })
        if response.status_code == 200:
            if not response.json()["authorized"]:
                update.message.reply_text(
                    f"Welcome {user['first_name']}\nIf you are new,you must authorize yourself first to use bot"
                    f"\nIt's so easy,just tap on the Authorize button", reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("Authorize", callback_data='authorize')], ]))
            else:
                update.message.reply_text(f"Welcome back {user['first_name']}\nYou are already authorized to use bot!",
                                          reply_markup=InlineKeyboardMarkup([
                                              [InlineKeyboardButton('Categories', callback_data='categories')],
                                              [InlineKeyboardButton('Search', callback_data='search')],
                                              [InlineKeyboardButton('Create a new project',
                                                                    callback_data='createProject')],
                                              [InlineKeyboardButton('My Projects', callback_data='myProjects')],
                                              [InlineKeyboardButton('My Requests', callback_data='myRequests')]]))
            context.user_data["authorized"] = response.json()["authorized"]
            context.user_data["userTOKEN"] = response.json()["token"]
            resp = requests.get(url=f"{host_url}api/v1/user/me",
                                headers={
                                    'Authorization': f"Token {context.user_data['userTOKEN']}"}).json()["results"][0]
            context.user_data['requested_projects'] = resp['requested_projects']
            context.user_data['userID'] = resp['id']
            context.user_data['is_banned'] = False
        elif response.status_code == 403:
            update.message.reply_text(response.json()["message"])
            context.user_data['is_banned'] = True
    else:
        if not context.user_data["authorized"]:
            update.message.reply_text(
                f"Welcome {user['first_name']}\nIf you are new,you must authorize yourself first to use bot"
                f"\nIt's so easy,just tap on the Authorize button", reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Authorize", callback_data='authorize')], ]))
        else:
            update.message.reply_text(
                f"You've started the bot before {user['first_name']}.\nYou are already authorized to use bot!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('Categories', callback_data='categories')],
                    [InlineKeyboardButton('Search', callback_data='search')],
                    [InlineKeyboardButton('Create a new project', callback_data='createProject')],
                    [InlineKeyboardButton('My Projects', callback_data='myProjects')],
                    [InlineKeyboardButton('My Requests', callback_data='myRequests')]]))


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


TITLE, DESCRIPTION, PRICE, FILES, CATEGORY = range(5)


def createProject(update, context):
    try:
        q = update
        if update.callback_query.data == 'createProject':
            q = update.callback_query
            q.answer()
    except:
        pass
    if context.user_data['authorized'] == True:
        response = requests.get(url=f"{host_url}api/v1/user/me",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"}).json()["results"][
            0]
        # if response['maximum_projects'] >= response['joined_active_projects']:
        q.message.reply_text("Please enter the title of project")
        return TITLE
    else:
        q.message.reply_text(authorizeText)
        return ConversationHandler.END


def nameProject(update, context):
    context.user_data['titleNew'] = update.message.text
    update.message.reply_text("Please enter the description of your project:")
    return DESCRIPTION


def descriptionProject(update, context):
    context.user_data['description'] = update.message.text
    update.message.reply_text("Please enter the price as Toman(min=10000,max=10000000):")
    return PRICE


def projectByslug(update, context):
    slug = update.message.text.replace('/start slug', '')
    response = requests.get(url=f"{host_url}api/v1/projects/{slug}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        if response.json()['count'] == 1:
            update.message.reply_text(f"{response.json()['results'][0]['name']}")
        else:
            update.message.reply_text("This Project is not available!")
    else:
        update.message.reply_text("Access denied!")


def acceptRequest(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    id = q.data.replace('accept-Req-', '')
    response = requests.get(url=f"{host_url}api/v1/projects/request/{id}/apply",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        q.message.reply_text(text="Request accepted", reply_markup=None)
        results = response.json()
        try:
            context.bot.send_message(chat_id=results['applicant'],
                                     text=f"Your request for {results['project']} has been accepted")
        except:
            pass
    elif response.status_code == 403:
        q.message.reply_text(text="You are not allowed to accept this request", reply_markup=None)
    elif response.status_code == 400:
        q.message.reply_text(text="This request is already accepted", reply_markup=None)
    elif response.status_code == 404:
        q.message.reply_text(text="You have accepted a request for this project before!", reply_markup=None)
    else:
        q.message.reply_text(text="Access is denied", reply_markup=None)


def declineRequest(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    id = q.data.replace('decline-Req-', '')
    response = requests.get(url=f"{host_url}api/v1/projects/request/{id}/refuse",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        q.message.reply_text(text="Request declined", reply_markup=None)
        results = response.json()
        try:
            context.bot.send_message(chat_id=results['applicant'],
                                     text=f"Your request for {results['project']} has been declined")
        except:
            pass
    elif response.status_code == 403:
        q.message.reply_text(text="You are not allowed to decline this request", reply_markup=None)
    elif response.status_code == 400:
        q.message.reply_text(text="This request is already declined", reply_markup=None)
    elif response.status_code == 404:
        q.message.reply_text(text="Not found!", reply_markup=None)
    else:
        q.message.reply_text(text="Access is denied", reply_markup=None)


def priceProject(update, context):
    context.user_data['price'] = update.message.text
    if int(context.user_data['price']) < 10000 or int(context.user_data['price']) > 10000000:
        update.message.reply_text('please enter a value in range (10000,10000000)!')
        return PRICE
    else:
        update.message.reply_text("Please enter the project files(you can just send"
                                  " 1 file so use rar files if you have multiple files):",reply_markup=(InlineKeyboardMarkup([
            [InlineKeyboardButton('Pass',callback_data='/noFile')]])))
        return FILES


def filesProject(update: Update, context):
    if update.callback_query.data == '/noFile':
        q=update.callback_query
        q.answer()
        context.user_data['files'] = None
    elif not update.message.document:
        q=update
        if not update.message.text == 'pass':
            update.message.reply_text('please send a file!')
            return FILES
        context.user_data['files'] = None
    else:
        msg = q.message.forward(chat_id=Files_channel)
        context.user_data['files'] = msg.message_id

    xlist = []
    response = requests.get(url=f"{host_url}api/v1/categories",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    jdata = response.json()
    for c in range(jdata['results'][-1]['id']):
        try:
            k = jdata['results'][c]['category']
            j = jdata['results'][c]['id']
            xlist.append([InlineKeyboardButton(k, callback_data=f"/categoryP-{k}-{j}")])
        except:
            break
    reply_markup = InlineKeyboardMarkup(xlist)
    q.message.reply_text("please select the categories you want:", reply_markup=reply_markup)
    return CATEGORY


def get_file(update: Update, context: CallbackContext):
    if not update.message.document:
        if update.message.text == 'pass':
            fileID = None
    else:
        msg = update.message.forward(chat_id=Files_channel)
        fileID = msg.message_id
    try:
        if fileID:
            new_response = requests.get(
                url=f"{host_url}api/v1/projects/file/{fileID}/{context.user_data['edit_project_id']}",
                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
            if new_response.status_code == 200:
                update.message.reply_text("File is added successfully!")
    except:
        update.message.reply_text('please send a file!')


def messageHandler(update: Update, context: CallbackContext):
    if (context.user_data['authorized'] == True) and (context.user_data['userTOKEN'] != ""):
        resp = requests.get(url=f"{host_url}api/v1/user/me",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"}).json()
    if context.user_data['turn'] == 1:
        context.user_data['turn'] = 0
        newEmail = update.message.text
        response = requests.put(url=f"{host_url}api/v1/user/me/edit/{context.user_data['userID']}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                json={
                                    "first_name": resp['results'][0]['first_name'],
                                    "last_name": resp['results'][0]['last_name'],
                                    "phone_number": resp['results'][0]['phone_number'],
                                    "email": newEmail})
        if response.status_code == 200:
            update.message.reply_text(text="Your first name changed successfully!")
    elif context.user_data['turn'] == 2:
        context.user_data['turn'] = 0
        newFirstname = update.message.text
        response = requests.put(url=f"{host_url}api/v1/user/me/edit/{context.user_data['userID']}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                json={
                                    "first_name": newFirstname,
                                    "last_name": resp['results'][0]['last_name'],
                                    "phone_number": resp['results'][0]['phone_number'],
                                    "email": resp['results'][0]['email']})
        if response.status_code == 200:
            update.message.reply_text(text="Your first name changed successfully!")
    elif context.user_data['turn'] == 3:
        context.user_data['turn'] = 0
        newLastname = update.message.text
        response = requests.put(url=f"{host_url}api/v1/user/me/edit/{context.user_data['userID']}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                json={
                                    "first_name": resp['results'][0]['first_name'],
                                    "last_name": newLastname,
                                    "phone_number": resp['results'][0]['phone_number'],
                                    "email": resp['results'][0]['email']})
        if response.status_code == 200:
            update.message.reply_text(text="Your lastname changed successfully!")
    elif context.user_data['turn'] == 4:
        context.user_data['turn'] = 0
        newNumber = update.message.text
        if "+98" in newNumber:
            newNumber = newNumber.replace("+98", "0")
        response = requests.put(url=f"{host_url}api/v1/user/me/edit/{context.user_data['userID']}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                json={
                                    "first_name": resp['results'][0]['first_name'],
                                    "last_name": resp['results'][0]['last_name'],
                                    "email": resp['results'][0]['email'],
                                    "phone_number": newNumber})
        if response.status_code == 200:
            update.message.reply_text(text="Your phone number changed successfully!")
        elif response.status_code == 400:
            update.message.reply_text(text="Please Enter a valid number!")
    elif context.user_data['turn'] == 5:
        name = update.message.text
        response = requests.put(url=f"{host_url}api/v1/projects/self/{context.user_data['edit_project_id']}/edit",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                data={
                                    'name': name,
                                    'description': context.user_data['edit_project_description'],
                                    'price': context.user_data['edit_project_price'],
                                    'categories': context.user_data['edit_project_categories']})
        if response.status_code == 200:
            update.message.reply_text(text="Your project successfully edited!")
        else:
            update.message.reply_text(text="Something went wrong!")
    elif context.user_data['turn'] == 6:
        description = update.message.text
        response = requests.put(url=f"{host_url}api/v1/projects/self/{context.user_data['edit_project_id']}/edit",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                data={
                                    'name': context.user_data['edit_project_name'],
                                    'description': description,
                                    'price': context.user_data['edit_project_price'],
                                    'categories': context.user_data['edit_project_categories']})
        if response.status_code == 200:
            update.message.reply_text(text="Your project successfully edited!")
        else:
            update.message.reply_text(text="Something went wrong!")
    elif context.user_data['turn'] == 7:
        price = update.message.text
        response = requests.put(url=f"{host_url}api/v1/projects/self/{context.user_data['edit_project_id']}/edit",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                data={
                                    'name': context.user_data['edit_project_name'],
                                    'description': context.user_data['edit_project_description'],
                                    'price': price,
                                    'categories': context.user_data['edit_project_categories']})
        if response.status_code == 200:
            update.message.reply_text(text="Your project successfully edited!")
        else:
            update.message.reply_text(text="Something went wrong!")


def categorylist(update: Update, context: CallbackContext):
    xlist = []
    try:
        q = update
        if update.callback_query.data == 'categories':
            q = update.callback_query
            q.answer()
    except:
        pass
    if context.user_data["userTOKEN"]:
        response = requests.get(url=f"{host_url}api/v1/categories",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            jdata = response.json()
            for c in range(jdata['results'][-1]['id']):
                try:
                    k = jdata['results'][c]['category']
                    xlist.append([InlineKeyboardButton(k, callback_data=f"/category-{k}")])
                except:
                    break
            if response.json()['next']:
                k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="next", callback_data=f"/cate-page-{k}")])
            if response.json()['previous']:
                k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="previous", callback_data=f"/cate-page-{k}")])

            reply_markup = InlineKeyboardMarkup(xlist)

            q.message.reply_text('Please choose:', reply_markup=reply_markup)
        else:
            q.message.reply_text(
                "You are not logged in!\nIf you have an account please /login\nor /register a new account")
    else:
        q.message.reply_text(
            "You are not logged in!\nIf you have an account please /login\nor /register a new account")


def projectlist(update, context: CallbackContext):
    xlist = []
    try:
        q = update
        if update.callback_query.data == 'myProjects':
            q = update.callback_query
            q.answer()
    except:
        pass
    if context.user_data["authorized"]:
        response = requests.get(url=f"{host_url}api/v1/projects/self",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            jdata = response.json()
            for c in range(jdata['results'][-1]['id']):
                try:
                    k = jdata['results'][c]['slug']
                    g = jdata['results'][c]['id']
                    xlist.append(
                        [InlineKeyboardButton(jdata['results'][c]['name'], callback_data=f"{g}/my-project-{k}")])
                except:
                    break
            if response.json()['next']:
                k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="next", callback_data=f"/my-page-{k}")])
            if response.json()['previous']:
                k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="previous", callback_data=f"/my-page-{k}")])
            reply_markup = InlineKeyboardMarkup(xlist)

            q.message.reply_text('Please choose:', reply_markup=reply_markup)
    else:
        q.message.reply_text(
            authorizeText)


SEARCH_QUERY = 0


def search(update, context: CallbackContext):
    try:
        q = update
        if update.callback_query.data == 'search':
            q = update.callback_query
            q.answer()
    except:
        pass
    if context.user_data["authorized"]:
        q.message.reply_text(text="Please enter what you searching for:")
        return SEARCH_QUERY
    else:
        q.message.reply_text(
            authorizeText)
        return ConversationHandler.END


def projectsearch(update, context: CallbackContext):
    xlist = []
    word = update.message.text
    if context.user_data["authorized"]:
        response = requests.get(url=f"{host_url}api/v1/projects/search/{word}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            jdata = response.json()
            if jdata['count'] == 0:
                update.message.reply_text(text="No projects found!")
                return ConversationHandler.END
            for c in range(jdata['results'][-1]['id']):
                try:
                    k = jdata['results'][c]['slug']
                    xlist.append([InlineKeyboardButton(jdata['results'][c]['name'], callback_data=f"/project-{k}")])
                except:
                    break
            if response.json()['next']:
                k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="next", callback_data=f"/new-page-{k}")])
            if response.json()['previous']:
                k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="previous", callback_data=f"/new-page-{k}")])
            reply_markup = InlineKeyboardMarkup(xlist)
            update.message.reply_text('Please choose:', reply_markup=reply_markup)
    else:
        update.message.reply_text(
            authorizeText)
    return ConversationHandler.END


def profileUser(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    if context.user_data["userTOKEN"]:
        userID, resumeID = q.data.replace('profile', '').split('and')
        response = requests.get(url=f"{host_url}api/v1/user/{userID}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            jdata = response.json()
            id = jdata['username']
            try:
                keyboard = [[InlineKeyboardButton("Telegram Account", url=f"tg://user?id={id}")]]
                update.message.reply_text(text=f"First name : {jdata['first_name']}\nLast name : {jdata['last_name']}"
                                               f"\nPhone number : {jdata['phone_number']}\nEmail : {jdata['email']}"
                                          , reply_markup=InlineKeyboardMarkup(keyboard), )
            except:
                update.message.reply_text(text=f"First name : {jdata['first_name']}\nLast name : {jdata['last_name']}"
                                               f"\nPhone number : {jdata['phone_number']}\nEmail : {jdata['email']}"
                                               f"\nThis user's telegram account isn't available due to his/her privacy settings")
            if resumeID != ("0" or 0):
                try:
                    context.bot.copy_message(chat_id=update.message.chat_id, from_chat_id=Resume_channel,
                                             message_id=resumeID)
                except:
                    update.message.reply_text(text="This user has no resume")
            else:
                update.message.reply_text(text="This user has no resume!")
        else:
            update.message.reply_text(
                "There is no user with this ID!")
    else:
        update.message.reply_text(
            "Something went wrong\nPlease press /start to solve the problem")


def profile(update, context):
    if context.user_data['authorized'] == True:
        try:
            response = requests.get(url=f"{host_url}api/v1/user/me",
                                    headers={'Authorization': f"Token {context.user_data['userTOKEN']}"}).json()[
                "results"][0]
            print(response)
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Edit", callback_data="/edit-profile")]])
            update.message.reply_text(
                f'First name : {response["first_name"]}\nLast name : {response["last_name"]}'
                f'\nPhone number : {response["phone_number"]}\nEmail : {response["email"]}',
                reply_markup=reply_markup)
            context.user_data['userName_'] = response["username"]
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=response['profile_img'])
        except Exception as e:
            print(e)
            pass
    else:
        update.message.reply_text(
            text=authorizeText)


DETAILS = 0


def button(update: Update, context: CallbackContext):
    """Parses the CallbackQuery and updates the message text."""
    resp = requests.get(url=f"{host_url}api/v1/user/me",
                        headers={
                            'Authorization': f"Token {context.user_data['userTOKEN']}"}).json()["results"][0]
    context.user_data['requested_projects'] = resp['requested_projects']
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    try:
        if not context.user_data['authorized']:
            query.edit_message_text(
                text=authorizeText)
    except:
        query.edit_message_text(text=authorizeText)
    # if "/request-" in query.data:
    #     global str,authorized
    #     str = query.data.replace('/request-','')
    #     if authorized == False:
    #         update.message.reply_text(
    #             'You are not logged in!\nPlease /login or /register a new account', reply_markup=ReplyKeyboardRemove()
    #         )
    #         return ConversationHandler.END
    #     return DETAILS
    if query.data == "/edit-profile":
        buttons = [[InlineKeyboardButton("firstname", callback_data="/edit-firstname")],
                   [InlineKeyboardButton("lastname", callback_data="/edit-lastname")],
                   [InlineKeyboardButton("phone number", callback_data="/edit-number")],
                   [InlineKeyboardButton("email", callback_data="/edit-email")], ]
        query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data == '/edit-name-project':
        context.user_data['turn'] = 5
        query.message.edit_text('Please enter new name:')

    elif query.data == '/edit-description-project':
        context.user_data['turn'] = 6
        query.message.edit_text('Please enter new description:')

    elif query.data == '/edit-price-project':
        context.user_data['turn'] = 7
        query.message.edit_text('Please enter new price:')

    elif query.data == '/edit-categories-project':
        context.user_data['turn'] = 8
        xlist = []
        response = requests.get(url=f"{host_url}api/v1/categories",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        jdata = response.json()
        jdata = response.json()
        for c in range(jdata['results'][-1]['id']):
            try:
                k = jdata['results'][c]['category']
                j = jdata['results'][c]['id']
                xlist.append([InlineKeyboardButton(k, callback_data=f"/categoryP-{k}-{j}")])
            except:
                break
        reply_markup = InlineKeyboardMarkup(xlist)
        query.message.edit_text('Please select the categories you want:', reply_markup=reply_markup)

    elif query.data == '/edit-file-project-':
        context.user_data['turn'] = 9
        query.message.edit_text('Please send new file:')

    elif query.data == "/edit-email":
        query.edit_message_reply_markup(reply_markup=None)
        query.message.reply_text(text=f"Please enter your new {query.data.replace('/edit-', '')}")
        context.user_data['turn'] = 1

    elif query.data == "/edit-firstname":
        query.edit_message_reply_markup(reply_markup=None)
        query.message.reply_text(text=f"Please enter your new {query.data.replace('/edit-', '')}")
        context.user_data['turn'] = 2

    elif query.data == "/edit-lastname":
        query.edit_message_reply_markup(reply_markup=None)
        query.message.reply_text(text=f"Please enter your new {query.data.replace('/edit-', '')}")
        context.user_data['turn'] = 3

    elif query.data == "/edit-number":
        query.edit_message_reply_markup(reply_markup=None)
        query.message.reply_text(text=f"Please enter your new {query.data.replace('/edit-', '')}")
        context.user_data['turn'] = 4

    elif query.data == "/my-projects":
        xlist = []
        if context.user_data["authorized"]:
            response = requests.get(url=f"{host_url}api/v1/projects/self",
                                    headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
            if response.status_code == 200:
                jdata = response.json()
                for c in range(jdata['results'][-1]['id']):
                    try:
                        k = jdata['results'][c]['slug']
                        g = jdata['results'][c]['id']
                        xlist.append(
                            [InlineKeyboardButton(jdata['results'][c]['name'], callback_data=f"{g}/my-project-{k}")])
                    except:
                        break
                if response.json()['next']:
                    k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
                    xlist.append([InlineKeyboardButton(text="next", callback_data=f"/my-page-{k}")])
                if response.json()['previous']:
                    k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
                    xlist.append([InlineKeyboardButton(text="previous", callback_data=f"/my-page-{k}")])
                reply_markup = InlineKeyboardMarkup(xlist)

                query.message.edit_text('Please choose:', reply_markup=reply_markup)
        else:
            update.message.reply_text(
                authorizeText)

    elif "/request-of-project-" in query.data:
        slug = query.data.replace('/request-of-project-', '')
        if requests.get(f"{host_url}api/v1/projects/{slug}",
                        headers={'Authorization': f"Token {context.user_data['userTOKEN']}"}).json()['count'] == 0:
            query.edit_message_text(text="This project is not available!")
            return ConversationHandler.END
        response = requests.get(url=f"{host_url}api/v1/projects/self/{slug}/requests",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        buttons = []
        if response.json()['count'] > 0:
            # c = ""
            buttons = []
            n = 0
            for i in response.json()['results']:
                n += 1
                buttons.append([InlineKeyboardButton(f"Request {n}", callback_data=f"/reqID-{i['id']}")])
            buttons.append([InlineKeyboardButton(text="Back", callback_data="/my-projects")])
            query.edit_message_text(text="Requests of selected project:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            buttons.append([InlineKeyboardButton(text="Back", callback_data="/my-projects")])
            query.edit_message_text(text=f"No requests for selected project",
                                    reply_markup=InlineKeyboardMarkup(buttons))

    elif "/reqID-" in query.data:
        id = query.data.replace('/reqID-', '')
        response = requests.get(url=f"{host_url}api/v1/projects/self/request/{id}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.json()['count'] > 0:
            i = response.json()['results'][0]
            # url = helpers.create_deep_linked_url(context.bot.username, f"accept-Req-{i['id']}")
            # decline_url = helpers.create_deep_linked_url(context.bot.username, f"decline-Req-{i['id']}")
            # new_url = url.replace("https://t.me/", "https://t.me/s/")
            if i['resumeID']:
                resumeID = i['resumeID']
            else:
                resumeID = "0"
            # new_url = helpers.create_deep_linked_url(context.bot.username, f"profile{i['applicant']}and{resumeID}")
            url_report = helpers.create_deep_linked_url(context.bot.username, f"report_r{i['applicant']}and{i['id']}")
            query.edit_message_text(text=f"{i['applicantFullName']}\n\n{i['details']}",
                                    reply_markup=InlineKeyboardMarkup(
                                        [[InlineKeyboardButton(text="Accept", callback_data=f"accept-Req-{i['id']}"),
                                          InlineKeyboardButton(text="Decline", callback_data=f"decline-Req-{i['id']}")],
                                         [InlineKeyboardButton(text="Profile",
                                                               callback_data=f"profile{i['applicant']}and{resumeID}")],
                                         [InlineKeyboardButton(text="Report", url=url_report)],
                                         [InlineKeyboardButton(text="Back", callback_data="/my-projects")]]))
        else:
            query.edit_message_text(text=f"No requests for selected project", reply_markup=None)

    elif "/category-" in query.data:
        context.user_data['preCategory'] = query.data.replace('/category-', '')
        response = requests.get(url=f"{host_url}api/v1/projects/categories/{context.user_data['preCategory']}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        counter = 0
        count = response.json()['count']
        buttons = []
        while counter < count:
            try:
                k = response.json()['results'][counter]['slug']
                project = response.json()['results'][counter]['name']
                buttons.append([InlineKeyboardButton(project, callback_data=f"/project-{k}")])
                counter += 1
            except:
                break
        if response.json()['next']:
            k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
            buttons.append([InlineKeyboardButton(text="next", callback_data=f"/page-{k}")])
        if response.json()['previous']:
            k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
            buttons.append([InlineKeyboardButton(text="previous", callback_data=f"/page-{k}")])
        query.edit_message_text(text=f"Selected category: {query.data.replace('/category-', '')}",
                                reply_markup=InlineKeyboardMarkup(buttons))

    elif "/project-" in query.data:
        slug = query.data.replace('/project-', '')
        response = requests.get(url=f"{host_url}api/v1/projects/{slug}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        n = response.json()['results'][0]
        try:
            if context.user_data['preCategory']:
                buttons = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Back', callback_data=f"/category-{context.user_data['preCategory']}")]])
                context.user_data['preCategory'] = None
            else:
                buttons = None
        except:
            buttons = None
        if n['id'] in context.user_data['requested_projects']:
            query.edit_message_text(
                text=f"Selected project: {n['name']}\nPrice: {n['price']}\nCategories: {n['categories']}\nYou requested this project before!",
                reply_markup=buttons)

        elif n['employer'] == context.user_data['userID']:
            query.edit_message_text(
                text=f"Selected project: {n['name']}\nPrice: {n['price']}\nCategories: {n['categories']}\nYou can't request for your own project!",
                reply_markup=buttons)
        url2 = helpers.create_deep_linked_url(context.bot.username, f"report_p{n['employer']}and{n['id']}")
        if buttons:
            buttons.inline_keyboard.append([InlineKeyboardButton('Request', callback_data=f"request{n['id']}")])
            buttons.inline_keyboard.append([InlineKeyboardButton('Report', url=url2)])
        else:
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton('Request', callback_data=f"request{n['id']}")],
                                            [InlineKeyboardButton('Report', url=url2)]])
        query.edit_message_text(
            text=f"Selected project: {n['name']}\nPrice: {n['price']}\nCategories: {n['categories']}",
            reply_markup=buttons, disable_web_page_preview=True)

    elif "/page-" in query.data:
        link = query.data.replace('/page-', "")
        response = requests.get(url=f"{host_url}{link}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        count = response.json()['count']
        counter = 0
        buttons = []
        while counter < count:
            try:
                k = response.json()['results'][counter]['slug']
                buttons.append([InlineKeyboardButton(k, callback_data=f"/project-{k}")])
                counter += 1
            except:
                break
        if response.json()['next']:
            k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
            buttons.append([InlineKeyboardButton(text="next", callback_data=f"/page-{k}")])
        if response.json()['previous']:
            k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
            buttons.append([InlineKeyboardButton(text="previous", callback_data=f"/page-{k}")])
        query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(buttons))

    elif "/new-page-" in query.data:
        link = query.data.replace('/page-', "")
        response = requests.get(url=f"{host_url}{link}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            jdata = response.json()
            for c in range(jdata['results'][-1]['id']):
                try:
                    k = jdata['results'][c]['slug']
                    xlist.append([InlineKeyboardButton(jdata['results'][c]['name'], callback_data=f"project-{k}")])
                except:
                    break
            if response.json()['next']:
                k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="next", callback_data=f"/new-page-{k}")])
            if response.json()['previous']:
                k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="previous", callback_data=f"/new-page-{k}")])
            reply_markup = InlineKeyboardMarkup(xlist)
            update.message.reply_text('Please choose:', reply_markup=reply_markup)
        else:
            update.message.reply_text(
                authorizeText)

    elif "/my-project-" in query.data:
        id, slug = query.data.split('/my-project-')
        response = requests.get(url=f"{host_url}api/v1/projects/self/{id}/edit",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            n = response.json()
            xlist = [[InlineKeyboardButton('Check requests', callback_data=f"/request-of-project-{slug}")],
                     [InlineKeyboardButton('Edit project', callback_data=f"/projectMe-edit-{id}")],
                     [InlineKeyboardButton('Delete project', callback_data=f"/projectMe-delete-{id}")],
                     [InlineKeyboardButton('Back', callback_data="/my-projects")]]
            reply_markup = InlineKeyboardMarkup(xlist)
            categories = n["categories"]
            query.edit_message_text(f"Selected project: {n['name']}\nDescription: {n['description']}"
                                    f"\nPrice: {n['price']}\nCategories: {categories}", reply_markup=reply_markup)
        else:
            xlist = [[InlineKeyboardButton('Back', callback_data="/my-projects")]]
            reply_markup = InlineKeyboardMarkup(xlist)
            query.edit_message_text("you can't edit this project because your project have freelancer!",
                                    reply_markup=reply_markup)

    elif "/projectMe-delete-yes" in query.data:
        id = query.data.replace('/projectMe-delete-yes-', '')
        response = requests.delete(url=f"{host_url}api/v1/projects/self/{id}/edit",
                                   headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 204:
            query.edit_message_text(text="Project deleted!")
        else:
            query.edit_message_text(text="Error!")

    elif "/projectMe-delete-no" == query.data:
        query.edit_message_text(text="Project not deleted!")

    elif "/projectMe-delete-" in query.data:
        id = query.data.replace('/projectMe-delete-', '')
        query.edit_message_text("Are you sure you want to delete this project?",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton('Yes', callback_data=f"/projectMe-delete-yes-{id}"),
                                    InlineKeyboardButton('No', callback_data=f"/projectMe-delete-no")]]))

    elif "/projectMe-edit-" in query.data:
        id = query.data.replace('/projectMe-edit-', '')
        response = requests.get(url=f"{host_url}api/v1/projects/self/{id}/edit",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        n = response.json()
        # url = helpers.create_deep_linked_url(context.bot.username, f"get-file{n['id']}")
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton('Name', callback_data="/edit-name-project")],
             [InlineKeyboardButton('Description', callback_data="/edit-description-project")],
             [InlineKeyboardButton('Price', callback_data="/edit-price-project")],
             [InlineKeyboardButton('Categories', callback_data="/edit-categories-project")],
             [InlineKeyboardButton('File', callback_data=f"get-file{n['id']}")],
             [InlineKeyboardButton('Back', callback_data="/my-projects")]
             ])
        context.user_data['edit_project_categories'] = n['category']
        context.user_data['edit_project_name'] = n['name']
        context.user_data['edit_project_description'] = n['description']
        context.user_data['edit_project_price'] = n['price']
        # context.user_data['edit_project_file'] = n['fileID']
        context.user_data['edit_project_id'] = id
        query.edit_message_reply_markup(reply_markup=buttons)
        # try:
        #     context.bot.copy_message(chat_id=query.message.chat_id,from_chat_id=Files_channel,message_id=n['fileID'])
        # except:
        #     query.message.reply_text("You haven't uploaded any file yet!")


    elif "/my-page-" in query.data:
        link = query.data.replace('/my-page-', "")
        response = requests.get(url=f"{host_url}{link}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        count = response.json()['count']
        counter = 0
        buttons = []
        while counter < count:
            try:
                k = response.json()['results'][counter]['slug']
                buttons.append([InlineKeyboardButton(response.json()['results'][counter]['slug'],
                                                     callback_data=f"/my-project-{k}")])
                counter += 1
            except:
                break
        if response.json()['next']:
            k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
            buttons.append([InlineKeyboardButton(text="next", callback_data=f"/page-{k}")])
        if response.json()['previous']:
            k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
            buttons.append([InlineKeyboardButton(text="previous", callback_data=f"/page-{k}")])
        query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(buttons))
    elif "/cate-page-" in query.data:
        link = query.data.replace('/cate-page-', "")
        response = requests.get(url=f"{host_url}{link}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        count = response.json()['count']
        counter = 0
        buttons = []
        while counter < count:
            try:
                k = response.json()['results'][counter]['slug']
                buttons.append([InlineKeyboardButton(k, callback_data=f"/category-{k}")])
                counter += 1
            except:
                break
        if response.json()['next']:
            k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
            buttons.append([InlineKeyboardButton(text="next", callback_data=f"/page-{k}")])
        if response.json()['previous']:
            k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
            buttons.append([InlineKeyboardButton(text="previous", callback_data=f"/page-{k}")])
        query.edit_message_text(text=query.message.text, reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data == "/Done-create":
        category = [int(j) for j in context.user_data['selectedCategories'].keys()]
        if context.user_data['turn'] == 8:
            context.user_data['turn'] = 0
            response = requests.put(url=f"{host_url}api/v1/projects/self/{context.user_data['edit_project_id']}/edit",
                                    headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                    data={
                                        'name': context.user_data['edit_project_name'],
                                        'description': context.user_data['edit_project_description'],
                                        'price': context.user_data['edit_project_price'],
                                        'category': category})
            context.user_data['selectedCategories'], context.user_data['edit_project_name'], \
            context.user_data['edit_project_description'], context.user_data['edit_project_price'] = {}, '', '', ''
            if response.status_code == 200:
                query.message.edit_text("Project edited successfully!", reply_markup=None)
            else:
                query.message.edit_text("Something went wrong!", reply_markup=None)
        else:
            response = requests.post(url=f"{host_url}api/v1/projects/create",
                                     headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                     json={
                                         "name": context.user_data['titleNew'],
                                         "description": context.user_data['description'],
                                         "price": context.user_data['price'],
                                         "category": category})
            if response.status_code == 201:
                query.edit_message_text(text="Project created successfully!")
            if context.user_data['files']:
                new_response = requests.get(
                    url=f"{host_url}api/v1/projects/file/{context.user_data['files']}/{response.json()['id']}",
                    headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
            context.user_data['selectedCategories'], context.user_data['titleNew'], context.user_data['description'], \
            context.user_data['price'], context.user_data['files'] = {}, None, None, None, None
            if response.status_code == 201:
                query.message.edit_text('Your project successfully created!', reply_markup=None)
            else:
                query.message.edit_text('There is a problem!\nPlease try again later.', reply_markup=None)
            return ConversationHandler.END

    elif "/categoryP" in query.data:
        i = -1
        while True:
            if query.data[i - 1].isdigit():
                i -= 1
            else:
                break
        if not "/categoryPD-" in query.data:
            c = query.data.replace("/categoryP-", "")[:i - 1]
            context.user_data['selectedCategories'][query.data[i:-1] + query.data[-1]] = c
        else:
            # c = query.data.replace("/categoryPD-", "")[:i - 1]
            del context.user_data['selectedCategories'][query.data[i:-1] + query.data[-1]]

        xlist = []
        response = requests.get(url=f"{host_url}api/v1/categories",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        jdata = response.json()
        for c in range(jdata['results'][-1]['id']):
            try:
                k = jdata['results'][c]['category']
                j = jdata['results'][c]['id']
                if not str(j) in context.user_data['selectedCategories'].keys():
                    xlist.append([InlineKeyboardButton(k, callback_data=f"/categoryP-{k}-{j}")])
                else:
                    xlist.append([InlineKeyboardButton(f"{k}(Selected)", callback_data=f"/categoryPD-{k}-{j}")])
            except:
                break
        if context.user_data['selectedCategories'] != {}:
            xlist.append([InlineKeyboardButton("✅SUBMIT✅", callback_data="/Done-create")])
        reply_markup = InlineKeyboardMarkup(xlist)
        context.user_data['strCategories'] = ""
        for n in context.user_data['selectedCategories'].values():
            context.user_data['strCategories'] += f"{n},"
        query.edit_message_text(
            text=f"Selected categories:{context.user_data['strCategories']}\nPlease select the categories you want:",
            reply_markup=reply_markup)
        # query.edit_message_reply_markup(reply_markup=reply_markup)
        return CATEGORY


CHANGE, RESUME = 0, 1


def send_resume(update, context):
    response = requests.get(url=f"{host_url}api/v1/user/resume/{context.user_data['userID']}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200 and response.json()['resumeID']:
        try:
            context.bot.copy_message(chat_id=update.message.chat_id, from_chat_id=Resume_channel,
                                     message_id=response.json()['resumeID'])
            update.message.reply_text("It's your resume\nDo you want to change it?", reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton('Yes'), KeyboardButton('No')]]))
            context.user_data['preResumeID'] = response.json()['resumeID']
            return CHANGE
        except:
            pass
    if context.user_data['authorized']:
        if context.user_data['userTOKEN']:
            update.message.reply_text("Please send your resume")
            return RESUME
        else:
            update.message.reply_text("Something went wrong!\nPlease press /start to solve it.")
    update.message.reply_text(text=authorizeText)
    return ConversationHandler.END


def change_resume(update, context):
    if update.message.text == 'Yes':
        update.message.reply_text("Please send your new resume", reply_markup=ReplyKeyboardRemove())
        return RESUME
    if update.message.text == 'No':
        context.user_data['preResumeID'] = None
        update.message.reply_text("Ok, I won't change your resume", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    else:
        update.message.reply_text("Please select between Yes or No")
        return CHANGE


def get_resume(update: Update, context: CallbackContext):
    # context.user_data['resume'] = update.message.document.file_id
    # context.bot.forward_message(chat_id="-1001780176235", from_chat_id=update.message.chat_id,message_id=update.message.message_id)
    msg = update.message.forward(chat_id=Resume_channel)
    try:
        context.bot.deleteMessage(chat_id=Resume_channel, message_id=context.user_data['preResumeID'])
        context.user_data['preResumeID'] = None
    except:
        pass
    response = requests.put(url=f"{host_url}api/v1/user/resume/{context.user_data['userID']}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                            json={"resumeID": msg.message_id})
    if response.status_code == 200:
        update.message.reply_text("Your resume successfully uploaded!")
    update.message.reply_text(msg.message_id)
    update.message.reply_text("Resume received")
    return ConversationHandler.END


def request(update: Update, context):
    q = update.callback_query
    q.answer()
    context.user_data['projectID'] = q.data.replace('/start request', '')
    if context.user_data['authorized'] and context.user_data['projectID']:
        q.message.reply_text("Please enter details(if you don't want just type 'None')")
        return DETAILS
    elif context.user_data['authorized']:
        q.message.reply_text(
            "You didn't choose any project!\nUse /categories or /search or /projects-all to see projects")
        return ConversationHandler.END
    else:
        q.message.reply_text(
            authorizeText)
        return ConversationHandler.END


def report_bot(update, context):
    context.user_data['report_title'] = 'report'
    context.user_data['report_type'] = 'b'
    update.message.reply_text("Please send your report:")
    return 1


def report_project(update, context):
    context.user_data['reported_user'], context.user_data['report_title'] = update.message.text.replace(
        '/start report_p', '').split('and')
    context.user_data['report_type'] = 'p'
    if context.user_data['authorized'] and context.user_data['reported_user']:
        update.message.reply_text("Please enter details(if you don't want just type 'None')")
        return 1
    elif context.user_data['authorized']:
        update.message.reply_text(
            "You didn't choose any project!\nUse /categories or /search or /projects-all to see projects")
        return ConversationHandler.END
    else:
        update.message.reply_text(
            authorizeText)
        return ConversationHandler.END


def report_request(update, context):
    context.user_data['reported_user'], context.user_data['report_title'] = update.message.text.replace(
        '/start report_r', '').split('and')
    context.user_data['report_type'] = 'r'
    if context.user_data['authorized'] and context.user_data['reported_user']:
        update.message.reply_text("Please enter details(if you don't want just type 'None')")
        return 1
    elif context.user_data['authorized']:
        update.message.reply_text(
            "You didn't choose any request!\nUse /categories or /search or /projects-all to see projects")
        return ConversationHandler.END
    else:
        update.message.reply_text(
            authorizeText)
        return ConversationHandler.END


def report_details(update, context):
    details = update.message.text
    if context.user_data['report_type'] != 'b':
        response = requests.post(url=f"{host_url}api/v1/report",
                                 headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                 json={"type": context.user_data['report_type'],
                                       'reported_id': context.user_data['report_title'],
                                       "details": details,
                                       "reported_user": context.user_data['reported_user']})
    else:
        response = requests.post(url=f"{host_url}api/v1/report",
                                 headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                                 json={"type": context.user_data['report_type'],
                                       "reported_id": context.user_data['report_title'],
                                       "details": details,
                                       "reported_user": None})
    if response.status_code == 201:
        update.message.reply_text("Report successfully sent!")
        return ConversationHandler.END
    else:
        update.message.reply_text("Something went wrong!")
        return ConversationHandler.END


def send_file(update: Update, context):
    q = update.callback_query
    q.answer()
    id = q.data.replace('get-file', '')
    response = requests.get(url=f"{host_url}api/v1/projects/self/{id}/edit",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200 and response.json()['fileID']:
        try:
            context.bot.copy_message(chat_id=update.message.chat_id, from_chat_id=Files_channel,
                                     message_id=response.json()['fileID'])
            q.message.reply_text("It's your project's file\nDo you want to change it?",
                                 reply_markup=ReplyKeyboardMarkup(
                                     [[KeyboardButton('Yes'), KeyboardButton('No')]]))
            context.user_data['preFileID'] = response.json()['fileID']
            context.user_data['preProject'] = id
            return CHANGE
        except:
            pass
    if context.user_data['authorized']:
        if context.user_data['userTOKEN']:
            context.user_data['preProject'] = id
            q.message.reply_text("Please send the file")
            return RESUME
        else:
            q.message.reply_text("Something went wrong!\nPlease press /start to solve it.")
    q.message.reply_text(text=authorizeText)
    return ConversationHandler.END


def change_file(update, context):
    if update.message.text == 'Yes':
        update.message.reply_text("Please send your new file", reply_markup=ReplyKeyboardRemove())
        return RESUME
    if update.message.text == 'No':
        context.user_data['preFileID'] = None
        context.user_data['preProject'] = None
        update.message.reply_text("Ok, I won't change your file", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    else:
        update.message.reply_text("Please select between Yes or No")
        return CHANGE


def get_file(update: Update, context: CallbackContext):
    # context.user_data['resume'] = update.message.document.file_id
    # context.bot.forward_message(chat_id="-1001780176235", from_chat_id=update.message.chat_id,message_id=update.message.message_id)
    msg = update.message.forward(chat_id=Files_channel)
    try:
        id = context.user_data['preProject']
        context.user_data['preProject'] = None
        context.bot.deleteMessage(chat_id=Files_channel, message_id=context.user_data['preFileID'])
        context.user_data['preFileID'] = None
    except:
        pass
    response = requests.get(url=f"{host_url}api/v1/projects/file/{msg.message_id}/{id}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        update.message.reply_text("Your file successfully uploaded!")
    else:
        update.message.reply_text("Something went wrong!\nPlease press /start to solve it.")
    return ConversationHandler.END


def details(update: Update, context: CallbackContext):
    text = update.message.text
    response = requests.post(url=f"{host_url}api/v1/projects/request",
                             headers={'Authorization': f"Token {context.user_data['userTOKEN']}"},
                             json={
                                 "project": context.user_data['projectID'],
                                 "details": text})
    context.user_data['projectID'] = None
    if response.status_code == 201:
        update.message.reply_text("your request has been sent successfully")
        data = response.json()
        try:
            context.bot.send_message(chat_id=data['employer'],
                                     text=f"{update.message.from_user['first_name']} has requested for {data['project']}")
        except:
            pass
    elif response.status_code == 400:
        update.message.reply_text(response.json()['project'])
    else:
        update.message.reply_text("something went wrong")
    return ConversationHandler.END


FIRSTNAME, LASTNAME, NUMBER, EMAIL = range(4)


def authorize(update: Update, context: CallbackContext):
    try:
        q = update
        if update.callback_query.data == 'authorize':
            q = update.callback_query
            q.answer()
    except:
        pass
    # if context.user_data['is_banned']:
    #     q.message.reply_text("You are banned from using this bot")
    #     return ConversationHandler.END
    if context.user_data['authorized'] == True:
        q.message.reply_text(
            'You are already authorized!')
        return ConversationHandler.END
    q.message.reply_text("Enter your first name:")
    return FIRSTNAME


def first_name(update: Update, context):
    context.user_data['first_nameLogin'] = update.message.text
    # logger.info("username of %s: %s", user.first_name, update.message.text)
    update.message.reply_text("Enter your last name:")
    return LASTNAME


def last_name(update: Update, context):
    context.user_data['last_nameLogin'] = update.message.text
    # logger.info("username of %s: %s", user.first_name, update.message.text)
    update.message.reply_text("Enter your phone number:")
    return NUMBER


def phone_number(update: Update, context):
    context.user_data['phone_numberLogin'] = update.message.text
    if "+98" in context.user_data['phone_numberLogin']:
        context.user_data['phone_numberLogin'] = context.user_data['phone_numberLogin'].replace("+98", "0")
    # logger.info("username of %s: %s", user.first_name, update.message.text)
    update.message.reply_text("Enter your email:")
    return EMAIL

def email(update: Update, context):
    context.user_data['emailLogin'] = update.message.text
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    func = random.randint(1, 3)
    if func == 1:
        update.message.reply_text(f"{num1} + {num2} = ?")
        context.user_data['answer'] = num1 + num2
    else:
        update.message.reply_text(f"{num1} - {num2} = ")
        context.user_data['answer'] = num1 - num2
    return 4


def testHuman(update: Update, context: CallbackContext):
    if update.message.text == str(context.user_data['answer']):
        response = requests.put(url=f"{host_url}api/v1/user/me/edit/{context.user_data['userID']}", json={
            "first_name": context.user_data['first_nameLogin'],
            "last_name": context.user_data['last_nameLogin'],
            "phone_number": context.user_data['phone_numberLogin'],
            "email": context.user_data['emailLogin'],
        }, headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            context.user_data['authorized'] = response.json()['authorized']
            update.message.reply_text("Congrats!\nYou are authorized now!", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('Categories', callback_data='categories')],
                [InlineKeyboardButton('Search', callback_data='search')],
                [InlineKeyboardButton('Create a new project', callback_data='createProject')],
                [InlineKeyboardButton('My Projects', callback_data='myProjects')],
                [InlineKeyboardButton('My Requests', callback_data='myRequests')],
            ]))
    else:
        update.message.reply_text("Wrong answer!\nPlease try again to authorize yourself.",
                                  reply_markup=InlineKeyboardMarkup([
                                      [InlineKeyboardButton('Authorize', callback_data='authorize')],
                                  ]))
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    update.message.reply_text('/start the bot and try again\n'
                              'If the problem is still there, please contact the developer by /support')
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def checkRequests_user(update, context):
    try:
        q = update
        if update.callback_query.data == 'myRequests':
            q = update.callback_query
            q.answer()
    except:
        pass
    if context.user_data['authorized']:
        response = requests.get(url=f"{host_url}api/v1/projects/self/requests",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            if response.json()['count'] > 0:
                c = ""
                for i in response.json()['results']:
                    if i['applied']:
                        g = '✅'
                    elif i['applied'] == False:
                        g = '❌'
                    else:
                        g = '⌛'
                    url = helpers.create_deep_linked_url(context.bot.username, f"slug{i['projectSlug']}")
                    c += f"{i['projectName']}([Check Project]({url})):{g}\n"
                    # text = f"You can also mask the deep-linked URLs as links: [▶️ CLICK HERE]({url})."
                    # update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
                q.message.reply_text(text=f"Your recent requests: {response.json()['count']}\n{c}",
                                     parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        q.message.reply_text(authorizeText)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(Token, use_context=True)
    # j = updater.job_queue
    # j.run_repeating(checkRequests, 60)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(
        CommandHandler("start", projectByslug, Filters.regex('slug'))
    )
    dp.add_handler(
        CallbackQueryHandler(acceptRequest, pattern='accept-Req-')
    )
    dp.add_handler(
        CallbackQueryHandler(profileUser, pattern='profile')
    )
    dp.add_handler(
        CallbackQueryHandler(declineRequest, pattern='decline-Req-')
    )

    dp.add_handler(CommandHandler("check_requests", checkRequests_user))
    dp.add_handler(CallbackQueryHandler(checkRequests_user, pattern='myRequests'))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("categories", categorylist))
    dp.add_handler(CallbackQueryHandler(categorylist, pattern='categories'))
    # dp.add_handler(CommandHandler("logout", logout))
    dp.add_handler(CommandHandler("profile", profile))
    dp.add_handler(CommandHandler("my_projects", projectlist))
    dp.add_handler(CallbackQueryHandler(projectlist, pattern='myProjects'))

    authorize_handler = ConversationHandler(
        entry_points=[CommandHandler('authorize', authorize),
                      CallbackQueryHandler(authorize, pattern='authorize')],
        states={
            FIRSTNAME: [MessageHandler(Filters.text & ~Filters.command, first_name)],
            LASTNAME: [MessageHandler(Filters.text & ~Filters.command, last_name)],
            NUMBER: [MessageHandler(Filters.text & ~Filters.command, phone_number)],
            EMAIL: [MessageHandler(Filters.text & ~Filters.command, email)],
            4: [MessageHandler(Filters.text & ~Filters.command, testHuman)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    request_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(request, pattern='request')],
        states={
            DETAILS: [MessageHandler(Filters.text & ~Filters.command, details)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    report_handler = ConversationHandler(
        entry_points=[CommandHandler("start", report_project, Filters.regex('report_p')),
                      CommandHandler("start", report_request, Filters.regex('report_r')),
                      CommandHandler('report', report_bot)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, report_details)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    search_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search),
                      CallbackQueryHandler(search, pattern='search')],
        states={
            DETAILS: [MessageHandler(Filters.text & ~Filters.command, projectsearch)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    file_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(send_file, pattern='get-file')],
        states={
            CHANGE: [MessageHandler(Filters.text & ~Filters.command, change_file)],
            RESUME: [MessageHandler(~Filters.command & Filters.document, get_file)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    resume_handler = ConversationHandler(
        entry_points=[CommandHandler('send_resume', send_resume)],
        states={
            CHANGE: [MessageHandler(Filters.text & ~Filters.command, change_resume)],
            RESUME: [MessageHandler(~Filters.command & Filters.document, get_resume)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    create_project_handler = ConversationHandler(
        entry_points=[CommandHandler("new_project", createProject),
                      CallbackQueryHandler(createProject, pattern='createProject')],
        states={
            TITLE: [MessageHandler(Filters.text & ~Filters.command, nameProject)],
            DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, descriptionProject)],
            PRICE: [MessageHandler(Filters.text & ~Filters.command, priceProject)],
            FILES: [MessageHandler(~Filters.command, filesProject),
                    CallbackQueryHandler(filesProject,pattern='/noFile')],
            CATEGORY: [CallbackQueryHandler(button)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dp.add_handler(authorize_handler)
    dp.add_handler(request_handler)
    dp.add_handler(create_project_handler)
    dp.add_handler(resume_handler)
    dp.add_handler(file_handler)
    dp.add_handler(search_handler)
    dp.add_handler(report_handler)

    dp.add_handler(CallbackQueryHandler(button))

    # log all errors
    # dp.add_error_handler(error)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.document, get_file))
    dp.add_handler(MessageHandler(Filters.text, messageHandler))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
