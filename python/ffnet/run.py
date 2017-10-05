# -*- coding: utf-8 -*-
try:
    import sys
    import os

    sys.path.insert(0, os.path.abspath('..'))
    sys.path.insert(0, os.path.abspath('.'))
    sys.path.insert(0, os.path.abspath('./python'))
except:
    pass
import copy
import logging
import re
import time
import urllib
import urllib2
from datetime import datetime

import exc
from EPUB import EpubWriter
from gziphttp import GZipProcessor
from htmlcleanup import stripHTML
from py import ffnet_notify
import urlparse as up
import cookielib as cl
import HtmlTagStack as stack
import sys
import bs4
import pytz

DEBUG = False

logger = logging.getLogger(__name__)

try:
    import chardet
except ImportError:
    chardet = None

ffnetgenres = ["Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy", "Friendship", "General",
               "Horror", "Humor", "Hurt-Comfort", "Mystery", "Parody", "Poetry", "Romance", "Sci-Fi",
               "Spiritual", "Supernatural", "Suspense", "Tragedy", "Western"]

langs = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese": "zh",
    "Japanese": "ja",
    "Dutch": "nl",
    "Portuguese": "pt",
    "Russian": "ru",
    "Italian": "it",
    "Bulgarian": "bg",
    "Polish": "pl",
    "Hungarian": "hu",
    "Hebrew": "he",
    "Arabic": "ar",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Filipino": "fil",
    "Esperanto": "eo",
    "Hindi": "hi",
    "Punjabi": "pa",
    "Farsi": "fa",
    "Greek": "el",
    "Romanian": "ro",
    "Albanian": "sq",
    "Serbian": "sr",
    "Turkish": "tr",
    "Czech": "cs",
    "Indonesian": "id",
    "Croatian": "hr",
    "Catalan": "ca",
    "Latin": "la",
    "Korean": "ko",
    "Vietnamese": "vi",
    "Thai": "th",
    "Devanagari": "hi",

    ## These are from/for AO3:

    u'العربية': 'ar',
    u'беларуская': 'be',
    u'Български език': 'bg',
    u'Català': 'ca',
    u'Čeština': 'cs',
    u'Cymraeg': 'cy',
    u'Dansk': 'da',
    u'Deutsch': 'de',
    u'Ελληνικά': 'el',
    u'English': 'en',
    u'Esperanto': 'eo',
    u'Español': 'es',
    u'eesti keel': 'et',
    u'فارسی': 'fa',
    u'Suomi': 'fi',
    u'Wikang Filipino': 'fil',
    u'Français': 'fr',
    u'Gaeilge': 'ga',
    u'Gàidhlig': 'gd',
    u'עִבְרִית': 'he',
    u'हिन्दी': 'hi',
    u'Hrvatski': 'hr',
    u'Magyar': 'hu',
    u'Bahasa Indonesia': 'id',
    u'Íslenska': 'is',
    u'Italiano': 'it',
    u'日本語': 'ja',
    u'한국말': 'ko',
    u'Lingua latina': 'la',
    u'Lietuvių': 'lt',
    u'Latviešu valoda': 'lv',
    u'मराठी': 'mr',
    u'بهاس ملايو ': 'ms',
    u'Nederlands': 'nl',
    u'Norsk': 'no',
    u'ਪੰਜਾਬੀ': 'pa',
    u'Polski': 'pl',
    u'Português': 'pt',
    u'Quenya': 'qya',
    u'Română': 'ro',
    u'Русский': 'ru',
    u'Slovenčina': 'sk',
    u'Shqip': 'sq',
    u'српски': 'sr',
    u'Svenska': 'sv',
    u'ไทย': 'th',
    u'tlhIngan-Hol': 'tlh',  # Klingon. Has a real ISO 639-2 code.
    # 'Thermian':'', # Alien language from Galaxy Quest.
    u'Türkçe': 'fr',
    u'українська': 'uk',
    u'Tiếng Việt': 'vi',
    u'中文': 'zh',
    u'Bahasa Malaysia': 'zsm',
}


