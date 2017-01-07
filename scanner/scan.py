import os
from rq import Queue
from redis import StrictRedis

ACCESS_TOKEN = os.environ['GITHUB_CRAWLER_ACCESS_TOKEN']

def scan_public_users(*github_ids):
    connection = StrictRedis(host = 'redis', port = 6379)
    crawler_queue = Queue('public_github_scanner', connection = connection)
    population_queue = Queue('population_analyzer', connection = connection)
    for github_id in github_ids:
        scan_repos = crawler_queue.enqueue_call(func = 'scanner.scan_all_repos', args = (ACCESS_TOKEN, github_id), timeout = 3600)
        population_queue.enqueue_call(func = 'leaderboard.update_ranking_for_user', args = (github_id,), timeout = 3600, depends_on = scan_repos)
