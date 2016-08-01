import os
import errno
from sru import Sru
from time import sleep
from xml.etree.ElementTree import ElementTree as ET
from xml.etree.ElementTree import XML
import hashlib
import requests
import logging
from logging.handlers import RotatingFileHandler
from tqdm import tqdm
from collections import Counter

logger = logging.getLogger('KB-harvester')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
handler = RotatingFileHandler("KB-harvester.log", maxBytes=5*1024*1024, backupCount=3)
handler.setFormatter(formatter)
logger.addHandler(handler)

NAMESPACES = {'dc': 'http://purl.org/dc/elements/1.1/',
              'ddd': 'http://www.kb.nl/namespaces/ddd',
              'dddx': 'http://www.kb.nl/ddd',
              'dcx': 'http://krait.kb.nl/coop/tel/handbook/telterms.html',
              'didl': 'urn:mpeg:mpeg21:2002:02-DIDL-NS',
              'dcterms': 'http://purl.org/dc/terms/',
              'oai': 'http://www.openarchives.org/OAI/2.0/',
              'didmodel': 'urn:mpeg:mpeg21:2002:02-DIDMODEL-NS',
              'srw_dc': 'info:srw/schema/1/dc-v1.1',
              'dcmitype': 'http://purl.org/dc/dcmitype/',
              'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
              'srw': 'http://www.loc.gov/zing/srw/'}


def check_md5(content, digest):
    m = hashlib.md5()
    m.update(content)
    return m.hexdigest() == digest


