import os
import time
import string
import random
from collections import Counter
from multiprocessing import current_process

from rq import Queue
from redis import StrictRedis
from github import Github

#import authgen
import rsyslog

#current_process().name = os.environ['HOSTNAME']
#rsyslog.setup(log_level = os.environ['LOG_LEVEL'])

def get_github_users(query = None, language = 'python', count = 10, repos = '>0'):
    username = os.environ['GITHUB_CRAWLER_USERNAME']
    password = os.environ['GITHUB_CRAWLER_PASSWORD']
    query = query or random.choice(string.ascii_lowercase) + random.choice(string.ascii_lowercase)
    return list(user.login for user in Github().search_users(
            query = query,
            type = 'user',
            repos = repos,
            language = language
            )[0:count])

def update_ranking(github_id):
    Queue('population_analyzer', connection = StrictRedis(host = 'redis', port = 6379)).enqueue('leaderboard.update_ranking_for_user', github_id)

def clean():
    Queue('population_analyzer', connection = StrictRedis(host = 'redis', port = 6379)).enqueue('leaderboard.clean')

def scan_public_users(*github_ids, show_progress = True, force_overwrite = False):
    github_ids = github_ids or get_github_users()
    connection = StrictRedis(host = 'redis', port = 6379)
    crawler_queue = Queue('public_github_scanner', connection = connection)
    jobs = []
    for github_id in github_ids:
        job = crawler_queue.enqueue_call(
                func = 'scanner.scan_public_repos',
                args = (github_id,),
                kwargs = { 'force_overwrite': force_overwrite },
                result_ttl=86400,
                )
        jobs.append(job)
    if show_progress:
        show_progress_bars(*jobs)
    return jobs


def show_progress_bars(*jobs):
    from IPython.lib import backgroundjobs
    bgjobs = backgroundjobs.BackgroundJobManager()
    for job in jobs:
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
    while True:
        scan_job.refresh()
        if 'finished' in scan_job.meta:
            percentage_complete = sum(scan_job.meta['finished'].values()) / max(sum(scan_job.meta['steps'].values()), 1)
            scan_progress.value = 1.0 if scan_job.status == 'finished' else max(0.01, percentage_complete) # the metadata is bogus once the job is finished
        scan_progress.bar_style = bar_styles[scan_job.status]
        if scan_job.status == 'finished':
            scan_progress.value = 1.0
            scan_progress.bar_style = bar_styles[scan_job.status]
            break
        elif scan_job.status == 'failed':
            scan_progress.value = max(0.01, scan_progress.value)
            break
        else:
            time.sleep(2)

def scan_public_repo(github_login, repo_name, cleanup=True):
    queue = Queue('public_github_scanner', connection = StrictRedis(host = 'redis', port = 6379))
    queue.enqueue('scanner.scan_public_repo', github_login, repo_name, cleanup)

def scan_private_repo(auth_token, repo_name, cleanup=True):
    queue = Queue('private_github_scanner', connection = StrictRedis(host = 'redis', port = 6379))
    queue.enqueue('scanner.scan_private_repo', auth_token, repo_name, cleanup)

def scan_public_commit(github_login, repo_name, commit_sha, cleanup=True):
    queue = Queue('public_github_scanner', connection = StrictRedis(host = 'redis', port = 6379))
    queue.enqueue('scanner.scan_public_commit', github_login, repo_name, commit_sha, cleanup)

if __name__ == '__main__':
    print(get_github_users())
