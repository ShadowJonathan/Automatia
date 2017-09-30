import run as story
import re
import logging
import urllib
import bs4
from datetime import datetime, timedelta
import json
import py
import exc
import os
import pytz
from dateutil.tz import tzlocal
import dateutil.parser

now = lambda: datetime.utcnow().replace(tzinfo=tzlocal())

logger = logging.getLogger(__name__)


class InvalidCategory(Exception):
    def __init__(self, cat):
        self.cat = cat

    def __str__(self):
        return "Catagory Invalid: %s" % self.cat


VALID_CATAGORIES = [
    ("Anime/Manga", 'anime', 'manga'),
    ("Misc", 'misc'),
    ("Books", 'books', 'book'),
    ("Movies", 'movies', 'movie'),
    ("Cartoons", 'cartoons', 'cartoon'),
    ("Plays/Musicals", 'plays', 'musicals', 'play'),
    ("Comics", 'comics', 'comic'),
    ("TV Shows", 'tv', 'tv shows'),
    ("Games", 'games', 'game'),
]

CAT2URL = {
    "Anime/Manga": 'anime',
    "Books": 'book',
    "Cartoons": 'cartoon',
    "Games": 'game',
    "Misc": 'misc',
    "Plays/Musicals": 'play',
    "Movies": 'movie',
    "TV Shows": 'tv'
}

_downloader = story.WebClient()


def conv(number):
    m = re.search(r'([\d.]+)K$', number)
    if m:
        return int(float(m.group(1)) * 1000)
    else:
        return int(number.replace(',', ''))


def Valid_category(name):
    for cat_t in VALID_CATAGORIES:
        if name.lower() in cat_t:
            return cat_t[0]
    return False


def Url_category(name):
    if not Valid_category(name):
        return False
    else:
        for cat_t in VALID_CATAGORIES:
            if name.lower() in cat_t:
                return cat_t[1]


def SmartGetAllArchives(category):
    path = os.path.dirname(os.path.realpath(__file__)) + '/cache/' + category + '/meta.json'
    # print path
    try:
        os.makedirs(os.path.dirname(path))
    except:
        pass
    h = JSONHandler(path)
    if h.data.get('last_updated'):
        h.data['last_updated'] = make_datetime(h.data.get('last_updated'))
    if len(h.data) < 1 or not h.data.get('last_updated'):
        h.process({'archives': GetAllArchives(category), 'last_updated': now()})
        h.save()
    elif h.data.get('last_updated') < now() - timedelta(days=7):
        h.process({'archives': GetAllArchives(category), 'last_updated': now()})
        h.save()
    return h.data['archives']


def GetAllArchives(catagory, crossover=False):
    cat = Valid_category(catagory)
    if cat is False:
        raise InvalidCategory(catagory)
    _, soup = _downloader.get('http://www.fanfiction.net/' + (crossover and 'crossovers/' or '') + CAT2URL[cat] + "/")
    entries = soup.select("#list_output div")
    E = []
    logger.debug("Processing %d entries..." % len(entries))
    for e in entries:
        E.append((
            e.select('a')[0].string,
            conv(e.select('span.gray')[0].string.replace('(', '').replace(')', '')),
            e.select('a')[0]['href']
        ))
    return E


def handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    elif isinstance(x, Entry):
        return x.data
    raise TypeError("Unknown type")


def make_datetime(json_date):
    try:
        return datetime.strptime(json_date, '%Y-%m-%dT%H:%M:%S.%fZ')
    except:
        pass
    try:
        return datetime.strptime(json_date, '%Y-%m-%dT%H:%M:%S.%f')
    except:
        pass
    try:
        return datetime.strptime(json_date, '%Y-%m-%dT%H:%M:%S')
    except:
        pass
    return dateutil.parser.parse(json_date)


class JSONHandler:
    def __init__(self, file_name):
        self.file_name = file_name
        try:
            with open(file_name) as data_file:
                self.data = json.load(data_file)
        except:
            self.data = {}

    def process(self, data):
        for k, v in data.items():
            self.data[k] = v

    def save(self):
        with open(self.file_name, 'w+') as outfile:
            outfile.write(json.dumps(self.data, default=handler))


