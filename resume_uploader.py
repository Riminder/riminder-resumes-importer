#!/usr/bin/python3
"""Uploads resume on riminder platform."""
import random
import threading
import argparse
import os
import json
import sys
import time

import riminder

VALID_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.doc', '.docx', '.rtf', '.dotx', '.odt', 'odp', 'ppt', 'pptx', 'rtf', 'msg']
INVALID_FILENAME = ['.', '..']
SIZE_PROGRESS_BAR = 50

VERBOSE_LEVEL_SILENT = 'silent'
VERBOSE_LEVEL_NORMAL = 'normal'
VERBOSE_LEVEL_VERBOSE = 'verbose'


class Upload_result(object):
    """Container for upload result."""

    def __init__(self):
        """Init."""
        self.is_success = False
        self.result = None
        self.file = None

    def setFailure(self, err, file):
        """Set the object with a failed upload."""
        self.is_success = False
        self.result = err
        self.file = file

    def setSuccess(self, resp, file):
        """Set the object with a succeed upload."""
        self.is_success = True
        self.result = resp
        self.file = file


class Upload_worker(threading.Thread):
    """Worker for that manage upload."""

    def __init__(self, worker_id, api, source_id, timestamp_reception):
        """Init."""
        threading.Thread.__init__(self)
        self.file_to_process = None
        self.callback = None
        self.api = api
        self.source_id = source_id
        self.timestamp_reception = timestamp_reception
        self.worker_id = worker_id

    def set_file(self, file, cb):
        """Add a for next upload."""
        self.file_to_process = file
        self.callback = cb

    def process_file(self):
        """Upload file and notify supervisor."""
        res = send_file(self.api, self.source_id, self.file_to_process, self.timestamp_reception)
        self.file_to_process = None
        self.callback(self.worker_id, res)

    def run(self):
        """Upload file until no file is place by callback."""
        while self.file_to_process is not None:
            self.process_file()


class UploadSupervisor(object):
    """Manage upload, worker, and logging."""

    def __init__(self, cml_args, files):
        """Init using command args datas and files to upload."""
        self.api = riminder.Riminder(cml_args.api_key)
        self.paths = files
        self.is_recurcive = cml_args.r
        self.source_id = cml_args.source_id
        self.v_level = VERBOSE_LEVEL_NORMAL
        if args.silent:
            self.v_level = VERBOSE_LEVEL_SILENT
        if args.verbose:
            self.v_level = VERBOSE_LEVEL_VERBOSE
        self.n_worker = cml_args.n_worker
        self.timestamp_reception = cml_args.timestamp_reception
        self.workers = {}
        self.lock_worker = threading.Lock()
        self.lock_printer = threading.Lock()
        self.results = []
        self.n_failed = 0
        self.n_file_to_send = len(self.paths)
        self.logfile = None
        if cml_args.logfile is not None:
            self.logfile = open(cml_args.logfile, mode='w')

    def _set_worker_file(self, workerID):
        if len(self.paths) == 0:
            return
        self.workers[workerID].set_file(self.paths.pop(), self.worker_callback)

    def _init_workers(self):
        for i in range(self.n_worker):
            self.workers[i] = Upload_worker(i, self.api, self.source_id, self.timestamp_reception)
            self._set_worker_file(i)

    def worker_callback(self, workerID, file_result):
        """Callback function used by workers to notify when file has been sended."""
        self.lock_worker.acquire()
        self.results.append(file_result)
        if not file_result.is_success:
            self.n_failed += 1
        self._set_worker_file(workerID)

        self.print_update(file_result)
        self.lock_worker.release()

    def start(self):
        """Start process."""
        self.print_start()
        self._init_workers()
        self.lock_worker.acquire()
        if self.v_level == VERBOSE_LEVEL_NORMAL:
            self.print_update(None)
        for idx, w in enumerate(self.workers):
            self.workers[idx].start()
            time.sleep(0.1)
        self.lock_worker.release()

        for idx, w in enumerate(self.workers):
            self.workers[idx].join()
        self.print_end()

    def _calc_percentage_processed(self, on=100):
        return int((len(self.results) * on) / self.n_file_to_send)

    def _print_update_progress_bar(self):
        percent_proceed = self._calc_percentage_processed()
        progress_bar_processed = self._calc_percentage_processed(SIZE_PROGRESS_BAR)
        random_pic = random.randint(0, 5)

        bar = ''
        bar2 = ''
        for i in range(SIZE_PROGRESS_BAR):
            c = ' '
            if i < progress_bar_processed:
                c = '='
            bar += c
        bar = '[{}]'.format(bar)

        for z in range(5):
            c = '.'
            if z == random_pic:
                c = ' '
            bar2 += c

        to_print = '{} %{} {}     \r'.format(bar, percent_proceed, bar2)
        return to_print

    def _print_finished_file(self, file_result, add_percentage=True):
        percent_proceed = self._calc_percentage_processed()
        file_data = {'file': file_result.file, 'sended': file_result.is_success, 'result': str(file_result.result)}
        file_data = json.dumps(file_data)
        if add_percentage:
            return '[%{}] - {}\n'.format(percent_proceed, file_data)
        return '{}\n'.format(file_data)

    def _print_all_file_to_send(self):
        to_send = ''
        for path in self.paths:
            to_send += '{}\n'.format(path)
        return to_send

    def _print_numerical_datas(self, n_sended=False, n_total=False, n_failed=False):
        to_print = ''
        if n_sended:
            to_print += 'sended: {}\n'.format(self.n_file_to_send - self.n_failed)
        if n_failed:
            to_print += 'failed: {}\n'.format(self.n_failed)
        if n_total:
            to_print += 'total: {}\n'.format(self.n_file_to_send)
        return to_print

    def print_something(self, to_print, is_err=False, is_no_end=False):
        """Print on term."""
        self.lock_printer.acquire()
        out = sys.stdout
        end = '\n'
        if is_err:
            out = sys.stderr
        if is_no_end:
            end = ''
        print(to_print, file=out, end=end, flush=True)
        self.lock_printer.release()

    def print_start(self):
        """Print data a start."""
        if self.v_level == VERBOSE_LEVEL_SILENT:
            return
        to_print = ''
        if self.v_level != VERBOSE_LEVEL_SILENT:
            to_print = 'file to send: {}'.format(self._print_numerical_datas(n_total=True))
        if self.v_level == VERBOSE_LEVEL_VERBOSE:
            to_print += self._print_all_file_to_send()
        self.print_something(to_print)

    def print_update(self, last_file_result):
        """Print data when a file has been sent."""
        if self.v_level == VERBOSE_LEVEL_SILENT:
            return
        to_print = ''
        if self.v_level == VERBOSE_LEVEL_NORMAL:
            to_print = self._print_update_progress_bar()
            self.print_something(to_print, is_no_end=True)
        if self.v_level == VERBOSE_LEVEL_VERBOSE:
            to_print = self._print_finished_file(last_file_result)
            to_print = to_print[:-1]
            self.print_something(to_print)
        if self.logfile is not None and last_file_result is not None:
            to_print = self._print_finished_file(last_file_result, add_percentage=False)
            self.logfile.write(to_print)

    def print_end(self):
        """Print data when all process is done."""
        if self.v_level == VERBOSE_LEVEL_SILENT:
            return
        to_print = ''
        to_print_file = ''
        if self.v_level == VERBOSE_LEVEL_VERBOSE:
            for res in self.results:
                to_print_file += self._print_finished_file(res, add_percentage=False)
            to_print += self._print_numerical_datas(n_total=True, n_sended=True, n_failed=True)
            self.print_something(to_print_file, is_err=True)
            self.print_something(to_print)
            return
        if self.v_level == VERBOSE_LEVEL_NORMAL:
            for res in self.results:
                if not res.is_success:
                    to_print_file += self._print_finished_file(res, add_percentage=False)
            to_print += self._print_numerical_datas(n_total=True, n_sended=True, n_failed=True)
            self.print_something(to_print_file, is_err=True)
            self.print_something(to_print)


