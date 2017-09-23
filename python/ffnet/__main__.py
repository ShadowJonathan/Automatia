from run import *
import exc
import logging
import time
import os
import sys
import search

sys.path.insert(0, os.path.abspath('.'))
try:
    sys.path.insert(0, os.path.abspath('./python'))
except:
    pass
from py import ffnet_notify, ffnet_archive

try:
    os.mkdir('log')
except:
    pass

logging.basicConfig(filename='log/log%s.log' % time.time())

logger.setLevel(logging.DEBUG)

try:
    dirpath = None
    try:
        if '-d' in sys.argv:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            print "Debug on"
    except:
        pass

    if "-archive" not in sys.argv:
        url = ''
        for arg in sys.argv[1:]:
            if arg.startswith('-'):
                continue
            else:
                url = arg
                break

        logger.debug('Url is %s' % url)
        if not url:
            raise exc.NoURL()

        got_arg = None
        try:
            nextarg = lambda: sys.argv[sys.argv[1:].index(arg) + 2]
            for arg in sys.argv[1:]:
                got_arg = arg
                if arg == '-dir':
                    dirpath = nextarg()

        except IndexError:
            raise exc.InvalidArgs(got_arg)

        try:
            s = Story(url, init=True)
            if '-m' in sys.argv:
                s.meta()
            else:
                s.meta().write(dirpath=dirpath)
        except exc.FailedToDownload:
            ffnet_notify().fail('Download Failed', 4).post()
        except exc.StoryDoesNotExist:
            ffnet_notify().fail("Story Does Not Exist", 1).post()
        except exc.RegularExpresssionFailed:
            ffnet_notify().fail("Regex failed", 2).post()
        except urllib2.URLError as e:
            ffnet_notify().fail("Network Error: %s" % e, 3).post()
    else:
        category = None
        archive = None
        action = None
        show_affected = '-sa' in sys.argv

        got_arg = None
        try:
            nextarg = lambda: sys.argv[sys.argv[1:].index(arg) + 2]
            for arg in sys.argv[1:]:
                got_arg = arg
                if arg == '-c':
                    category = nextarg()
                if arg == '-a':
                    archive = nextarg()
                if arg == '-action':
                    action = nextarg()
        except IndexError:
            raise exc.InvalidArgs(got_arg)

        if action == 'stamps' or '-stamps' in sys.argv:
            s = {}
            for c in ['movie', 'play', 'tv', 'misc', 'game', 'cartoon', 'book', 'anime']:
                s[c] = search.Archive.get_stamps(c)
            ffnet_archive().stamps(s).post()
        elif (not category) or category and (not search.Valid_category(category)):
            raise exc.InvalidArgs('NO VALID CATEGORY ARG')
        elif not archive:
            ffnet_archive().archive_index(search.SmartGetAllArchives(category)).post()
        else:
            a = None
            action = action or 'info'
            if action != 'dump' and action != 'info' and action != 'stamps':
                a = search.Archive('/' + search.CAT2URL[search.Valid_category(category)] + "/" + archive + '/')

            if '-allow-m' in sys.argv:
                a.args.Rating(10)

            if action == 'update':
                limit = None
                if '-limit' in sys.argv:
                    limit = int(sys.argv[sys.argv[1:].index('-limit') + 2])
                a.update(limit, show_affected)
            elif action == 'refresh':
                ALL = '-all' in sys.argv
                a.refresh(ALL, show_affected)
            elif action == 'info':
                search.Archive.info(search.CAT2URL[search.Valid_category(category)], archive)
            elif action == 'getinfo':
                a.update(1)
                search.Archive.info(search.CAT2URL[search.Valid_category(category)], archive)
            elif action == 'dump':
                dump = search.Archive.dump_cache(search.CAT2URL[search.Valid_category(category)], archive)
                ffnet_archive().dump(dump).post()

            ffnet_archive().done().post()


except exc.NoURL:
    ffnet_notify().fail("No Url", 0).post()
except exc.ArchiveDoesNotExist, a:
    ffnet_notify().fail(str(a), 6).post()
#except Exception as e:
#    ffnet_notify().fail("Unknown Error: %s" % e, 10).post()

    # 0: no url
    # 1: story doesn't exist
    # 2: regex failed/url invalid
    # 3: networking error
    # 4: download fail
    # 5: internal arg fail
    # 6: archive not exist

    # 10: unknown error
