import sys
from time import sleep
from os import environ
from difflib import SequenceMatcher

import praw
import prawcore
import bmemcached


# function to search for the phrase
def findt(Text, Type):
    Trigger = 'Did you ever hear the tragedy of Darth Plagueis the wise'
    if Type == 0:
        return SequenceMatcher(None, Trigger, Text).ratio()
    elif SequenceMatcher(None, Trigger, Text).ratio() > 0.8:
        return True
    else:
        return False


# function to search for specific words using difflib
def wordmatch(Text, Object):
    # split string into individual words
    TWords = Text.split()
    # check each word
    for i in range(len(TWords)):
        # if word is more than 80% match, return 'True'
        if SequenceMatcher(None, Object, TWords[i]).ratio() > 0.8:
            return True


# initialise cache using details in premade environmental variable
Cache = bmemcached.Client(environ.get('MEMCACHEDCLOUD_SERVERS').split(','),
                          environ.get('MEMCACHEDCLOUD_USERNAME'),
                          environ.get('MEMCACHEDCLOUD_PASSWORD'))


# function to log activity to avoid duplicate comments
def log(ID):
    # add id to log
    Cache.set('actions', Cache.get('actions') + [str(ID)])
    # add 1 to 'Matches'
    Cache.set('Matches', Cache.get('Matches') + 1)


# function to increment, output and log number of posts scanned so far
Scanned = Cache.get('Scanned')


def progress():
    global Scanned
    # add 1 to 'Scanned'
    Scanned += 1
    # if 'Scanned' is a multiple of 10, dislay it and record it to cache
    if Scanned % 100 == 0:
        print(str(Scanned) + ' comments scanned.')
        Cache.set('Scanned', Scanned)


# fetch details from environmental variables
BotA = {'ClientID': environ['ClientID'],
        'ClientSecret': environ['ClientSecret'],
        'Password': environ['Password'],
        'UserAgent': 'python3.6.1:darthplagueisbot:v1.3.3 (by /u/Sgp15)',
        'Username': environ['Username']}

# initialise reddit object with details
reddit = praw.Reddit(client_id=BotA['ClientID'],
                     client_secret=BotA['ClientSecret'],
                     password=BotA['Password'],
                     user_agent=BotA['UserAgent'],
                     username=BotA['Username'])

# which subreddit bot will be active in
subreddit = reddit.subreddit('PrequelMemes')

# phrase to reply with
Tragedy = "I thought not. It's not a story the Jedi would tell you. "\
          "It's a Sith legend. Darth Plagueis was a Dark Lord of the Sith, "\
          'so powerful and so wise he could use the Force to influence the midichlorians to create life... '\
          'He had such a knowledge of the dark side that he could even keep the ones he cared about from dying. '\
          'The dark side of the Force is a pathway to many abilities some consider to be unnatural. '\
          'He became so powerful... the only thing he was afraid of was losing his power, which eventually, '\
          'of course, he did. Unfortunately, he taught his apprentice everything he knew, '\
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
                CommentBody = comment.body.encode('ascii', 'replace')
                # check for general match,
                # check for essential terms,
                # check comment has not been replied to already,
                # check comment is not the wrong phrase
                if (findt(CommentBody, 1) and
                    wordmatch(CommentBody.lower(), 'plagueis') and
                    wordmatch(CommentBody.lower(), 'tragedy') and
                    not str(comment) in Cache.get('actions') and
                    not SequenceMatcher(None, Tragedy, CommentBody).ratio() > 0.66):
                    
                    # newline
                    print('')
                    # display id, body, author and match percentage of comment
                    print(comment)
                    print(CommentBody)
                    print(comment.author)
                    print(findt(CommentBody, 0))
                    # reply to comment
                    comment.reply(Tragedy)
                    # add comment to list of comments that have been replied to
                    log(comment)
                    # newline
                    print('')
            # countdown for new accounts with limited comments/minute
            except praw.exceptions.APIException as err:
                ErrorDetails = str(err)
                # get time till you can comment again from error details
                WaitTime = ErrorDetails[54:55]
                print('Wait ' + WaitTime + ' minutes to work.')
                Time = int(WaitTime)
                # display time remaining every minute
                for i in range(Time):
                    sleep(60)
                    Time -= 1
                    print(str(Time) + ' minute(s) left.')
            # generic error handler
            except:
                print('ERROR')
                # get error details and display them
                e = sys.exc_info()
                print(e)
    # handler for error thrown when connection resets
    except prawcore.exceptions.RequestException as err:
        print(str(err))
        print('Connection reset.')
