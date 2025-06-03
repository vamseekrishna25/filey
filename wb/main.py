import os

import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
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

def make_app():
    return tornado.web.Application([
        (r"/(.*)", MainHandler),
    ])


def main():
    app = make_app()
    port = 8000
    while port<9000:
        try:
            app.listen(port)
            print(f"Serving HTTP on 0.0.0.0 port {port} (http://0.0.0.0:{port}/) ...")
            tornado.ioloop.IOLoop.current().start()
            
        except:
            port+=1
    
if __name__ == "__main__":
    main()