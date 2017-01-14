import os
import time
from collections import Counter
from multiprocessing import current_process

from rq import Queue
from redis import StrictRedis
from github import Github

import authgen
import rsyslog

current_process().name = os.environ['HOSTNAME']
rsyslog.setup(log_level = os.environ['LOG_LEVEL'])

def scan_public_users(*github_ids, show_progress = True):
    connection = StrictRedis(host = 'redis', port = 6379)
    crawler_queue = Queue('public_github_scanner', connection = connection, default_timeout = 3600)
    jobs = []
    for github_id in github_ids:
        job = crawler_queue.enqueue_call(
                func = 'scanner.scan_public_repos',
                args = (github_id,),
                result_ttl=86400,
                )
        jobs.append(job)
    if show_progress:
        show_progress_bars(*jobs)
    return jobs

def show_progress_bars(*jobs):
    from IPython.lib import backgroundjobs
    bgjobs = backgroundjobs.BackgroundJobManager()
    for job in reversed(jobs): # ipywidgets displays newest things on top
        bgjobs.new(show_progress_bar, job)
        #show_progress_bar(job)

def show_progress_bar(scan_job):
    from ipywidgets import FloatProgress, Label, VBox, HBox
    from IPython.display import display
    progress_bars = []
    scan_progress = FloatProgress(value=0.0, min=0.0, max=1.0, step=0.01, bar_style='info')
    scan_label = Label('Scan user repositories')
    box = VBox([
        Label('GitHub user "{}"'.format(scan_job.args[-1])),
        HBox([ scan_progress, scan_label ]),
        ])
    display(box)
    bar_styles = {'queued': 'info', 'started': 'info', 'deferred': 'warning', 'failed': 'danger', 'finished': 'success' }
    while 'finished' not in scan_job.meta:
        time.sleep(0.1)
        scan_job.refresh()
    while True:
        scan_job.refresh()
        percentage_complete = sum(scan_job.meta['finished'].values()) / max(sum(scan_job.meta['steps'].values()), 1)
        scan_progress.value = 1.0 if scan_job.status == 'finished' else max(0.01, percentage_complete) # the metadata is bogus once the job is finished
        scan_progress.bar_style = bar_styles[scan_job.status]
        time.sleep(2)
