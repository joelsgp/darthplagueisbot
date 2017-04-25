import praw
import sys
from winsound import Beep
from time import sleep

#function to check percentage match
def findmatch(Text, Object, PercForMatch, WhichData):
    Text = Text.lower()
    Object = Object.lower()
    
    OWords = Object.split()
    
    PercPerWord = (1 / len(OWords)) * 100

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

#function to log activity to avoid duplicate comments
def log(ID):
    with open('actions.txt', 'a+') as ActRecord:
        ActRecord.write('\n' + str(ID))

#function to increment and output number of posts scanned so far
def progress():
    global Scanned
    Scanned += 1
    if Scanned % 10 == 0:
        print(str(Scanned) + ' comments scanned.')
        Beep(125, 250)

#fetch details from file
File = open('details.txt', 'r')
Details = File.read()

BotA = {'ClientID': Details[Details.index('!')+1:Details.index('"')],
        'ClientSecret': Details[Details.index('£')+1:Details.index('$')],
        'Password': Details[Details.index('%')+1:Details.index('^')],
        'UserAgent': 'python3.6.1:darthplagueisbot:v1.3 (by /u/Sgp15)',
        'Username': Details[Details.index('&')+1:Details.index('*')]}

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
ActRecord = open('actions.txt', 'r')
Record = ActRecord.read()
while True:
    for comment in subreddit.stream.comments():
        try:
            progress()
            if findt(comment.body, 1) and not str(comment) in Record and not findmatch(comment.body, Tragedy, 73, 1):
                Beep(250, 250)
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
                Beep(250, 125)
        except:
            print('ERROR')
            e = sys.exc_info()
            print(e)
            
