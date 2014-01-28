import web, random, salt.client.api, time, json

urls = (
    '/', 'Main', 
    '/login', 'Login',
    '/ajax/settings', 'Settings',
    '/ajax/listminions', 'ListMinions',
    '/ajax/listkeys', 'ListKeys',
    '/ajax/runcommand', 'RunCommand',
)

class App:
    def __init__(self):
        self.settings = {"quickactions": [{'title': 'Reboot', 'fun': 'system.reboot', 'arg': []}, {'title': 'Reload', 'fun': 'service.restart', 'arg': ['lightdm']}]}
        self.salt = salt.client.api.APIClient()
        self.users = []
        self.usersettings = {'expiration': 86400} # This should be from config

        self.auth_method = "salt" # This should be set from the config file eventually
        if self.auth_method == "salt":
            self.eauth = "pam" # Also load this from config, can be PAM or LDAP

    def add_user(self, username, password):
        if self.auth_method == "salt":
            try:
                token = self.salt.create_token({'username': username, 'password': password, 'eauth': self.eauth})['token']
            except salt.exceptions.EauthAuthenticationError:
                print("Login error for user", username)
                return False

            self.users.append(User(username, password, token, self.usersettings))
            return self.users[-1]

    def check_user(self, cookie_id):
        for user in self.users:
            if cookie_id == user.cookie_id:
                if time.time() < user.expires:
                    user.expires = time.time() + self.usersettings['expiration']
                    return user
                else:
                    self.users.remove(user)
                    return False

        return False

    def check_cookie(self, web):
        cookie_id = web.cookies().get('key')
        user = self.check_user(cookie_id)
        if user:
            web.setcookie('key', user.regen_cookie_id(), self.usersettings['expiration'])
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
    def __init__(self, username, password, token, usersettings):
        self.username = username
        self.password = password
        self.cookie_id = str(random.randint(1,1000000000))
        self.expires = time.time() + usersettings['expiration']
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

        web.setcookie('key', user.cookie_id, app.usersettings['expiration'])
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

class RunCommand:
    def POST(self):
        user = app.check_cookie(web)
        if not user: return web.seeother('/login')

        data = web.input()
        try:
            result = app.salt.run({'mode': 'sync', 'timeout': 30.0, 'tgt': data['tgt'], 'fun': data['fun'], 'arg': json.loads(data['arg']), 'token': user.token})
            print(result)

        except KeyError as err:
            print("RunCommand error:/n" + repr(err))
            return json.dumps({'error': repr(err)})

        if result.get('result'): result = result.get('result')

        web.header('Content-Type', 'application/json')
        print("RunCommand result:/n" + str(result))
        return json.dumps({'result': str(result)})


app = App()
render = web.template.render('templates/')
if __name__ == "__main__":
    webapp = web.application(urls, globals())
    webapp.run()
