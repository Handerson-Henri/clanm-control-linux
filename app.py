#!/usr/bin/env python3
import argparse
import json
from clanm import backend

def main():
    parser=argparse.ArgumentParser(description='Clanm Control Linux')
    parser.add_argument('--detect',action='store_true')
    parser.add_argument('--preview',metavar='PNG',help='Renderizar interface em display de teste')
    args=parser.parse_args()
    if args.detect:
        print(json.dumps(backend.detect(),indent=2,ensure_ascii=False));return
    from clanm.ui import run
    run(args.preview)

if __name__=='__main__':main()
