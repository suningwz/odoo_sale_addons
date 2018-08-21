# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

# extend the WebsiteSale Class
class WebsiteSaleTPP(WebsiteSale):

# override the /shop/checkout route (with its ugly billing/shipping address forms)
    @http.route(['/shop/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        # setup variables
        isSignedIn = not(order.partner_id.id == request.website.user_id.sudo().partner_id.id)
        isBlankSndName = not(order.x_snd_name)
 
        # if form posted
        if 'x_snd_name' in post:

            # create a sending/billing partner if neccessary
            if not(isSignedIn) and post['x_snd_email']:
                Partner = request.env['res.partner']
                existing = Partner.sudo().search([("email","=",post['x_snd_email'])], limit=1)
                if len(existing) == 1:
                    partner_id = existing.id
                else:
                    new_values = {}
                    new_values['customer'] = True
                    new_values['team_id'] = request.website.salesteam_id and request.website.salesteam_id.id
                    lang = request.lang if request.lang in request.website.mapped('language_ids.code') else None
                    if lang:
                        new_values['lang'] = lang
                    new_values['name'] = post['x_snd_name']
                    new_values['phone'] = post['x_snd_phone']
                    new_values['email'] = post['x_snd_email']
                    partner_id = Partner.sudo().create(new_values).id
                order.partner_id = partner_id
                order.onchange_partner_id()
                order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]

            # store the new values into the order
            values = {}
            for field_name, field_value in post.items():
                if field_name in request.env['sale.order']._fields and field_name.startswith('x_'):
                    values[field_name] = field_value
            if values:
                order.write(values)
            return request.redirect("/shop/delivery")

        # OTHERWISE, its a form intial callup, so lets get values and show
        # copy across from parter_id when the user is signed in already
        if (isBlankSndName and isSignedIn):
            order.x_snd_name = order.partner_id.name
            order.x_snd_email = order.partner_id.email
            order.x_snd_phone = order.partner_id.phone

        values = {
            'order': order,
        }

         # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render("website_tpp.order_form_sender", values)

# add the /shop/delivery route
    @http.route(['/shop/delivery'], type='http', auth="public", website=True)
    def delivery(self, **post):
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        # setup variables
        google_maps_api_key = request.env['ir.config_parameter'].sudo().get_param('google_maps_api_key')
        isBlankRcvName = not(order.x_rcv_name)
        isBlankTo = not(order.x_to)

        # if form posted
        if 'x_rcv_name' in post:

            # create a delivery partner if neccessary
            if post['x_rcv_name'] and post['x_rcv_address']:
                Partner = request.env['res.partner']
                existing = Partner.sudo().search([
                    ("name","=",post['x_rcv_name']),
                    ("parent_id","=",order.partner_id.commercial_partner_id.id),
                    ], limit=1)
                if len(existing) == 1:
                    partner_id = existing.id
                else:
                    new_values = {}
                    new_values['customer'] = True
                    new_values['type'] = 'delivery'
                    new_values['parent_id'] = order.partner_id.id
                    new_values['team_id'] = request.website.salesteam_id and request.website.salesteam_id.id
                    lang = request.lang if request.lang in request.website.mapped('language_ids.code') else None
                    if lang:
                        new_values['lang'] = lang
                    new_values['name'] = post['x_rcv_name']
                    new_values['phone'] = post['x_rcv_phone']
                    new_values['email'] = post['x_rcv_email']
                    new_values['street'] = post['x_rcv_street']
                    new_values['city'] = post['x_rcv_city']
                    new_values['zip'] = post['x_rcv_zip']
                    state = request.env['res.country.state'].search([("code","=",post['x_rcv_state'])], limit=1)
                    if len(state) == 1:
                        new_values['state_id'] = state.id
                    country = request.env['res.country'].search([("name","=",post['x_rcv_country'])], limit=1)
                    if len(country) == 1:
                        new_values['country_id'] = country.id
                    partner_id = Partner.sudo().create(new_values).id
                order.partner_shipping_id = partner_id
                order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]

            # store the new values into the order
            values = {}
            for field_name, field_value in post.items():
                if field_name in request.env['sale.order']._fields and field_name.startswith('x_'):
                    values[field_name] = field_value
            if values:
                order.write(values)
            return request.redirect("/shop/payment")

        # OTHERWISE, its a form intial callup, so lets get values and show
        # copy x_to name across to blank x_rcv_name (but only if blank)
        if (isBlankRcvName and not(isBlankTo)):
            order.x_rcv_name = order.x_to

        # otherwise form has just been called up
        values = {
            'order': order,
            'google_maps_api_key': google_maps_api_key,
        }

         # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render("website_tpp.order_form_delivery", values)

