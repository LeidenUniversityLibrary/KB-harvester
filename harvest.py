from nl.leidenuniv.library.harvester.harvester import Harvester
import argparse

parser = argparse.ArgumentParser(description='Harvest newspaper files by PPN.')
parser.add_argument('ppn', metavar='PPN',
                    help='the PPN of the newspaper to harvest')
parser.add_argument('--dir', metavar='directory', default='data/',
                    help='directory to store data in (default: ./data)')
parser.add_argument('--no-url-harvest', action='store_true', dest='no_harvest',
                    help='if specified, harvesting URLs is skipped')
parser.add_argument('--api-key', dest='api_key',
                    help='API key to use in OAI-PMH requests')
parser.add_argument('--errors-only', action='store_true', dest='errors_only',
                    help='harvest only URLs that are in the errors.tsv file')

args = parser.parse_args()

harv = Harvester(args.dir, key=args.api_key)
if not (args.errors_only or args.no_harvest):
    harv.harvest_newspaper_urls(args.ppn)

if args.errors_only:
    harv.harvest_newspaper_error_issues(args.ppn)
else:
    harv.harvest_newspaper_issues(args.ppn)
