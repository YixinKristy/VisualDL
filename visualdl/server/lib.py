# Copyright (c) 2017 VisualDL Authors. All Rights Reserve.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =======================================================================

from __future__ import absolute_import
from functools import partial  # noqa: F401
import sys
import time
import os
import io
import csv
import numpy as np
from visualdl.server.log import logger
from visualdl.io import bfile
from visualdl.utils.string_util import encode_tag, decode_tag
from visualdl.component import components


MODIFY_PREFIX = {}
MODIFIED_RUNS = []
EMBEDDING_NAME = {}
embedding_names = []


def s2ms(timestamp):
    return timestamp * 1000 if timestamp < 2000000000 else timestamp


def get_components(log_reader):
    components = log_reader.components(update=True)
    return list(components)


def get_runs(log_reader):
    runs = []
    for item in log_reader.runs():
        if item in log_reader.tags2name:
            runs.append(log_reader.tags2name[item])
        else:
            runs.append(item)
    return runs


def get_tags(log_reader):
    return log_reader.tags()


def get_logs(log_reader, component):
    all_tag = log_reader.data_manager.get_reservoir(component).keys
    tags = {}
    for item in all_tag:
        index = item.rfind('/')
        run = item[0:index]
        tag = encode_tag(item[index + 1:])
        if run in tags.keys():
            tags[run].append(tag)
        else:
            tags[run] = [tag]
        if run not in log_reader.tags2name.keys():
            log_reader.tags2name[run] = run
            log_reader.name2tags[run] = run
    fake_tags = {}
    for key, value in tags.items():
        if key in log_reader.tags2name:
            fake_tags[log_reader.tags2name[key]] = value
        else:
            fake_tags[key] = value

    run2tag = {'runs': [], 'tags': []}
    for run, tags in fake_tags.items():
        run2tag['runs'].append(run)
        run2tag['tags'].append(tags)

    run_prefix = os.getenv('VISUALDL_RUN_PREFIX')
    global MODIFY_PREFIX, MODIFIED_RUNS
    if component not in MODIFY_PREFIX:
        MODIFY_PREFIX.update({component: False})
    if run_prefix and not MODIFY_PREFIX[component]:
        MODIFY_PREFIX[component] = True
        temp_name2tags = log_reader.name2tags.copy()
        for key, value in temp_name2tags.items():
            if key in MODIFIED_RUNS:
                continue
            index = key.find(run_prefix)
            if index != -1:
                temp_key = key[index+len(run_prefix):]

                log_reader.name2tags.pop(key)
                log_reader.name2tags.update({temp_key: value})

                log_reader.tags2name.pop(value)
                log_reader.tags2name.update({value: temp_key})

                run2tag['runs'][run2tag['runs'].index(key)] = temp_key
            else:
                temp_key = key

            MODIFIED_RUNS.append(temp_key)

    return run2tag


for name in components.keys():
    exec("get_%s_tags=partial(get_logs, component='%s')" % (name, name))


def get_scalar(log_reader, run, tag):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("scalar").get_items(
        run, decode_tag(tag))
    results = [[s2ms(item.timestamp), item.id, item.value] for item in records]
    return results


def get_scalar_data(log_reader, run, tag, type='tsv'):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    result = log_reader.get_log_data('scalar', run, decode_tag(tag))
    delimeter = '\t' if 'tsv' == type else ','
    with io.StringIO() as fp:
        csv_writer = csv.writer(fp, delimiter=delimeter)
        csv_writer.writerow(['id', 'tag', 'timestamp', 'value'])
        csv_writer.writerows(result)
        result = fp.getvalue()
        return result


def get_image_tag_steps(log_reader, run, tag):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("image").get_items(
        run, decode_tag(tag))
    result = [{
        "step": item.id,
        "wallTime": s2ms(item.timestamp)
    } for item in records]
    return result


def get_individual_image(log_reader, run, tag, step_index):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("image").get_items(
        run, decode_tag(tag))
    return records[step_index].image.encoded_image_string


def get_text_tag_steps(log_reader, run, tag):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("text").get_items(
        run, decode_tag(tag))
    result = [{
        "step": item.id,
        "wallTime": s2ms(item.timestamp)
    } for item in records]
    return result


def get_individual_text(log_reader, run, tag, step_index):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("text").get_items(
        run, decode_tag(tag))
    return records[step_index].text.encoded_text_string


def get_audio_tag_steps(log_reader, run, tag):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("audio").get_items(
        run, decode_tag(tag))
    result = [{
        "step": item.id,
        "wallTime": s2ms(item.timestamp)
    } for item in records]
    return result


def get_individual_audio(log_reader, run, tag, step_index):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("audio").get_items(
        run, decode_tag(tag))
    result = records[step_index].audio.encoded_audio_string
    return result


def get_pr_curve(log_reader, run, tag):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("pr_curve").get_items(
        run, decode_tag(tag))
    results = []
    for item in records:
        pr_curve = item.pr_curve
        length = len(pr_curve.precision)
        num_thresholds = [float(v) / length for v in range(1, length + 1)]
        results.append([s2ms(item.timestamp),
                        item.id,
                        list(pr_curve.precision),
                        list(pr_curve.recall),
                        list(pr_curve.TP),
                        list(pr_curve.FP),
                        list(pr_curve.TN),
                        list(pr_curve.FN),
                        num_thresholds])
    return results


