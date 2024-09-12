import sys
import threading

import webview as wv
from werkzeug.serving import make_server

from libs.flask.app import app as flask_app


class Goverlay:
    def __init__(self) -> None:
        self.running = False

        self.server = make_server("localhost", 8000, flask_app)
        flask_app.app_context().push()

        self.pannel: wv.Window
        self.pannel = wv.create_window("Goverlay - pannel", "http://localhost:8000/")
        self.pannel.events.closed += lambda: self.destroy_pannel()
        flask_app.pannel = self.pannel

        self.projection: wv.Window
        self.projection = wv.create_window("Goverlay - projection")
        self.projection.hidden = True
        self.projection.events.closing += lambda: self.destroy_projection()
        flask_app.projection = self.projection

    def start(self):
        self.running = True
        threading.Thread(target=self.start_server, daemon=True).start()
        wv.start()

    def destroy_projection(self):
        if self.running:
            self.projection.hide()
            return False
        return True

    def start_server(self):
        self.server.serve_forever()
        print("server stopped")
        sys.exit()

    def destroy_pannel(self):
        self.running = False
        self.projection.destroy()
        self.server.shutdown()


if __name__ == "__main__":
    Goverlay().start()
