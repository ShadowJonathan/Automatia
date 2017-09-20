from base import Notification


class ffnet_notify(Notification):
    def __init__(self):
        Notification.__init__(self)
        self.messages['orig'] = "ffnet"

    def accepted(self):
        self.messages['accepted'] = True
        return self

    def fail(self, reason, fail_code=-1):
        self.messages['failed'] = True
        self.messages['fail_reason'] = reason
        self.messages['fail_code'] = fail_code
        return self

    def shadow(self, story_id):
        self.messages['shadow_id'] = str(story_id)
        return self

    def progress_init(self, total):
        self.messages['chap_total'] = total
        self.messages['chap_current'] = None
        return self

    def progress(self, chap):
        self.messages['chap_current'] = chap
        return self

    def end(self, file_name):
        self.messages['finished'] = True
        self.messages['file_name'] = file_name
        return self

    def meta(self, data):
        self.messages['meta'] = data
        return self
