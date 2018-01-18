import tornado.ioloop
import tornado.web
import json
import subprocess
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK

HEAD = 'head_commit'
HEAD_COMMITTER = 'committer'
HEAD_COMMIT_MSG = 'message'
REPOS = "repository"
REPOS_NAME = "name"
REPOS_FULLNAME = "full_name"
PUSHER = "pusher"
SENDER = "sender"
REF = 'ref'


def get_branch(body):
    return body[REF].split('/')[-1]


def get_git_addr(repos_name, user_name='Romeren'):
    return 'git@github.com:Romeren/' + repos_name + '.git'


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


def restart_proccess(process_name):
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


def raspboard_handler(body):
    branch = get_branch(body)
    if(branch != 'master'):
        return
    print('Starting deployment...')

    repos_name = 'RaspBoard'
    git_addr = 'git@github.com:Romeren/' + repos_name + '.git'
    broker_process = repos_name + ".service_framework.component_broker.main"
    container_process = repos_name + ".main"

    update_repository(repos_name, git_addr)

    restart_proccess(broker_process)
    restart_proccess(container_process)

    print('Deployment done!')


def chromecast_handler(body):
    branch = get_branch(body)
    if(branch != 'master'):
        return
    print('Starting deployment...')

    repos_name = 'chromecast_idlescreen'
    git_addr = get_git_addr(repos_name)
    process_name = repos_name + ".main"

    update_repository(repos_name, git_addr)

    restart_proccess(process_name)

    print('Deployment done!')


managed_repos = {
    'Romeren/RaspBoard': raspboard_handler,
    'Romeren/chromecast_idlescreen': chromecast_handler
}


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
        if(body[REPOS][REPOS_FULLNAME] not in managed_repos):
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
        handler = managed_repos[body[REPOS][REPOS_FULLNAME]]
        handler(body)


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])


print('STARTED!')
chromecast_handler({'ref': 'on/master'})
raspboard_handler({'ref': 'on/master'})
if __name__ == "__main__":
    app = make_app()
    app.listen(9876)
    tornado.ioloop.IOLoop.current().start()
