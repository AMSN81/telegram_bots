import logging
import json
import requests
from requests.models import Response
import os

from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext, \
    ConversationHandler, jobqueue
from telegram.utils import helpers

Token = os.getenv("ADMIN_BOT")
Token2 = os.getenv("API_KEY")
Resume_channel = os.getenv("RESUME_CHANNEL")
Files_channel = os.getenv("FILES_CHANNEL")
Projects_channel = os.getenv("PROJECTS_CHANNEL")
host_url = "http://127.0.0.1:8000/"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    if context.user_data == {}:
        context.user_data['turn'] = 0
        context.user_data['authorized'] = False
        context.user_data['userName_'] = ""
        context.user_data['userTOKEN'] = ""
        context.user_data['projectID'] = None
        # context.user_data['userID'] = None
        context.user_data['selectedCategories'] = {}
    user = update.message.from_user
    response = requests.post(url=f"{host_url}api/v1/login", json={
        "username": user['id'],
    })
    if response.status_code == 200 and response.json()['is_superuser'] == True:
        update.message.reply_text(f"Welcome \n{user['first_name']}")
        context.user_data["authorized"] = response.json()["authorized"]
        context.user_data['superuser'] = True
        context.user_data["userTOKEN"] = response.json()["token"]
        # resp = requests.get(url=f"{host_url}api/v1/user/me",
        #                     headers={
        #                         'Authorization': f"Token {context.user_data['userTOKEN']}"}).json()["results"][0]
        # context.user_data['userID'] = resp['id']

    elif response.status_code == 200 and response.json()['is_staff'] == True:
        update.message.reply_text(f"Welcome \n{user['first_name']}")
        context.user_data["authorized"] = response.json()["authorized"]
        context.user_data['superuser'] = False
        context.user_data["userTOKEN"] = response.json()["token"]
        # resp = requests.get(url=f"{host_url}api/v1/user/me",
        #                     headers={
        #                         'Authorization': f"Token {context.user_data['userTOKEN']}"}).json()["results"][0]
        # context.user_data['userID'] = resp['id']
    else:
        update.message.reply_text('You are not supposed to be here!')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if '/check_project' in query.data:
        id, slug = query.data.split('/check_project')
        response = requests.get(url=f"{host_url}api/v1/projects/{slug}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        query.edit_message_text(
            text=response.json()['results'], reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton('Back', callback_data=f"backRep_p{id}")]]))

    elif '/check_request' in query.data:
        id_, req_id = query.data.split('/check_request')
        response = requests.get(url=f"{host_url}api/v1/projects/self/request/{req_id}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        query.edit_message_text(
            text=response.json()['results'], reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton('Back', callback_data=f"backRep_r{id_}")]]))

    elif '/repP' in query.data:
        id_, slug = query.data.split('/repP')
        response = requests.get(url=f"{host_url}api/v1/projects/{slug}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        query.edit_message_text(text=response.json()['results'], reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Back', callback_data=f"pCheck_{id_}")]]))

    elif '/repR' in query.data:
        id_, req_id = query.data.split('/repR')
        response = requests.get(url=f"{host_url}api/v1/projects/self/request/{req_id}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        query.edit_message_text(text=response.json()['results'], reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Back', callback_data=f"rCheck_{id_}")]]))

    elif '/ban_' in query.data:
        if 'A/' in query.data:
            id_ = query.data.replace('A/ban_', '')
            response = requests.put(url=f"{host_url}api/v1/report/set/{id_}",
                                    headers={'Authorization': f"Token {context.user_data['userTOKEN']}"}, json={
                    "condition": 'b',
                })
            if response.status_code == 200:
                query.edit_message_text('user banned successfully')
            else:
                query.edit_message_text('something went wrong')
        else:
            id_ = query.data.replace('/ban_', '')
            query.edit_message_text('Ban reported user and invalidate the project?', reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('Yes', callback_data=f'A/ban_{id_}')],
                [InlineKeyboardButton('No', callback_data='/deleteM')]]))

    elif '/false_' in query.data:
        if 'A/' in query.data:
            id_ = query.data.replace('A/false_', '')
            response = requests.put(url=f"{host_url}api/v1/report/set/{id_}",
                                    headers={'Authorization': f"Token {context.user_data['userTOKEN']}"}, json={
                    "condition": 'f',
                })
            if response.status_code == 200:
                query.edit_message_text('user warned successfully')
            else:
                query.edit_message_text('something went wrong')
        else:
            id_ = query.data.replace('/false_', '')
            query.edit_message_text('Warn reporter?', reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('Yes', callback_data=f'A/false_{id_}')],
                [InlineKeyboardButton('No', callback_data='/deleteM')]]))

    elif '/warn_' in query.data:
        if 'A/' in query.data:
            id_ = query.data.replace('A/warn_', '')
            response = requests.put(url=f"{host_url}api/v1/report/set/{id_}",
                                    headers={'Authorization': f"Token {context.user_data['userTOKEN']}"}, json={
                    "condition": 'w',
                })
            if response.status_code == 200:
                query.edit_message_text('user warned successfully')
            else:
                query.edit_message_text('something went wrong')
        else:
            id_ = query.data.replace('/warn_', '')
            query.edit_message_text('Warn reported user and invalidate the project?',
                                    reply_markup=InlineKeyboardMarkup([
                                        [InlineKeyboardButton('Yes', callback_data=f'A/warn_{id_}')],
                                        [InlineKeyboardButton('No', callback_data='/deleteM')]]))

    elif '/solve_' in query.data:
        if 'A/' in query.data:
            id_ = query.data.replace('A/solve_', '')
            response = requests.put(url=f"{host_url}api/v1/report/set/{id_}",
                                    headers={'Authorization': f"Token {context.user_data['userTOKEN']}"}, json={
                    "condition": 's',
                })
            if response.status_code == 200:
                query.edit_message_text('report saved as solved successfully')
            else:
                query.edit_message_text('something went wrong')
        else:
            id_ = query.data.replace('/solve_', '')
            query.edit_message_text('bug is solved already?', reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('Yes', callback_data=f'A/solve_{id_}')],
                [InlineKeyboardButton('No', callback_data='/deleteM')]]))

    elif '/ignore_' in query.data:
        if 'A/' in query.data:
            id_ = query.data.replace('A/ignore_', '')
            response = requests.put(url=f"{host_url}api/v1/report/set/{id_}",
                                    headers={'Authorization': f"Token {context.user_data['userTOKEN']}"}, json={
                    "condition": 'i',
                })
            if response.status_code == 200:
                query.edit_message_text('report ignored')
            else:
                query.edit_message_text('something went wrong')
        else:
            id_ = query.data.replace('/ignore_', '')
            query.edit_message_text('Ignore report?', reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('Yes', callback_data=f'A/ignore_{id_}')],
                [InlineKeyboardButton('No', callback_data='/deleteM')]]))


