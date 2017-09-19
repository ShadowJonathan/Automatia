# -*- coding: utf-8 -*-
import logging
import string
import StringIO
import zipfile
import urllib
import re
import os
import bs4
import sys
from htmlcleanup import stripHTML, removeEntities
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from xml.dom.minidom import getDOMImplementation
try:
    sys.path.insert(0, os.path.abspath('.'))
    sys.path.insert(0, os.path.abspath('./python'))
except:
    pass
from py import ffnet_notify

logger = logging.getLogger(__name__)


class EpubWriter:
    def __init__(self, story):

        self.S = story

        self.EPUB_CSS = string.Template('''${output_css}''')

        self.EPUB_TITLE_PAGE = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
            <title>${title}</title>
            <style type="text/css">
                body{font-family:'Arial',sans-serif;}
            </style>
        </head>
        <body>
            <div style="text-align: center;">
                <h1>${title}</h1>
                
                <h3><i>by ${author}</i></h3>
                <div style="text-align: left;">
                    <div>
                        ${summary}
                    </div>
                    
                    <span>
                        ${combinedInfo}
                    </span>
                </div>
            </div>
            
            <div style="text-align: left;">
                URL: <a href="${storyUrl}">${storyUrl}</a>
            </div>
        </body>
        </html>
''')

        self.EPUB_TOC_PAGE_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${title} by ${author}</title>
<style type="text/css">
body{font-family:'Arial',sans-serif;}
</style>
</head>
<body>
<div>
<h3>Table of Contents</h3>
''')

        self.EPUB_TOC_ENTRY = string.Template('''
<a href="file${index}.xhtml">${chapter}</a><br />
''')

        self.EPUB_TOC_PAGE_END = string.Template('''
</div>
</body>
</html>
''')

        self.EPUB_CHAPTER_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>${chapter}</title>
<style type="text/css">
body{font-family:'Arial',sans-serif;}
</style>
<meta name="chapterurl" content="${url}" />
<meta name="chaptertitle" content="${chapter}" />
</head>
<body>
<h2 style="text-align: center;">${chapter}</h2>
''')

        self.EPUB_CHAPTER_END = string.Template('''
</body>
</html>
''')

        self.EPUB_LOG_PAGE_START = string.Template('''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Update Log</title>
<style type="text/css">
body{font-family:'Arial',sans-serif;}
</style>
</head>
<body>
<h3>Update Log</h3>
''')

        self.EPUB_LOG_UPDATE_START = string.Template('''
<p class='log_entry'>
''')

        self.EPUB_LOG_ENTRY = string.Template('''
<b>${label}:</b> <span id="${id}">${value}</span>
''')

        self.EPUB_LOG_UPDATE_END = string.Template('''
</p><hr />
''')

        self.EPUB_LOG_PAGE_END = string.Template('''
</body>
</html>
''')

        self.EPUB_LOG_PAGE_END = string.Template('''
