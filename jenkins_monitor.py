# pip install selenium
# pip install python-jenkins

import json
import jenkins
import os
from os.path import expanduser
from selenium import webdriver
from sys import argv, stdout
from time import sleep, time
from colorama import init as coloramaInit, Fore, Back, Style
coloramaInit()

config_file = expanduser(r'~\Dropbox\Work\Python\Programms\txt\build_monitor_config.txt')
jenkins_address = 'http://'
driver = None
# if not os.path.exists(expanduser(r'~\scripts\build_monitoring')): os.makedirs(expanduser(r'~\scripts\build_monitoring'))
# config_file = expanduser(r'~\scripts\build_monitoring\build_monitor_config.txt')
server = None
build_is_running = False

def get_config(config_file=config_file):
    return json.load(open(config_file, 'r'))

def write_config(new_config, config_file=config_file):
    json.dump(new_config, open(config_file, 'w'))

def server_init(address):
    return jenkins.Jenkins(address)

def get_job_state(job_name):
    global build_is_running
    state = server.get_job_info(job_name)
    status = state['color']
    if 'anime' in status: build_is_running = True
    else: build_is_running = False
    state['color'] = state['color'].replace('_anime', '')
    return state

def job_status(job_state):
    return job_state['color']

def job_init(job, config):
    new_job = {
        'name': job,
        'acknowledged': False,
        'last_check': job_status(get_job_state(job))
    }
    config['jobs'].append(new_job)
    return config

def create_config():
    print('Press enter when you finish adding jobs\n')
    jobs_init = []
    add_job = True
    while add_job:
        add_job = input('Add job: ')
        if add_job: jobs_init.append(add_job)
    print('Press enter if you wanna leave default settings\n')
    server = input('Jenkings address: ' + jenkins_address + '\n ')
    if not server: server = jenkins_address
    open_on_fail = input('open_on_fail: True\n')
    if not open_on_fail: open_on_fail = True
    config = {
        "jobs_init": jobs_init,
        "server": server,
        "open_on_fail": open_on_fail
    }
    write_config(config, config_file)
    return config
    
def first_run_init():
    global server
    config = create_config()
    config['jobs'] = []
    server = server_init(config['server'])
    for job in config['jobs_init']:
        print('Initializing ' + job)
        config = job_init(job, config)
    config.pop('jobs_init')
    write_config(config, config_file)

def open_last_build_link(job_state, status):
    driver = webdriver.Chrome(expanduser(r'~\Dropbox\Work\Python\chromedriver.exe'))
    # driver = webdriver.Firefox()
    if 'anime' in status:
        build = 1
    else:
        build = 0
    driver.get(job_state['builds'][build]['url'])
    driver.maximize_window()
    driver.implicitly_wait(60*60*24)
    driver.find_element_by_id('not existed element for browser to wait')

def get_queue_status(job):
    try: 
        queue_status = job['queueItem']['why']
        if 'Waiting' in queue_status: queue_status = 'Waiting for builder'
    except: return ''
    return '\t' + queue_status

def print_status(job, status, old_status, job_state):
    status_changed = ''
    build_run_info = ''
    dim_if_acknowledged = ''
    illuminate_running_build = ''
    illuminate_pending_build = ''
    queue_status = get_queue_status(job_state)
    status_colors = {
        'blue': Fore.GREEN,
        'red': Fore.RED + Style.BRIGHT,
        'aborted': Fore.YELLOW
    }
    if status != old_status: status_changed = '\tSTATUS CHANGED'
    if build_is_running:
        build_run_info = '\tbuild is running'
        illuminate_running_build = Back.WHITE
    if job['acknowledged']: dim_if_acknowledged = Style.DIM
    if queue_status: illuminate_pending_build = Back.BLUE

    print(status_colors[status] + dim_if_acknowledged + illuminate_running_build + illuminate_pending_build + 
        job['name'] + ':' + ' '*(40 - len(job['name'])) + status + status_changed + build_run_info + queue_status + 
        Style.RESET_ALL)

def check_jobs(config):
    print('Performing jobs check\n')
    for job in config['jobs']:
        job_state = get_job_state(job['name'])
        old_status = job['last_check']
        status = job_status(job_state)
        job['last_check'] = status
        print_status(job, status, old_status, job_state)
        if config['open_on_fail'] and status == 'red' and not job['acknowledged']:
            try: open_last_build_link(job_state, status)
            except: pass
            acknowledge = input('Понять и простить (y/n)? : ')
            if acknowledge == 'y' or len(acknowledge) == 0:
                job['acknowledged'] = True
        elif status == 'blue': job['acknowledged'] = False
        write_config(config, config_file)

def add_job(config):
    job = input('Job to add: ')
    config = job_init(job, config)
    write_config(config, config_file)

def list_jobs(config):
    for job in config['jobs']:
        print(job['name'])

