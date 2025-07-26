import os
import secrets
from typing import Optional

import tornado.ioloop
import tornado.web
import socket
import tornado.websocket
import asyncio

# Add this import for template path
from tornado.web import RequestHandler, Application

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
        self.render("login.html", error=None)  # Always provide 'error'

    def post(self):
        token = self.get_argument("token", "")
        if token == ACCESS_TOKEN:
            self.set_secure_cookie("user", "authenticated")
            self.redirect("/")
        else:
            self.render("login.html", error="Invalid token. Try again.")

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
            file_data = []
            for f_name in files:
                file_data.append({
                    'name': f_name,
                    'is_dir': os.path.isdir(os.path.join(abspath, f_name))
                })
            self.render("directory.html", path=path, files=file_data)
        elif os.path.isfile(abspath):
            filename = os.path.basename(abspath)
            if self.get_argument('download', None):
                self.set_header('Content-Type', 'application/octet-stream')
                self.set_header('Content-Disposition', f'attachment; filename="{filename}"')
                with open(abspath, 'rb') as f:
                    self.write(f.read())
            else:
                with open(abspath, 'r', encoding='utf-8', errors='replace') as f:
                    file_content = f.read()
                self.render("file.html", filename=filename, path=path, file_content=file_content)
        else:
            self.set_status(404)
            self.write("File not found")

class FileStreamHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True  # Allow all origins for now

    async def open(self, path):
        self.file_path = os.path.abspath(os.path.join(os.getcwd(), path))
        self.running = True
        if not os.path.isfile(self.file_path):
            await self.write_message(f"File not found: {self.file_path}")
            self.close()
            return
        try:
            self.file = open(self.file_path, 'r', encoding='utf-8', errors='replace')
            self.file.seek(0, os.SEEK_END)  # Start at end of file
        except Exception as e:
            await self.write_message(f"Error opening file: {e}")
            self.close()
            return
        self.loop = tornado.ioloop.IOLoop.current()
        self.periodic = tornado.ioloop.PeriodicCallback(self.send_new_lines, 500)
        self.periodic.start()

    async def send_new_lines(self):
        if not self.running:
            return
        where = self.file.tell()
        line = self.file.readline()
        while line:
            await self.write_message(line)
            where = self.file.tell()
            line = self.file.readline()
        self.file.seek(where)

    def on_close(self):
        self.running = False
        if hasattr(self, 'periodic'):
            self.periodic.stop()
        if hasattr(self, 'file'):
            self.file.close()

def make_app(settings):
    # Add template_path to settings
    settings["template_path"] = os.path.join(os.path.dirname(__file__), "templates")
    return tornado.web.Application([
        (r"/login", LoginHandler),
        (r"/stream/(.*)", FileStreamHandler),
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
            print(f"http://{socket.getfqdn()}:{port}/")
            tornado.ioloop.IOLoop.current().start()
            
        except OSError:
            port+=1
    
if __name__ == "__main__":
    main()