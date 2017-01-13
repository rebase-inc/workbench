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

def scan_public_users(*github_logins, show_progress = True):
    connection = StrictRedis(host = 'redis', port = 6379)
    crawler_queue = Queue('public_github_scanner', connection = connection, default_timeout = 3600)
    jobs = []
    for github_login in github_logins:
        access_token = authgen.create_github_access_token(USERNAME, PASSWORD, 'public scan {}'.format(github_login))
        scan_repos = crawler_queue.enqueue_call(func = 'scanner.scan_all_repos', args = (access_token, github_login), result_ttl=86400, meta = {'remaining': [], 'finished': []})
        delete_token = crawler_queue.enqueue_call(func = 'scanner.delete_github_access_token', args = (USERNAME, PASSWORD, access_token), timeout = 60, depends_on = scan_repos)
        jobs.append((scan_repos, delete_token))
    if show_progress:
        show_progress_bars(*jobs)
    return jobs


def show_progress_bars(*jobs):
    from IPython.lib import backgroundjobs
    bgjobs = backgroundjobs.BackgroundJobManager()
    for job in reversed(jobs): # ipywidgets displays newest things on top
        bgjobs.new(show_progress_bar, *job)
        #show_progress_bar(*job)

def show_progress_bar(scan_job, delete_job):
    from ipywidgets import FloatProgress, Label, VBox, HBox
    from IPython.display import display
    progress_bars = []
    scan_progress = FloatProgress(value=0.0, min=0.0, max=1.0, step=0.01, bar_style='info')
    scan_label = Label('Scan user repositories')
    delete_progress = FloatProgress(value=0.0, min=0.0, max=1.0, step=0.01, bar_style='info')
    delete_label = Label('Delete authentication token')
    box = VBox([
        Label('GitHub user "{}"'.format(scan_job.args[-1])),
        HBox([ scan_progress, scan_label ]),
        HBox([ delete_progress, delete_label ])
        ])
    display(box)
    bar_styles = {'queued': 'info', 'started': 'info', 'deferred': 'warning', 'failed': 'danger', 'finished': 'success' }
    while True:
        scan_job.refresh() # get new meta data
        scan_progress.value = len(scan_job.meta['finished']) / float(len(scan_job.meta['finished'] + scan_job.meta['remaining']) or 1.0)
        scan_progress.bar_style = bar_styles[scan_job.status]
        delete_progress.value = 0.0 if delete_job.status in ['queued', 'started', 'deferred'] else 1.0
        delete_progress.bar_style = bar_styles[delete_job.status]
        if scan_progress.value == delete_progress.value == 1.0 or scan_job.status == 'failed':
            time.sleep(2) # enough time for graphics to update
            break
        time.sleep(2)


def crawler_run(func, *args):
    crawler_queue = Queue(
        'public_github_scanner',
        connection=StrictRedis(host='redis'),
    )
    # if the crawler would create/delete its own token, there would be not need to 
    # keep track of the job progress
    access_token = authgen.create_github_access_token(USERNAME, PASSWORD, 'public scan {}'.format(args))
    crawler_job = crawler_queue.enqueue_call(
        func=func,
        args=(access_token, *args),
    )
    crawler_queue.enqueue_call(
        func='scanner.delete_github_access_token',
        args=(USERNAME, PASSWORD, access_token),
        timeout=60,
        depends_on=crawler_job
    )


def scan_repo(github_login, repo_name, leave_clone=True):
    crawler_run('scanner.scan_repo', github_login, repo_name, leave_clone)


def scan_commit(github_login, repo_name, commit_sha, leave_clone=True):
    crawler_run('scanner.scan_commit', github_login, repo_name, commit_sha, leave_clone)


