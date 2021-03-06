import os
from pprint import pprint, pformat
from fabric.contrib.files import append, exists, sed
from fabric.context_managers import shell_env
from fabric.api import env, local, run
import random

REPO_URL = 'https://github.com/ephes/ml_jobcontrol.git'
SECRET_KEY = os.environ["SECRET_KEY"]

def _create_directory_structure_if_necessary(site_folder):
    for subfolder in ('database', 'static', 'virtualenv', 'source'):
        run('mkdir -p %s/%s' % (site_folder, subfolder))

def _get_latest_source(source_folder):
    if exists(source_folder + '/.git'):
        run('cd %s && git fetch' % (source_folder,))
    else:
        run('git clone -b develop %s %s' % (REPO_URL, source_folder))
    current_commit = local("git log -n 1 --format=%H", capture=True)
    run('cd %s && git reset --hard %s' % (source_folder, current_commit))

def _update_settings(source_folder, site_name):
    settings_path = source_folder + '/ml_jobcontrol/ml_jobcontrol/settings/production.py'
    sed(settings_path, "DEBUG = True", "DEBUG = False")
    sed(settings_path,
        'ALLOWED_HOSTS =.+$',
        'ALLOWED_HOSTS = ["%s"]' % (site_name,)
    )

def _update_virtualenv(source_folder):
    virtualenv_folder = source_folder + '/../virtualenv'
    if not exists(virtualenv_folder + '/bin/pip'):
        run('virtualenv %s' % (virtualenv_folder,))
    run('%s/bin/pip install -r %s/requirements.txt' % (
            virtualenv_folder, source_folder
    ))

def _update_static_files(source_folder):
    with shell_env(SECRET_KEY=SECRET_KEY):
        run('cd %s && ../virtualenv/bin/python ml_jobcontrol/manage.py collectstatic --settings=ml_jobcontrol.settings.production --noinput' % ( # 1
            source_folder,
        ))

def _update_database(source_folder):
    with shell_env(SECRET_KEY=SECRET_KEY):
        run('cd %s && ../virtualenv/bin/python ml_jobcontrol/manage.py syncdb --settings=ml_jobcontrol.settings.production --noinput' % (
            source_folder,
        ))
        run('cd %s && ../virtualenv/bin/python ml_jobcontrol/manage.py migrate --settings=ml_jobcontrol.settings.production --noinput' % (
            source_folder,
        ))

def deploy():
    site_folder = '/home/%s/sites/%s' % (env.user, env.host)
    source_folder = site_folder + '/source'
    _create_directory_structure_if_necessary(site_folder)
    _get_latest_source(source_folder)
    _update_settings(source_folder, env.host)
    _update_virtualenv(source_folder)
    _update_static_files(source_folder)
    _update_database(source_folder)