class WebClient:
    def __init__(self):
        self.cookiejar = self.get_empty_cookiejar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self.cookiejar),
            GZipProcessor()
        )

    @staticmethod
    def get_empty_cookiejar():
        return cl.LWPCookieJar()

    # parameters is a dict()
    def _fetchUrl(self, url, parameters=None, referer=None):

        excpt = None
        if url.startswith("file://"):
            # only one try for file:s.
            sleeptimes = [0]
        else:
            sleeptimes = [0, 0.5, 4, 9]
        for sleeptime in sleeptimes:
            if sleeptime:
                logger.debug("Sleeping for %d secs" % sleeptime)
            time.sleep(sleeptime)
            try:
                data = self._fetchUrlRawOpened(url, parameters=parameters)
                logger.debug("Loaded url %s" % url)
                return self._decode(data)
            except urllib2.HTTPError, he:
                excpt = he
                if he.code in (403, 404, 410):
                    logger.warn("Caught an exception reading URL: %s  Exception %s." % (
                        unicode(safe_url(url)), unicode(he)))
                    break  # break out on 404
            except Exception, e:
                excpt = e
                logger.warn("Caught an exception reading URL: %s sleeptime(%s) Exception %s." % (
                    unicode(safe_url(url)), sleeptime, unicode(e)))

        logger.error("Giving up on %s" % safe_url(url))
        logger.debug(excpt, exc_info=True)
        raise excpt

    def _decode(self, data):
        decode = ["utf8",
                  "Windows-1252",
                  "iso-8859-1"]
        for code in decode:
            try:
                # print code
                if code == "auto":
                    if not chardet:
                        logger.info(
                            "chardet not available, skipping 'auto' encoding")
                        continue
                    detected = chardet.detect(data)
                    # print detected
                    if detected['confidence'] > 0.9:
                        logger.debug("using chardet detected encoding:%s(%s)" % (
                            detected['encoding'], detected['confidence']))
                        code = detected['encoding']
                    else:
                        logger.debug("chardet confidence too low:%s(%s)" % (
                            detected['encoding'], detected['confidence']))
                        continue
                return data.decode(code)
            except:
                logger.debug("code failed:" + code)
                pass
        logger.info("Could not decode story, tried:%s Stripping non-ASCII." % decode)
        return "".join([x for x in data if ord(x) < 128])

    def do_sleep(self, extrasleep=4):
        time.sleep(float(extrasleep))

    def _fetchUrlRawOpened(self, url, parameters=None):

        # Specific UA because too many sites are blocking the default python UA.
        headers = [('User-Agent', '')]

        self.opener.addheaders = headers

        opened = self.opener.open(
            url.replace(' ', '%20'),
            parameters and urllib.urlencode(parameters) or None,
            30.0)

        data = opened.read()

        return data

    def get_attr_keys(self, soup):
        if hasattr(soup, '_getAttrMap') and getattr(soup, '_getAttrMap') is not None:
            # bs3
            # print "bs3 attrs:%s"%soup._getAttrMap().keys()
            return soup._getAttrMap().keys()
        elif hasattr(soup, 'attrs') and isinstance(soup.attrs, dict):
            # print "bs4 attrs:%s"%soup.attrs.keys()
            # bs4
            return soup.attrs.keys()
        return []

    def make_soup(self, data):
        data = data.replace("noscript>", "fff_hide_noscript>")
        soup = bs4.BeautifulSoup(data, 'html5lib')
        soup = bs4.BeautifulSoup(unicode(soup), 'html5lib')
        for ns in soup.find_all('fff_hide_noscript'):
            ns.name = 'noscript'
        return soup

    def get(self, url):
        data = self._fetchUrl(url)
        return data, self.make_soup(data)


