from odoo import http, _, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class GymCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        # Member Logic
        member = request.env['gym.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if 'gym_subscription_count' in counters:
            values['gym_subscription_count'] = member.subscription_ids.search_count([('member_id', '=', member.id)]) if member else 0
            
        if 'gym_class_count' in counters:
             domain = [
                ('state', '=', 'scheduled'),
                ('start_datetime', '>=', fields.Datetime.now())
            ]
             values['gym_class_count'] = request.env['gym.class.session'].sudo().search_count(domain)

        # Trainer Logic
        trainer = request.env['gym.trainer'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if 'gym_trainer_session_count' in counters:
            values['gym_trainer_session_count'] = request.env['gym.class.session'].sudo().search_count([('trainer_id', '=', trainer.id)]) if trainer else 0
            
        return values
        
    @http.route(['/my/gym/classes', '/my/gym/classes/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_gym_classes(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        member = request.env['gym.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not member:
            return request.render("tara_gym.portal_my_gym_no_member", values)

        Session = request.env['gym.class.session']
        domain = [
            ('state', '=', 'scheduled'),
            ('start_datetime', '>=', fields.Datetime.now())
        ]
        
        # Pager
        class_count = Session.sudo().search_count(domain)
        pager = portal_pager(
            url="/my/gym/classes",
            url_args={},
            total=class_count,
            page=page,
            step=10
        )
        
        sessions = Session.sudo().search(domain, limit=10, offset=pager['offset'], order='start_datetime asc')
        
        values.update({
            'sessions': sessions,
            'member': member,
            'page_name': 'gym_classes',
            'pager': pager,
            'default_url': '/my/gym/classes',
        })
        return request.render("tara_gym.portal_my_gym_classes_list", values)

    @http.route(['/my/gym/class/enroll/<int:session_id>'], type='http', auth="user", website=True, methods=['POST'])
    def portal_gym_class_enroll(self, session_id, **kw):
        partner = request.env.user.partner_id
        member = request.env['gym.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not member:
            return request.redirect('/my')

        session = request.env['gym.class.session'].sudo().browse(session_id)
        
        # Check if already enrolled
        existing = request.env['gym.class.enrollment'].sudo().search([
            ('session_id', '=', session.id),
            ('member_id', '=', member.id)
        ])
        
        if not existing:
             try:
                request.env['gym.class.enrollment'].sudo().create({
                    'session_id': session.id,
                    'member_id': member.id,
                })
             except Exception as e:
                 # Ideally handle full capacity or unique constraint errors gracefully
                 pass
        
        return request.redirect('/my/gym/classes')


    @http.route(['/my/gym/subscriptions', '/my/gym/subscriptions/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_gym_subscriptions(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        member = request.env['gym.member'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not member:
            return request.render("tara_gym.portal_my_gym_no_member", values)

        Subscription = request.env['gym.membership.subscription']
        domain = [('member_id', '=', member.id)]

        subscriptions = Subscription.sudo().search(domain)
        values.update({
            'subscriptions': subscriptions,
            'page_name': 'gym_subscription',
            'default_url': '/my/gym/subscriptions',
        })
        return request.render("tara_gym.portal_my_gym_subscriptions", values)

    @http.route(['/my/gym/trainer/sessions', '/my/gym/trainer/sessions/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_gym_trainer_sessions(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        trainer = request.env['gym.trainer'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not trainer:
            return request.redirect('/my') # Or show a "Not a trainer" page

        Session = request.env['gym.class.session']
        domain = [('trainer_id', '=', trainer.id)]
        
        # Pager
        session_count = Session.sudo().search_count(domain)
        pager = portal_pager(
            url="/my/gym/trainer/sessions",
            url_args={},
            total=session_count,
            page=page,
            step=10
        )
        
        sessions = Session.sudo().search(domain, limit=10, offset=pager['offset'], order='start_datetime desc')
        
        values.update({
            'sessions': sessions,
            'page_name': 'gym_trainer_session',
            'pager': pager,
            'default_url': '/my/gym/trainer/sessions',
        })
        return request.render("tara_gym.portal_my_gym_trainer_sessions", values)
    
    @http.route(['/my/gym/trainer/session/<int:session_id>'], type='http', auth="user", website=True)
    def portal_my_gym_trainer_session_detail(self, session_id, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        trainer = request.env['gym.trainer'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        
        if not trainer:
            return request.redirect('/my')

        session = request.env['gym.class.session'].sudo().browse(session_id)
        if session.trainer_id.id != trainer.id:
            return request.redirect('/my/gym/trainer/sessions')
            
        values.update({
            'session': session,
            'page_name': 'gym_trainer_session',
        })
        return request.render("tara_gym.portal_my_gym_trainer_session_detail", values)