def bugReports(update: Update, context: CallbackContext):
    if update.callback_query:
        q = update.callback_query
        q.answer()
    else:
        q = update
    response = requests.get(f"{host_url}api/v1/reports/b",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        if response.json()['count'] == 0:
            q.message.reply_text("No reports!")
        else:
            data = response.json()['results'][0]
            id_ = data['id']
            reporter = data["reporter"]
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton('Solve', callback_data=f'/solve_{id_}'),
                                             InlineKeyboardButton('Ignore', callback_data=f'/ignore_{id_}')],
                                            [InlineKeyboardButton('Check Reporter',
                                                                  callback_data=f'check_user{reporter}')],
                                            [InlineKeyboardButton('Warn Reporter', callback_data=f'/false_{id_}')]])
            q.message.reply_text(f"Type:Bug\n\nReport:\n{data['details']}", reply_markup=buttons)


def requestReports(update: Update, context: CallbackContext):
    if update.callback_query:
        q = update.callback_query
        q.answer()
    else:
        q = update
    response = requests.get(f"{host_url}api/v1/reports/r",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        if response.json()['count'] == 0:
            q.message.reply_text("No reports!")
        else:
            data = response.json()['results'][0]
            id_ = data['id']
            req_id = data['title']
            reported = data["reported_user"]
            reporter = data["reporter"]
            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton('Check Request', callback_data=f'{id_}/check_request{req_id}')],
                 [InlineKeyboardButton('Check Reported User', callback_data=f'check_user{reported}')],
                 [InlineKeyboardButton('Check Reporter', callback_data=f'check_user{reporter}')],
                 [InlineKeyboardButton('Ban', callback_data=f'/ban_{id_}'),
                  InlineKeyboardButton('Warn', callback_data=f'/warn_{id_}'),
                  InlineKeyboardButton('Ignore', callback_data=f'/ignore_{id_}')],
                 [InlineKeyboardButton('Warn Reporter', callback_data=f'/false_{id_}')]])
            q.message.reply_text(f"Type:Request\n\nReport:\n{data['details']}", reply_markup=buttons)


def projectReports(update: Update, context: CallbackContext):
    if update.callback_query:
        q = update.callback_query
        q.answer()
    else:
        q = update
    response = requests.get(f"{host_url}api/v1/reports/p",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        if response.json()['count'] == 0:
            q.message.reply_text("No reports!")
        else:
            data = response.json()['results'][0]
            project_slug = data['slug']
            id = data['id']
            reported = data["reported_user"]
            reporter = data["reporter"]
            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton('Check Project', callback_data=f'{id}/check_project{project_slug}')],
                 [InlineKeyboardButton('Check Reported User', callback_data=f'check_user{reported}')],
                 [InlineKeyboardButton('Check Reporter', callback_data=f'check_user{reporter}')],
                 [InlineKeyboardButton('Ban', callback_data=f'/ban_{id}'),
                  InlineKeyboardButton('Warn', callback_data=f'/warn_{id}'),
                  InlineKeyboardButton('Ignore', callback_data=f'/ignore_{id}')],
                 [InlineKeyboardButton('Warn Reporter', callback_data=f'/false_{id}')]])
            q.message.reply_text(f"Type:Project\n\nReport:\n{data['details']}", reply_markup=buttons)


