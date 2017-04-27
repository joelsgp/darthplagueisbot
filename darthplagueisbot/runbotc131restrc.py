import praw
import sys
from time import sleep
from os import environ
import bmemcached

#function to check percentage match
def findmatch(Text, Object, PercForMatch, WhichData):
    Text = Text.lower()
    Object = Object.lower()
    
    OWords = Object.split()
    
    PercPerWord = (1 / float(len(OWords))) * 100

    MatchPerc = 0
    for i in range(len(OWords)):
        if OWords[i] in Text:
            MatchPerc += PercPerWord

    if MatchPerc >= PercForMatch:
        Match = True
    else:
        Match = False

    if WhichData == 1:
        return Match
    else:
        return MatchPerc

def findt(Text, Type):
    Tragedy = 'Did you ever hear the tragedy of Darth Plagueis the wise'
    return findmatch(Text, Tragedy, 73, Type)

#initialise cache
Cache = bmemcached.Client(environ.get('MEMCACHEDCLOUD_SERVERS').split(','),
                          environ.get('MEMCACHEDCLOUD_USERNAME'),
                          environ.get('MEMCACHEDCLOUD_PASSWORD'))
#function to log activity to avoid duplicate comments
def log(ID):
    Cache.set('actions', Cache.get('actions') + [str(ID)])

#function to increment and output number of posts scanned so far
def progress():
    global Scanned
    Scanned += 1
    if Scanned % 10 == 0:
        print(str(Scanned) + ' comments scanned.')

#fetch details from environmental variables
BotA = {'ClientID': environ['ClientID'],
        'ClientSecret': environ['ClientSecret'],
        'Password': environ['Password'],
        'UserAgent': 'python3.6.1:darthplagueisbot:v1.3.1 (by /u/Sgp15)',
        'Username': environ['Username']}

#initialise reddit object with details
reddit = praw.Reddit(client_id = BotA['ClientID'],
                     client_secret = BotA['ClientSecret'],
                     password = BotA['Password'],
                     user_agent = BotA['UserAgent'],
                     username = BotA['Username'])

#active zone
subreddit = reddit.subreddit('PrequelMemes')

Tragedy = 'I thought not. It\'s not a story the Jedi would tell you. It\'s a Sith legend. Darth Plagueis was a Dark Lord of the Sith, so powerful and so wise he could use the Force to influence the midichlorians to create life... He had such a knowledge of the dark side that he could even keep the ones he cared about from dying. The dark side of the Force is a pathway to many abilities some consider to be unnatural. He became so powerful... the only thing he was afraid of was losing his power, which eventually, of course, he did. Unfortunately, he taught his apprentice everything he knew, then his apprentice killed him in his sleep. It\'s ironic he could save others from death, but not himself.'

#run bot
Scanned = 0
while True:
    for comment in subreddit.comments():
        try:
            if Scanned == 0:
                firstscanned = str(comment)
            progress()
            if str(comment) in Cache.get('lastscanned'):
                Cache.set('lastscanned', firstscanned)
                print('Ending iteration')
                exit()
            if findt(comment.body, 1) and not str(comment) in Cache.get('actions') and not findmatch(comment.body, Tragedy, 66, 1):
                print('')
                print(comment)
                print(comment.body)
                print(comment.author)
                print(findt(comment.body, 0))
                comment.reply(Tragedy)
                log(comment)
                print('')
        except praw.exceptions.APIException as err:
            ErrorDetails = str(err)
            WaitTime = ErrorDetails[54:55]
            print('Wait ' + WaitTime + ' minutes to work.')
            Time = int(WaitTime)
            for i in range(Time):
                sleep(60)
                Time -= 1
                print(str(Time) + ' minute(s) left.')
            
