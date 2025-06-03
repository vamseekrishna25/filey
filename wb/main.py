import os
import secrets
from typing import Optional

import tornado.ioloop
import tornado.web

# Generate a random token at startup
ACCESS_TOKEN = os.environ.get('WB_ACCESS_TOKEN') or secrets.token_urlsafe(32)
print(f"Access token: {ACCESS_TOKEN}")

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self) -> Optional[str]:
        return self.get_secure_cookie("user")

class LoginHandler(BaseHandler):
    def get(self):
        if self.current_user:
            self.redirect("/")
            return
        self.write('''
        <html>
            <head><title>Login</title></head>
            <body>
                <h2>Login</h2>
                <form method="POST">
                    <input type="password" name="token" placeholder="Enter access token">
                    <input type="submit" value="Login">
                </form>
            </body>
        </html>
        ''')

    def post(self):
        token = self.get_argument("token", "")
        if token == ACCESS_TOKEN:
            self.set_secure_cookie("user", "authenticated")
            self.redirect("/")
        else:
            self.write("<html><body>Invalid token. <a href='/login'>Try again</a></body></html>")

class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, path):
        abspath = os.path.abspath(os.path.join(os.getcwd(), path))
        root = os.getcwd()
        if not abspath.startswith(root):
            self.set_status(403)
            self.write("Forbidden")
            return

        if os.path.isdir(abspath):
            files = os.listdir(abspath)
            files.sort()
            self.write("<html><body><h2>Directory listing for {}</h2><ul>".format(path or "/"))
            if path:
                parent = os.path.dirname(path.rstrip("/"))
                self.write(f'<li><a href="/{parent}">..</a></li>')
            for f in files:
                full = os.path.join(path, f) if path else f
                display = f + "/" if os.path.isdir(os.path.join(abspath, f)) else f
                self.write(f'<li><a href="/{full}">{display}</a></li>')
            self.write("</ul></body></html>")
        elif os.path.isfile(abspath):
            # Show file contents as plain text in the browser
            self.set_header('Content-Type', 'text/plain; charset=utf-8')
            with open(abspath, 'r', encoding='utf-8', errors='replace') as f:
                self.write(f.read())
        else:
            self.set_status(404)
            self.write("File not found")

def make_app(settings):
   
    return tornado.web.Application([
        (r"/login", LoginHandler),
        (r"/(.*)", MainHandler),
    ], **settings)


def main():
    settings = {
        "cookie_secret": ACCESS_TOKEN,
        "login_url": "/login",
    }
    app = make_app(settings)
    port = 8000
    while port<9000:
        try:
            print(settings,port)
            app.listen(port)
            print(f"Serving HTTP on 0.0.0.0 port {port} (http://0.0.0.0:{port}/) ...")

            tornado.ioloop.IOLoop.current().start()
            
        except:
            port+=1
    
if __name__ == "__main__":
    main()