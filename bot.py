import os
import sys
import time
import difflib
import logging

import praw
import prawcore
import bmemcached


logging.basicConfig(level=logging.INFO)
logging.getLogger('prawcore').disabled = True
logging.getLogger('bmemcached.protocol').disabled = True


__version__ = '2.1.1'


# TODO: add docstrings I guess if I want

SUBREDDIT_LIST = [
    'PrequelMemes',
    'controlmypc',
    'bottesting',
]
SUBREDDIT = '+'.join(SUBREDDIT_LIST)
USER_AGENT = f'python3.9.0:darthplagueisbot:v{__version__} (by /u/Sgp15)'

# phrase to reply to
TRIGGER = 'Did you ever hear the tragedy of Darth Plagueis the wise'
TRIGGER_ESSENTIAL_WORDS = ['plagueis', 'tragedy']
# phrase to reply with
TRAGEDY = "I thought not. It's not a story the Jedi would tell you. " \
          "It's a Sith legend. Darth Plagueis was a Dark Lord of the Sith, " \
          'so powerful and so wise he could use the Force to influence the midichlorians to create life... ' \
          'He had such a knowledge of the dark side that he could even keep the ones he cared about from dying. ' \
          'The dark side of the Force is a pathway to many abilities some consider to be unnatural. ' \
          'He became so powerful... the only thing he was afraid of was losing his power, which eventually, ' \
          'of course, he did. Unfortunately, he taught his apprentice everything he knew, ' \
          "then his apprentice killed him in his sleep. It's ironic he could save others from death, but not himself."

# TODO: hm maybe make this env var instead so it can be updated by cycling the program instead?
COMMENTS_SCANNED_LOG_INTERVAL = 100

# initialise cache using details in environment variables
MEMCACHE = bmemcached.Client(os.environ['MEMCACHEDCLOUD_SERVERS'].split(','),
                             os.environ['MEMCACHEDCLOUD_USERNAME'],
                             os.environ['MEMCACHEDCLOUD_PASSWORD'])


# function to search for specific words using difflib
def word_match(text, target_word, threshold=0.8):
    # split string into individual words
    text_words = text.split()
    # check each word
    for j in range(len(text_words)):
        # if word is more than 80% match, return 'True'
        if difflib.SequenceMatcher(a=target_word, b=text_words[j]).ratio() > threshold:
            return True


# function to search for a list of specific words using word_match
def all_words_match(text, target_words, threshold=0.8):
    for target_word in target_words:
        if not word_match(text, target_word, threshold):
            return False

    return True


# function to log activity to avoid duplicate comments
def log_comment_replied(comment_id):
    # add id to log
    # noinspection PyUnresolvedReferences
    MEMCACHE.set('actions', MEMCACHE.get('actions') + [comment_id])
    # add 1 to 'matches'
    MEMCACHE.incr('matches', 1)


# function to increment, output and log number of posts scanned so far
def incr_comments_counter(scanned, increment=1, interval=COMMENTS_SCANNED_LOG_INTERVAL):
    scanned += increment
    # if 'scanned' is a multiple of the interval, display it and record it to cache
    logging.debug(f'{scanned} comments scanned.')
    if scanned % interval == 0:
        logging.info(f'{scanned} comments scanned.')
        MEMCACHE.set('scanned', scanned)

    return scanned


# checks if a comment should be replied to
def check_comment(comment, match_ratio):
    # check for general match,
    # check for essential terms,
    # check comment is not the wrong phrase
    logging.debug(f'Match ratio: {match_ratio}')

    if match_ratio > 0.8:
        if all_words_match(comment.body.lower(), TRIGGER_ESSENTIAL_WORDS):
            if not difflib.SequenceMatcher(a=TRAGEDY, b=comment.body).ratio() > 0.66:
                return True
        else:
            logging.debug("Doesn't have essential words")
    else:
        logging.debug('Match ratio too low.')

    return False


def process_comment(comment, scanned):
    logging.debug('Scanning comment\n'
                  f'  id: {comment}\n'
                  f'  {comment.body}\n'
                  f'  user: {comment.author}')

    # increment 'comments checked' counter by 1
    scanned = incr_comments_counter(scanned)

    match_ratio = difflib.SequenceMatcher(a=TRIGGER, b=comment.body).ratio()
    if check_comment(comment, match_ratio):
        # check comment has not been replied to already
        if comment.id not in MEMCACHE.get('actions'):
            # display id, body, author and match percentage of comment
            logging.info('Comment matched\n'
                         f'  id: {comment}\n'
                         f'  {comment.body}\n'
                         f'  user: {comment.author}\n'
                         f'  match ratio: {round(match_ratio, 4)}')

            # reply to comment
            comment.reply(TRAGEDY)
            logging.info('Replied to comment.')
            # add comment to list of comments that have been replied to
            log_comment_replied(comment.id)
        else:
            logging.debug('Comment already replied to.')

    return scanned


# run bot
def main():
    scanned = MEMCACHE.get('scanned')

    # initialise reddit object with details from env vars
    reddit = praw.Reddit(client_id=os.environ['REDDIT_CLIENT_ID'],
                         client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                         password=os.environ['REDDIT_PASSWORD'],
                         user_agent=USER_AGENT,
                         username=os.environ['REDDIT_USERNAME'])
    logging.info('Logged in.')
    # which subreddit bot will be active in
    subreddit = reddit.subreddit(SUBREDDIT)

    try:
        # start reading comment stream
        for comment in subreddit.stream.comments():
            scanned = process_comment(comment, scanned)

    # countdown for new accounts with limited comments/minute
    except praw.exceptions.RedditAPIException as error:
        # get time till you can comment again, from error details
        wait_time = int(error.sleep_time)
        logging.error(f'Wait {wait_time} minutes to work.', exc_info=sys.exc_info())
        # display time remaining every minute
        for i in range(wait_time):
            time.sleep(60)
            wait_time -= 1
            logging.error(f'{wait_time} minute(s) left.')

    # handler for error thrown when connection resets
    except prawcore.exceptions.RequestException:
        logging.error('Request exception ', exc_info=sys.exc_info())
        logging.error('Connection reset.')


if __name__ == '__main__':
    main()
