# controllers\controllers.py
# controllers/controllers.py
from odoo import http
from odoo.http import request

class TicketController(http.Controller):

    @http.route('/api/tickets/stats', type='json', auth="public", website=True)
    def get_ticket_stats(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_tickets_stats()

    @http.route('/api/tickets/emergency', type='json', auth="public", website=True)
    def get_tickets_emergency(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_tickets_emergency()

    @http.route('/api/tickets/emergency/day', type='json', auth="public", website=True)
    def get_tickets_emergency_day(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_tickets_emergency_day()

    @http.route('/api/tickets/emergency/month', type='json', auth="public", website=True)
    def get_tickets_emergency_month(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_tickets_emergency_month()

    @http.route('/api/tickets/emergency/week', type='json', auth="public", website=True)
    def get_tickets_emergency_week(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_tickets_emergency_week()

    @http.route('/api/tickets/emergency/years', type='json', auth="public", website=True)
    def get_tickets_emergency_years(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_tickets_emergency_years()

    @http.route('/api/tickets/count/day', type='json', auth="public", website=True)
    def get_ticket_count_by_day(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_ticket_count_by_day()

    @http.route('/api/tickets/count/month', type='json', auth="public", website=True)
    def get_ticket_count_by_month(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_ticket_count_by_month()

    @http.route('/api/tickets/count/week', type='json', auth="public", website=True)
    def get_ticket_count_by_week(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_ticket_count_by_week()

    @http.route('/api/tickets/count/years', type='json', auth="public", website=True)
    def get_ticket_count_by_years(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_ticket_count_by_years()

    @http.route('/api/tickets/count/state', type='json', auth="public", website=True)
    def get_ticket_count_by_state(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_ticket_count_by_state()

    @http.route('/api/tickets/chart/today', type='json', auth="public", website=True)
    def get_today(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_today()

    @http.route('/api/tickets/chart/month', type='json', auth="public", website=True)
    def get_month(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_month()

    @http.route('/api/tickets/chart/week', type='json', auth="public", website=True)
    def get_week(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_week()

    @http.route('/api/tickets/chart/year', type='json', auth="public", website=True)
    def get_years(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_years()

    @http.route('/api/tickets/agents_stats', type='json', auth="public", website=True)
    def get_agents_stats(self):
        Ticket = request.env['ticket.ticket'].sudo()
        return Ticket.get_agents_stats()
    
    @http.route('/api/tickets/last_update', type='json', auth="public", website=True)
    def get_last_update(self):
        Ticket = request.env['ticket.ticket'].sudo()
        # Rechercher le ticket le plus récemment mis à jour
        latest_ticket = Ticket.search([], order='write_date desc', limit=1)
        return latest_ticket.write_date.isoformat() if latest_ticket else None


    # Vous pouvez ajouter d'autres routes selon les besoins.
