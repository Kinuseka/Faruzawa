from flask import Blueprint, render_template, redirect, abort
from flask import request as f_request
from flask import Response
from API import GogoAPI, Goscraper, paginator
from essentials.essentials import sitemap
import frzw_exceptions

main_handler = Blueprint('main_handler', __name__)

@sitemap.include()
@main_handler.route('/', methods=['GET'])
def mainIndex():
    goapi = GogoAPI()
    popular = goapi.popular()
    new = goapi.new()
    temp = render_template("home.html.j2", front=popular.get_titles(), popular = popular.get_titles(), new = new.get_titles())
    return Response(temp)

@main_handler.route('/home', methods=['GET'])
def redirectHome():
    return redirect('/')

@sitemap.include()
@main_handler.route('/popular', methods=['GET'])
def popIndex():
    current_page = int(f_request.args.get('page', 1))
    #API
    goapi = GogoAPI()
    gogo = goapi.popular()
    try:
        gogo = paginator(gogo, current_page)
    except frzw_exceptions.NotFoundPagination:
        return abort(404)
    pagination = gogo.get_pagination()
    #Pagination counter
    page_on = pagination['page_on']
    page_total = pagination['page_total']
    #Pagination guard
    if current_page > page_total or current_page < 1: return abort(404)
    temp = render_template("lister.html.j2", title='Popular', data=gogo.get_titles(), pagination=pagination)
    return Response(temp)

@sitemap.include()
@main_handler.route('/new', methods=['GET'])
def newIndex():
    current_page = int(f_request.args.get('page', 1))
    #API
    goapi = GogoAPI()
    gogo = goapi.new()
    try:
        gogo = paginator(gogo, current_page)
    except frzw_exceptions.NotFoundPagination:
        return abort(404)
    pagination = gogo.get_pagination()
    #Pagination counter
    page_on = pagination['page_on']
    page_total = pagination['page_total']
    #Pagination guard
    if current_page > page_total or current_page < 1: return abort(404)
    temp = render_template("lister.html.j2", title='New Releases', data=gogo.get_titles(), pagination=pagination)
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
    goapi = GogoAPI()
    search_res = goapi.search_anime(search_query=search_query)
    if not search_res or not search_res.get_result_count(): return render_template('errortemplates/notFound.html.j2', ajax=True), 404
    search_res = paginator(search_res, current_page)
    pagination = search_res.get_pagination()
    #Pagination counter
    page_on = pagination['page_on']
    page_total = pagination['page_total']
    #Pagination guard
    if current_page > page_total or current_page < 1: return render_template('errortemplates/notFound.html.j2', ajax=True), 404
    temp = render_template("lister.html.j2", ajax=True, data=search_res.get_titles(), pagination=pagination)
    return temp

@sitemap.include()
@main_handler.route('/about', methods=['GET'])
def aboutUs():
    return render_template('aboutUs.html.j2')
    

    