def notVerified(update: Update, context: CallbackContext):
    if update.callback_query:
        q = update.callback_query
        q.answer()
    else:
        q = update
    response = requests.get(f"{host_url}api/v1/projects/get/unverified",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        if response.json()['count'] == 0:
            q.message.reply_text("there's no new projects!")
        else:
            data = response.json()['results'][0]
            id_ = data['id']
            price = data["price"]
            project = data["name"]
            description = data["description"]
            employerName = data['employerName']
            employer = data['employer']
            categories = data['categories']
            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton('Check employer', callback_data=f'check_user{employer}')],
                 [InlineKeyboardButton('Verify', callback_data=f'/verify_{id_}')],
                 [InlineKeyboardButton('Refuse', callback_data=f'refuse_{id_}')]])
            q.message.reply_text(f"Project:{project}\nemployer name: {employerName}\n"
                                 f"description:{description}\nprice:{price}\n"
                                 f"categories:{categories}", reply_markup=buttons)


def getProject(update: Update, context: CallbackContext):
    q = update.callback_query
    id_ = q.data.replace('getP', '')
    response = requests.get(f"{host_url}api/v1/projects/id/{id_}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        if response.json()['count'] == 0:
            q.message.reply_text("Not found!")
        else:
            data = response.json()['results'][0]
            price = data["price"]
            project = data["name"]
            description = data["description"]
            employerName = data['employerName']
            employer = data['employer']
            categories = data['categories']
            condition = data['condition']
            if condition == 'v':
                buttons = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Check employer', callback_data=f'check_user{employer}')],
                     [InlineKeyboardButton('Refuse', callback_data=f'refuse_{id_}')]])
                q.message.reply_text(f"Project:{project}(verified)\nemployer name: {employerName}\n"
                                     f"description:{description}\nprice:{price}\n"
                                     f"categories:{categories}", reply_markup=buttons)
            elif condition == 'r':
                buttons = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Check employer', callback_data=f'check_user{employer}')],
                     [InlineKeyboardButton('Verify', callback_data=f'/verify_{id_}')]])
                q.message.reply_text(f"Project:{project}(refused)\nemployer name: {employerName}\n"
                                     f"description:{description}\nprice:{price}\n"
                                     f"categories:{categories}", reply_markup=buttons)
            elif condition == 'a':
                buttons = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Check employer', callback_data=f'check_user{employer}')],
                     [InlineKeyboardButton('Verify', callback_data=f'/verify_{id_}')],
                     [InlineKeyboardButton('Refuse', callback_data=f'refuse_{id_}')]])
                q.message.reply_text(f"Project:{project}(waiting)\nemployer name: {employerName}\n"
                                     f"description:{description}\nprice:{price}\n"
                                     f"categories:{categories}", reply_markup=buttons)
            else:
                buttons = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Check employer', callback_data=f'check_user{employer}')]])
                q.message.reply_text(f"Project:{project}(condition={condition})\nemployer name: {employerName}\n"
                                     f"description:{description}\nprice:{price}\n"
                                     f"categories:{categories}", reply_markup=buttons)

    q.answer()


def getReport(update: Update, context: CallbackContext):
    q = update.callback_query
    id_ = q.data.replace('getR', '')
    response = requests.get(f"{host_url}api/v1/report/{id_}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        if response.json()['count'] == 0:
            q.message.reply_text("Not found!")
        else:
            data = response.json()['results'][0]
            slug = data["slug"]
            time_diff = data["description"]
            reporter = data['reporter']
            details = data['details']
            title = data['title']
            type_ = data['type']
            condition = data['condition']
            reported = data["reported_user"]
            if condition == 'p':
                if type_ == 'p':
                    buttons = InlineKeyboardMarkup(
                        [[InlineKeyboardButton('Check Project', callback_data=f'{id_}/check_project{slug}')],
                         [InlineKeyboardButton('Check Reported User', callback_data=f'check_user{reported}')],
                         [InlineKeyboardButton('Check Reporter', callback_data=f'check_user{reporter}')],
                         [InlineKeyboardButton('Ban', callback_data=f'/ban_{id_}'),
                          InlineKeyboardButton('Warn', callback_data=f'/warn_{id_}'),
                          InlineKeyboardButton('Ignore', callback_data=f'/ignore_{id_}')],
                         [InlineKeyboardButton('Warn Reporter', callback_data=f'/false_{id_}')]])
                elif type_ == 'r':
                    buttons = InlineKeyboardMarkup(
                        [[InlineKeyboardButton('Check Request', callback_data=f'{id_}/check_request{title}')],
                         [InlineKeyboardButton('Check Reported User', callback_data=f'check_user{reported}')],
                         [InlineKeyboardButton('Check Reporter', callback_data=f'check_user{reporter}')],
                         [InlineKeyboardButton('Ban', callback_data=f'/ban_{id_}'),
                          InlineKeyboardButton('Warn', callback_data=f'/warn_{id_}'),
                          InlineKeyboardButton('Ignore', callback_data=f'/ignore_{id_}')],
                         [InlineKeyboardButton('Warn Reporter', callback_data=f'/false_{id_}')]])
                else:
                    buttons = InlineKeyboardMarkup([[InlineKeyboardButton('Solve', callback_data=f'/solve_{id_}'),
                                                     InlineKeyboardButton('Ignore', callback_data=f'/ignore_{id_}')],
                                                    [InlineKeyboardButton('Check Reporter',
                                                                          callback_data=f'check_user{reporter}')],
                                                    [InlineKeyboardButton('Warn Reporter',
                                                                          callback_data=f'/false_{id_}')]])
            else:
                buttons = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Check reporter', callback_data=f'check_user{reporter}')],
                     [InlineKeyboardButton('Warn Reporter', callback_data=f'/false_{id_}')]])
            q.edit_message_text(f"Report(condition:{condition})\ndetails:{details}\ntype:{type_}\n\n{time_diff}"
                                , reply_markup=buttons)

    q.answer()


