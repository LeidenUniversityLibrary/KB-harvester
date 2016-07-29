# KB harvester

This package provides a convenience tool and library for downloading metadata and files for historical newspapers from
the [Koninklijke Bibliotheek](https://www.kb.nl) (the Royal Library/National Library of the Netherlands).
The KB provides a [Python client module to access their data services APIs](https://github.com/KBNLresearch/KB-python-API), which uses SRU and OAI-PMH.
The library provided in this package wraps it to provide a simple interface allowing you to gather all publicly available files for newspapers identified by their PPN and save them locally.

*Be aware that the data you may download using this tool may not be redistributed or used for all purposes without clearing database and/or copyrights. See the [usage guidelines for Delpher](http://www.delpher.nl/nl/platform/pages/helpitems?title=gebruiksvoorwaarden) for more information or contact [KB Data Services](https://www.kb.nl/bronnen-zoekwijzers/dataservices-en-apis) for more information.*

## Installation

First, clone or download this repository to your machine:

    git clone https://github.com/bencomp/KB-harvester.git
    cd KB-harvester

The KB harvester depends on three packages: [`kb`](https://pypi.python.org/pypi/kb/), [`tqdm`](https://pypi.python.org/pypi/tqdm) and [`requests`](https://pypi.python.org/pypi/requests). If you have these installed in your environment or virtualenv and only want to run the command-line tool `harvest.py`, you're good to go. Otherwise, the command

    python setup.py install

will install the dependencies and the provided module in your environment/virtualenv.

## Usage

*Again, be aware of copyrights and/or database rights involved in using the data. See above for pointers.*

From the command line, run:

    python harvest.py <PPN>

where `<PPN>` is the PPN (a record identifier) for the newspaper (the full newspaper, not an individual issue) you want to download.
Optionally you can specify where you want to save the data (the default is `./data/`) by specifying `--dir <directory>` before the PPN. (*Note: make sure the path ends with a `/`.*)

While downloading, the tool shows several progress bars that indicate time spent and the estimated time remaining. The library is setup to wait between requests to the KB, to not overload the service that also runs the excellent portal [Delpher](https://www.delpher.nl).

The `harvest.py` tool is a simple example of using the library, as it is mostly a thin wrapper around it.
To use the KB harvester, consider the code below, in which `args.dir` is the optional data directory and `args.ppn` is the provided PPN.
 
    from nl.leidenuniv.library.harvester.harvester import Harvester
    
    harv = Harvester(args.dir)
    harv.harvest_newspaper_urls(args.ppn)
    harv.harvest_newspaper_issues(args.ppn)

The first line after initialising the `Harvester` collects the URLs, the second fetches the URLs and downloads the files for each issue.

## Output

The following files are produced by the tool:

- `data/issues-<PPN>.txt` holds the URLs for the metadata of each issue of newspaper `<PPN>`
- `data/<issue PPN>/` contains the files for an individual issue
- `data/<issue PPN>/<issue PPN>.oai-header.xml` is the OAI-PMH header that came with the metadata
- `data/<issue PPN>/<issue PPN>.didl.xml` is the issue metadata and structure in the DIDL format
- `data/<issue PPN>/<xxx>_<issue PPN>.pdf` is the PDF file containing the complete issue
- `data/<issue PPN>/<xxx>_<issue PPN>_<ddd>_access.jp2` is the JPEG2000 scan (lower resolution) of page `<ddd>`
- `data/<issue PPN>/<xxx>_<issue PPN>_<ddd>_alto.xml` is the ALTO XML containing the OCR results for page `<ddd>`
- `data/<issue PPN>/<xxx>_<issue PPN>_<dddd>_articletext.xml` is a simple representation of the article text for article `<dddd>`, containing separate markup for title and paragraphs
- `data/<issue PPN>/errors.tsv` is created and added to when the URL (an OAI-PMH `GetRecord` request) returns an error
- `KB-harvester.log` is a (rotated) log file containing log messages including debug messages.

Some files mentioned in the DIDL metadata are not available for download, such as the preservation (master) copies of the scans and technical metadata.

Note: the files for each issue add up to something between 5 and 100 MB, depending on the image quality and number of pages and articles.
