"""Upload worker file."""

import threading

from resume_importer import Upload_result


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
        """Add a file for next upload."""
        self.file_to_process = file
        self.callback = cb

    def process_file(self):
        """Upload file and notify supervisor."""
        res = _send_file(self.api, self.source_id, self.file_to_process, self.timestamp_reception)
        self.file_to_process = None
        self.callback(self.worker_id, res)

    def run(self):
        """Upload file until no new file is placed by callback."""
        while self.file_to_process is not None:
            self.process_file()


def _send_file(api_client, source_id, file_path, timestamp_reception):
    """Send a resume using riminder python api and put result in an Upload_result object."""
    res = Upload_result.Upload_result()
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