class SearchArgs:
    def __init__(self, characters):
        self.args = {}
        self.chars = characters

    def Page(self, number):
        if number is None:
            try:
                del self.args['p']
            except:
                pass
        else:
            self.args['p'] = number

    def Clear(self):
        self.args = {}

    def Quick_Fav(self):
        self.Clear()
        self.Sort(4)

    def Quick_Follow(self):
        self.Clear()
        self.Sort(5)

    def Quick_Review(self):
        self.Clear()
        self.Sort(3)

    # srt =              Sort       [5]
    # t =                Time Range [11] (12)
    # g(1-2) / _g1 =    genre      [22]
    # lan =              Language   [dyn]
    # r =                Rating     [7]  (8)
    # len =              Length     [10]
    # s =                Status     [3]
    # c(1-4) / _c(1-2) = Character  [dyn]
    # v1 =               Custom     [dyn]
    def Sort(self, val):
        """
        1: Update Date (default)
        2: Publish Date
        3: Reviews
        4: Favs
        5: Follows

        :param val:
        :return:
        """
        self.args['srt'] = val

    def Time_Range(self, val):
        """
        0: All (default)
        1: U - 24H
        2: U - 1 Week
        3: U - 1 Month
        4: U - 6 Months
        5: U - 1 Year

        11: P - 24H
        12: P - 1 Week
        13: P - 1 Month
        14: P - 6 Months
        15: P - 1 Year

        :param val:
        :return:
        """
        self.args['t'] = val

    def Genre(self, val, index=1, negative=False):
        """
        0: All (default)
        6: Adventure
        10: Angst
        18: Crime
        4: Drama
        19: Family
        14: Fantasy
        21: Friendship
        1: General
        8: Horror
        3: Humor
        20: Hurt/comfort
        7: Mystery
        9: Parody
        5: Poetry
        2: Romance
        13: Sci-Fi
        15: Supernatural
        12: Suspense
        16: Tragedy
        17: Western

        :param val:
        :param index:
        :param negative:
        :return:
        """
        if negative:
            if index > 1:
                raise IndexError
        else:
            if index > 2:
                raise IndexError
        self.args['%sg%d' % (negative and "_" or "", index)] = val

    def Rating(self, val):
        """
        10: All
        103: K -> T (default)
        102: K -> K+
        1: K
        2: K+
        3: T
        4: M

        :param val:
        :return:
        """
        self.args['r'] = val

    def Language(self, val):
        pass

    def Character(self, val, index=1, negative=False):
        """
        0: All (default)
        dyn: Character

        :param val:
        :param index:
        :param negative:
        :return:
        """
        if negative:
            if index > 2:
                raise IndexError
        else:
            if index > 4:
                raise IndexError
        self.args['%sc%d' % (negative and "_" or "", index)] = val

    def Characters(self):
        return self.chars