def parse_args():
    """Parse command line argument."""
    argsParser = argparse.ArgumentParser(description='Send resume to the platform.')
    argsParser.add_argument('--paths', nargs='*', required=True)
    argsParser.add_argument('-r', action='store_const', const=True, default=False)
    argsParser.add_argument('--source_id', required=True)
    argsParser.add_argument('--api_key', required=True)
    argsParser.add_argument('--timestamp_reception', default=None)
    argsParser.add_argument('--verbose', action='store_const', const=True, default=False)
    argsParser.add_argument('--silent', action='store_const', const=True, default=False)
    argsParser.add_argument('--n-worker', default=3)
    argsParser.add_argument('--logfile', default=None, required=False)
    args = argsParser.parse_args()
    return args


def is_valid_extension(file_path):
    """Check if an file extension is valid."""
    ext = os.path.splitext(file_path)[1]
    if not ext:
        return False
    return ext in VALID_EXTENSIONS


def is_valid_filename(file_path):
    """Check if a filename is valid."""
    name = os.path.basename(file_path)
    return name not in INVALID_FILENAME


def get_files_from_dir(dir_path, is_recurcive):
    """Get all filepath from a given directory."""
    file_res = []
    files_path = os.listdir(dir_path)

    for file_path in files_path:
        true_path = os.path.join(dir_path, file_path)
        if os.path.isdir(true_path) and is_recurcive:
            if is_valid_filename(true_path):
                file_res += get_files_from_dir(true_path, is_recurcive)
            continue
        if is_valid_extension(true_path):
            file_res.append(true_path)
    return file_res


def get_filepaths_to_send(paths, is_recurcive):
    """Get all file path from a list of file and dirs."""
    res = []
    for fpath in paths:
        if not is_valid_filename(fpath):
            continue
        if os.path.isdir(fpath):
            res += get_files_from_dir(fpath, is_recurcive)
            continue
        if not is_valid_extension(fpath):
            continue
        res.append(fpath)
    return res


def send_file(api_client, source_id, file_path, timestamp_reception):
    """Send a resume using riminder python api."""
    res = Upload_result()
    try:
        resp = api_client.profile.add(source_id=source_id,
            file_path=file_path,
            timestamp_reception=timestamp_reception)
        if resp['code'] != 200 and resp['code'] != 201:
            res.setFailure(ValueError('Invalid response: ' + str(resp)), file_path)
        else:
            res.setSuccess(resp, file_path)
    except BaseException as e:
        res.setFailure(e, file_path)
    return res


args = parse_args()
paths = get_filepaths_to_send(args.paths, args.r)
supervisor = UploadSupervisor(args, paths)
supervisor.start()