def get_roc_curve(log_reader, run, tag):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("roc_curve").get_items(
        run, decode_tag(tag))
    results = []
    for item in records:
        roc_curve = item.roc_curve
        length = len(roc_curve.tpr)
        num_thresholds = [float(v) / length for v in range(1, length + 1)]
        results.append([s2ms(item.timestamp),
                        item.id,
                        list(roc_curve.tpr),
                        list(roc_curve.fpr),
                        list(roc_curve.TP),
                        list(roc_curve.FP),
                        list(roc_curve.TN),
                        list(roc_curve.FN),
                        num_thresholds])
    return results


def get_pr_curve_step(log_reader, run, tag=None):
    fake_run = run
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    run2tag = get_pr_curve_tags(log_reader)  # noqa: F821
    tag = run2tag['tags'][run2tag['runs'].index(fake_run)][0]
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("pr_curve").get_items(
        run, decode_tag(tag))
    results = [[s2ms(item.timestamp), item.id] for item in records]
    return results


def get_roc_curve_step(log_reader, run, tag=None):
    fake_run = run
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    run2tag = get_roc_curve_tags(log_reader)  # noqa: F821
    tag = run2tag['tags'][run2tag['runs'].index(fake_run)][0]
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("roc_curve").get_items(
        run, decode_tag(tag))
    results = [[s2ms(item.timestamp), item.id] for item in records]
    return results


def get_embeddings_list(log_reader):
    run2tag = get_logs(log_reader, 'embeddings')

    for run, _tags in zip(run2tag['runs'], run2tag['tags']):
        run = log_reader.name2tags[run] if run in log_reader.name2tags else run
        for tag in _tags:
            name = path = os.path.join(run, tag)
            if name in EMBEDDING_NAME:
                return embedding_names
            EMBEDDING_NAME.update({name: {'run': run, 'tag': tag}})
            records = log_reader.data_manager.get_reservoir("embeddings").get_items(
                run, decode_tag(tag))
            row_len = len(records[0].embeddings.embeddings)
            col_len = len(records[0].embeddings.embeddings[0].vectors)
            shape = [row_len, col_len]
            embedding_names.append({'name': name, 'shape': shape, 'path': path})
    return embedding_names


def get_embedding_labels(log_reader, name):
    run = EMBEDDING_NAME[name]['run']
    tag = EMBEDDING_NAME[name]['tag']
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("embeddings").get_items(
        run, decode_tag(tag))
    labels = []
    for item in records[0].embeddings.embeddings:
        labels.append(item.label)

    label_meta = records[0].embeddings.label_meta
    if label_meta:
        labels = [label_meta] + labels

    with io.StringIO() as fp:
        csv_writer = csv.writer(fp, delimiter='\t')
        csv_writer.writerows(labels)
        labels = fp.getvalue()

    # labels = "\n".join(str(i) for i in labels)
    return labels


def get_embedding_tensors(log_reader, name):
    run = EMBEDDING_NAME[name]['run']
    tag = EMBEDDING_NAME[name]['tag']
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("embeddings").get_items(
        run, decode_tag(tag))
    vectors = []
    for item in records[0].embeddings.embeddings:
        vectors.append(item.vectors)
    vectors = np.array(vectors).flatten().astype(np.float32).tobytes()
    return vectors


def get_histogram(log_reader, run, tag):
    run = log_reader.name2tags[run] if run in log_reader.name2tags else run
    log_reader.load_new_data()
    records = log_reader.data_manager.get_reservoir("histogram").get_items(
        run, decode_tag(tag))

    results = []
    for item in records:
        histogram = item.histogram
        hist = histogram.hist
        bin_edges = histogram.bin_edges
        histogram_data = []
        for index in range(len(hist)):
            histogram_data.append([bin_edges[index], bin_edges[index+1], hist[index]])
        results.append([s2ms(item.timestamp), item.id, histogram_data])

    return results


def get_graph(log_reader):
    result = b""
    if log_reader.model:
        with bfile.BFile(log_reader.model, 'rb') as bfp:
            result = bfp.read_file(log_reader.model)
    return result


def retry(ntimes, function, time2sleep, *args, **kwargs):
    """
    try to execute `function` `ntimes`, if exception catched, the thread will
    sleep `time2sleep` seconds.
    """
    for i in range(ntimes):
        try:
            return function(*args, **kwargs)
        except Exception:
            if i < ntimes-1:
                error_info = '\n'.join(map(str, sys.exc_info()))
                logger.error("Unexpected error: %s" % error_info)
                time.sleep(time2sleep)
            else:
                import traceback
                traceback.print_exc()


def cache_get(cache):
    def _handler(key, func, *args, **kwargs):
        data = cache.get(key)
        if data is None:
            logger.warning('update cache %s' % key)
            data = func(*args, **kwargs)
            cache.set(key, data)
            return data
        return data

    return _handler
