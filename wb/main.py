import os
import secrets
import argparse
import json
from typing import TYPE_CHECKING
 
 if TYPE_CHECKING:
     from typing import Optional

import tornado.ioloop
import tornado.web
import socket
import tornado.websocket
import asyncio
import shutil
from collections import deque

# Add this import for template path
from tornado.web import RequestHandler, Application

# Will be set in main() after parsing configuration
ACCESS_TOKEN = None
ROOT_DIR = os.getcwd()

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self) -> str | None:
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
        abspath = os.path.abspath(os.path.join(ROOT_DIR, path))
        root = ROOT_DIR
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
    def get_current_user(self) -> str | None:
        return self.get_secure_cookie("user")

    def check_origin(self, origin):
        return True  # Allow all origins for now

    async def open(self, path):
        if not self.current_user:
            self.close()
            return
            
        self.file_path = os.path.abspath(os.path.join(ROOT_DIR, path))
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
            upload_path = os.path.join(ROOT_DIR, directory)
            if not os.path.abspath(upload_path).startswith(ROOT_DIR):
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
            final_path = os.path.join(ROOT_DIR, directory, relative_path)
            final_path_abs = os.path.abspath(final_path)

            if not final_path_abs.startswith(os.path.abspath(os.path.join(ROOT_DIR, directory))):
                self.set_status(403)
                self.write(f"Forbidden path: {relative_path}")
                return

            os.makedirs(os.path.dirname(final_path_abs), exist_ok=True)
            
            with open(final_path_abs, 'wb') as f:
                f.write(file_body)
        
        self.set_status(200)
        self.write("Upload successful")

class DeleteHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        path = self.get_argument("path", "")
        abspath = os.path.abspath(os.path.join(ROOT_DIR, path))
        root = ROOT_DIR
        if not abspath.startswith(root):
            self.set_status(403)
            self.write("Forbidden")
            return
        if os.path.isdir(abspath):
            shutil.rmtree(abspath)
        elif os.path.isfile(abspath):
            os.remove(abspath)
        parent = os.path.dirname(path)
        self.redirect("/" + parent if parent else "/")

class RenameHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        path = self.get_argument("path", "")
        new_name = self.get_argument("new_name", "")
        abspath = os.path.abspath(os.path.join(ROOT_DIR, path))
        new_abspath = os.path.abspath(os.path.join(ROOT_DIR, os.path.dirname(path), new_name))
        root = ROOT_DIR
        if not (abspath.startswith(root) and new_abspath.startswith(root)):
            self.set_status(403)
            self.write("Forbidden")
            return
        os.rename(abspath, new_abspath)
        parent = os.path.dirname(path)
        self.redirect("/" + parent if parent else "/")

def make_app(settings):
    # Add template_path to settings
    settings["template_path"] = os.path.join(os.path.dirname(__file__), "templates")
    return tornado.web.Application([
        (r"/login", LoginHandler),
        (r"/stream/(.*)", FileStreamHandler),
        (r"/upload", UploadHandler),
        (r"/delete", DeleteHandler),
        (r"/rename", RenameHandler),
        (r"/(.*)", MainHandler),
    ], **settings)


def main():
    parser = argparse.ArgumentParser(description="Run Filey")
    parser.add_argument("--config", help="Path to JSON config file")
    parser.add_argument("--root", help="Root directory to serve")
    parser.add_argument("--port", type=int, help="Port to listen on")
    parser.add_argument("--token", help="Access token for login")
    args = parser.parse_args()

    config = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)

    root = args.root or config.get("root") or os.getcwd()
    port = args.port or config.get("port") or 8000
    token = args.token or config.get("token") or os.environ.get("WB_ACCESS_TOKEN") or secrets.token_urlsafe(32)

    global ACCESS_TOKEN, ROOT_DIR
    ACCESS_TOKEN = token
    ROOT_DIR = os.path.abspath(root)

    print(f"Access token: {ACCESS_TOKEN}")

    settings = {
        "cookie_secret": ACCESS_TOKEN,
        "login_url": "/login",
    }
    app = make_app(settings)
    while True:
        try:
            app.listen(port)
            print(f"Serving HTTP on 0.0.0.0 port {port} (http://0.0.0.0:{port}/) ...")
            print(f"http://{socket.getfqdn()}:{port}/")
            tornado.ioloop.IOLoop.current().start()
            break
        except OSError:
            port += 1
    
if __name__ == "__main__":
    main()