class Entry:
    def __init__(self, soup, data=None):
        if data:
            self.data = data
            self.data['last_refreshed'] = make_datetime(self.data['last_refreshed'])
            if self.data.get('updated'):
                self.data['updated'] = make_datetime(self.data['updated'])
            self.data['published'] = make_datetime(self.data['published'])
            return

        self.data = {
            'title': [St for St in soup.select('a.stitle')[0].stripped_strings][0],
            'url': 'http://www.fanfiction.net' + soup.select('a.stitle')[0]['href'],
            'summary': [St for St in soup.select('div.z-padtop')[0].stripped_strings][0],
            'genre': [],
            'reviews': 0,
            'favs': 0,
            'follows': 0,
            'completed': False,
            'characters': [],
            'ships': [],
        }
        self.soup = soup

        rer = re.compile(r'(?:(?:www|m)\.fanfiction\.net/s/)?(\d+)(?:/\d+)?', re.I).search(self.data['url'])
        if not rer:
            raise story.exc.RegularExpresssionFailed('(?:www|m)\.fanfiction\.net/s/(\d+)(?:/(\d+))?', self.data['url'])
        self.data['storyID'] = self.storyID = self.ID = rer.group(1)

        a = soup.find('a', href=re.compile(r"^/u/\d+"))
        self.data['authorId'] = a['href'].split('/')[2]
        self.data['authorUrl'] = 'https://www.fanfiction.net' + a['href']
        self.data['author'] = a.string

        info = soup.select('.z-padtop2.xgray')[0].decode_contents(formatter="html").split(' - ')

        try:
            # Rating
            rating = info[0]
            if 'Rated:' in rating:
                rating = rating[7:]
            self.data['rating'] = rating

            info.pop(0)

            # Language
            self.data['language'] = info[0]
            self.data['langcode'] = story.langs[info[0]] or None

            info.pop(0)

            # Genres
            info[0] = info[0].replace('Hurt/Comfort', 'Hurt-Comfort')
            genrelist = info[0].split('/')  # Hurt/Comfort already changed above.
            goodgenres = True
            for g in genrelist:
                if g.strip() not in story.ffnetgenres:
                    if "Chapters" not in g:
                        logger.warn(g + " not in ffnetgenres")
                    goodgenres = False
            if goodgenres:
                self.data['genre'].extend(genrelist)
                info.pop(0)

            # Chapters
            self.data['chapters'] = int(info[0][10:])

            info.pop(0)

            # Words
            self.data['words'] = int(info[0][7:].replace(',', ''))

            info.pop(0)

            # Follow, Review, Fav
            hasFFFleft = lambda: \
                "Reviews" in info[0] \
                or "Favs" in info[0] \
                or "Follows" in info[0]

            while hasFFFleft():
                if "Reviews" in info[0]:
                    self.data['reviews'] = int(info[0][9:].replace(',', ''))
                elif "Favs" in info[0]:
                    self.data['favs'] = int(info[0][6:].replace(',', ''))
                elif "Follows" in info[0]:
                    self.data['follows'] = int(info[0][9:].replace(',', ''))
                info.pop(0)

            # Updated, Published
            if "Updated" in info[0]:
                self.data['updated'] = datetime.fromtimestamp(
                    float(bs4.BeautifulSoup(info[0], 'html5lib').select('span')[0]['data-xutime']),
                    pytz.utc)
                info.pop(0)

            self.data['published'] = datetime.fromtimestamp(
                float(bs4.BeautifulSoup(info[0], 'html5lib').select('span')[0]['data-xutime']),
                pytz.utc)
            info.pop(0)

            # Characters
            if info and "Complete" not in info[0]:
                chars_ships_text = info[0]
                self.data['characters'].extend(
                    filter(lambda x: not not x,
                           [s.strip() for s in chars_ships_text.replace('[', '').replace(']', ',').split(',')]))
                l = chars_ships_text
                while '[' in l:
                    self.data['ships'].append(l[l.index('[') + 1:l.index(']')].replace(', ', '/'))
                    l = l[l.index(']') + 1:]
                info.pop(0)

            # Complete
            if info:
                if "Complete" in info[0]:
                    self.data['completed'] = True
                else:
                    logger.warn("\"" + info[0] + "\" unknown.")
                    if len(info) > 1:
                        logger.warn("\"" + info + "\", much more than possible.")
                info.pop(0)

            self.data['last_refreshed'] = now()
        except ValueError, v:
            logger.error("VALUE ERROR: " + str(v) + " WITH " + info[0])
            import traceback
            traceback.print_exc()


class EntryList(dict):
    def __init__(self, f=None):
        if f:
            for k, v in f.items():
                f[k] = Entry(None, data=v)
        dict.__init__(self, f or [])

    def _make_list(self):
        l = list()
        for v in self.values():
            l.append(v)
        return l

    def _get_sorted(self, key):
        l = self._make_list()
        l.sort(key=key, reverse=True)
        return l

    def Get_Favs(self):
        return self._get_sorted(lambda e: e.data['favs'])

    def Get_Follows(self):
        return self._get_sorted(lambda e: e.data['follows'])

    def Get_Reviews(self):
        return self._get_sorted(lambda e: e.data['reviews'])

    def Latest_Updated(self):
        l = self._make_list()
        if not l:
            return now()
        l.sort(key=lambda x: x.data.get('updated') or x.data['published'], reverse=True)
        return l[0].data.get('updated') or l[0].data['published']

    def Earliest_Updated(self):
        l = self._make_list()
        if not l:
            return now()
        l.sort(key=lambda x: x.data.get('updated') or x.data['published'])
        return l[0].data.get('updated') or l[0].data['published']

    def Latest_Refresh(self):
        l = self._make_list()
        if not l:
            return now()
        l.sort(key=lambda x: x.data.get('last_refresh'), reverse=True)
        return l[0].data.get('last_refresh')

    def Earliest_Refresh(self):
        l = self._make_list()
        if not l:
            return now()
        l.sort(key=lambda x: x.data.get('last_refresh'))
        return l[0].data.get('last_refresh')


Affected = []


