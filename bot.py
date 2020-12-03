import os
import time
import difflib

import asyncpraw
import asyncprawcore
import bmemcached


__version__ = '2.1.0'


# TODO: switch from print to logging?

SUBREDDIT_LIST = [
    'PrequelMemes',
    'bottesting',
    'controlmypc',
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
def incr_comments_counter(scanned, increment=1):
    scanned += increment
    # if 'scanned' is a multiple of 10, display it and record it to cache
    if scanned % 100 == 0:
        print(str(scanned) + ' comments scanned.')
        MEMCACHE.set('scanned', scanned)

    return scanned


# checks if a comment should be replied to
def check_comment(comment, match_ratio):
    # check for general match,
    # check for essential terms,
    # check comment is not the wrong phrase
    if match_ratio > 0.8:
        if all_words_match(comment.body.lower(), TRIGGER_ESSENTIAL_WORDS):
            if not difflib.SequenceMatcher(a=TRAGEDY, b=comment.body).ratio() > 0.66:
                return True
    else:
        return False


async def process_comment(comment, scanned):
    # increment 'comments checked' counter by 1
    await incr_comments_counter(scanned)

    # check comment has not been replied to already
    if comment.id not in MEMCACHE.get('actions'):
        match_ratio = difflib.SequenceMatcher(a=TRIGGER, b=comment.body).ratio()

        if check_comment(comment, match_ratio):
            # display id, body, author and match percentage of comment
            print('\n'
                  f'id: {comment}\n'
                  f'{comment.body}\n'
                  f'user: {comment.author}\n'
                  f'match ratio: {match_ratio}\n')

            # reply to comment
            await comment.reply(TRAGEDY)
            # add comment to list of comments that have been replied to
            log_comment_replied(comment.id)

    return scanned


# run bot
def main():
    scanned = MEMCACHE.get('scanned')

    # initialise reddit object with details from env vars
    reddit = asyncpraw.Reddit(client_id=os.environ['REDDIT_CLIENT_ID'],
                              client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                              password=os.environ['REDDIT_PASSWORD'],
                              user_agent=USER_AGENT,
                              username=os.environ['REDDIT_USERNAME'])
    print('logged in')
    # which subreddit bot will be active in
    subreddit = await reddit.subreddit(SUBREDDIT)

    try:
        # start reading comment stream
        async for comment in subreddit.stream.comments():
            scanned = await process_comment(comment, scanned)

    # countdown for new accounts with limited comments/minute
    except asyncpraw.exceptions.RateLimitExceeded as error:
        # get time till you can comment again, from error details
        wait_time = int(error.sleep_time)
        print(f'Wait {wait_time} minutes to work.')
        # display time remaining every minute
        for i in range(wait_time):
            time.sleep(60)
            wait_time -= 1
            print(f'{wait_time} minute(s) left.')

    # handler for error thrown when connection resets
    except asyncprawcore.exceptions.RequestException as error:
        print(str(error))
        print('Connection reset.')


if __name__ == '__main__':
    main()
