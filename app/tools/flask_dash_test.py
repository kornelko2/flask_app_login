import dash
import dash_html_components as html
import flask

server = flask.Flask(__name__)


@server.route("/")
def home():
    return "Hello, Flask!"


app = dash.Dash(server=server, routes_pathname_prefix="/dash/")

app.layout = html.Div("This is the Dash app.")

if __name__ == "__main__":
    app.run_server(debug=True)