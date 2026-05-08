#! /usr/bin/env python3

import argparse
import pds3parse
import csv
import itertools
import sys
import glob
import os

def to_dict(parsed, context=""):
    result = {}
    #print (parsed)
    names = [e['value']['scalar'] for e in parsed if e['name'] == 'NAME']
    objname = names[0] if names else None
    prefix = context + objname + '.' if objname else context

    for entry in parsed:
        key = prefix + entry['name']
        if entry['type'] in ('attribute', 'pointer'):
            values = entry['value']
            if isinstance(values, dict) and 'scalar' in values:
                result[key] = values['scalar'].strip()
            elif isinstance(values, dict) and 'set' in values:
                result[key] = ';'.join(
                    sub["scalar"].strip() for sub in values['set'] if "scalar" in sub)
            elif isinstance(values, list):
                result[key] = ';'.join([x['scalar'].strip() for x in values])
            else:
                print(f'Unmatched entry: {entry}')
        elif entry['type'] == 'object':
            subresult = to_dict(entry['value'], key + ".")
            result.update(subresult)
        elif entry['type'] == 'group':
            subresult = to_dict(entry['value'], key + ".")
            result.update(subresult)
        else:
            print(f'Unmatched entry: {entry}')

    return result


def file_to_dict(parser, filepath):
    print(f"Processing {filepath}...")
    with open(filepath) as f:
        data = f.read()
        parsed = parser.parse(data)
        parsed_dict = to_dict(parsed) if parsed is not None else {}
        parsed_dict['meta.filepath'] = filepath
        return parsed_dict


def find_labels(dirname, filter):
    print(f"Finding labels in {dirname} with filter {filter}")
    return (os.path.join(dirname, x) 
            for x in glob.iglob(filter, root_dir=dirname, recursive=True) 
            if os.path.isfile(os.path.join(dirname, x)))

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--output-file",
                           default="out.csv",
                           help='The name of the csv file to write to. Defaults to out.csv')
    argparser.add_argument("--src-dir",
                           default="out.csv",
                           help='The name of the directory to pull label files from. '
                                'This can supplement the list of label files or replace it. ')
    argparser.add_argument("--filter", help='A filter to apply to the labels. This is a glob pattern to match the label file name.', default="**/*.[Ll][Bb][Ll]")
    argparser.add_argument("labels", nargs="*")
    args = argparser.parse_args()

    parser = pds3parse.parser

    if args.src_dir:
        labels = itertools.chain.from_iterable((args.labels, find_labels(args.src_dir, args.filter)))
    else:
        labels = args.labels

    result = [file_to_dict(parser, filepath) for filepath in labels]

    # print(result)
    headers = set(itertools.chain.from_iterable([x.keys() for x in result]))
    with (open(args.output_file, 'w')) as outfile:
        csvout = csv.DictWriter(outfile, headers)
        csvout.writeheader()
        csvout.writerows(result)

    print("Done.")

if __name__ == '__main__':
    sys.exit(main())