def verifyP(update: Update, context: CallbackContext):
    q = update.callback_query
    id_ = q.data.replace('verify_', '')
    q.edit_message_text('Are you sure?', reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton('Yes', callback_data=f'sure_vp{id_}')],
        [InlineKeyboardButton('No', callback_data=f'getP{id_}')]]))
    q.answer()


def sure_verify(update: Update, context: CallbackContext):
    q = update.callback_query
    id_ = q.data.replace('sure_vp', '')
    response = requests.get(f"{host_url}api/v1/projects/{id_}/verify",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        q.edit_message_text('project verified successfully.', reply_markup=None)
    q.answer()


def refuseP(update: Update, context: CallbackContext):
    q = update.callback_query
    id_ = q.data.replace('refuse_', '')
    q.edit_message_text('Are you sure?', reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton('Yes', callback_data=f'sure_rp{id_}')],
        [InlineKeyboardButton('No', callback_data=f'getP{id_}')]]))
    q.answer()


def sure_refuse(update: Update, context: CallbackContext):
    q = update.callback_query
    id_ = q.data.replace('sure_rp', '')
    response = requests.get(f"{host_url}api/v1/projects/{id_}/invalidate",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        q.edit_message_text('project refused successfully.', reply_markup=None)
    q.answer()


def backReport(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    if 'backRep_p' in q.data:
        qID = q.data.replace('backRep_p', '')
        response = requests.get(f"{host_url}api/v1/report/{qID}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            if response.json()['count'] == 0:
                q.message.reply_text("No reports!")
            else:
                data = response.json()['results'][0]
                project_slug = data['slug']
                id = data['id']
                reported = data["reported_user"]
                reporter = data["reporter"]
                buttons = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Check Project', callback_data=f'{id}/check_project{project_slug}')],
                     [InlineKeyboardButton('Check Reported User', callback_data=f'check_user{reported}')],
                     [InlineKeyboardButton('Check Reporter', callback_data=f'check_user{reporter}')],
                     [InlineKeyboardButton('Ban', callback_data=f'/ban_{id}'),
                      InlineKeyboardButton('Warn', callback_data=f'/warn_{id}'),
                      InlineKeyboardButton('Ignore', callback_data=f'ignore_{id}')],
                     [InlineKeyboardButton('Warn Reporter', callback_data=f'/false_{id}')]])
                q.edit_message_text(f"Type:Project\n\nReport:\n{data['details']}", reply_markup=buttons)

    elif 'backRep_r' in q.data:
        qID = q.data.replace('backRep_r', '')
        response = requests.get(f"{host_url}api/v1/report/{qID}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            if response.json()['count'] == 0:
                update.message.reply_text("No reports!")
            else:
                data = response.json()['results'][0]
                id_ = data['id']
                req_id = data['title']
                reported = data["reported_user"]
                reporter = data["reporter"]
                buttons = InlineKeyboardMarkup(
                    [[InlineKeyboardButton('Check Report', callback_data=f'{id_}/check_request{req_id}')],
                     [InlineKeyboardButton('Check Reported User', callback_data=f'check_user{reported}')],
                     [InlineKeyboardButton('Check Reporter', callback_data=f'check_user{reporter}')],
                     [InlineKeyboardButton('Ban', callback_data=f'/ban_{id_}'),
                      InlineKeyboardButton('Warn', callback_data=f'/warn_{id_}'),
                      InlineKeyboardButton('Ignore', callback_data=f'/ignore_{id_}')],
                     [InlineKeyboardButton('Warn Reporter', callback_data=f'/false_{id_}')]])
                update.message.reply_text(f"Type:Report\n\nReport:\n{data['details']}", reply_markup=buttons)


def checkUser(update: Update, context: CallbackContext):
    q = update.callback_query
    id_ = q.data.replace('check_user', '')
    response = requests.get(f"{host_url}api/v1/user/{id_}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        q.message.reply_text(response.json(), reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Delete this message', callback_data="/deleteM")]]))
        q.answer()
    else:
        q.answer(text='not found')


def deleteMessage(update: Update, context: CallbackContext):
    q = update.callback_query
    message_id = q.message.message_id
    context.bot.delete_message(message_id=message_id, chat_id=update.effective_chat.id)
    q.answer('deleted successfully')


def checked_by(update: Update, context: CallbackContext):
    if context.user_data["authorized"]:
        if context.user_data['superuser']:
            update.message.reply_text('Choose:', reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('Projects checked by me', callback_data='checkedP')],
                [InlineKeyboardButton('Reports checked by me', callback_data='checkedR')],
                [InlineKeyboardButton('Checked by another admins', callback_data='admin_checked')]]))
        else:
            update.message.reply_text('Choose:', reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('Projects checked by me', callback_data='checkedP')],
                [InlineKeyboardButton('Reports checked by me', callback_data='checkedR')]]))


