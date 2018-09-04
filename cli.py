import click
import sample
import ana_rcp
import csv
import rawlen
import json
import os
import errno


def _mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


@click.command('convert', help='Convert to JSON.')
@click.option('-f', '--file', help='path to input file',
              type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
              required=True)
@click.option('-d', '--dir', default=None,
              help='path to write the outout',
              type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True))
def _convert(file, dir):
    with open(file) as f:
        contents = f.read()
        output = None
        if file.endswith('.ana') or file.endswith('.rcp'):
            output = ana_rcp.parse_ana_rcp(contents)
        elif file.endswith('.csv'):
            output = csv.parse_csv(contents)
        elif file.endswith('rawlen.txt'):
            output = rawlen.parse_rawlen(contents)
        elif os.path.basename(file).startswith('Sample') and file.endswith('.txt'):
            output = sample.parse_sample(contents)

    if not dir:
        print(json.dumps(output, indent=4))
    else:
        if file[0] == '/':
            file = file[1:]
        output_file = os.path.join(dir,  ('%s.json' % file))
        _mkdir_p(os.path.dirname(output_file))
        with open(output_file, 'w') as o:
            json.dump(output, o, indent=4)


if __name__ == "__main__":
   _convert()
