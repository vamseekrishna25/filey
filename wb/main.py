import os
import secrets
from typing import Optional

import tornado.ioloop
import tornado.web
import socket
import tornado.websocket
import asyncio
from collections import deque

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
                start_streaming = self.get_argument('stream', None) is not None
                self.render("file.html", filename=filename, path=path, file_content=file_content, start_streaming=start_streaming)
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

        # Send last 100 lines first
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='replace') as f:
                last_100_lines = deque(f, 100)
            if last_100_lines:
                await self.write_message("".join(last_100_lines))
        except Exception as e:
            await self.write_message(f"Error reading file history: {e}")

        try:
            self.file = open(self.file_path, 'r', encoding='utf-8', errors='replace')
            self.file.seek(0, os.SEEK_END)  # Start at end of file for new lines
        except Exception as e:
            await self.write_message(f"Error opening file for streaming: {e}")
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

class UploadHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        directory = self.get_argument("directory", "")
        file_infos = self.request.files.get('files', [])
        
        # This handles the single-file upload from the button
        if not file_infos:
            file_info = self.request.files.get('file', [])[0]
            filename = file_info['filename']
            upload_path = os.path.join(os.getcwd(), directory)
            if not os.path.abspath(upload_path).startswith(os.getcwd()):
                self.set_status(403)
                self.write("Forbidden")
                return
            os.makedirs(upload_path, exist_ok=True)
            with open(os.path.join(upload_path, filename), 'wb') as f:
                f.write(file_info['body'])
            self.redirect("/" + directory)
            return

        # This handles the drag-and-drop upload
        for file_info in file_infos:
            relative_path = file_info['filename']
            file_body = file_info['body']
            
            # Sanitize the relative path to prevent directory traversal
            # and ensure it's a safe path
            final_path = os.path.join(os.getcwd(), directory, relative_path)
            final_path_abs = os.path.abspath(final_path)

            if not final_path_abs.startswith(os.path.abspath(os.path.join(os.getcwd(), directory))):
                self.set_status(403)
                self.write(f"Forbidden path: {relative_path}")
                return

            os.makedirs(os.path.dirname(final_path_abs), exist_ok=True)
            
            with open(final_path_abs, 'wb') as f:
                f.write(file_body)
        
        self.set_status(200)
        self.write("Upload successful")

def make_app(settings):
    # Add template_path to settings
    settings["template_path"] = os.path.join(os.path.dirname(__file__), "templates")
    return tornado.web.Application([
        (r"/login", LoginHandler),
        (r"/stream/(.*)", FileStreamHandler),
        (r"/upload", UploadHandler),
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