</body>
</html>
''')

        self.EPUB_COVER = string.Template('''
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"><head><title>Cover</title><style type="text/css" title="override_css">
@page {padding: 0pt; margin:0pt}
body { text-align: center; padding:0pt; margin: 0pt; }
div { margin: 0pt; padding: 0pt; }
</style></head><body><div>
<img src="${coverimg}" alt="cover"/>
</div></body></html>
''')

    def _write(self, out, text):
        out.write(text.encode('utf8'))

    def writeTitlePage(self, out, PAGE):
        entries = [
            ('rating', 'Rated: Fiction %s'),
            'language',
            ('genre', lambda s: '/'.join(s)),
            ('characters', lambda c: ', '.join(c)),
            ('numChapters', 'Chapters: %s'),
            ('numWords', 'Words: %s'),
            ('reviews', 'Reviews: %s'),
            ('favs', 'Favs: %s'),
            ('follows', 'Follows: %s'),
            ('dateUpdated', lambda u: 'Updated: %s' % u.strftime("%d/%m/%Y")),
            ('datePublished', lambda u: 'Published: %s' % u.strftime("%d/%m/%Y")),
            ('status', 'Status: %s'),
            ('storyID', 'id: %s'),
        ]

        combinedInfo = []

        for entry in entries:
            def replaceFunc(x):
                return x

            if isinstance(entry, tuple):
                orig = entry
                entry = orig[0]
                if callable(orig[1]):
                    replaceFunc = orig[1]
                else:
                    def replaceFunc(x):
                        return orig[1] % x
            if self.S.metadata.get(entry):
                combinedInfo.append(replaceFunc(self.S.metadata.get(entry)))
        combinedInfo = ' - '.join(combinedInfo)
        self.S.metadata['combinedInfo'] = combinedInfo
        self._write(out, PAGE.substitute(self.S.metadata))

    def writeTOCPage(self, out, START, ENTRY, END):
        if self.S.metadata['numChapters'] > 1:

            self._write(out, START.substitute(self.S.metadata))

            for index, chap in enumerate(self.S.chapterUrls):
                self._write(out, ENTRY.substitute({'chapter': chap[0],
                                                   'number': index + 1,
                                                   'index': "%04d" % (index + 1),
                                                   'url': chap[1]}))

            self._write(out, END.substitute(self.S.metadata))

    def write(self, report=False, dirpath=None):

        n = ffnet_notify().progress_init(int(self.S.metadata['numChapters'])).shadow(self.S.storyID)

        file_name = string.Template("${title} - ${author}.epub").substitute(self.S.metadata).encode('utf8')
        if dirpath:
            file_name = os.path.normpath(dirpath + (dirpath[-1] != "/" and "/" or "") + file_name)
        else:
            file_name = 'stories/' + file_name
        logger.info("Save directly to file: %s" % file_name)
        try:
            os.makedirs(os.path.dirname(os.path.normpath(file_name)))
        except: pass

        outstream = open(file_name, "wb")

        outputepub = ZipFile(outstream, 'w', compression=ZIP_STORED)
        outputepub.debug = 3
        outputepub.writestr('mimetype', 'application/epub+zip')
        outputepub.close()
        outputepub = ZipFile(outstream, 'a', compression=ZIP_DEFLATED)
        outputepub.debug = 3
        containerdom = getDOMImplementation().createDocument(None, "container", None)
        containertop = containerdom.documentElement
        containertop.setAttribute("version", "1.0")
        containertop.setAttribute("xmlns", "urn:oasis:names:tc:opendocument:xmlns:container")
        rootfiles = containerdom.createElement("rootfiles")
        containertop.appendChild(rootfiles)
        rootfiles.appendChild(newTag(containerdom, "rootfile", {"full-path": "content.opf",
                                                                "media-type": "application/oebps-package+xml"}))
        outputepub.writestr("META-INF/container.xml", containerdom.toxml(encoding='utf-8'))
        containerdom.unlink()
        del containerdom

        # TODO change this?
        # uniqueid = 'fanficfare-uid:%s-u%s-s%s' % (
        #     self.S.metadata['site'],
        #     self.S.metadata['authorId'][0],
        #     self.S.metadata['storyId']
        # )

        contentdom = getDOMImplementation().createDocument(None, "package", None)
        package = contentdom.documentElement
        package.setAttribute("version", "2.0")
        package.setAttribute("xmlns", "http://www.idpf.org/2007/opf")
        package.setAttribute("unique-identifier", "fanficfare-uid")
        metadata = newTag(contentdom, "metadata",
                          attrs={"xmlns:dc": "http://purl.org/dc/elements/1.1/",
                                 "xmlns:opf": "http://www.idpf.org/2007/opf"})
        package.appendChild(metadata)

        if self.S.metadata['title']:
            metadata.appendChild(newTag(contentdom, "dc:title", text=self.S.metadata['title']))

        if self.S.metadata['author']:
            metadata.appendChild(newTag(contentdom, "dc:creator",
                                        attrs={"opf:role": "aut"},
                                        text=self.S.metadata['author']))

        metadata.appendChild(
            newTag(contentdom, "dc:contributor", text="Automatia",
                   attrs={"opf:role": "bkp"}))
        metadata.appendChild(newTag(contentdom, "dc:rights", text=""))
        if self.S.metadata['langcode']:
            metadata.appendChild(newTag(contentdom, "dc:language", text=self.S.metadata['langcode']))
        else:
            metadata.appendChild(newTag(contentdom, "dc:language", text='en'))

        # published, created, updated, calibre
        #  Leave calling self.story.getMetadataRaw directly in case date format changes.
        if self.S.metadata['datePublished']:
            metadata.appendChild(newTag(contentdom, "dc:date",
                                        attrs={"opf:event": "publication"},
                                        text=self.S.metadata['datePublished'].strftime("%Y-%m-%d")))

        if 'dateUpdated' in self.S.metadata:
            metadata.appendChild(newTag(contentdom, "dc:date",
                                        attrs={"opf:event": "modification"},
                                        text=self.S.metadata['dateUpdated'].strftime("%Y-%m-%d")))
            metadata.appendChild(newTag(contentdom, "meta",
                                        attrs={"name": "calibre:timestamp",
                                               "content": self.S.metadata['dateUpdated'].strftime(
                                                   "%Y-%m-%dT%H:%M:%S")}))

        if self.S.metadata['description']:
            metadata.appendChild(newTag(contentdom, "dc:description", text=self.S.metadata['description']))

        # FIXME ???
        # for subject in self.story.getSubjectTags():
        #     metadata.appendChild(newTag(contentdom, "dc:subject", text=subject))

        if self.S.metadata['storyUrl']:
            metadata.appendChild(newTag(contentdom, "dc:identifier",
                                        attrs={"opf:scheme": "URL"},
                                        text=self.S.metadata['storyUrl']))
            metadata.appendChild(newTag(contentdom, "dc:source",
                                        text=self.S.metadata['storyUrl']))

        items = []  # list of (id, href, type, title) tuples(all strings)
        itemrefs = []  # list of strings -- idrefs from .opfs' spines
        items.append(("ncx", "toc.ncx", "application/x-dtbncx+xml", None))

        guide = None
        coverIO = None

        coverimgid = "image0000"

        # FIXME cover
        # if None:  # not self.story.cover and self.story.oldcover:
        #     logger.debug("writer_epub: no new cover, has old cover, write image.")
        #     (oldcoverhtmlhref,
        #      oldcoverhtmltype,
        #      oldcoverhtmldata,
        #      oldcoverimghref,
        #      oldcoverimgtype,
        #      oldcoverimgdata) = self.story.oldcover
        #     outputepub.writestr(oldcoverhtmlhref, oldcoverhtmldata)
        #     outputepub.writestr(oldcoverimghref, oldcoverimgdata)
        #
        #     coverimgid = "image0"
        #     items.append((coverimgid,
        #                   oldcoverimghref,
        #                   oldcoverimgtype,
        #                   None))
        #     items.append(("cover", oldcoverhtmlhref, oldcoverhtmltype, None))
        #     itemrefs.append("cover")
        #     metadata.appendChild(newTag(contentdom, "meta", {"content": "image0",
        #                                                      "name": "cover"}))
        #     guide = newTag(contentdom, "guide")
        #     guide.appendChild(newTag(contentdom, "reference", attrs={"type": "cover",
        #                                                              "title": "Cover",
        #                                                              "href": oldcoverhtmlhref}))

        # TODO
        # if None:  # self.getConfig('include_images'):
        #     imgcount = 0
        #     for imgmap in self.story.getImgUrls():
        #         imgfile = "OEBPS/" + imgmap['newsrc']
        #         outputepub.writestr(imgfile, imgmap['data'])
        #         items.append(("image%04d" % imgcount,
        #                       imgfile,
        #                       imgmap['mime'],
        #                       None))
        #         imgcount += 1
        #         if 'cover' in imgfile:
        #             # make sure coverimgid is set to the cover, not
        #             # just the first image.
        #             coverimgid = items[-1][0]

        # items.append(("style", "OEBPS/stylesheet.css", "text/css", None))

        # TODO
        # if None:  # self.story.cover:
        #     # Note that the id of the cover xhmtl *must* be 'cover'
        #     # for it to work on Nook.
        #     items.append(("cover", "OEBPS/cover.xhtml", "application/xhtml+xml", None))
        #     itemrefs.append("cover")
        #     #
        #     # <meta name="cover" content="cover.jpg"/>
        #     metadata.appendChild(newTag(contentdom, "meta", {"content": coverimgid,
        #                                                      "name": "cover"}))
        #     # cover stuff for later:
        #     # at end of <package>:
        #     # <guide>
        #     # <reference type="cover" title="Cover" href="Text/cover.xhtml"/>
        #     # </guide>
        #     guide = newTag(contentdom, "guide")
        #     guide.appendChild(newTag(contentdom, "reference", attrs={"type": "cover",
        #                                                              "title": "Cover",
        #                                                              "href": "OEBPS/cover.xhtml"}))
        #
        #     if self.hasConfig("cover_content"):
        #         COVER = string.Template(self.getConfig("cover_content"))
        #     else:
        #         COVER = self.EPUB_COVER
        #     coverIO = StringIO.StringIO()
        #     coverIO.write(
        #         COVER.substitute(dict(self.story.getAllMetadata().items() + {'coverimg': self.story.cover}.items())))

        items.append(("title_page", "OEBPS/title_page.xhtml", "application/xhtml+xml", "Title Page"))
        itemrefs.append("title_page")

        # if self.S.metadata['numChapters'] > 1:
        #     items.append(("toc_page", "OEBPS/toc_page.xhtml", "application/xhtml+xml", "Table of Contents"))
        #     itemrefs.append("toc_page")
        # collect chapter urls and file names for internalize_text_links option.

        chapurlmap = {}
        for index, chap in enumerate(self.S.chapterUrls):
            i = index + 1
            items.append(("file%04d" % i,
                          "OEBPS/file%04d.xhtml" % i,
                          "application/xhtml+xml",
                          "%d. %s" % (i, chap[0])))
            itemrefs.append("file%04d" % i)
            chapurlmap[chap[1]] = "file%04d.xhtml" % i
            # url -> relative epub file name.

        manifest = contentdom.createElement("manifest")
        package.appendChild(manifest)
        for item in items:
            (item_id, href, item_type, title) = item
            manifest.appendChild(newTag(contentdom, "item",
                                        attrs={'id': item_id,
                                               'href': href,
                                               'media-type': item_type}))

        spine = newTag(contentdom, "spine", attrs={"toc": "ncx"})
        package.appendChild(spine)
        for itemref in itemrefs:
            spine.appendChild(newTag(contentdom, "itemref",
                                     attrs={"idref": itemref,
                                            "linear": "yes"}))
        # guide only exists if there's a cover.
        if guide:
            package.appendChild(guide)

        # write content.opf to zip.
        contentxml = contentdom.toxml(encoding='utf-8')

        # tweak for brain damaged Nook STR.  Nook insists on name before content.
        contentxml = contentxml.replace('<meta content="%s" name="cover"/>' % coverimgid,
                                        '<meta name="cover" content="%s"/>' % coverimgid)
        outputepub.writestr("content.opf", contentxml)

        contentdom.unlink()
        del contentdom

        # create toc.ncx file
        tocncxdom = getDOMImplementation().createDocument(None, "ncx", None)
        ncx = tocncxdom.documentElement
        ncx.setAttribute("version", "2005-1")
        ncx.setAttribute("xmlns", "http://www.daisy.org/z3986/2005/ncx/")
        head = tocncxdom.createElement("head")
        ncx.appendChild(head)
        # head.appendChild(newTag(tocncxdom, "meta",
        #                         attrs={"name": "dtb:uid", "content": uniqueid}))
        head.appendChild(newTag(tocncxdom, "meta",
                                attrs={"name": "dtb:depth", "content": "1"}))
        head.appendChild(newTag(tocncxdom, "meta",
                                attrs={"name": "dtb:totalPageCount", "content": "0"}))
        head.appendChild(newTag(tocncxdom, "meta",
                                attrs={"name": "dtb:maxPageNumber", "content": "0"}))

        docTitle = tocncxdom.createElement("docTitle")
        docTitle.appendChild(newTag(tocncxdom, "text", text=self.S.metadata['title']))
        ncx.appendChild(docTitle)

        tocnavMap = tocncxdom.createElement("navMap")
        ncx.appendChild(tocnavMap)

        # <navPoint id="<id>" playOrder="<risingnumberfrom0>">
        #   <navLabel>
        #     <text><chapter title></text>
        #   </navLabel>
        #   <content src="<chapterfile>"/>
        # </navPoint>
        index = 0
        for item in items:
            (item_id, href, item_type, title) = item
            # only items to be skipped, cover.xhtml, images, toc.ncx, stylesheet.css, should have no title.
            if title:
                navPoint = newTag(tocncxdom, "navPoint",
                                  attrs={'id': item_id,
                                         'playOrder': unicode(index)})
                tocnavMap.appendChild(navPoint)
                navLabel = newTag(tocncxdom, "navLabel")
                navPoint.appendChild(navLabel)
                # the xml library will re-escape as needed.
                navLabel.appendChild(newTag(tocncxdom, "text", text=stripHTML(title)))
                navPoint.appendChild(newTag(tocncxdom, "content", attrs={"src": href}))
                index = index + 1

        # write toc.ncx to zip file
        outputepub.writestr("toc.ncx", tocncxdom.toxml(encoding='utf-8'))
        tocncxdom.unlink()
        del tocncxdom

        # write stylesheet.css file.
        # outputepub.writestr("OEBPS/stylesheet.css", self.EPUB_CSS.substitute({'output_css': css_text}))

        TITLE_PAGE = self.EPUB_TITLE_PAGE

        if coverIO:
            outputepub.writestr("OEBPS/cover.xhtml", coverIO.getvalue())
            coverIO.close()

        titlepageIO = StringIO.StringIO()
        self.writeTitlePage(out=titlepageIO,
                            PAGE=TITLE_PAGE)
        if titlepageIO.getvalue():  # will be false if no title page.
            outputepub.writestr("OEBPS/title_page.xhtml", titlepageIO.getvalue())
        titlepageIO.close()

        # # TODO write toc page.
        # tocpageIO = StringIO.StringIO()
        # self.writeTOCPage(tocpageIO,
        #                   self.EPUB_TOC_PAGE_START,
        #                   self.EPUB_TOC_ENTRY,
        #                   self.EPUB_TOC_PAGE_END)
        # if tocpageIO.getvalue():  # will be false if no toc page.
        #     outputepub.writestr("OEBPS/toc_page.xhtml", tocpageIO.getvalue())
        # tocpageIO.close()

        CHAPTER_START = self.EPUB_CHAPTER_START
        CHAPTER_END = self.EPUB_CHAPTER_END

        for index, chap in enumerate(self.S.chapterUrls):  # (url,title,html)
            chap_data = self.S.getChapterText(index)
            if report:
                n.progress(index+1)\
                    .post()

            logger.debug('Writing chapter text for: %s' % chap[0])
            vals = {'url': removeEntities(chap[1]),
                    'chapter': removeEntities(chap[0]),
                    # 'origchapter': removeEntities(chap.origtitle),
                    # 'tocchapter': removeEntities(chap.toctitle),
                    'index': "%04d" % (index + 1),
                    'number': index + 1}
            # escape double quotes in all vals.
            for k, v in vals.items():
                if isinstance(v, basestring): vals[k] = v.replace('"', '&quot;')
            fullhtml = CHAPTER_START.substitute(vals) + chap_data.strip() + CHAPTER_END.substitute(vals)
            fullhtml = re.sub(r'(</p>|<br ?/>)\n*', r'\1\n', fullhtml)

            outputepub.writestr("OEBPS/file%04d.xhtml" % (index + 1), fullhtml.encode('utf-8'))
            del fullhtml

        for zf in outputepub.filelist:
            zf.create_system = 0
        outputepub.close()

        ### STOP WRITE

        # zipout.writestr(string.Template("${title} - ${storyID}.epub").substitute(self.S.metadata).encode('utf8'),
        #                zipio.getvalue())

        outstream.close()

        # zipout.close()
        if report:
            ffnet_notify()\
                .shadow(self.S.storyID)\
                .end(file_name)\
                .post()


def newTag(dom, name, attrs=None, text=None):
    tag = dom.createElement(name)
    if attrs is not None:
        for attr in attrs.keys():
            tag.setAttribute(attr, attrs[attr])
    if text is not None:
        tag.appendChild(dom.createTextNode(text))
    return tag
