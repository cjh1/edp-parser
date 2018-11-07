import json
import glob
import re
import click
from girder_client import GirderClient

channel_to_element = {
    'A': 'mn',
    'B': 'fe',
    'C': 'ni',
    'D': 'cu',
    'E': 'co',
    'F': 'zn'
}

def _ingest_runs(gc, project, composite, dir):
    # Find the exp file
    [exp_path] = glob.glob('%s/**/*.exp.json' % dir, recursive=True)

    # Extract run information
    with open(exp_path) as f:
        exp = json.load(f)

    run_ids = exp['run_ids']

    runs = {}
    for run_id, name in zip(run_ids, [x['rcp_file'] for x in exp['runs']]):
        run_file = glob.glob('%s/**/%s.json' % (dir, name), recursive=True)
        assert len(run_file) == 1
        with open(run_file[0]) as f:
            run = json.load(f)
            for key in list(run.keys()):
                if key.startswith('files_technique__'):
                    del run[key]

                #if key.startswith('echem_params'):
                #    print(key)

            run = {
                'runId': run_id,
                'solutionPh': float(run['solution_ph']),
                'plateId': run['plate_id'],
                'electrolyte': run['electrolyte']
            }

            run = gc.post('edp/projects/%s/composites/%s/runs' % (project, composite), json=run)
            runs[run_id] = run['_id']


    return (run_ids, runs)

def _ingest_samples(gc, project, composite, dir, ana_file, run_map):

    samples = {}
    scalars_to_extract = ['Emin.Vrhe', 'Emax.Vrhe', 'Jmin.mAcm2', 'Jmax.mAcm2']
    comp_regex = re.compile('([a-zA-Z]+)\.PM.AtFrac')


    [ana_file] = glob.glob('%s/**/%s' % (dir, ana_file), recursive=True)

    with open(ana_file) as f:
        ana = json.load(f)

    run_ids = ana['run_ids']
    for key, value in ana.items():
        if key.startswith('ana__'):
            [file_path] = value['files_multi_run']['fom_files'].keys()
            plate_ids = value['plate_ids']

            if 'platemap_comp4plot_keylist' not in value['parameters']:
                continue

            keylist = value['parameters']['platemap_comp4plot_keylist']

            elements = [channel_to_element[x] for x in keylist]

            platemap = {
                'plateId': plate_ids,
                'elements': elements
            }

            [file_path] = glob.glob('%s/**/%s.json' % (dir, file_path), recursive=True)
            with open(file_path) as lf:
                loading = json.load(lf)
            sample_numbers = loading['sample_no']
            run_ints = loading['runint']
            plate_ids = loading['plate_id']

            compositions = {}
            for key, value in loading.items():
                match = comp_regex.match(key)
                if match:
                    element = match.group(1).lower()
                    if element in elements:
                        compositions[element] = value

            for i, (plate_id, sample_number, run_int) in enumerate(zip(plate_ids, sample_numbers, run_ints)):
                # Only process if we haven't already seen it in another platemap
                if sample_number not in samples.setdefault(plate_id, {}):
                    sample_meta = {}
                    sample_meta['runId'] = run_map[run_ids[int(run_int)-1]]
                    sample_meta['sampleNum'] = sample_number

                    comp = {}
                    sample_meta['composition'] = comp
                    for e in compositions.keys():
                        comp[e] = compositions[e][i]

                    scalars = sample_meta.setdefault('scalars', {})
                    for s in scalars_to_extract:
                        if s in loading:
                            # We need to replace . with the unicode char so we
                            # can store the key in mongo
                            k = s.replace('.', '\\u002e')
                            scalars[k] = loading[s][i]

                    sample = gc.post('edp/projects/%s/composites/%s/samples'
                                        % (project, composite), json=sample_meta)

                    samples.setdefault(plate_id, {})[sample_number] = sample

                    # Now look up time series data
                    [timeseries_file] = glob.glob('%s**/ana__1__Sample%d_*.txt.json'
                                                    % (dir, sample_number), recursive=True)
                    #timeseries_ids = []
                    #for timeseries_file in timeseries_files:
                    with open(timeseries_file) as tf:
                        timeseries = json.load(tf)
                        timeseries = {key.replace('.', '\\u002e'):value for (key,value) in timeseries.items()}
                        timeseries = {
                            'data': timeseries
                        }
                        timeseries = gc.post(
                            'edp/projects/%s/composites/%s/samples/%s/timeseries'
                                % (project, composite,sample['_id']), json=timeseries)
                else:
                    sample = samples.setdefault(plate_id, {}).get(sample_number)


                platemap.setdefault('sampleIds', []).append(sample['_id'])

            # Now create the plate map
            platemap = gc.post('edp/projects/%s/composites/%s/platemaps' % (project, composite), json=platemap)


@click.command(help='Ingest data')
@click.option('-p', '--project', default=None, help='the project id', required=True)
@click.option('-c', '--composite', default=None, help='the composite id', required=True)
@click.option('-d', '--dir', help='base path to data to ingest',
              type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True), default='.')
@click.option('-a', '--ana-file', default=None,
              help='the ana file to process',
              type=str, required=True)
@click.option('-u', '--api-url', default='http://localhost:8080/api/v1', help='RESTful API URL '
                   '(e.g https://girder.example.com/api/v1)')
@click.option('-k', '--api-key', envvar='GIRDER_API_KEY', default=None,
              help='[default: GIRDER_API_KEY env. variable]', required=True)
def _ingest(project, composite, dir, ana_file, api_url, api_key):
    if dir[-1] != '/':
        dir += '/'
    gc = GirderClient(apiUrl=api_url)
    gc.authenticate(apiKey=api_key)

    (run_ids, runs) = _ingest_runs(gc, project, composite, dir)
    _ingest_samples(gc, project, composite, dir, ana_file, runs)

if __name__ == '__main__':
    _ingest()
