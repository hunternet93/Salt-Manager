import web, random, salt.client.api, time, json, yaml, sys, importlib

# TODO: Fix key accept/reject giving 0 arguments error

class Bunch(dict):
    """This is a basic generic object that the App object will use for named modules, i.e. app.modules.test
       Copied from: http://code.activestate.com/recipes/52308-the-simple-but-handy-collector-of-a-bunch-of-named/?in=user-97991#c4"""
    def __init__(self,**kw):
        dict.__init__(self,kw)
        self.__dict__ = self


class App:
    def __init__(self):
        self.urls = [
            '/', 'Main', 
            '/login', 'Login',
            '/ajax/settings', 'Settings',
            '/ajax/listminions', 'ListMinions',
            '/ajax/listkeys', 'ListKeys',
            '/ajax/listmodules', 'ListModules',
            '/ajax/runcommand', 'RunCommand',
        ]

        try:
            settings_file = open('settings.yaml')
        except IOError:
            print('settings.yaml file not found, using default settings')
            self.settings = {'quickactions': []}
        else:
            self.settings = yaml.load(settings_file)

        self.salt = salt.client.api.APIClient()
        self.users = []

        if not self.settings.get('eauth'):
            print('eauth not specified, defaulting to pam authentication')
            self.settings['eauth'] = 'pam'

        if self.settings.get('modules'):
            self.modules = Bunch()
            sys.path.append('modules/')

            self.settings['options'] = {}

            for moduledict in self.settings['modules']:
                setattr(self.modules, moduledict['name'], importlib.import_module(moduledict['name']))
                module = getattr(self.modules, moduledict['name'])

                module.options = moduledict.get('options')
                self.settings['options'][moduledict['name']] = module.options

                module.app = self
                module.web = web

                self.urls += ['/' + moduledict['name'], module.webapp]

            del self.settings['modules']

        print(self.urls)
        print(self.settings)

    def add_user(self, username, password):
        try:
            token = self.salt.create_token({'username': username, 'password': password, 'eauth': self.settings['eauth']})['token']
        except salt.exceptions.EauthAuthenticationError:
            print('Login error for user:', username)
            return False

        self.users.append(User(username, password, token, self.settings))
        return self.users[-1]

    def check_user(self, cookie_id):
        for user in self.users:
            if cookie_id == user.cookie_id:
                try:
                    self.salt.verify_token(user.token)
                except salt.exceptions.EauthAuthenticationError:
                    self.users.remove(user)
                    return False
                else:
                    return user

        return False

    def check_cookie(self, web):
        cookie_id = web.cookies().get('key')
        user = self.check_user(cookie_id)
        if user:
            web.setcookie('key', user.regen_cookie_id(), self.settings['auth_cookie_expiration'], path='/')
            return user
        else:
            return False

    def del_user(self, cookie_id):
        user = self.check_user(cookie_id)
        if user:
            self.users.remove(user)
            return True
        else:
            return False

class User:
    def __init__(self, username, password, token, settings):
        self.username = username
        self.password = password
        self.cookie_id = str(random.randint(1,1000000000))
        self.token = token

    def regen_cookie_id(self):
        self.cookie_id = str(random.randint(1,1000000000))
        return self.cookie_id

class Main:
    def GET(self):
        user = app.check_cookie(web)
        if not user: return web.seeother('/login')

        return render.main()

class Login:
    def GET(self):
        user = app.check_cookie(web)
        if user:
            return web.seeother('/')

        return render.login('')

    def POST(self):
        data = web.input()
        
        try:
            user = app.add_user(data['username'], data['password'])

        except KeyError as err:
            if err.args[0] == 'username':
                return render.login('You must enter a username')
            if err.args[0] == 'password':
                return render.login('You must enter a password')

        if not user:
            return render.login('Incorrect username or password')

        web.setcookie('key', user.cookie_id, app.settings['auth_cookie_expiration'], path='/')
        return web.seeother('/')

class Settings:
    def GET(self):
        user = app.check_cookie(web)
        if not user: return web.seeother('/login')

        web.header('Content-Type', 'appication/json')
        return json.dumps(app.settings)

    # Possibly write POST to change settings?

class ListMinions:
    def GET(self):
        user = app.check_cookie(web)
        if not user: return web.seeother('/login')

        listkeys = app.salt.run({'fun': 'wheel.key.list_all', 'token': user.token})
        minions = listkeys['data']['return']['minions']

        minions = [{'hostname': x} for x in minions]

        web.header('Content-Type', 'application/json')
        return json.dumps({'minions': minions})

class ListKeys:
    def GET(self):
        user = app.check_cookie(web)
        if not user: return web.seeother('/login')

        listkeys = app.salt.run({'fun': 'wheel.key.list_all', 'token': user.token})
        minions = listkeys['data']['return']['minions']
        minions_unaccepted = listkeys['data']['return']['minions_pre']

        minions = [{'hostname': x, 'accepted': True} for x in minions]
        minions_unaccepted = [{'hostname': x, 'accepted': False} for x in minions_unaccepted]

        web.header('Content-Type', 'application/json')
        return json.dumps({'minions': minions, 'minions_unaccepted': minions_unaccepted})

class ListModules:
    def GET(self):
        user = app.check_cookie(web)
        if not user: return web.seeother('/login')

        modules = []
        for module in app.modules.values():
            modules.append({'title': module.title, 'url': module.mainpage})

        web.header('Content-Type', 'application/json')
        return json.dumps(modules)

class RunCommand:
    def POST(self):
        user = app.check_cookie(web)
        if not user: return web.seeother('/login')

        data = web.input()
        print('running command:', {'mode': 'sync', 'timeout': 30.0, 'tgt': data['tgt'], 'fun': data['fun'], 'arg': json.loads(data['arg']), 'token': user.token})
        try:
            result = app.salt.run({'mode': 'sync', 'timeout': 30.0, 'tgt': data['tgt'], 'fun': data['fun'], 'arg': json.loads(data['arg']), 'token': user.token})
            print(result)

        except KeyError as err:
            print('RunCommand error:/n' + repr(err))
            return json.dumps({'error': repr(err)})

        if result.get('result'): result = result.get('result')

        web.header('Content-Type', 'application/json')
        print('RunCommand result:/n' + str(result))
        return json.dumps({'result': str(result)})


app = App()
render = web.template.render('templates/')
if __name__ == '__main__':
    webapp = web.application(app.urls, globals())
    webapp.run()
