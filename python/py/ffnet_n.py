from base import Notification


class ffnet_notify(Notification):
    def __init__(self):
        Notification.__init__(self)
        self.messages['orig'] = "ffnet"
        self.progress_prefix = ''

    def accepted(self):
        self.messages['accepted'] = True
        return self

    def fail(self, reason, fail_code=-1):
        self.messages['failed'] = True
        self.messages['fail_reason'] = reason
        self.messages['fail_code'] = fail_code
        self.messages['type'] = 'error'
        return self

    def shadow(self, story_id):
        self.messages['shadow_id'] = str(story_id)
        return self

    def progress_init(self, total, prefix='chap'):
        self.messages['_progress_name'] = prefix
        self.messages['_total'] = total
        self.messages['_current'] = None
        return self

    def progress(self, num):
        self.messages['_current'] = num
        return self

    def end(self, file_name):
        self.messages['finished'] = True
        self.messages['file_name'] = file_name
        return self

    def meta(self, data):
        self.messages['meta'] = data
        return self


class ffnet_archive(ffnet_notify):
    def __init__(self):
        ffnet_notify.__init__(self)
        self.messages['sub_orig'] = 'archive'

    def done(self):
        self.messages['done'] = True
        return self

    def dump(self, data):
        self.messages['dump'] = True
        self.messages['file_path'] = data[0]
        self.messages['latest_refresh'] = data[1]
        return self

    def info(self, initialised=False, earliest=None, latest=None, amount=None):
        self.messages['initialised'] = initialised
        self.messages['earliest'] = earliest
        self.messages['latest'] = latest
        self.messages['amount'] = amount
        return self

    def archive_index(self, results):
        self.messages['data'] = [{'name': e[0], 'len': e[1], 'url': e[2]} for e in results]
        return self
