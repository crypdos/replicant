import markovify
from utils.customerrors import Busy, ModelAlreadyExists, ModelDoesntExist

class TextModel:
    def __init__(self, bot):
        self.bot = bot
        self.name = None
        self.authorid = None
        self.model = None
        self.busy = False

    async def create_discord_model(self, authorid, name):
        if self.busy:
            raise Busy
        self.busy = True
        if self.authorid == authorid:
            self.busy = False
            raise ModelAlreadyExists
        self.name = name
        self.authorid = authorid
        wordlist = ""
        for (coll, serverid) in self.bot._cfg.items('scrapeservers'):
            query = self.bot._db[coll].find({"author_id" : authorid}, {"_id": 0, "content": 1})
            async for doc in query:
                wordlist += doc['content'] + '\n'
        self.model = markovify.NewlineText(wordlist)
        print("Done creating model")
        self.busy = False

    async def create_forum_model(self, authorid, name):
        if self.busy:
            raise Busy
        self.busy = True
        if self.authorid == authorid:
            self.busy = False
            raise ModelAlreadyExists
        self.name = name
        self.authorid = authorid
        wordlist = ""
        for forum in self.bot._cfg.get("scrapeforums", "forums").split(','):
            query = self.bot._db[forum].find({"user_id" : int(authorid)}, {"_id": 0, "content": 1})
            async for doc in query:
                wordlist += doc['content'] + '\n'
        self.model = markovify.NewlineText(wordlist)
        print(f"Done creating model {name}")
        self.busy = False

    async def make_sentence(self, beginning = None):
        if not self.model:
            raise ModelDoesntExist
        if not beginning:
            return self.model.make_sentence(tries=1000)
        try:
            sentence = self.model.make_sentence_with_start(beginning, tries=1000)
            if sentence:
                return sentence
            else:
                return self.model.make_sentence(tries=1000)
        except KeyError: # beginword not found
            return self.model.make_sentence(tries=1000)

