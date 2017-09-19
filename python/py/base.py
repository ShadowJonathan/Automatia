import datetime
import json


def handler(x):
    import ffnet
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    elif isinstance(x, ffnet.search.Entry):
        return x.data
    raise TypeError("Unknown type")


class Notification:
    def __init__(self):
        self.messages = {'type': 'notification'}

    def post(self):
        print json.dumps(self.messages, default=handler)
