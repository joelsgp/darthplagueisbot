import asyncio
import os
import sys
import time
import difflib
import logging
from typing import Optional

import aiosqlite
import dotenv
import asyncpraw
import asyncpraw.models
import asyncprawcore


__version__ = '3.0.0b'


# todo: if someone replies to a bot message with 'is it possible to learn this power', answer 'not from a jedi'


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout
)
logging.getLogger('prawcore').disabled = True


DB_PATH = 'dpbot.db'
SUBREDDIT_LIST = (
    'PrequelMemes',
    'controlmypc',
    'bottesting',
)
SUBREDDIT = '+'.join(SUBREDDIT_LIST)
PYTHON_VERSION = sys.version.split()[0]
USER_AGENT = f'python{PYTHON_VERSION}:darthplagueisbot:v{__version__} (by /u/Sgp15)'

# phrase to reply to
TRIGGER = 'Did you ever hear the tragedy of Darth Plagueis the wise'
TRIGGER_ESSENTIAL_WORDS = ['plagueis', 'tragedy']
# phrase to reply with
TRAGEDY = """\
I thought not. It's not a story the Jedi would tell you.
It's a Sith legend. Darth Plagueis was a Dark Lord of the Sith, 
so powerful and so wise he could use the Force to influence the midichlorians to create life... 
He had such a knowledge of the dark side that he could even keep the ones he cared about from dying. 
The dark side of the Force is a pathway to many abilities some consider to be unnatural. 
He became so powerful... the only thing he was afraid of was losing his power, which eventually, 
of course, he did. Unfortunately, he taught his apprentice everything he knew, 
then his apprentice killed him in his sleep. It's ironic - he could save others from death, but not himself.\
"""

if os.environ.get('COMMENTS_SCANNED_LOG_INTERVAL'):
    COMMENTS_SCANNED_LOG_INTERVAL = int(os.environ.get('COMMENTS_SCANNED_LOG_INTERVAL'))
else:
    COMMENTS_SCANNED_LOG_INTERVAL = 100


# function to search for specific words using difflib
def word_match(text, target_word, threshold=0.8):
    # split string into individual words
    text_words = text.split()
    # check each word
    for j in range(len(text_words)):
        # if word is more than 80% match, return 'True'
        if difflib.SequenceMatcher(a=target_word, b=text_words[j]).ratio() > threshold:
            return True

    return False


# function to search for a list of specific words using word_match
def all_words_match(text, target_words, threshold=0.8):
    for target_word in target_words:
        if not word_match(text, target_word, threshold):
            return False

    return True


class DarthPlagueisBot:
    scanned: int
    matches: int

    def __init__(self):
        self.loop = True
        self.db: Optional[aiosqlite.Connection] = None

    async def on_ready(self):
        self.db = await aiosqlite.connect(DB_PATH)

        init_db = """
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS scanned (
            count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS matches (
            count INTEGER DEFAULT 0
        );
"""
        await self.db.execute(init_db)
        await self.db.commit()

        async with self.db.execute('SELECT count FROM scanned; SELECT count FROM mathes;') as cur:
            rows = await cur.fetchall()
            self.scanned = rows[0]
            self.matches = rows[1]

    async def close(self):
        if self.db is not None:
            await self.db.close()

    # function to log activity to avoid duplicate comments
    def log_comment_replied(self, comment_id: int):
        # add id to log
        await self.db.execute('INSERT INTO actions VALUES (?)', (comment_id,))
        # add 1 to 'matches'
        self.matches += 1
        await self.db.execute('UPDATE matches SET count=?', (self.matches,))
        await self.db.commit()

    def comment_already_actioned(self, comment_id: int) -> bool:
        async with self.db.execute('SELECT * FROM actions WHERE id=?', (comment_id,)) as cur:
            row = cur.fetchone()
        return bool(row)

    # function to increment, output and log number of posts scanned so far
    def incr_comments_counter(self, increment: int = 1, interval: int = COMMENTS_SCANNED_LOG_INTERVAL):
        self.scanned += increment
        # if 'scanned' is a multiple of the interval, display it and record it to cache
        logging.debug(f'%s comments scanned.', self.scanned)
        if self.scanned % interval == 0:
            logging.info(f'{self.scanned} comments scanned.')
            await self.db.execute('UPDATE scanned SET count=?', (self.scanned,))
            await self.db.commit()

    # checks if a comment should be replied to
    @staticmethod
    def check_comment(comment, match_ratio) -> bool:
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

    def process_comment(self, comment: asyncpraw.models.Comment):
        logging.debug('Scanning comment\n'
                      f'  id: {comment}\n'
                      f'  {comment.body}\n'
                      f'  user: {comment.author}')

        # increment 'comments checked' counter by 1
        self.incr_comments_counter()

        match_ratio = difflib.SequenceMatcher(a=TRIGGER, b=comment.body).ratio()
        if self.check_comment(comment, match_ratio):
            # check comment has not been replied to already
            if not self.comment_already_actioned(comment.id):
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
                self.log_comment_replied(comment.id)
            else:
                logging.debug('Comment already replied to.')

    async def start(self):
        await self.on_ready()

        # initialise reddit object with details from env vars
        reddit = asyncpraw.Reddit(
            client_id=os.environ['REDDIT_CLIENT_ID'],
            client_secret=os.environ['REDDIT_CLIENT_SECRET'],
            password=os.environ['REDDIT_PASSWORD'],
            user_agent=USER_AGENT,
            username=os.environ['REDDIT_USERNAME']
        )
        logging.info('Logged in.')
        # which subreddit bot will be active in
        subreddit = await reddit.subreddit(SUBREDDIT)

        try:
            # start reading comment stream
            async for comment in subreddit.stream.comments():
                self.process_comment(comment)
                if not self.loop:
                    break

        # countdown for new accounts with limited comments/minute
        except asyncpraw.exceptions.RedditAPIException as error:
            # get time till you can comment again, from error details
            wait_time = int(error.sleep_time)
            logging.exception(f'Wait {wait_time} minutes to work.')
            # display time remaining every minute
            for i in range(wait_time):
                time.sleep(60)
                wait_time -= 1
                logging.error(f'{wait_time} minute(s) left.')

        # handler for error thrown when connection resets
        except asyncprawcore.exceptions.RequestException:
            logging.exception('Request exception.')
            logging.error('Connection reset.')

        except asyncprawcore.exceptions.ServerError:
            logging.exception('Reddit server error.')

    def run(self):
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            self.loop = False
            asyncio.create_task(self.close())


def main():
    dotenv.load_dotenv()
    bot = DarthPlagueisBot()
    bot.run()


if __name__ == '__main__':
    main()
