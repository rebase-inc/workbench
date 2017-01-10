import os
import time
from multiprocessing import current_process

from rq import Queue
from redis import StrictRedis
from github import Github

import authgen
import rsyslog

current_process().name = os.environ['HOSTNAME']
rsyslog.setup(log_level = os.environ['LOG_LEVEL'])

USERNAME = os.environ['GITHUB_CRAWLER_USERNAME']
PASSWORD = os.environ['GITHUB_CRAWLER_PASSWORD']

def scan_public_users(*github_ids, show_progress = True):
    connection = StrictRedis(host = 'redis', port = 6379)
    crawler_queue = Queue('public_github_scanner', connection = connection)
    population_queue = Queue('population_analyzer', connection = connection)
    jobs = []
    for github_id in github_ids:
        access_token = authgen.create_github_access_token(USERNAME, PASSWORD, 'public scan {}'.format(github_id))
        scan_repos = crawler_queue.enqueue_call(func = 'scanner.scan_all_repos', args = (access_token, github_id), timeout = 3600, result_ttl=86400)
        delete_token = crawler_queue.enqueue_call(func = 'scanner.delete_github_access_token', args = (USERNAME, PASSWORD, access_token), timeout = 60, depends_on = scan_repos)
        jobs.append((scan_repos, delete_token))
    if show_progress:
        show_scan_progress(*jobs)
    else:
        return [ (a.id, b.id, c.id) for (a,b,c) in jobs ]

def show_scan_progress(*scan_jobs):
    from IPython.lib import backgroundjobs
    bgjobs = backgroundjobs.BackgroundJobManager()
    for scan_job in reversed(scan_jobs): # ipywidgets displays newest things on top
        #_show_scan_progress(scan_job)
        bgjobs.new(_show_scan_progress, scan_job)

def _show_scan_progress(scan_job):
    from ipywidgets import FloatProgress, Label, VBox, HBox
    from IPython.display import display
    progress_bars = []
    label = Label('GitHub user "{}"'.format(scan_job[0].args[-1]))
    progress_bars.append(HBox([FloatProgress(value=0.0, min=0.0, max=1.0, step=0.01, bar_style='info'), Label('Scan user repositories')]))
    progress_bars.append(HBox([FloatProgress(value=0.0, min=0.0, max=1.0, step=0.01, bar_style='info'), Label('Delete authentication token')]))
    box = VBox([label] + progress_bars)
    display(box)
    finished = 0
    while True:
        for job, progress_bar in zip(scan_job, progress_bars):
            if job.status in ['queued', 'started', 'deferred']:
                time.sleep(5)
                continue
            elif job.status == 'finished':
                finished += 1
                progress_bar.children[0].value = 1.0
                progress_bar.children[0].bar_style = 'success'
                print(job.result)
            else:
                finished += 1
                progress_bar.children[0].value = 1.0
                progress_bar.children[0].bar_style = 'danger'
        if finished == len(scan_job):
            break
