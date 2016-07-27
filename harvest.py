from nl.leidenuniv.library.harvester.harvester import Harvester
import argparse

parser = argparse.ArgumentParser(description='Harvest newspaper files by PPN.')
parser.add_argument('ppn', metavar='PPN',
                    help='the PPN of the newspaper to harvest')
parser.add_argument('--dir', metavar='directory', default='data/',
                    help='directory to store data in (default: ./data)')

args = parser.parse_args()

harv = Harvester(args.dir)
harv.harvest_newspaper_urls(args.ppn)
harv.harvest_newspaper_issues(args.ppn)
