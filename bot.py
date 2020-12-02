import os
import time
import difflib

import praw
import prawcore
import bmemcached


# TODO: switch from print to logging

# constants
# SUBREDDIT = 'PrequelMemes'
SUBREDDIT = 'bottesting'
USER_AGENT = 'python3.9.0:darthplagueisbot:v2.0.0 (by /u/Sgp15)'

# phrase to reply to
TRIGGER = 'Did you ever hear the tragedy of Darth Plagueis the wise'
# phrase to reply with
TRAGEDY = "I thought not. It's not a story the Jedi would tell you. " \
          "It's a Sith legend. Darth Plagueis was a Dark Lord of the Sith, " \
          'so powerful and so wise he could use the Force to influence the midichlorians to create life... ' \
          'He had such a knowledge of the dark side that he could even keep the ones he cared about from dying. ' \
          'The dark side of the Force is a pathway to many abilities some consider to be unnatural. ' \
          'He became so powerful... the only thing he was afraid of was losing his power, which eventually, ' \
          'of course, he did. Unfortunately, he taught his apprentice everything he knew, ' \
          "then his apprentice killed him in his sleep. It's ironic he could save others from death, but not himself."

# initialise cache using details in environment variables
MEMCACHE = bmemcached.Client(os.environ['MEMCACHEDCLOUD_SERVERS'].split(','),
                             os.environ['MEMCACHEDCLOUD_USERNAME'],
                             os.environ['MEMCACHEDCLOUD_PASSWORD'])


# function to search for the phrase
def find_in_text(text, behaviour, trigger=TRIGGER):

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


# function to log activity to avoid duplicate comments
def log(comment_id):
    # add id to log
    MEMCACHE.set('actions', MEMCACHE.get('actions').append(comment_id))
    # add 1 to 'matches'
    MEMCACHE.incr('matches', 1)


# function to increment, output and log number of posts scanned so far
def progress(scanned_current):
    scanned_current += 1
    # if 'scanned' is a multiple of 10, display it and record it to cache
    if scanned_current % 100 == 0:
        print(str(scanned_current) + ' comments scanned.')
        MEMCACHE.set('scanned', scanned_current)

    return scanned_current


scanned = MEMCACHE.get('scanned')

# initialise reddit object with details from env vars
reddit = praw.Reddit(client_id=os.environ['REDDIT_CLIENT_ID'],
                     client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                     password=os.environ['REDDIT_PASSWORD'],
                     user_agent=USER_AGENT,
                     username=os.environ['REDDIT_USERNAME'])
print('logged in')
# which subreddit bot will be active in
subreddit = reddit.subreddit(SUBREDDIT)


# run bot
while True:
    try:
        # start reading comment stream
        for comment in subreddit.stream.comments():
            try:
                # increment 'comments checked' counter by 1
                # noinspection PyTypeChecker
                progress(scanned)
                # check for general match,
                # check for essential terms,
                # check comment has not been replied to already,
                # check comment is not the wrong phrase
                if (find_in_text(comment.body, 1) and
                        word_match(comment.body.lower(), 'plagueis') and
                        word_match(comment.body.lower(), 'tragedy') and
                        not str(comment) in MEMCACHE.get('actions') and
                        not difflib.SequenceMatcher(None, TRAGEDY, comment.body).ratio() > 0.66):
                    # display id, body, author and match percentage of comment
                    print('\n'
                          f'id: {comment}\n'
                          f'{comment.body}\n'
                          f'user: {comment.author}\n'
                          f'match ratio: {find_in_text(comment.body, 0)}\n')

                    # reply to comment
                    comment.reply(TRAGEDY)
                    # add comment to list of comments that have been replied to
                    log(comment)

            # countdown for new accounts with limited comments/minute
            except praw.exceptions.RedditAPIException as err:
                error_details = str(err)
                # get time till you can comment again from error details
                wait_time = int(error_details[54:55])
                print(f'Wait {wait_time} minutes to work.')
                # display time remaining every minute
                for i in range(wait_time):
                    time.sleep(60)
                    wait_time -= 1
                    print(f'{wait_time} minute(s) left.')

    # handler for error thrown when connection resets
    except prawcore.exceptions.RequestException as err:
        print(str(err))
        print('Connection reset.')