def search(update: Update, context: CallbackContext):
    if context.user_data["authorized"]:
        # if context.user_data['superuser']:
        #     update.message.reply_text('Search:', reply_markup=InlineKeyboardMarkup([
        #         [InlineKeyboardButton('Projects', callback_data='searchP')],
        #         [InlineKeyboardButton('Reports', callback_data='searchR')],
        #         [InlineKeyboardButton('Users', callback_data='searchU')],
        #     ]))
        # else:
        update.message.reply_text('Search:', reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('Projects', callback_data='searchP')],
            [InlineKeyboardButton('Reports', callback_data='searchR')]]))


def searchP(update: Update, context: CallbackContext):  # triger a conversation handler
    q = update.callback_query
    q.answer()
    q.edit_message_text('Search type: Project\nPlease enter what you searching for:')
    return 1


def searchR(update: Update, context: CallbackContext):  # triger a conversation handler
    q = update.callback_query
    q.answer()
    q.edit_message_text('Search type: Report\nPlease enter what you searching for:')
    return 2


# def searchU(update:Update,context:CallbackContext): #triger a conversation handler
#     q = update.callback_query
#     q.answer()
#     q.edit_message_text('Search type: User\nPlease enter what you searching for:')
#     return 3

def searchProject(update: Update, context: CallbackContext):
    word = update.message.text
    response = requests.get(url=f"{host_url}api/v1/projects/search_all/{word}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        j = response.json()
        xlist = []
        if j['count'] == 0:
            update.message.reply_text(text="No projects found!")
            return ConversationHandler.END
        for c in j['results']:
            try:
                k = c['id']
                xlist.append([InlineKeyboardButton(c['name'], callback_data=f"getP{k}")])
            except:
                break
        if response.json()['next']:
            k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
            xlist.append([InlineKeyboardButton(text="next", callback_data=f"/search-page-P{k}")])
        if response.json()['previous']:
            k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
            xlist.append([InlineKeyboardButton(text="previous", callback_data=f"/search-page-P{k}")])
        reply_markup = InlineKeyboardMarkup(xlist)
        update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return ConversationHandler.END


def searchReport(update: Update, context: CallbackContext):
    word = update.message.text
    response = requests.get(url=f"{host_url}api/v1/reports/search_all/{word}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        j = response.json()
        if j['count'] == 0:
            update.message.reply_text(text="No reports found!")
            return ConversationHandler.END
        Text = ''
        xlist = []
        for c in j['results']:
            if t := c['type'] == 'b':
                t = 'bug'
            elif t == 'p':
                t = 'project'
            elif t == 'r':
                t = 'report'
            Text += f'type:{t}\nid:{c["id"]}\ndetails:{c["details"]}\n*-*-*-*-*-*-*-*-*\n'
            xlist.append([InlineKeyboardButton(f'id:{c["id"]}', callback_data=f"getR{c['id']}")])
        if j['next']:
            k = j['next'].replace('http://127.0.0.1:8000/', '')
            xlist.append([InlineKeyboardButton(text="next", callback_data=f"/search-page-R{k}")])
        if response.json()['previous']:
            k = j['previous'].replace('http://127.0.0.1:8000/', '')
            xlist.append([InlineKeyboardButton(text="previous", callback_data=f"/search-page-R{k}")])
        reply_markup = InlineKeyboardMarkup(xlist)
        update.message.reply_text(Text, reply_markup=reply_markup)
    return ConversationHandler.END


def searchPage(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    if '-P' in q.data:
        response = requests.get(url=f"{host_url}{q.data.replace('/search-page-P', '')}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            j = response.json()
            for c in j['results']:
                try:
                    k = c['id']
                    xlist.append([InlineKeyboardButton(c['name'], callback_data=f"getP{k}")])
                except:
                    break
            if response.json()['next']:
                k = response.json()['next'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="next", callback_data=f"/search-page-{k}")])
            if response.json()['previous']:
                k = response.json()['previous'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="previous", callback_data=f"/search-page-{k}")])
            reply_markup = InlineKeyboardMarkup(xlist)
            q.edit_message_text('Please choose:', reply_markup=reply_markup)
    elif '-R' in q.data:
        response = requests.get(url=f"{host_url}{q.data.replace('/search-page-R', '')}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            j = response.json()
            Text = ''
            for c in j['results']:
                if t := c['type'] == 'b':
                    t = 'bug'
                elif t == 'p':
                    t = 'project'
                elif t == 'r':
                    t = 'report'
                Text += f'type:{t}\nid:{c["id"]}\ndetails:{c["details"]}\n*-*-*-*-*-*-*-*-*\n'
                xlist.append([InlineKeyboardButton(f'id:{c["id"]}', callback_data=f"getR{c['id']}")])
            if j['next']:
                k = j['next'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="next", callback_data=f"/search-page-R{k}")])
            if response.json()['previous']:
                k = j['previous'].replace('http://127.0.0.1:8000/', '')
                xlist.append([InlineKeyboardButton(text="previous", callback_data=f"/search-page-R{k}")])
            reply_markup = InlineKeyboardMarkup(xlist)
            q.message.reply_text(Text, reply_markup=reply_markup)