class Issue():
    """An issue of a newspaper"""

    def __init__(self, oai_data, path="data/"):
        logger.debug(u"Initialising issue with {0:s}".format(oai_data))
        self.oai_data = oai_data
        self.oai_header = oai_data.find('.//oai:header', NAMESPACES)
        logger.debug(oai_data.find('.//oai:metadata/*', NAMESPACES))
        self.didl = oai_data.find('.//didl:DIDL', NAMESPACES)
        logger.debug(self.didl)
        self.data_path = path
        logger.info("init issue")

    @property
    def identifier(self):
        """Returns the issue identifier"""
        ident = self.didl.find('.//dcx:recordIdentifier', NAMESPACES)
        return ident.text

    @property
    def ppn_issue(self):
        """Returns the issue PPN"""
        return self.identifier.split(":")[1]

    @property
    def ppn_paper(self):
        """Returns the PPN of the newspaper"""
        return self.didl.find('.//dc:identifier[@xsi:type="dcx:PPN"]', NAMESPACES).text

    def check_file_existence(self, filename, digest):
        logger.debug(u"Checking existence of {0:s}".format(filename))
        try:
            f = open(self.issue_path + filename, 'r')
        except OSError as oe:
            logger.debug(u"{0:s} does not exist".format(filename))
            return False
        except IOError as ie:
            logger.debug(u"{0:s} does not exist".format(filename))
            return False
        else:
            with f:
                return check_md5(f.read(),digest)

    def save_binary(self, url, digest, filename):
        if not self.check_file_existence(filename, digest):
            logger.debug(u"Downloading {0:s}".format(url))
            p = requests.get(url)
            if not p.status_code == 200:
                raise Exception(u'Error while getting data from {0:s}'.format(url))
            logger.debug(u"MD5 checksum matches download: {0}".format(check_md5(p.content, digest)))
            logger.debug(u"Saving as {0:s}".format(filename))
            with open(self.issue_path + filename, 'wb') as f:
                f.write(p.content)
            logger.info(u"Saved {0:s} to {1:s}".format(url, filename))
            logger.debug("Sleeping for a sec")
            sleep(1)
        else:
            logger.debug("%s already downloaded :)" % url)

    def save_pages(self):
        """Retrieve and store page images and XML"""

        def page_role(elem):
            return elem.find(".//didl:Statement[@dc:type='role']", NAMESPACES).text.startswith("page")

        def page_image(elem):
            return elem.find(".//didl:Statement[@dc:type='role']", NAMESPACES).text == "image"

        def save_component(component):
            resource = component.find("./didl:Resource", NAMESPACES)
            url = resource.attrib["ref"]
            digest = resource.attrib["{http://krait.kb.nl/coop/tel/handbook/telterms.html}md5_checksum"]
            filename = resource.attrib["{http://krait.kb.nl/coop/tel/handbook/telterms.html}filename"]
            self.save_binary(url, digest, filename)

        def page_alto(elem):
            return elem.find(".//didl:Statement[@dc:type='role']", NAMESPACES).text == "alto"

        pages = filter(page_role, self.didl.findall("./didl:Item/didl:Item", NAMESPACES))
        for page in tqdm(pages, desc="Pages", leave=False, disable=False, position=1):
            components = page.findall("./didl:Component", NAMESPACES)
            map(save_component, filter(page_image, components))
            map(save_component, filter(page_alto, components))

    def save_articles(self):
        """Retrieve and store article text in XML"""

        def article_role(elem):
            return elem.find(".//didl:Statement[@dc:type='role']", NAMESPACES).text.startswith("article")

        def save_component(component):
            resource = component.find("./didl:Resource", NAMESPACES)
            url = resource.attrib["ref"]
            digest = resource.attrib["{http://krait.kb.nl/coop/tel/handbook/telterms.html}md5_checksum"]
            filename = resource.attrib["{http://krait.kb.nl/coop/tel/handbook/telterms.html}filename"]
            self.save_binary(url, digest, filename)

        def article_ocr(elem):
            return elem.find(".//didl:Statement[@dc:type='role']", NAMESPACES).text == "ocr"

        articles = filter(article_role, self.didl.findall("./didl:Item/didl:Item", NAMESPACES))
        for article in tqdm(articles, desc="Articles", leave=False, disable=False, position=1):
            components = article.findall("./didl:Component", NAMESPACES)
            map(save_component, filter(article_ocr, components))

    def save_pdf(self):
        """Get the PDF of the issue, save it to a file"""
        pdf_data = self.didl.find(".//didl:Descriptor[didl:Statement='pdf']/../didl:Resource", NAMESPACES)
        pdf_url = pdf_data.attrib["ref"]
        pdf_digest = pdf_data.attrib["{http://krait.kb.nl/coop/tel/handbook/telterms.html}md5_checksum"]
        pdf_filename = pdf_data.attrib["{http://krait.kb.nl/coop/tel/handbook/telterms.html}filename"]
        self.save_binary(pdf_url, pdf_digest, pdf_filename)

    @property
    def issue_path(self):
        return self.data_path + self.ppn_issue + "/"

    def save_header(self):
        """Save the OAI-PMH header to a file"""
        t = ET(self.oai_header)
        t.write(self.issue_path + self.ppn_issue + ".oai-header.xml", "utf-8")

    def save_metadata(self):
        """Save the DIDL metadata to a file"""
        t = ET(self.didl)
        t.write(self.issue_path + self.ppn_issue + ".didl.xml", "utf-8")