class Archive(story.WebClient):
    @staticmethod
    def _get_chars(soup):
        chars = []
        ets = soup.select('select[name=characterid1] > option')
        for e in ets:
            chars.append((e['value'], e.string))
        return chars

    @staticmethod
    def dump_cache(category, archive):
        path = os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + '/cache/' + category + '/' + archive + \
                                '.json')
        # print path
        try:
            cache = JSONHandler(path)
        except Exception, e:
            raise Exception("Cannot get JSON file, this probably doesnt exist: " + str(e))
        return path, EntryList(cache.data).Latest_Refresh()

    @staticmethod
    def info(category, archive):
        path = os.path.dirname(os.path.realpath(__file__)) + '/cache/' + category + '/' + archive + \
               '.json'
        if os.path.exists(path):
            cache = EntryList(JSONHandler(path).data)
            al = GetAllArchives(category)
            meta = al[next(index for (index, d) in enumerate(al) if archive.lower() in d[2].lower())]
            py.ffnet_archive().info(True, category, archive, cache.Earliest_Updated(), cache.Latest_Updated(),
                                    len(cache), meta).post()
        else:
            py.ffnet_archive().info(False, category, archive).post()

    @staticmethod
    def get_stamps(category):
        h = JSONHandler(os.path.dirname(os.path.realpath(__file__)) + '/cache/' + category + '/meta.json')
        return h.data.get('stamps')

    def __init__(self, url):
        story.WebClient.__init__(self)
        self.url = 'https://www.fanfiction.net' + (url[0] != '/' and '/' or '') + str(url)
        data, self.soup = self.get(self.url)
        if 'The page you are looking for does not exist' in data:
            raise exc.ArchiveDoesNotExist(self.url)
        rer = re.search(r'www.fanfiction.net/(\w+?)/(.+?)/', self.url)
        self.category = rer.group(1)
        self.archive_name = rer.group(2)
        self.characters = self._get_chars(self.soup)
        self.args = SearchArgs(self.characters)
        self.entries = EntryList()

    def _get_url_plus_args(self, page=None):
        self.args.Page(page)
        return self.url + "?" + urllib.urlencode(self.args.args)

    def _convert_entries(self, soup):
        for e in soup.select('#content_wrapper_inner > div.z-list.zhover.zpointer'):
            entry = Entry(e)
            self.entries[entry.ID] = entry
            global Affected
            Affected.append(entry.ID)

    def _get_first(self, pages=1):
        for x in range(0, pages):
            logger.debug("Getting page %d of %d" % (x + 1, pages))
            self._get_page(self._get_url_plus_args(x or None))

    def _get_all(self, limit=None):
        count = None
        limit = limit or 20
        n = py.ffnet_archive()
        r = self.args.args.get('r')
        if r and (r == 10 or r == 4):
            _, soup = self.get(self.url + '?r=10')
        else:
            soup = self.soup
        for e in soup.select('#content_wrapper_inner > center > a'):
            if e.string == 'Last':
                count = int(re.search(r'p=(\d+)', e['href']).group(1))
                break
        count = count and count < limit and count or limit
        n.progress_init(count, 'page')
        for x in range(0, count):
            logger.debug("Getting page %d of %d" % (x + 1, count))
            self._get_page(x or None)
            n.progress(x).post()

    def _get_page(self, page):
        _, soup = self.get(self._get_url_plus_args(page))
        self._convert_entries(soup)

    def _get_till(self, time):
        i = 1
        while True:
            self._get_page(i)
            i += 1
            print self.entries.Earliest_Updated(), time
            if self.entries.Earliest_Updated() <= time:
                return

    def _get_cache(self):
        path = os.path.dirname(os.path.realpath(__file__)) + '/cache/' + self.category + '/' + self.archive_name + \
               '.json'
        # print path
        try:
            os.makedirs(os.path.dirname(path))
        except:
            pass
        return JSONHandler(path)

    def _meta_update(self):
        path = os.path.dirname(os.path.realpath(__file__)) + '/cache/' + self.category + '/meta.json'
        h = JSONHandler(path)
        if not h.data.get('stamps'):
            h.data['stamps'] = {}
        h.data['stamps'][self.archive_name] = now()
        h.save()

    def _show_affected(self):
        global Affected
        py.ffnet_archive().affected(Affected).post()

    def update(self, limit=None, show_affected=False):
        cache = self._get_cache()
        self._get_all(limit)
        cache.process(self.entries)
        cache.save()
        self._meta_update()
        if show_affected:
            self._show_affected()

    def refresh(self, ALL=False, show_affected=False):
        cache = self._get_cache()
        l = EntryList(cache.data)
        if ALL:
            self._get_till(l.Earliest_Updated())
        else:
            self._get_till(l.Latest_Updated())
        cache.process(self.entries)
        cache.save()
        self._meta_update()
        if show_affected:
            self._show_affected()
