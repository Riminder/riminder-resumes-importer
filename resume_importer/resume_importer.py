#!/usr/bin/python3
"""Uploads resume on riminder platform."""
import argparse
import os
import sys

from resume_importer import Upload_supervisor


def parse_args():
    """Parse command line argument."""
    argsParser = argparse.ArgumentParser(description='Send resume to the platform.')
    argsParser.add_argument('--paths', nargs='*', required=True)
    argsParser.add_argument('-r', action='store_const', const=True, default=False)
    argsParser.add_argument('--source_id', default=None)
    argsParser.add_argument('--api_key', default=None)
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
    return ext in Upload_supervisor.VALID_EXTENSIONS


def is_valid_filename(file_path):
    """Check if a filename is valid."""
    name = os.path.basename(file_path)
    return name not in Upload_supervisor.INVALID_FILENAME


def get_files_from_dir(dir_path, is_recurcive):
    """Get all filepath from a given directory."""
    file_res = []
    files_path = os.listdir(dir_path)

    for file_path in files_path:
        # true path is the path from the dir_path to the selected file
        true_path = os.path.join(dir_path, file_path)

        # Get file recursivly in subdirectories if asked
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


def get_from_stdin(message):
    """Prompt a message and wait for user input."""
    print(message, end='', flush=True)
    res = sys.stdin.readline()
    res = res[:-1]
    return res


def get_user_data(args):
    """Get command line missing datas."""
    if args.api_key is None:
        args.api_key = get_from_stdin('api secret key: ')
    if args.source_id is None:
        args.source_id = get_from_stdin('source id: ')
    return args


def main():
    """Well..."""
    # Prepare upload
    args = parse_args()
    args = get_user_data(args)
    paths = get_filepaths_to_send(args.paths, args.r)

    # Start upload.
    supervisor = Upload_supervisor.UploadSupervisor(args, paths)
    supervisor.start()


if __name__ == '__main__':
    main()
