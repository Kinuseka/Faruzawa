from flask import Flask, send_from_directory, render_template, redirect, request, Response
from subroutes import img_proxy, external_image_proxy, err_handlers, episode_handler, video_handler
from essentials.essentials import sitemap
from constants import Constants, version, version_label
from essentials.tools import cover_src
from mainHandler import main_handler
from flask_session import Session
from loguru import logger
import os
log = logger.bind(name="CFSession")

app = Flask(__name__)
app.config["SERVER_NAME"] = Constants.server_name
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = f".session_cookies/"
#Modifiers
Session(app)
#Routes
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),'favicon.ico', mimetype='image/x-icon')
@app.errorhandler(404)
def http_notfound(error):
    return render_template('errortemplates/notFound.html.j2'), 404
@app.before_request
def clear_trailing():
    rp = request.path 
    if rp != '/' and rp.endswith('/'):
        return redirect(rp[:-1])
@app.route("/sitemap.xml")
def sitemap_route():
    return sitemap.generate()
@app.route("/robots.txt")
def robotstxt_route():
    return Response(Constants.robots_txt, mimetype='text/plain')
@app.context_processor
def inject_global_variable():
    return {
        "base_url": Constants.full_name,
        "version_num": version,
        "version_label": version_label,
        "cover_src": cover_src,
    }
app.register_blueprint(main_handler)
app.register_blueprint(episode_handler)
app.register_blueprint(img_proxy, url_prefix='/img')
app.register_blueprint(external_image_proxy, url_prefix='/imgext')
app.register_blueprint(err_handlers)
app.register_blueprint(video_handler)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.url_map.strict_slashes = False
#Add app to sitemap
sitemap.init_app(app=app)


if __name__ == '__main__':
    app.run('0.0.0.0', 3008, debug=True, threaded=True)