class Harvester():
    def __init__(self, path="data/", key=None):
        self.data_path = path
        self.url_counts = Counter()
        self.api_key = key
        try:
            # os.access(self.data_path, os.F_OK)
            os.makedirs(self.data_path)
        except IOError as ioe:
            if ioe.errno == errno.EACCES:
                logger.critical(ioe)
                exit(1)
            elif ioe.errno == errno.EEXIST:
                logger.debug("Data path already exists")
        except OSError as ose:
            if ose.errno == errno.EEXIST:
                logger.debug("Data path already exists")
            else:
                logger.critical(u"Could not create data storage path '{0:s}'".format(path))
                exit(1)

    def harvest_newspaper_urls(self, ppn, start=1):
        """Get and process all issues of a newspaper identified by PPN"""
        logger.info(u"Starting URL harvest for PPN {0:s}".format(ppn))
        query = u"ppn exact {0:s} sortBy dc.date/sort.ascending".format(ppn)
        client = Sru()
        with tqdm(desc=u"URLs (PPN: {0:s})".format(ppn), unit="issue", miniters=1) as pbar:
            for resp in client.search(query=query, collection="DDD", maximumrecords=100, startrecord=start):
                pbar.total = len(resp)
                records = resp.record_data.findall(".//srw:records/srw:record", namespaces=NAMESPACES)
                maxpos = records[-1].findtext("./srw:recordPosition", namespaces=NAMESPACES)
                logger.info(u"Max recordPosition in response: {0:s}".format(maxpos))
                urls = map(self.get_record_url, records)
                logger.debug(u"No of URLs in response: {0}".format(len(urls)))
                with open(self.data_path + u"issues-{0:s}.txt".format(ppn), 'a') as f:
                    for url in urls:
                        f.write(url + "\n")
                pbar.update(len(urls))
                self.url_counts[ppn] += len(urls)
                sleep(2)

    def url_with_key(self, url):
        """Return the OAI-PMH request URL with this Harvester's API key if set"""
        if self.api_key is not None:
            parts = url.partition('oai')
            return "{0}{1}/{2}{3}".format(parts[0], parts[1], self.api_key, parts[2])
        else:
            return url

    def harvest_issue_files(self, url_in):
        url = self.url_with_key(url_in)
        logger.debug(u"Getting issue from {0:s}...".format(url))
        issue = self.get_issue(url, self.data_path)
        if issue.oai_data.find('{http://www.openarchives.org/OAI/2.0/}error') is not None:
            code = issue.oai_data.find('{http://www.openarchives.org/OAI/2.0/}error').attrib
            logger.error(u"OAI error found: {0:s}".format(code['code']))
            # raise Exception("OAI error! '%s'" % code)
            with open(self.data_path + "errors.tsv", 'a') as f:
                f.write("%s\t%s\n" % (url, code['code']))
            return

        # Make directory for issue
        try:
            os.mkdir(self.data_path + issue.ppn_issue)
            logger.info(u"Created directory for issue {0:s}".format(issue.ppn_issue))
        except OSError:
            # Directory already exists
            logger.debug(u"Could not create directory {0:s} - assuming it already exists".format(
                self.data_path + issue.ppn_issue))
        except AttributeError:
            # Something is incomplete
            logger.warning("Something is incomplete")
            logger.warning(issue.oai_data.find('.//oai:header', NAMESPACES))
            return

        issue.save_header()
        issue.save_metadata()
        logger.debug(u"Issue ID: {0:s}; Paper PPN: {1:s}".format(issue.identifier, issue.ppn_paper))
        issue.save_pdf()
        issue.save_pages()
        issue.save_articles()

    @staticmethod
    def get_record_url(record_data):
        key = record_data.find('.//dddx:metadataKey', NAMESPACES)
        if key is not None:
            logger.debug(u"Found record URL {0:s}".format(key.text))
            return key.text
        else:
            return "no url"

    @staticmethod
    def get_issue(issue_url, path):
        """Get the issue record (including references to files)"""
        r = requests.get(issue_url)

        if not r.status_code == 200:
            raise Exception(u'Error while getting data from {0:s}'.format(issue_url))

        logger.debug(u"Received {0:s} bytes".format(r.headers['content-length']))
        return Issue(XML(r.content), path)

    def harvest_newspaper_issues(self, ppn):
        """Retrieve issue files from stored URLs based on the newspaper PPN"""
        try:
            f = open(self.data_path + u"issues-{0:s}.txt".format(ppn), 'r')
        except OSError:
            logger.error(
                u"Could not read the URLs for PPN {0:s} from {1:s}".format(ppn, self.data_path + "issues-%s.txt" % ppn))
        else:
            with f:
                for line in tqdm(f, desc="Issues", total=self.url_counts[ppn], unit=" issue", position=0):
                    self.harvest_issue_files(line.strip())
                    sleep(2)

    def harvest_newspaper_error_issues(self, ppn):
        """Retrieve issue files from previously failing URLs based on the newspaper PPN"""
        try:
            with open(self.data_path + "errors.tsv", 'r') as countlines:
                for line in tqdm(countlines, desc='Errors', unit=' URL'):
                    self.url_counts[ppn] += 1

            f = open(self.data_path + "errors.tsv", 'r')
        except OSError:
            logger.error(u"Could not read the URLs for PPN {0:s} from {1:s}".format(ppn, self.data_path + "errors.tsv"))
        else:
            with f:
                for line in tqdm(f, desc="Issues", total=self.url_counts[ppn], unit=" issue", position=0):
                    self.harvest_issue_files(line.split('\t')[0])
                    sleep(2)