class base_adapter(WebClient):
    def __init__(self):
        WebClient.__init__(self)

    def utf8FromSoup(self, url, soup, allow_replace_br_with_p=True):
        start = datetime.now()
        soup = copy.copy(soup)
        retval = self._do_utf8FromSoup(url, soup, allow_replace_br_with_p)
        return retval

    def _do_utf8FromSoup(self, url, soup, allow_replace_br_with_p=True):

        fetch = self._fetchUrl

        acceptable_attributes = ['href', 'name', 'class', 'id']

        # if self.getConfig("keep_style_attr"):
        #     acceptable_attributes.append('style')
        # if self.getConfig("keep_title_attr"):
        #     acceptable_attributes.append('title')

        # print("include_images:"+self.getConfig('include_images'))
        if None:  # self.getConfig('include_images'):
            acceptable_attributes.extend(('src', 'alt', 'longdesc'))
            try:
                for img in soup.find_all('img'):
                    # some pre-existing epubs have img tags that had src stripped off.
                    if img.has_attr('src'):
                        (img['src'], img['longdesc']) = self.story.addImgUrl(url, img['src'], fetch,
                                                                             coverexclusion=self.getConfig(
                                                                                 'cover_exclusion_regexp'))
            except AttributeError as ae:
                logger.info("Parsing for img tags failed--probably poor input HTML.  Skipping images.")

        for attr in self.get_attr_keys(soup):
            if attr not in acceptable_attributes:
                del soup[attr]  ## strip all tag attributes except href and name

        try:
            for t in soup.findAll(recursive=True):
                for attr in self.get_attr_keys(t):
                    if attr not in acceptable_attributes:
                        del t[attr]  ## strip all tag attributes except acceptable_attributes

                # these are not acceptable strict XHTML.  But we do already have
                # CSS classes of the same names defined
                if t and hasattr(t, 'name') and t.name is not None:
                    if t.name in ['u']:
                        t['class'] = t.name
                        t.name = 'span'
                    if t.name in 'center':
                        t['class'] = t.name
                        t.name = 'div'
                    # removes paired, but empty non paragraph tags.
                    if t.name not in 'p' and t.string != None and len(t.string.strip()) == 0:
                        t.extract()

                    # remove script tags cross the board.
                    if t.name == 'script':
                        t.extract()

        except AttributeError, ae:
            if "%s" % ae != "'NoneType' object has no attribute 'next_element'":
                logger.error("Error parsing HTML, probably poor input HTML. %s" % ae)

        retval = unicode(soup)

        # if self.getConfig('nook_img_fix') and not self.getConfig('replace_br_with_p'):
        #     retval = re.sub(r"(?!<(div|p)>)\s*(?P<imgtag><img[^>]+>)\s*(?!</(div|p)>)",
        #                     "<div>\g<imgtag></div>", retval)

        # Don't want html, head or body tags in chapter html--writers add them.
        # This is primarily for epub updates.
        retval = re.sub(r"</?(html|head|body)[^>]*>\r?\n?", "", retval)

        if allow_replace_br_with_p:
            # Apply heuristic processing to replace <br> paragraph
            # breaks with <p> tags.
            start = datetime.now()
            retval = replace_br_with_p(retval)

        # if self.getConfig('replace_hr'):
        #     # replacing a self-closing tag with a container tag in the
        #     # soup is more difficult than it first appears.  So cheat.
        #     retval = re.sub("<hr[^>]*>", "<div class='center'>* * *</div>", retval)

        return retval