def list_jobs_in_progress(config):
    counter = 0
    for job in config['jobs']:
        state = server.get_job_info(job['name'])
        status = state['color']
        if 'anime' in status:
            print(job['name'])
            counter += 1
            job_in_progress = job['name']
        try: 
            queue_status = state['queueItem']
            if queue_status:
                print(job['name'])
                counter += 1
                job_in_progress = job['name']
        except: pass
    if not counter: print('No jobs to wait')
    return job_in_progress if counter == 1 else False

def remove_job(config):
    list_jobs(config)
    job_to_delete = input('\nJob to remove: ')
    for job in config['jobs']:
        if job['name'] == job_to_delete: config['jobs'].remove(job)
    write_config(config, config_file)

def swith_open_on_fail_flag(config):
    flag = config['open_on_fail']
    print('Current flag is ' + str(flag) + ' changing to ' + str(not flag))
    config['open_on_fail'] = not flag
    write_config(config, config_file)

def display_config(config):
    print('\n')
    for key, value in config.items():
        if key != 'jobs': print(str(key) + ' - ' + str(value))
    print('\nJobs: ')
    for job in config['jobs']:
        print('\n' + job['name'])
        for key, value in job.items():
            if key != 'name': print('\t' + str(key) + ' - ' + str(value))

def edit_config():
    global server
    config = get_config()
    server = server_init(config['server'])
    options = {
        '1': {
            'name': 'add job',
            'action': add_job
        },
        '2': {
            'name': 'remove job',
            'action': remove_job
        },
        '3': {
            'name': 'swith open_on_fail flag',
            'action': swith_open_on_fail_flag
        },
        '4': {
            'name': 'display config',
            'action': display_config
        }
    }
    print('What do you wanna change?\n')
    for key in sorted(options.keys()):
        print(str(key) + ' - ' + options[key]['name'])
    choise = input('\nChoose number: ')
    config = options[choise]['action'](config=config)

def change_acknowledge_flag():
    config = get_config()

    for job in config['jobs']:
        if job['acknowledged']: print(job['name'])

    chosen_job = input('\nChoose job: ')

    for job in config['jobs']:
        if job['name'] == chosen_job: job['acknowledged'] = False

    write_config(config)

def convert_time(seconds):
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "[ %d:%02d:%02d ]" % (h, m, s)

def write_notification_message(message):
    stdout.write(message + '\r')
    stdout.flush()

def notify_when_build_is_done():
    build_is_about_to_start = True
    config = get_config()
    job_in_progress = list_jobs_in_progress(config)
    job_name = job_in_progress or input('\nChoose the job: ')
    start_time = time()
    job_state = get_job_state(job_name)
    queue_status = get_queue_status(job_state)
    print('\n\t\t' + Fore.CYAN + Style.BRIGHT + job_name + Style.RESET_ALL + '\n')

    while queue_status or build_is_running:
        current_time = time()
        time_dif = current_time - start_time
        queue_message = ''
        building_message = ''
        job_state = get_job_state(job_name)
        queue_status = get_queue_status(job_state)

        base_message = convert_time(time_dif) + ' - Waiting for '
        queue_message = base_message + 'builder available...'
        building_message = base_message + ' build to finish...'

        if queue_status:
            write_notification_message(queue_message)
            continue

        if build_is_about_to_start:
            print(queue_message + '\n')
            build_is_about_to_start = False

        if build_is_running:
            write_notification_message(building_message)
        else: print(building_message)

        sleep(2)
    
    job_state = get_job_state(job_name)
    status = job_status(job_state)
    open_last_build_link(job_state, status)
    exit()

def print_help():
    print('''
Config example:
{
  "server": ''' + jenkins_address + ''',
  "open_on_fail": "True",
  "jobs_init": [
    "some-trunk"
  ]
}
open_on_fail flag will open browser with failed build.
When you're done analyzing - just close the browser
You can acknowledge fail and browser won't be opened next time.

        ''')
    print('Call with no arguments performs check for all jobs from config\n')
    print('''Optional arguments: 

        init - performs first run initialization
        config - edit config file
        ''')


if __name__ == '__main__':
    try:
        if len(argv) == 1:
            config = get_config()
            server = server_init(config['server'])
            check_jobs(config)

        elif argv[1] == '--help':
            print_help()

        elif argv[1] == 'init':
            first_run_init()

        elif argv[1] == 'config':
            edit_config()

        action = input('''\nPress enter to finish
            1 - help,
            2 - config,
            3 - change acknowledge flag
            4 - notify when build is done
            ''')

        if len(action) == 0: exit()
        elif action == '1': print_help()
        elif action == '2': edit_config()
        elif action == '3': change_acknowledge_flag()
        elif action == '4': notify_when_build_is_done()

        input('\nPress enter to finish')
    except Exception as e: input(e)
