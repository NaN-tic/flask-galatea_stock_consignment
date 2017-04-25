from flask import Blueprint, render_template, current_app, abort, g, \
    url_for, request, session, redirect, flash, jsonify, send_file
from galatea.tryton import tryton
from galatea.utils import slugify
from galatea.helpers import login_required, customer_required, manager_required
from galatea.csrf import csrf
from flask_babel import gettext as _, lazy_gettext, ngettext
from flask_paginate import Pagination
from trytond.transaction import Transaction
import tempfile

project = Blueprint('project', __name__, template_folder='templates')

DISPLAY_MSG = lazy_gettext('Displaying <b>{start} - {end}</b> of <b>{total}</b>')

LIMIT = current_app.config.get('TRYTON_PAGINATION_PROJECT_LIMIT', 20)

Project = tryton.pool.get('project.work')
GalateaUser = tryton.pool.get('galatea.user')

@project.route("/<int:id>", endpoint="project")
@login_required
@customer_required
@tryton.transaction()
def project_detail(lang, id):
    '''Project Detail'''
    customer = session.get('customer')
    if not session.get('logged_in'):
        session.pop('customer', None)

    projects = Project.search([
        ('id', '=', id),
        ('party', '=', customer),
        ('galatea', '=', True),
        ], limit=1)
    if not projects:
        abort(404)

    project, = Project.browse(projects)

    #breadcumbs
    breadcrumbs = [{
        'slug': url_for('my-account', lang=g.language),
        'name': _('My Account'),
        }, {
        'slug': url_for('.projects', lang=g.language),
        'name': _('Projects'),
        }, {
        'slug': url_for('.project', lang=g.language, id=project.id),
        'name': project.rec_name,
        }]

    return render_template('project.html',
            breadcrumbs=breadcrumbs,
            project=project,
            )

@project.route("/", endpoint="projects")
@login_required
@customer_required
@tryton.transaction()
def project_list(lang):
    '''Projects'''

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    domain = [
        ('party', '=', session['customer']),
        ('galatea', '=', True),
        ]
    q = request.args.get('q')
    if q:
        domain.append(('rec_name', 'ilike', '%'+q+'%'))
        session.q = q
    else:
        domain.append(('type', '=', 'project'))
        session.q = None
    if hasattr(Project, 'galatea_domain'):
        domain += Project.galatea_domain()

    phase = request.args.get('phase', type=int)
    if phase:
        domain.append(('task_phase', '=', phase))
        session.phase = phase
    tracker = request.args.get('tracker', type=int)
    if tracker:
        domain.append(('tracker', '=', tracker))
        session.tracker = tracker
    priority = request.args.get('priority')
    if priority:
        domain.append(('priority', '=', priority))
        session.priority = priority

    total = Project.search_count(domain)
    offset = (page-1)*LIMIT
    projects = Project.search(domain, offset, LIMIT)

    pagination = Pagination(
        page=page, total=total, per_page=LIMIT, display_msg=DISPLAY_MSG, bs_version='3')

    #breadcumbs
    breadcrumbs = [{
        'slug': url_for('my-account', lang=g.language),
        'name': _('My Account'),
        }, {
        'slug': url_for('.projects', lang=g.language),
        'name': _('Projects'),
        }]

    return render_template('projects.html',
            breadcrumbs=breadcrumbs,
            pagination=pagination,
            projects=projects,
            )
