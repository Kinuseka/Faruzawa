from flask import Blueprint, render_template
from flask import Response

err_handlers = Blueprint('error_handler', __name__)
@err_handlers.route('/404.html')
def http_notfound():
    return render_template('notFound.html.j2'), 404