class Story(base_adapter):
    def __init__(self, url, init=False):
        base_adapter.__init__(self)

        self.metadata = {
            'category': [],
            'genre': [],
            'characters': [],
            'ships': [],
        }

        self.chapterUrls = []

        rer = re.compile(r'(?:(?:www|m)\.fanfiction\.net/s/)?(\d+)(?:/\d+)?', re.I).search(url)
        if not rer:
            raise exc.RegularExpresssionFailed('(?:www|m)\.fanfiction\.net/s/(\d+)(?:/(\d+))?', url)
        self.metadata['storyID'] = self.storyID = rer.group(1)

        self._setURL('http://www.fanfiction.net/s/%s/1' % self.storyID)

        if init:
            self._getmetadata()

    def _setURL(self, url):
        self.url = url
        self.parsedUrl = up.urlparse(url)
        self.host = self.parsedUrl.netloc
        self.path = self.parsedUrl.path
        self.metadata['storyUrl'] = url

    def _getmetadata(self):
        url = 'http://www.fanfiction.net/s/%s/1' % self.storyID

        try:
            data, soup = self.get(url)
        except urllib2.HTTPError as e:
            if e.code == 404:
                raise exc.StoryDoesNotExist(url)
            else:
                raise e

        if "Unable to locate story" in data:
            raise exc.StoryDoesNotExist(url)

        if "not found. Please check to see you are not using an outdated url." in data:
            raise exc.FailedToDownload(
                "Error downloading Chapter: %s! Chapter not found. Please check to see you are not using an outdated url." % url)

        a = soup.find('a', href=re.compile(r"^/u/\d+"))
        self.metadata['authorId'] = a['href'].split('/')[2]
        self.metadata['authorUrl'] = 'https://' + self.host + a['href']
        self.metadata['author'] = a.string

        categories = soup.select('div#pre_story_links a.xcontrast_txt')

        if len(categories) > 1:
            self.metadata['category'].append(stripHTML(categories[1]))
        elif 'Crossover' in categories[0]['href']:
            caturl = "https://%s%s" % ('www.fanfiction.net', categories[0]['href'])
            catsoup = self.make_soup(self._fetchUrl(caturl))
            found = False
            for a in catsoup.findAll('a', href=re.compile(r"^/crossovers/.+?/\d+/")):
                self.metadata['category'].append(stripHTML(a))
                found = True
            if not found:
                # Fall back.  I ran across a story with a Crossver
                # category link to a broken page once.
                # http://www.fanfiction.net/s/2622060/1/
                # Naruto + Harry Potter Crossover
                logger.info("Fall back category collection")
                for c in stripHTML(categories[0]).replace(" Crossover", "").split(' + '):
                    self.metadata['category'].append(c)

        a = soup.find('a', href=re.compile(r'https?://www\.fictionratings\.com/'))
        rating = a.string
        if 'Fiction' in rating:
            rating = rating[9:]
        self.metadata['rating'] = rating

        gui_table1i = soup.find('div', {'id': 'content_wrapper_inner'})

        self.metadata['title'] = stripHTML(gui_table1i.find('b'))

        summarydiv = gui_table1i.find('div', {'style': 'margin-top:2px'})
        if summarydiv:
            self.metadata['summary'] = self.metadata['description'] = stripHTML(summarydiv)

        grayspan = gui_table1i.find('span', {'class': 'xgray xcontrast_txt'})
        metatext = stripHTML(grayspan).replace('Hurt/Comfort', 'Hurt-Comfort')

        if 'Status: Complete' in metatext:
            self.metadata['status'] = 'Completed'
        else:
            self.metadata['status'] = 'In-Progress'

        metalist = metatext.split(" - ")

        # Rated: Fiction K - English - Words: 158,078 - Published: 02-04-11 Rated: Fiction T - English -
        # Adventure/Sci-Fi - Naruto U. - Chapters: 22 - Words: 114,414 - Reviews: 395 - Favs: 779 - Follows: 835 -
        # Updated: 03-21-13 - Published: 04-28-12 - id: 8067258

        if metalist[0].startswith('Rated:'):
            metalist = metalist[1:]

        self.metadata['language'] = metalist[0]
        self.metadata['langcode'] = langs[metalist[0]] or None
        metalist = metalist[1:]

        genrelist = metalist[0].split('/')  # Hurt/Comfort already changed above.
        goodgenres = True
        for g in genrelist:
            if g.strip() not in ffnetgenres:
                logger.warn(g + " not in ffnetgenres")
                goodgenres = False

        if goodgenres:
            self.metadata['genre'].extend(genrelist)
            metalist = metalist[1:]

        dates = soup.findAll('span', {'data-xutime': re.compile(r'^\d+$')})
        if len(dates) > 1:
            self.metadata['dateUpdated'] = datetime.fromtimestamp(float(dates[0]['data-xutime']), pytz.utc)
        self.metadata['datePublished'] = datetime.fromtimestamp(float(dates[-1]['data-xutime']), pytz.utc)

        metakeys = {
            'Chapters': False,
            'Status': False,
            'id': False,
            'Updated': False,
            'Published': False,
            'Reviews': 'reviews',
            'Favs': 'favs',
            'Follows': 'follows',
            'Words': 'numWords',
        }

        chars_ships_list = []
        while len(metalist) > 0:
            m = metalist.pop(0)
            if ':' in m:
                key = m.split(':')[0].strip()
                if key in metakeys:
                    if metakeys[key]:
                        self.metadata[metakeys[key]] = m.split(':')[1].strip()
                    continue
            chars_ships_list.append(m)

        chars_ships_text = ' - '.join(chars_ships_list)
        # print("chars_ships_text:%s"%chars_ships_text)
        # with 'pairing' support, pairings are bracketed w/o comma after
        # [Caspian X, Lucy Pevensie] Edmund Pevensie, Peter Pevensie
        self.metadata['characters'].extend(chars_ships_text.replace('[', '').replace(']', ',').split(','))

        l = chars_ships_text
        while '[' in l:
            self.metadata['ships'].append(l[l.index('[') + 1:l.index(']')].replace(', ', '/'))
            l = l[l.index(']') + 1:]

        select = soup.find('select', {'name': 'chapter'})

        def ster(title_str):
            return re.sub(r'\d+\.\s(.*)', lambda x: x.group(1), title_str)

        if select is None:
            # no selector found, so it's a one-chapter story.
            self.chapterUrls.append((ster(self.metadata.get('title')), url))
        else:
            allOptions = select.findAll('option')
            for o in allOptions:
                url = u'http://%s/s/%s/%s/' % ('www.fanfiction.net',
                                               self.storyID,
                                               o['value'])
                title = u"%s" % o
                title = re.sub(r'<[^>]+>', '', title)
                self.chapterUrls.append((ster(title), url))

        self.metadata['numChapters'] = len(self.chapterUrls)

        ffnet_notify().accepted().post()
        logger.debug('Story metadata: ' + str(self.metadata))

        return data, soup

    def getChapterText(self, count):
        if not self.chapterUrls:
            logger.warn("_getmetadata not called, calling to get chapter urls...")
            self._getmetadata()

        if count > len(self.chapterUrls):
            raise Exception("Chapter count too high, chapter only has %d chapters" % len(self.chapterUrls))

        url = self.chapterUrls[count][1]
        logger.debug('Getting chapter text from: %s' % url)
        data, soup = self.get(url)

        if "Please email this error message in full to <a href='mailto:support@fanfiction.com'>support@fanfiction.com</a>" in data:
            raise exc.FailedToDownload("Error downloading Chapter: %s!  FanFiction.net Site Error!" % url)

        div = soup.find('div', {'id': 'storytextp'})

        if None is div:
            logger.debug('div id=storytextp not found. data:%s' % data)
            raise exc.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, div)

    def write(self, dirpath=None):
        EpubWriter(self).write(True, dirpath=dirpath)

    def meta(self):
        makenumber = lambda n: (not isinstance(n, int)) and int(n.replace(',', '')) or n

        ffnet_notify().meta(meta_lend(
            [
                'author',
                ('authorId', 'authorID'),
                'title',
                'datePublished',
                'dateUpdated',
                'storyID',
                'genre',
                'summary',
                ('numChapters', 'chapters'),
                ('category', lambda l: len(l) > 1 and l or l[0]),
                ('reviews', makenumber, 0),
                ('favs', makenumber, 0),
                ('follows', makenumber, 0),
                ('numWords', makenumber, 0)
            ],
            self.metadata)
        ).post()
        return self


