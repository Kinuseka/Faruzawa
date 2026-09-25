from flask import Blueprint, render_template, redirect, abort
from flask import request as f_request
from flask import Response
from bridge import catalog
from essentials.essentials import sitemap
import frzw_exceptions

main_handler = Blueprint('main_handler', __name__)

@sitemap.include()
@main_handler.route('/', methods=['GET'])
def mainIndex():
    sections = catalog.home_sections()
    temp = render_template(
        "home.html.j2",
        front=sections["trending"],
        popular=sections["popular"],
        new=sections["new"],
    )
    return Response(temp)

@main_handler.route('/home', methods=['GET'])
def redirectHome():
    return redirect('/')

@sitemap.include()
@main_handler.route('/popular', methods=['GET'])
def popIndex():
    current_page = int(f_request.args.get('page', 1))
    try:
        titles, pagination = catalog.lister("popular", current_page)
    except frzw_exceptions.NotFoundPagination:
        return abort(404)
    temp = render_template("lister.html.j2", title='Popular', data=titles, pagination=pagination)
    return Response(temp)

@sitemap.include()
@main_handler.route('/new', methods=['GET'])
def newIndex():
    current_page = int(f_request.args.get('page', 1))
    try:
        titles, pagination = catalog.lister("new", current_page)
    except frzw_exceptions.NotFoundPagination:
        return abort(404)
    temp = render_template("lister.html.j2", title='New Releases', data=titles, pagination=pagination)
    return Response(temp)

@main_handler.route('/genre', methods=['GET'])
def genreIndex():
    return render_template('errortemplates/comingSoon.html.j2', title='503 Work in progress - Faruzawa'), 503

@sitemap.include()
@main_handler.route('/search.html', methods=['GET'])
def searchIndex():
    temp = render_template("search.html.j2")
    return Response(temp)

@main_handler.route('/search_query', methods=['POST'])
def searchAjax():
    search_query = f_request.args.get('data', None)
    current_page = int(f_request.args.get('page', 1))
    result = catalog.search(search_query, current_page)
    if not result:
        return render_template('errortemplates/notFound.html.j2', ajax=True), 404
    titles, pagination = result
    temp = render_template("lister.html.j2", ajax=True, data=titles, pagination=pagination)
    return temp

@sitemap.include()
@main_handler.route('/about', methods=['GET'])
def aboutUs():
    return render_template('aboutUs.html.j2')
    

    