#!/usr/bin/env python
# -*- coding: utf-8 -*- #

from fcntl import F_GETFL
from fcntl import F_SETFL
from fcntl import fcntl
import json
from os import O_NONBLOCK
from os import path
import subprocess
import tornado.ioloop
import tornado.web


# GIT PAYLOAD FIELDS
HEAD = 'head_commit'
HEAD_COMMITTER = 'committer'
HEAD_COMMIT_MSG = 'message'
REPOS = "repository"
REPOS_NAME = "name"
REPOS_FULLNAME = "full_name"
PUSHER = "pusher"
SENDER = "sender"
REF = 'ref'

# CONFIG FIELDS:
CONFIG_REPOSITORY = 'repository'
CONFIG_REPOS_NAME = 'name'
CONFIG_REPOS_USER = 'user_name'
CONFIG_REPOS_BRANCH = 'branch'
CONFIG_SYSTEMS = 'systems'
CONFIG_SYS_TYPE = 'type'
CONFIG_SYS_MAIN = 'main'


def get_config(file_name):
    if(not path.isfile(file_name)):
        file = open(file_name, 'w+')
        file.write(json.dumps({}))
        file.close()

    repos_file = open(file_name, 'r')
    config = ""
    try:
        config = repos_file.read()
        # print(config)
        config = config.replace('\n', '')
        config = config.replace('\t', '')
        config = config.replace('  ', '')
        # print(config)
        config = json.loads(config)
    except Exception as e:
        print(e)
        print('Config file not readable!')
        exit()
    return config


def get_branch(body):
    return body[REF].split('/')[-1]


def get_git_addr(repos_name, user_name):
    return 'git@github.com:' + user_name + '/' + repos_name + '.git'


def update_repository(repos_name, git_addr):
    info = subprocess.check_output(['ls'])
    items = info.decode('utf-8').split('\n')
    if(repos_name not in items):
        print('Cloning repository', repos_name)
        info = subprocess.check_output(['git', 'clone', git_addr])
        print(info)
    print('Downloading newest software', repos_name)
    info = subprocess.check_output(['git', '-C', repos_name, 'pull'])
    print(info)


def restart_proccess(process_type, process_name):
    if(process_type != 'python'):
        return

    p = subprocess.Popen(['ps', '-ax'],
                         stdout=subprocess.PIPE)
    out = subprocess.Popen(['grep', process_name],
                           stdin=p.stdout,
                           stdout=subprocess.PIPE)
    p.wait()
    for line in iter(out.stdout.readline, ''):
        l = line[:-1].strip().split(' ')
        l = [x for x in l if x != '']
        if(len(l) < 7):
            continue
        pid = l[0]
        program = l[4]
        param = l[6]
        if(program != 'python'):
            continue
        print('Stopping process', pid, program, param)
        kill = ['kill', pid]
        subprocess.check_output(kill)

    cmd = ['python', '-m', process_name]
    print('Starting program', cmd)
    p = subprocess.Popen(cmd,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=False)
    flags = fcntl(p.stdout, F_GETFL)
    fcntl(p.stdout, F_SETFL, flags | O_NONBLOCK)


def repository_handler(body, config, force=False):
    if(CONFIG_REPOSITORY not in config or
       CONFIG_REPOS_NAME not in config[CONFIG_REPOSITORY] or
       CONFIG_REPOS_USER not in config[CONFIG_REPOSITORY]):
        return

    if(not force):
        branch = get_branch(body)
        if(CONFIG_REPOS_BRANCH in config[CONFIG_REPOSITORY] and
           branch != config[CONFIG_REPOSITORY][CONFIG_REPOS_BRANCH]):
            return

    print('Starting deployment...')

    git_addr = get_git_addr(config[CONFIG_REPOSITORY][CONFIG_REPOS_NAME],
                            config[CONFIG_REPOSITORY][CONFIG_REPOS_USER])

    update_repository(config[CONFIG_REPOSITORY][CONFIG_REPOS_NAME], git_addr)

    if(CONFIG_SYSTEMS in config):
        for system in config[CONFIG_SYSTEMS]:
            if(CONFIG_SYS_TYPE in system and CONFIG_SYS_MAIN in system):
                restart_proccess(system[CONFIG_SYS_TYPE],
                                 system[CONFIG_SYS_MAIN])

    print('Deployment done!')


class MainHandler(tornado.web.RequestHandler):

    def post(self):
        body = None
        # headers = self.request.headers

        # parse request body to json
        try:
            bodystr = self.request.body.decode('utf-8').replace("'", '"')
            body = json.loads(bodystr)
        except Exception as e:
            print(e)
            print('Faild to load request body!')
            return
        if(body is None):
            return

        # validate content
        if(HEAD not in body or
           HEAD_COMMITTER not in body[HEAD] or
           HEAD_COMMIT_MSG not in body[HEAD] or
           REPOS not in body or
           REPOS_NAME not in body[REPOS] or
           REPOS_FULLNAME not in body[REPOS] or
           PUSHER not in body or
           SENDER not in body or
           REF not in body):
            return

        # validate repository
        if(body[REPOS][REPOS_FULLNAME] not in config):
            return

        print('-------------------------')
        print('---Commintted by---')
        print(body[HEAD][HEAD_COMMITTER])
        print('---Committed on----')
        print(body[REPOS][REPOS_FULLNAME])
        print('---Commit msg------')
        print(body[HEAD][HEAD_COMMIT_MSG])
        print('---On branch-------')
        print(get_branch(body))
        # print('SENDER:')
        # print(body[SENDER])
        # print('PUSHER:')
        # print(body[PUSHER])
        # print("HEADERS")
        # print(headers)
        print('-------------------------')
        repository_handler(body, config[body[REPOS][REPOS_FULLNAME]])


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

print('Reading config file...')
repos_config = 'repos.config'
config = get_config(repos_config)
print(config)
print('Initing repositories...')

for x in config:
    repository_handler('', config[x], force=True)

print('WebService started!')
if __name__ == "__main__":
    app = make_app()
    app.listen(9876)
    tornado.ioloop.IOLoop.current().start()