def projectsChecked_by(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    if 'checkedPlink_' in q.data:
        link = q.data.replace('checkedPlink_', '')
        response = requests.get(f"{host_url}{link}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    else:
        response = requests.get(f"{host_url}api/v1/projects/admin/checked_by",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        resp = response.json()
        if resp['count'] > 0:
            buttons = []
            for member in resp['results']:
                buttons.append([InlineKeyboardButton(member['id'], callback_data=f'pCheck_{member["slug"]}')])
            if resp['previous']:
                k = resp.json()['previous'].replace(host_url, '')
                buttons.append([InlineKeyboardButton('Previous', callback_data=f'checkedPlink_{k}')])
            if resp['next']:
                k = resp.json()['next'].replace(host_url, '')
                if not resp['previous']:
                    buttons.append([InlineKeyboardButton('Next', callback_data=f'checkedPlink_{k}')])
                else:
                    buttons[-1].append(InlineKeyboardButton('Next', callback_data=f'checkedPlink_{k}'))
            if buttons:
                q.edit_message_text(resp['results'], reply_markup=InlineKeyboardMarkup(buttons))
            else:
                q.edit_message_text(resp['results'])
        else:
            q.edit_message_text('The list is empty.')
    else:
        q.edit_message_text('There is a problem.')


def reportsChecked_by(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    if 'checkedRlink_' in q.data:
        link = q.data.replace('checkedRlink_', '')
        response = requests.get(f"{host_url}{link}",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    else:
        response = requests.get(f"{host_url}api/v1/reports/admin/checked_by",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        resp = response.json()
        if resp['count'] > 0:
            buttons = []
            for member in resp['results']:
                buttons.append([InlineKeyboardButton(member['id'], callback_data=f'rCheck_{member["id"]}')])
            if resp['previous']:
                k = resp.json()['previous'].replace(host_url, '')
                buttons.append([InlineKeyboardButton('Previous', callback_data=f'checkedRlink_{k}')])
            if resp['next']:
                k = resp.json()['next'].replace(host_url, '')
                if not resp['previous']:
                    buttons.append([InlineKeyboardButton('Next', callback_data=f'checkedRlink_{k}')])
                else:
                    buttons[-1].append(InlineKeyboardButton('Next', callback_data=f'checkedPlink_{k}'))
            if buttons:
                q.edit_message_text(resp['results'], reply_markup=InlineKeyboardMarkup(buttons))
            else:
                q.edit_message_text(resp['results'])
        else:
            q.edit_message_text('The list is empty.')
    else:
        q.edit_message_text('There is a problem.')


def projectCheck(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    slug = q.data.replace('pCheck_', '')
    response = requests.get(f"{host_url}api/v1/projects/all/{slug}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        resp = response.json()
        if resp['count'] > 0:
            q.edit_message_text(f'Project:\n{resp["results"]}', reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('Check employer', callback_data=f'check_user{resp["results"][0]["employer"]}')],
            ]))
        else:
            q.edit_message_text('Not Found!')
    else:
        q.edit_message_text('There is a problem!')


def reportCheck(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    id_ = q.data.replace('rCheck_', '')
    response = requests.get(f"{host_url}api/v1/report/{id_}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        resp = response.json()
        if resp['count'] > 0:
            buttons = [
                [InlineKeyboardButton('Check reporter', callback_data=f'check_user{resp["results"][0]["reporter"]}')]]
            if resp['results'][0]['type'] == 'p':
                buttons.append(
                    [InlineKeyboardButton('Check project', callback_data=f'{id_}/repP{resp["results"][0]["slug"]}')])
                buttons.append([InlineKeyboardButton('Check employer',
                                                     callback_data=f'check_user{resp["results"][0]["reported_user"]}')])
            elif resp['results'][0]['type'] == 'r':
                buttons.append(
                    [InlineKeyboardButton('Check request', callback_data=f'{id_}/repR{resp["results"][0]["title"]}')])
                buttons.append([InlineKeyboardButton('Check applicant',
                                                     callback_data=f'check_user{resp["results"][0]["reported_user"]}')])
            q.edit_message_text(f'Report:\n{resp["results"]}', reply_markup=InlineKeyboardMarkup(buttons))
        else:
            q.edit_message_text('Not Found!')
    else:
        q.edit_message_text('There is a problem!')


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Progress cancelled successfully.', reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


# def notChecked(context:CallbackContext):
#         response = requests.get(f"{host_url}api/v1/not_checked").json()
#         if response['all'] > 0:
#             response2 = requests.get(f"{host_url}api/v1/admins/all")
#             for j in response2.json()["results"]:
#                 try:
#                     context.bot.send_message(chat_id=j['username'],text=f'New projects : {response["Unverified Projects"]}\n'
#                                                                         f'New project reports : {response["Project Reports"]}\n'
#                                                                         f'New request reports : {response["Request Reports"]}\n'
#                                                                         f'New bug Reports : {response["Bug Reports"]}',
#                                              reply_markup=InlineKeyboardMarkup([
#                                                  [InlineKeyboardButton('New Projects',callback_data='newProjects')],
#                                                  [InlineKeyboardButton('Project reports',callback_data='pReports')],
#                                                  [InlineKeyboardButton('request reports',callback_data='rReports')],
#                                                  [InlineKeyboardButton('bug reports',callback_data='bReports')],
#                                              ]))
#                 except:pass

def admin_dashboard(update: Update, context: CallbackContext):
    if context.user_data['superuser']:
        update.message.reply_text(f'Hi {update.message.from_user.first_name}', reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('New admin(Phone Number)', callback_data='/newAdmin')],
            [InlineKeyboardButton('Demote admin(Phone Number)', callback_data='/removeAdmin')],
            [InlineKeyboardButton('Admins list', callback_data='/listAdmin')],
            [InlineKeyboardButton('Send message to all', callback_data='/msgAll')]]))


def message_get(update: Update, context: CallbackContext):
    q = update.callback_query
    q.edit_message_text('please send what you want to announce to all users:',
                        reply_markup=None)
    q.answer()
    return 1


def message_all(update: Update, context: CallbackContext):
    resp = requests.post(f"{host_url}api/v1/admin/msg_all",data={'msg':update.message.text},
                        headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if resp.status_code == 200:
        update.message.reply_text('message sent successfully.')
    else:
        update.message.reply_text(f'status:{resp.status_code}\ncontent:{resp.content}')
    return ConversationHandler


def listAdmin(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    if context.user_data['superuser']:
        response = requests.get(f"{host_url}api/v1/admin/all",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            j = response.json()
            if j['count'] == 0:
                q.message.reply_text('the list is empty!')
            else:
                xlist = []
                for admin in j['results']:
                    xlist.append([InlineKeyboardButton(admin['fullname'], callback_data=f'check_admin{admin["id"]}')])
                q.message.reply_text('Admins:', reply_markup=InlineKeyboardMarkup(xlist))
        else:
            q.message.reply_text(f'status:{response.status_code}\n{response.text}')


def bannedUsers(update: Update, context: CallbackContext):
    if context.user_data['superuser']:
        response = requests.get(f"{host_url}api/v1/admin/banned",
                                headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
        if response.status_code == 200:
            j = response.json()
            if j['count'] == 0:
                update.message.reply_text('The list is empty!')
            else:
                xlist = []
                for i in j['results']:
                    xlist.append([InlineKeyboardButton(f"{i['first_name']} {i['last_name']}",
                                                       callback_data=f"check_user{i['id']}")])
                update.message.reply_text('Banned users:', reply_markup=InlineKeyboardMarkup(xlist))


def checkAdmin(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    id_ = q.data.replace('check_admin', '')
    response = requests.get(f"{host_url}api/v1/user/{id_}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        j = response.json()
        q.message.reply_text(j, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Demote to user', callback_data=f"/demoteSure_{id_}")],
             [InlineKeyboardButton('Ban admin', callback_data=f"/banSure_{id_}")]]))
    else:
        q.message.reply_text(f'status:{response.status_code}\n{response.text}')


def banSure(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    id_ = q.data.replace('/banSure_', '')
    q.edit_message_text('Are you sure that you wanna ban this admin', reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton('Yes', callback_data=f'/banAdmin_{id_}')],
        [InlineKeyboardButton('No', callback_data='/deleteM')]
    ]))


def banAdmin(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    id_ = q.data.replace('/banAdmin_', '')
    response = requests.get(f"{host_url}api/v1/admin/ban/id/{id_}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        q.edit_message_text('Admin successfully banned.')


def demoteSure(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    id_ = q.data.replace('/demoteSure_', '')
    q.edit_message_text('Are you sure that you wanna demote this admin to user?', reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton('Yes', callback_data=f'/demoteAdmin_{id_}')],
        [InlineKeyboardButton('No', callback_data='/deleteM')]
    ]))


def demoteAdmin(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    id_ = q.data.replace('/demoteAdmin_', '')
    response = requests.get(f"{host_url}api/v1/admin/remove/id/{id_}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        q.edit_message_text('Admin successfully demoted to user.')
    else:
        q.edit_message_text(f'status:{response.status_code}\nresponse:{response.content}')


def newAdmin(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    if context.user_data['superuser']:
        q.edit_message_text('User to Admin:\nEnter the phone number:')
        return 1


def removeAdmin(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    if context.user_data['superuser']:
        q.edit_message_text("Admin to User:\nEnter the phone number:")
        return 1


def getNumberAdmin(update: Update, context: CallbackContext):
    number = update.message.text
    response = requests.get(f"{host_url}api/v1/admin/add/{number}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        update.message.reply_text(f'{number} is now an admin')
    else:
        update.message.reply_text(f'status:{response.status_code}\n{response.text}')
    return ConversationHandler.END


def removeNumberAdmin(update: Update, context: CallbackContext):
    number = update.message.text
    response = requests.get(f"{host_url}api/v1/admin/remove/{number}",
                            headers={'Authorization': f"Token {context.user_data['userTOKEN']}"})
    if response.status_code == 200:
        update.message.reply_text(f"{number} isn't now an admin")
    else:
        update.message.reply_text(f'status:{response.status_code}\n{response.text}')
    return ConversationHandler.END


def idk(update: Update, context):
    update.message.reply_text('what?')


def main():
    updater = Updater(Token, use_context=True)
    dp = updater.dispatcher

    search_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(searchP, pattern='searchP'),
                      CallbackQueryHandler(searchR, pattern='searchR')],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, searchProject)],
            2: [MessageHandler(Filters.text & ~Filters.command, searchReport)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    newAdmin_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(newAdmin, pattern='/newAdmin')],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, getNumberAdmin)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    message_all_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(message_get,pattern='/msgAll')],
        states={
            1 : [MessageHandler(Filters.text,message_all)]
        },
        fallbacks=[CommandHandler('cancel',cancel)]
    )

    removeAdmin_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(removeAdmin, pattern='/removeAdmin')],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, removeNumberAdmin)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # on different commands - answer in Telegram
    # updater.job_queue.run_repeating(notChecked,120)
    dp.add_handler(CallbackQueryHandler(searchPage, pattern='/search-page'))
    dp.add_handler(search_handler)
    dp.add_handler(message_all_handler)
    dp.add_handler(newAdmin_handler)
    dp.add_handler(removeAdmin_handler)
    dp.add_handler(CommandHandler('dashboard', admin_dashboard))
    dp.add_handler(CallbackQueryHandler(backReport, pattern='backRep'))
    dp.add_handler(CallbackQueryHandler(banSure, pattern='/banSure_'))
    dp.add_handler(CallbackQueryHandler(banAdmin, pattern='/banAdmin_'))
    dp.add_handler(CallbackQueryHandler(demoteSure, pattern='/demoteSure_'))
    dp.add_handler(CallbackQueryHandler(demoteAdmin, pattern='/demoteAdmin_'))
    dp.add_handler(CallbackQueryHandler(getProject, pattern='getP'))
    dp.add_handler(CallbackQueryHandler(getReport, pattern='getR'))
    dp.add_handler(CallbackQueryHandler(projectsChecked_by, pattern='checkedP'))
    dp.add_handler(CallbackQueryHandler(reportsChecked_by, pattern='checkedR'))
    dp.add_handler(CallbackQueryHandler(reportCheck, pattern='rCheck_'))
    dp.add_handler(CallbackQueryHandler(projectCheck, pattern='pCheck_'))
    dp.add_handler(CallbackQueryHandler(checkUser, pattern='check_user'))
    dp.add_handler(CallbackQueryHandler(listAdmin, pattern='/listAdmin'))
    dp.add_handler(CallbackQueryHandler(checkAdmin, pattern='check_admin'))
    dp.add_handler(CallbackQueryHandler(deleteMessage, pattern='/deleteM'))
    dp.add_handler(CallbackQueryHandler(verifyP, pattern='verify_'))
    dp.add_handler(CallbackQueryHandler(refuseP, pattern='refuse_'))
    dp.add_handler(CallbackQueryHandler(sure_refuse, pattern='sure_rp'))
    dp.add_handler(CallbackQueryHandler(sure_verify, pattern='sure_vp'))
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("checked", checked_by))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("project_reports", projectReports))
    dp.add_handler(CallbackQueryHandler(projectReports, pattern='pReports'))
    dp.add_handler(CommandHandler("request_reports", requestReports))
    dp.add_handler(CallbackQueryHandler(requestReports, pattern='rReports'))
    dp.add_handler(CommandHandler("bug_reports", bugReports))
    dp.add_handler(CallbackQueryHandler(bugReports, pattern='bReports'))
    dp.add_handler(CommandHandler("notVerified", notVerified))
    dp.add_handler(CallbackQueryHandler(notVerified, pattern='newProjects'))
    dp.add_handler(CommandHandler('search', search))
    # (DONE) add new handlers for searching between reports or projects(or users or requests)
    # add new button for sending message to user in check_user (handle in back_end)
    # (HARD! only available for superusers not staff!) !down below!
    # add new handler for add new admin or make an admin a normal user or more
    # complete checked_by buttons for seeing reports or projects checked by another admin
    # add new handler for invalidating or ban users or others with a command like this (/setChange -u -ban or ...)
    # a function just for getting all users projects or reports as a list
    # add a new button on project page to get all reports about that project
    # asks admin if he wants an autocheck for reports or projects and get the seconds for that

    dp.add_handler(CallbackQueryHandler(button))

    # log all errors
    dp.add_error_handler(error)
    dp.add_handler(MessageHandler(Filters.all, idk))
    # dp.add_handler(MessageHandler(Filters.text,messageHandler))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
