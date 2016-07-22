import os
import errno
from sru import Sru
from time import sleep
from xml.etree.ElementTree import ElementTree as ET
from xml.etree.ElementTree import XML
import hashlib
import requests
import logging

logger = logging.getLogger('KB-harvester')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("KB-harvester.log")
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
        self.oai_data = oai_data
        self.oai_header = oai_data.find('.//oai:header', NAMESPACES)
        self.didl = oai_data.find('.//didl:DIDL', NAMESPACES)
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
        logger.debug("Checking existence of %s" % filename)
        try:
            f = open(self.issue_path + filename, 'r')
        except OSError:
            logger.debug("%s does not exist")
            return False
        else:
            with f:
                return check_md5(f,digest)

    def save_binary(self, url, digest, filename):
        if not self.check_file_existence(filename, digest):
            logger.debug("Downloading %s" % url)
            p = requests.get(url)
            if not p.status_code == 200:
                raise Exception('Error while getting data from %s' % url)
            logger.debug("MD5 checksum matches download: %s" % check_md5(p.content, digest))
            logger.debug("Saving as %s" % filename)
            with open(self.issue_path + filename, 'wb') as f:
                f.write(p.content)
            logger.info("Saved %s to %s" % (url, filename))
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
        for page in pages:
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
        for article in articles:
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
    def __init__(self, path="data/"):
        self.data_path = path
        try:
            os.access(self.data_path, os.F_OK)
            os.makedirs(path=self.data_path)
        except IOError as ioe:
            if ioe.errno == errno.EACCES:
                logger.critical(ioe)
                exit(1)
            elif ioe.errno == errno.EEXIST:
                logger.debug("Data path already exists")
        except OSError:
            logger.critical("Could not create data storage path '%s'" % path)
            exit(1)

    def harvest_newspaper_urls(self, ppn, start=1):
        """Get and process all issues of a newspaper identified by PPN"""
        query = "ppn exact %s sortBy dc.date/sort.ascending" % ppn
        client = Sru()
        for resp in client.search(query=query, collection="DDD", maximumrecords=100, startrecord=start):
            records = resp.record_data.findall(".//srw:records/srw:record", namespaces=NAMESPACES)
            maxpos = records[-1].findtext("./srw:recordPosition", namespaces=NAMESPACES)
            print "Max recordPosition in response:", maxpos
            urls = map(self.get_record_url, records)
            with open("issues-%s.txt" % ppn, 'a') as f:
                for url in urls:
                    f.write(url + "\n")
            sleep(5)

    def harvest_issue_files(self, url):
        issue = self.get_issue(url, self.data_path)

        # Make directory for issue
        try:
            os.mkdir(self.data_path + issue.ppn_issue)
            logger.info("Created directory for %s" % issue.ppn_issue)
        except OSError:
            # Directory already exists
            logger.debug("Could not create directory %s - assuming it already exists" % self.data_path + issue.ppn_issue)

        issue.save_header()
        issue.save_metadata()
        logger.debug("Issue ID: %s; Paper PPN: %s" % (issue.identifier, issue.ppn_paper))
        issue.save_pdf()
        issue.save_pages()
        issue.save_articles()

    @staticmethod
    def get_record_url(record_data):
        key = record_data.find('.//dddx:metadataKey', NAMESPACES)
        if key is not None:
            return key.text
        else:
            return "no url"

    @staticmethod
    def get_issue(issue_url, path):
        """Get the issue record (including references to files)"""
        r = requests.get(issue_url)

        if not r.status_code == 200:
            raise Exception('Error while getting data from %s' % issue_url)

        return Issue(XML(r.content), path)

    def harvest_newspaper_issues(self, ppn):
        """Retrieve issue files from stored URLs based on the newspaper PPN"""
        try:
            f = open(self.data_path + "issues-%s.txt" % ppn, 'r')
        except OSError as e:
            print "You should harvest the URLs for PPN %s first. Did you?"
        else:
            with f:
                for line in f:
                    self.harvest_issue_files(line)
                    sleep(2)
