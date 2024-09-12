from flask import Flask, render_template, request, session
from sgfmill import sgf
from sgfmill.common import format_vertex
from webview import Window

from libs.grid import Grid


class Application(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret_key = "goverlay"
        self.config["TEMPLATES_AUTO_RELOAD"] = True
        self.projection: Window
        self.pannel: Window
        self.projection_grid: Grid


app = Application(__name__)


@app.route("/")
def pannel():
    return render_template("pannel.jinja")


@app.route("/projection_calibration")
def projection_calibration():
    return render_template("projection_calibration.jinja")


@app.route("/game", methods=["GET", "POST"])
def game():

    if request.method == "GET":
        return render_template("game.jinja")

    try:
        sgf_file = request.files["sgf_file"]
        sgf_content = sgf_file.stream.read()
        game = sgf.Sgf_game.from_bytes(sgf_content)
    except:
        return render_template("game.jinja")

    # winner = game.get_winner()
    # board_size = game.get_size()
    # b_player = root_node.get("PB")
    # w_player = root_node.get("PW")
    # root_node = game.get_root()

    moves = []

    for node in game.get_main_sequence():
        player, coordinates = node.get_move()
        if player:
            move = format_vertex(coordinates)
            moves.append([player, move, list(coordinates)])

    app.projection.load_url("http://localhost:8000/projection")
    app.projection.show()
    return render_template("game.jinja", moves=moves)


@app.route("/enable_fullscreen")
def enable_fullscreen():
    if not app.projection.fullscreen:
        app.projection.toggle_fullscreen()
    return {"result": "done"}


@app.route("/disable_fullscreen")
def disable_fullscreen():
    if app.projection.fullscreen:
        app.projection.toggle_fullscreen()
    return {"result": "done"}


@app.route("/toggle_fullscreen")
def toggle_fullscreen():
    app.projection.toggle_fullscreen()
    return {"result": "done"}


@app.route("/show_projection_calibration", methods=["POST"])
def show_projection_calibration():
    if session.get("dim", -1) != request.json["dim"]:
        session["dim"] = request.json["dim"]
        app.projection_grid = Grid(session["dim"])
        app.projection_grid.recalculate_dots()
        app.projection.load_url("http://localhost:8000/projection_calibration")
    app.projection.show()
    return {"result": "done"}


@app.route("/projection")
def projection():
    return render_template("projection.jinja")


@app.route("/projection/grid/get")
def get_projection_grid():
    return app.projection_grid.get_dots()


@app.route("/projection/grid/move", methods=["POST"])
def move_projection_grid():
    id = request.json["id"]
    cx = request.json["cx"]
    cy = request.json["cy"]

    return app.projection_grid.update_data(id, cx, cy)


@app.route("/log", methods=["POST"])
def log():
    text = request.json["text"]
    print(text)
    return "ok"


@app.route("/projection/grid/highlight", methods=["POST"])
def projection_grid_highlight():

    positions = request.json["coordinates"]

    for dot in app.projection_grid.all_dots.values():
        dot["stroke"] = "black"

    for position in positions:
        i, j = position
        app.projection_grid.all_dots[f"c-{i}-{j}"]["stroke"] = "yellow"

    app.projection.evaluate_js("update_data();")
    # app.projection.evaluate_js("window.location.reload();")

    return {"result": "done"}


@app.route("/hide_projection")
def hide_projection():
    app.projection.hide()
    return {"result": "done"}


@app.route("/close")
def close():
    app.pannel.destroy()
    return "closing"
