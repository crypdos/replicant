class NotEnoughMessages(Exception):
    def __init__(self, username,msgcount, cutoff):
        self.username = username
        self.msgcount = msgcount
        self.cutoff = cutoff

class ModelAlreadyExists(Exception):
    pass

class ModelDoesntExist(Exception):
    pass

class Busy(Exception):
    pass

class AlreadyScraping(Exception):
    pass