def meta_lend(keys, dic):
    d = {}
    for k in keys:
        k1 = k2 = k
        do = lambda x: x
        default = None
        if type(k) is tuple:
            if len(k) > 2:
                default = k[2]
            if isinstance(k[0], basestring) and isinstance(k[1], basestring):
                k2 = k[0]
                k1 = k[1]
            elif callable(k[1]):
                do = k[1]
                k1 = k2 = k[0]

        # logger.debug("meta_lend: getting %s... [%s] *%s >%s ^%s" % (
        #     k1 == k2 and k1 or '(%s/%s)' % (k1, k2),
        #     k,
        #     default,
        #     dic.get(k2, default),
        #     do(dic.get(k2, default))
        # ))

        d[k1] = do(dic.get(k2, default))
    return d


def safe_url(url):
    return re.sub(re.compile(r'(?P<attr>(password|name|login).?=)[^&]*(?P<amp>&|$)', flags=re.MULTILINE),
                  r'\g<attr>XXXXXXXX\g<amp>', url)


def replace_br_with_p(body):
    was_run_marker = u'FFF_replace_br_with_p_has_been_run'
    if was_run_marker in body:
        logger.debug("replace_br_with_p previously applied, skipping.")
        return body

    def is_valid_block(block):
        return unicode(block).find('<') == 0 and unicode(block).find('<!') != 0

    def soup_up_div(body):
        blockTags = ['address', 'aside', 'blockquote', 'del', 'div', 'dl', 'fieldset', 'form', 'ins', 'noscript', 'ol',
                     'p', 'pre', 'table', 'ul']
        recurseTags = ['blockquote', 'div', 'noscript']

        tag = body[:body.index('>') + 1]
        tagend = body[body.rindex('<'):]

        body = body.replace(u'<br />', u'[br /]')

        # bs4 insists on wrapping *all* new soups in <html><body> if they
        # don't already have them.  This way we have just the div.
        soup = bs4.BeautifulSoup('<div id="soup_up_div">' + body + '</div>', 'html5lib').find('div', id="soup_up_div")

        body = u''
        lastElement = 1  # 1 = block, 2 = nested, 3 = invalid

        for i in soup.contents[0]:
            if unicode(i).strip().__len__() > 0:
                s = unicode(i)
                if type(i) == bs4.Tag:
                    if i.name in blockTags:
                        if lastElement > 1:
                            body = body.strip(r'\s*(\[br\ \/\]\s*)*\s*')
                            body += u'{/p}'

                        lastElement = 1

                        if i.name in recurseTags:
                            s = soup_up_div(s)

                        body += s.strip() + '\n'
                    else:
                        if lastElement == 1:
                            body = body.strip(r'\s*(\[br\ \/\]\s*)*\s*')
                            body += u'{p}'

                        lastElement = 2
                        body += s
                elif type(i) == bs4.Comment:
                    # body += s
                    # skip comments because '<!-- text -->' becomes just 'text'
                    pass
                else:
                    if lastElement == 1:
                        body = body.strip(r'\s*(\[br\ \/\]\s*)*\s*')
                        body += u'{p}'

                    lastElement = 3
                    body += s

        if lastElement > 1:
            body = body.strip(r'\s*(\[br\ \/\]\s*)*\s*')
            body += u'{/p}'

        body = body.replace(u'[br /]', u'<br />')

        return tag + body + tagend

    def logdebug(s):
        if DEBUG:
            logger.debug(s)
        pass

    def tag_sanitizer(html):
        blockTags = ['address', 'blockquote', 'del', 'div', 'dl', 'fieldset', 'form', 'ins', 'noscript', 'ol', 'pre',
                     'table', 'ul']

        def is_end_tag(tag):
            return re.match(r'</([^\ >]+)>', tag) is not None

        def is_comment_tag(tag):
            return re.match(r'<\!\-\-([^>]+)>', tag) is not None

        def is_closed_tag(tag):
            return re.match(r'<(.+?)/>', tag) is not None

        body = u''
        tags = re.findall(r'(<[^>]+>)([^<]*)', html)

        for rTag in tags:
            name = stack.get_tag_name(rTag[0])
            is_end = is_end_tag(rTag[0])
            is_closed = is_closed_tag(rTag[0]) or is_comment_tag(rTag[0])

            # is_comment = is_comment_tag(rTag[0])
            # logdebug(u'%s >  isEnd: %s >  isClosed: %s >  isComment: %s'%(name, unicode(is_end), unicode(is_closed), unicode(is_comment)))
            # logdebug(u'> %s%s\n'%(rTag[0], rTag[1]))

            if name in blockTags:
                body += rTag[0]
                body += rTag[1]
            elif name == u'p':
                if is_end:
                    body += stack.spool_end()
                    body += rTag[0]
                    body += rTag[1]
                elif is_closed:
                    body += rTag[0]
                    body += rTag[1]
                else:
                    body += rTag[0]
                    body += stack.spool_start()
                    body += rTag[1]
            else:
                if is_end:
                    t = stack.get_last()
                    tn = stack.get_tag_name(t)
                    rTn = stack.get_tag_name(rTag[0])
                    if tn == rTn:
                        body += rTag[0]
                        stack.pop()
                elif not is_closed:
                    stack.push(rTag[0])
                    body += rTag[0]
                else:
                    body += rTag[0]

                body += rTag[1]
        stack.flush()
        return body

    # Ascii character (and Unicode as well) xA0 is a non-breaking space, ascii code 160.
    # However, Python Regex does not recognize it as a whitespace, so we'll be changing it to a regular space.
    # .strip() so "\n<div>" at beginning is also recognized.
    body = body.replace(u'\xa0', u' ').strip()

    if body.find('>') == -1 or body.rfind('<') == -1:
        return body

    # logdebug(u'---')
    # logdebug(u'BODY start.: ' + body[:4000])
    # logdebug(u'--')
    # logdebug(u'BODY end...: ' + body[-250:])
    # logdebug(u'BODY.......: ' + body)
    # logdebug(u'---')

    # clean breaks (<br />), removing whitespaces between them.
    body = re.sub(r'\s*<br[^>]*>\s*', r'<br />', body)

    # change surrounding div to a p and remove attrs Top surrounding
    # tag in all cases now should be div, to just strip the first and
    # last tags.
    if is_valid_block(body) and body.find('<div') == 0:
        body = body[body.index('>') + 1:body.rindex('<')].strip()

    # BS is doing some BS on entities, meaning &lt; and &gt; are turned into < and >... a **very** bad idea in html.
    body = re.sub(r'&(.+?);', r'XAMP;\1;', body)

    body = soup_up_div(u'<div>' + body + u'</div>')

    body = body[body.index('>') + 1:body.rindex('<')]

    # Find all existing blocks with p, pre and blockquote tags, we need to shields break tags inside those.
    # This is for "lenient" mode, however it is also used to clear break tags before and after the block elements.
    blocksRegex = re.compile(r'(\s*<br\ />\s*)*\s*<(pre|p|blockquote|table)([^>]*)>(.+?)</\2>\s*(\s*<br\ />\s*)*',
                             re.DOTALL)
    body = blocksRegex.sub(r'\n<\2\3>\4</\2>\n', body)

    # if aggressive mode = true
    # blocksRegex = re.compile(r'(\s*<br\ */*>\s*)*\s*<(pre)([^>]*)>(.+?)</\2>\s*(\s*<br\ */*>\s*)*', re.DOTALL)
    # In aggressive mode, we also check breakes inside blockquotes, meaning we can get orphaned paragraph tags.
    # body = re.sub(r'<blockquote([^>]*)>(.+?)</blockquote>', r'<blockquote\1><p>\2</p></blockquote>', body, re.DOTALL)
    # end aggressive mode

    blocks = blocksRegex.finditer(body)
    # For our replacements to work, we need to work backwards, so we reverse the iterator.
    blocksList = []
    for match in blocks:
        blocksList.insert(0, match)

    for match in blocksList:
        group4 = match.group(4).replace(u'<br />', u'{br /}')
        body = body[:match.start(4)] + group4 + body[match.end(4):]

    # change surrounding div to a p and remove attrs Top surrounding
    # tag in all cases now should be div, to just strip the first and
    # last tags.
    # body = u'<p>' + body + u'</p>'

    # Nuke div tags surrounding a HR tag.
    body = re.sub(r'<div[^>]+>\s*<hr[^>]+>\s*</div>', r'\n<hr />\n', body)

    # So many people add formatting to their HR tags, and ePub does not allow those, we are supposed to use css.
    # This nukes the hr tag attributes.
    body = re.sub(r'\s*<hr[^>]+>\s*', r'\n<hr />\n', body)

    # Remove leading and trailing breaks from HR tags
    body = re.sub(r'\s*(<br\ \/>)*\s*<hr\ \/>\s*(<br\ \/>)*\s*', r'\n<hr />\n', body)
    # Nuking breaks leading paragraps that may be in the body. They are eventually treated as <p><br /></p>
    body = re.sub(r'\s*(<br\ \/>)+\s*<p', r'\n<p></p>\n<p', body)
    # Nuking breaks trailing paragraps that may be in the body. They are eventually treated as <p><br /></p>
    body = re.sub(r'</p>\s*(<br\ \/>)+\s*', r'</p>\n<p></p>\n', body)

    # logdebug(u'--- 2 ---')
    # logdebug(u'BODY start.: ' + body[:250])
    # logdebug(u'--')
    # logdebug(u'BODY end...: ' + body[-250:])
    # logdebug(u'BODY.......: ' + body)
    # logdebug(u'--- 2 ---')

    # Because a leading or trailing non break tag will break the following code, we have to mess around rather badly for a few lines.
    body = body.replace(u'[', u'&squareBracketStart;')
    body = body.replace(u']', u'&squareBracketEnd;')
    body = body.replace(u'<br />', u'[br /]')

    breaksRegexp = [
        re.compile(r'([^\]])(\[br\ \/\])([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){2}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){3}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){4}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){5}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){6}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){7}([^\[])'),
        re.compile(r'([^\]])(\[br\ \/\]){8}([^\[])'),
        re.compile(r'(\[br\ \/\]){9,}')]

    breaksCount = [
        len(breaksRegexp[0].findall(body)),
        len(breaksRegexp[1].findall(body)),
        len(breaksRegexp[2].findall(body)),
        len(breaksRegexp[3].findall(body)),
        len(breaksRegexp[4].findall(body)),
        len(breaksRegexp[5].findall(body)),
        len(breaksRegexp[6].findall(body)),
        len(breaksRegexp[7].findall(body))]

    breaksMax = 0
    breaksMaxIndex = 0;

    for i in range(1, len(breaksCount)):
        if breaksCount[i] >= breaksMax:
            breaksMax = breaksCount[i]
            breaksMaxIndex = i

    lines = body.split(u'[br /]')
    contentLines = 0;
    contentLinesSum = 0;
    longestLineLength = 0;
    averageLineLength = 0;

    for line in lines:
        lineLen = len(line.strip())
        if lineLen > 0:
            contentLines += 1
            contentLinesSum += lineLen
            if lineLen > longestLineLength:
                longestLineLength = lineLen

    if contentLines == 0:
        contentLines = 1

    averageLineLength = contentLinesSum / contentLines

    logdebug(u'---')
    logdebug(u'Lines.............: ' + unicode(len(lines)))
    logdebug(u'contentLines......: ' + unicode(contentLines))
    logdebug(u'contentLinesSum...: ' + unicode(contentLinesSum))
    logdebug(u'longestLineLength.: ' + unicode(longestLineLength))
    logdebug(u'averageLineLength.: ' + unicode(averageLineLength))
    logdebug(u'---')
    logdebug(u'breaksMaxIndex....: ' + unicode(breaksMaxIndex))
    logdebug(u'len(breaksCount)-1: ' + unicode(len(breaksCount) - 1))
    logdebug(u'breaksMax.........: ' + unicode(breaksMax))

    if breaksMaxIndex == len(breaksCount) - 1 and breaksMax < 2:
        breaksMaxIndex = 0
        breaksMax = breaksCount[0]

    logdebug(u'---')
    logdebug(u'breaks 1: ' + unicode(breaksCount[0]))
    logdebug(u'breaks 2: ' + unicode(breaksCount[1]))
    logdebug(u'breaks 3: ' + unicode(breaksCount[2]))
    logdebug(u'breaks 4: ' + unicode(breaksCount[3]))
    logdebug(u'breaks 5: ' + unicode(breaksCount[4]))
    logdebug(u'breaks 6: ' + unicode(breaksCount[5]))
    logdebug(u'breaks 7: ' + unicode(breaksCount[6]))
    logdebug(u'breaks 8: ' + unicode(breaksCount[7]))
    logdebug(u'----')
    logdebug(u'max found: ' + unicode(breaksMax))
    logdebug(u'max Index: ' + unicode(breaksMaxIndex))
    logdebug(u'----')

    if breaksMaxIndex > 0 and breaksCount[0] > breaksMax and averageLineLength < 90:
        body = breaksRegexp[0].sub(r'\1 \n\3', body)

    # Find all instances of consecutive breaks less than otr equal to the max count use most often
    #  replase those tags to inverted p tag pairs, those with more connsecutive breaks are replaced them with a horisontal line
    for i in range(len(breaksCount)):
        # if i > 0 or breaksMaxIndex == 0:
        if i <= breaksMaxIndex:
            logdebug(unicode(i) + u' <= breaksMaxIndex (' + unicode(breaksMaxIndex) + u')')
            body = breaksRegexp[i].sub(r'\1</p>\n<p>\3', body)
        elif i == breaksMaxIndex + 1:
            logdebug(unicode(i) + u' == breaksMaxIndex+1 (' + unicode(breaksMaxIndex + 1) + u')')
            body = breaksRegexp[i].sub(r'\1</p>\n<p><br/></p>\n<p>\3', body)
        else:
            logdebug(unicode(i) + u' > breaksMaxIndex+1 (' + unicode(breaksMaxIndex + 1) + u')')
            body = breaksRegexp[i].sub(r'\1</p>\n<hr />\n<p>\3', body)

    body = breaksRegexp[8].sub(r'</p>\n<hr />\n<p>', body)

    # Reverting the square brackets
    body = body.replace(u'[', u'<')
    body = body.replace(u']', u'>')
    body = body.replace(u'&squareBracketStart;', u'[')
    body = body.replace(u'&squareBracketEnd;', u']')

    body = body.replace(u'{p}', u'<p>')
    body = body.replace(u'{/p}', u'</p>')

    # If for some reason, a third break makes its way inside the paragraph, preplace that with the empty paragraph for the additional linespaing.
    body = re.sub(r'<p>\s*(<br\ \/>)+', r'<p><br /></p>\n<p>', body)

    # change empty p tags to include a br to force spacing.
    body = re.sub(r'<p>\s*</p>', r'<p><br/></p>', body)

    # Clean up hr tags, and add inverted p tag pairs
    body = re.sub(r'(<div[^>]+>)*\s*<hr\ \/>\s*(</div>)*', r'\n<hr />\n', body)

    # Clean up hr tags, and add inverted p tag pairs
    body = re.sub(r'\s*<hr\ \/>\s*', r'</p>\n<hr />\n<p>', body)

    # Because the previous regexp may cause trouble if the hr tag already had a p tag pair around it, w nee dot
    # repair that. Repeated opening p tags are condenced to one. As we added the extra leading opening p tags,
    # we can safely assume that the last in such a chain must be the original. Lets keep its attributes if they are
    # there.
    body = re.sub(r'\s*(<p[^>]*>\s*)+<p([^>]*)>\s*', r'\n<p\2>', body)
    # Repeated closing p tags are condenced to one
    body = re.sub(r'\s*(<\/\s*p>\s*){2,}', r'</p>\n', body)

    # superflous cleaning, remove whitespaces traling opening p tags. These does affect formatting.
    body = re.sub(r'\s*<p([^>]*)>\s*', r'\n<p\1>', body)
    # superflous cleaning, remove whitespaces leading closing p tags. These does not affect formatting.
    body = re.sub(r'\s*</p>\s*', r'</p>\n', body)

    # Remove empty tag pairs
    body = re.sub(r'\s*<(\S+)[^>]*>\s*</\1>', r'', body)

    body = body.replace(u'{br /}', u'<br />')
    body = re.sub(r'XAMP;(.+?);', r'&\1;', body)
    body = body.strip()

    # re-wrap in div tag.
    body = u'<div id="' + was_run_marker + u'">\n' + body + u'</div>\n'
    return u'<!-- ' + was_run_marker + u' -->\n' + tag_sanitizer(body)


if __name__ == '__builtin__':
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

if __name__ == 'main':
    if not sys.argv[0]:
        print "no url specified"
        exit(1)
    Story(sys.argv[0], init=True).write()
