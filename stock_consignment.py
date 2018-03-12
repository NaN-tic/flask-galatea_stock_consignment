from flask import (Blueprint, render_template, current_app, g, url_for, request,
    session)
from galatea.tryton import tryton
from galatea.helpers import customer_required
from flask_babel import gettext as _, lazy_gettext
from flask_login import login_required
from datetime import date
from dateutil.relativedelta import relativedelta

stock_consignment = Blueprint('stock_consignment', __name__,
    template_folder='templates')

MONTHS = [0, 1, 2, 3]

Location = tryton.pool.get('stock.location')
Product = tryton.pool.get('product.product')
StockMoves = tryton.pool.get('stock.move')
InvoiceLine = tryton.pool.get('account.invoice.line')

@stock_consignment.route("/", endpoint="stock_consignment")
@login_required
@customer_required
@tryton.transaction()
def stock_list(lang):
    '''Stocks'''

    domain = [
        ('product_suppliers.party', '=', session['customer']),
        ]
    products = Product.search(domain)
    locations = Location.search([
            ('consignment_party', '=', session['customer']),
            ])
    location_ids = [location.id for location in locations]
    product_ids = []
    for product in products:
        moves = StockMoves.search_count([
                ('product', '=', product),
                ('effective_date', '>',
                    date.today() - relativedelta(months=len(MONTHS))),
                ['OR',
                    ('to_location', 'in', location_ids),
                    ('from_location', 'in', location_ids),
                    ]
                ])
        if moves:
            product_ids.append(product.id)
    pbl = {}
    if location_ids and product_ids:
        pbl = Product.products_by_location(location_ids=location_ids,
            product_ids=product_ids)
    stock = {}
    for product_id in product_ids:
        product = Product(product_id)
        supplier_code = ''
        for supplier in product.template.product_suppliers:
            if supplier.party.id == session['customer']:
                supplier_code = supplier.code
        product_name = ' '.join([supplier_code, product.rec_name])
        stock[product_id] = {
            'product': product_name,
            'quantity': 0,
            'locations': [],
            }
    for (location_id, product_id), quantity in pbl.items():
        if product_id not in product_ids:
            continue
        stock[product_id]['quantity'] += quantity
        location = Location(location_id).name
        stock[product_id]['locations'].append(location)
    for product_id in stock:
        stock[product_id]['locations'] = ', '.join(
            stock[product_id]['locations'])
        domain = [
            ('invoice.party', '=', session['customer']),
            ('product', '=', product_id),
            ]
        for month in MONTHS:
            quantity = 0
            first_day_current_month = (date.today().replace(day=1) -
                relativedelta(months=month))
            first_day_next_month = (first_day_current_month +
                relativedelta(months=1))
            invoice_lines = InvoiceLine.search(domain + [
                    ('invoice.invoice_date', '>=', first_day_current_month),
                    ('invoice.invoice_date', '<', first_day_next_month),
                    ])
            for invoice_line in invoice_lines:
                quantity += invoice_line.quantity
            stock[product_id]['month' + str(month)] = quantity

    breadcrumbs = [{
        'slug': url_for('my-account', lang=g.language),
        'name': _('My Account'),
        }, {
        'slug': url_for('.stock_consignment', lang=g.language),
        'name': _('Stock'),
        }]

    return render_template('stock_consignment.html',
            breadcrumbs=breadcrumbs,
            stock=stock,
            )
