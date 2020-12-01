import sys
import time
import difflib
from os import environ

import praw
import prawcore
import bmemcached


# constants
# SUBREDDIT = 'PrequelMemes'
SUBREDDIT = 'bottesting'


# function to search for the phrase
def find_in_text(text, behaviour):
    trigger = 'Did you ever hear the tragedy of Darth Plagueis the wise'
    if behaviour == 0:
        return difflib.SequenceMatcher(None, trigger, text).ratio()
    elif difflib.SequenceMatcher(None, trigger, text).ratio() > 0.8:
        return True
    else:
        return False


# function to search for specific words using difflib
def word_match(text, target_word):
    # split string into individual words
    text_words = text.split()
    # check each word
    for j in range(len(text_words)):
        # if word is more than 80% match, return 'True'
        if difflib.SequenceMatcher(None, target_word, text_words[j]).ratio() > 0.8:
            return True


# initialise cache using details in environment variables
memcache = bmemcached.Client(environ.get('MEMCACHEDCLOUD_SERVERS').split(','),
                             environ.get('MEMCACHEDCLOUD_USERNAME'),
                             environ.get('MEMCACHEDCLOUD_PASSWORD'))


# function to log activity to avoid duplicate comments
def log(comment_id):
    # add id to log
    memcache.set('actions', memcache.get('actions') + [str(comment_id)])
    # add 1 to 'Matches'
    memcache.set('Matches', memcache.get('Matches') + 1)


# function to increment, output and log number of posts scanned so far
scanned = memcache.get('scanned')


def progress():
    global scanned
    # add 1 to 'scanned'
    scanned += 1
    # if 'scanned' is a multiple of 10, display it and record it to cache
    if scanned % 100 == 0:
        print(str(scanned) + ' comments scanned.')
        memcache.set('scanned', scanned)


# fetch details from environmental variables
bot_account = {'ClientID': environ['ClientID'],
               'ClientSecret': environ['ClientSecret'],
               'Password': environ['Password'],
               'UserAgent': 'python3.6.1:darthplagueisbot:v1.3.3 (by /u/Sgp15)',
               'Username': environ['Username']}

# initialise reddit object with details
reddit = praw.Reddit(client_id=bot_account['ClientID'],
                     client_secret=bot_account['ClientSecret'],
                     password=bot_account['Password'],
                     user_agent=bot_account['UserAgent'],
                     username=bot_account['Username'])

# which subreddit bot will be active in
subreddit = reddit.subreddit(SUBREDDIT)

# phrase to reply with
TRAGEDY = "I thought not. It's not a story the Jedi would tell you. " \
          "It's a Sith legend. Darth Plagueis was a Dark Lord of the Sith, " \
          'so powerful and so wise he could use the Force to influence the midichlorians to create life... ' \
          'He had such a knowledge of the dark side that he could even keep the ones he cared about from dying. ' \
          'The dark side of the Force is a pathway to many abilities some consider to be unnatural. ' \
          'He became so powerful... the only thing he was afraid of was losing his power, which eventually, ' \
          'of course, he did. Unfortunately, he taught his apprentice everything he knew, ' \
          'then his apprentice killed him in his sleep. It\'s ironic he could save others from death, but not himself.'

# run bot
while True:
    try:
        # start reading comment stream
        for comment in subreddit.stream.comments():
            try:
                # increment 'comments checked' counter by 1
                progress()
                # ignore unknown unicode characters to avoid errors
                comment_body = comment.body.encode('ascii', 'replace')
                # check for general match,
                # check for essential terms,
                # check comment has not been replied to already,
                # check comment is not the wrong phrase
                if (find_in_text(comment_body, 1) and
                        word_match(comment_body.lower(), 'plagueis') and
                        word_match(comment_body.lower(), 'tragedy') and
                        not str(comment) in memcache.get('actions') and
                        not difflib.SequenceMatcher(None, TRAGEDY, comment_body).ratio() > 0.66):
                    # newline
                    print('')
                    # display id, body, author and match percentage of comment
                    print(comment)
                    print(comment_body)
                    print(comment.author)
                    print(find_in_text(comment_body, 0))
                    # reply to comment
                    comment.reply(TRAGEDY)
                    # add comment to list of comments that have been replied to
                    log(comment)
                    # newline
                    print('')
            # countdown for new accounts with limited comments/minute
            except praw.exceptions.APIException as err:
                error_details = str(err)
                # get time till you can comment again from error details
                WaitTime = error_details[54:55]
                print('Wait ' + WaitTime + ' minutes to work.')
                Time = int(WaitTime)
                # display time remaining every minute
                for i in range(Time):
                    time.sleep(60)
                    Time -= 1
                    print(str(Time) + ' minute(s) left.')
            # generic error handler
            except Exception:
                print('ERROR')
                # get error details and display them
                e = sys.exc_info()
                print(e)
    # handler for error thrown when connection resets
    except prawcore.exceptions.RequestException as err:
        print(str(err))
        print('Connection reset.')
