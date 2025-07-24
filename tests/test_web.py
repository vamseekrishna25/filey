import os
from tornado.testing import AsyncHTTPTestCase
import tornado.web

from wb.main import make_app, ACCESS_TOKEN

class AppTest(AsyncHTTPTestCase):
    def get_app(self):
        settings = {
            "cookie_secret": ACCESS_TOKEN,
            "login_url": "/login",
            "root_dir": os.getcwd(),
        }
        return make_app(settings)

    def test_login_and_list(self):
        response = self.fetch('/login', method='POST', body=f'token={ACCESS_TOKEN}', follow_redirects=False)
        self.assertEqual(response.code, 302)
        cookie = response.headers.get('Set-Cookie')
        self.assertIsNotNone(cookie)

        resp2 = self.fetch('/', headers={'Cookie': cookie})
        self.assertEqual(resp2.code, 200)
        self.assertIn(b'Directory listing', resp2.body)
