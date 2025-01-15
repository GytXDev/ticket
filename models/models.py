# models/models.py
from odoo import models, fields, api
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import random
import string

class Ticket(models.Model):
    _name = 'ticket.ticket'
    _description = 'Ticket'

    name = fields.Many2one('res.partner', required=True, string='Client ou Demandeur')
    problem_type = fields.Selection([('matériel', 'Matériel'), ('logiciel', 'Logiciel'), ('autre', 'Autre')], string='Type de problème')
    description = fields.Text(string='Description')
    short_description = fields.Char(string='Description', compute='_compute_short_description')
    short_directory = fields.Char(string='Responsable', compute='_compute_short_directory')
    statut = fields.Selection(
        [('non-résolu', 'Non Résolu'), ('résolu', 'Résolu')],
        string='Statut',
        default='non-résolu',
        compute='_compute_statut',
        store=True,
        readonly=False
    )
    location = fields.Char(string='Lieu')
    niveau_urgence = fields.Selection([('moyen', 'Moyen'), ('urgent', 'Urgent'), ('très urgent', 'Très Urgent')],
                                      string='Niveau d\'urgence')
    assignee = fields.Many2many('res.partner', string='Assigné à', domain=[('is_company', '=', False)])
    create_date = fields.Datetime(string='Date de création')
    user_ticket = fields.Char(string='Étiquette Utilisateur', required=True)
    period = fields.Char(compute='_compute_period', string='Info')
    directory = fields.Many2one('res.partner', string='Responsable', domain=[('is_company', '=', False)])
    contact = fields.Char(string='Contact')
    date_fix = fields.Date(string='Date d\'échéance')
    date_rest = fields.Char(compute='_compute_date_rest', string='Temps restant')
    # dernière mis à jour
    last_checked_on = fields.Datetime(string='Dernière vérification', default=fields.Datetime.now)
    duree = fields.Float(string='Durée')
    last_updated_on = fields.Datetime(string='Last Updated On', compute='_compute_last_updated_on', store=True)
    ticket_id = fields.Char(string='Identifiant', readonly=True, copy=False, default='ID none')
    email_recipients = fields.Text(
        string='Destinataires',
        help="Liste des adresses email des destinataires, séparées par des virgules."
    )


  #methode pour tronquer les noms des responsables
    def _truncate_directory(self, directory, max_length=17):
        return (directory[:max_length] + '...') if (directory and len(directory) > max_length) else directory


    def _truncate_description(self, description, max_length=100):
        return (description[:max_length] + '...') if (description and len(description) > max_length) else description

    @api.depends('description')
    def _compute_short_description(self):
        for ticket in self:
            ticket.short_description = self._truncate_description( ticket.description)

    @api.depends('directory')
    def _compute_short_directory(self):
        for ticket in self:
            ticket.short_directory= self._truncate_directory(ticket.directory)

    #contraintes
    @api.constrains('create_date', 'date_fix')
    def _check_dates(self):
        for ticket in self:
            if ticket.create_date and ticket.date_fix and ticket.date_fix < ticket.create_date.date():
                raise ValidationError("La date d'échéance ne peut pas être antérieure à la date de création.")


   #mis a jour du kanban_state
    @api.depends('kanban_state')
    def _compute_date_rest(self):
        current_date = date.today().strftime('%d/%m/%Y')
        for ticket in self:
            if ticket.kanban_state == 'done':
                ticket.date_rest = current_date
            else:
                ticket.date_rest = ''


    # Onchange Client ou Demandeur
    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            self.location = self.name.street or ''
            self.contact = self.name.phone or ''

    # kanban state
    kanban_state = fields.Selection([
        ('done', 'Tickets terminés'),
        ('cancelled', 'Tickets annulés'),
        ('in_progress', 'Tickets en cours'),
        ('new', 'Nouveaux tickets')
    ], string='Étape')


    #recuperer les mails
    def _get_recipients(self):
        recipients = []
        if self.assignee:
            recipients += [employee.email for employee in self.assignee]
        if self.directory and self.directory.email:
            recipients.append(self.directory.email)
        if self.name and self.name.email:
            recipients.append(self.name.email)
        return recipients

    #assignement du kanban_state

    @api.depends('write_date')
    def _compute_last_updated_on(self):
        for ticket in self:
            ticket.last_updated_on = ticket.write_date

    # changement de la valeur des statuts des tickets
    @api.onchange('kanban_state')
    def _onchange_kanban_state(self):
        if self.kanban_state == 'done':
            self.statut = 'résolu'
        else:
            self.statut = 'non-résolu'


    def _compute_period(self):
        for ticket in self:
            if ticket.kanban_state == 'done':
                current_date = ticket.last_updated_on
                current_date_str = current_date.strftime('%d/%m/%Y')
                ticket.period = current_date_str
            elif ticket.kanban_state == 'cancelled':
                current_date = ticket.last_updated_on
                current_date_str = current_date.strftime('%d/%m/%Y')
                ticket.period = current_date_str
            else:
                create_date = fields.Datetime.from_string(ticket.create_date)
                current_date = fields.Datetime.now()
                delta = current_date - create_date
                days = delta.days

                if days == 0:
                    period_str = "Créé aujourd'hui"
                elif days == 1:
                    period_str = "Il y a 1 jour"
                else:
                    period_str = f"Il y a {days} jours"

                ticket.period = period_str

    
    @api.model
    def get_smtp_user(self):
        # Recherchez le premier serveur de messagerie sortant
        outgoing_mail_server = self.env['ir.mail_server'].search([], limit=1)

        # Vérifiez si un serveur de messagerie sortant a été trouvé
        if outgoing_mail_server:
            smtp_user = outgoing_mail_server.smtp_user
            return smtp_user


     # Méthode pour envoyer un email
    def send_email(self, recipients, subject, body):
        # Vérifiez si le champ des destinataires est vide
        if not self.email_recipients:
            return  # Ne rien faire si aucun destinataire n'est spécifié

        # Utilisez les destinataires spécifiés dans le champ `email_recipients`
        email_recipients = self.email_recipients.split(',')
        email_recipients = [email.strip() for email in email_recipients if email.strip()]

        if not email_recipients:
            return  # Ne rien faire si le champ est mal formé ou vide après traitement
        
        #  Récupérer l'utilisateur SMTP configuré
        smtp_user = self.get_smtp_user()

        # Couleurs des badges
        urgency_colors = {
            'moyen': '#2ECC71',  # Vert
            'urgent': '#F1C40F',  # Jaune
            'très urgent': '#E74C3C',  # Rouge
        }

        status_colors = {
            'non-résolu': '#E74C3C',  # Rouge
            'résolu': '#2ECC71',  # Vert
        }

        # Construire les informations du ticket pour le corps de l'email
        ticket_info = f"""
        <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; color: #333;">
            <tr>
                <th style="text-align: left; background-color: #f2f2f2; padding: 10px;">Informations</th>
                <th style="text-align: left; background-color: #f2f2f2; padding: 10px;">Détails</th>
            </tr>
        """
        if self.name:
            ticket_info += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Client ou Demandeur</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{self.name.name}</td>
            </tr>
            """
        if self.problem_type:
            ticket_info += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Type de problème</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{self.problem_type}</td>
            </tr>
            """
        if self.description:
            ticket_info += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Description</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{self.description}</td>
            </tr>
            """
        if self.statut:
            color = status_colors.get(self.statut, '#333')
            ticket_info += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Statut</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                    <span style="background-color: {color}; color: white; padding: 5px 10px; border-radius: 5px;">{self.statut}</span>
                </td>
            </tr>
            """
        if self.niveau_urgence:
            color = urgency_colors.get(self.niveau_urgence, '#333')
            ticket_info += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Niveau d'urgence</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                    <span style="background-color: {color}; color: white; padding: 5px 10px; border-radius: 5px;">{self.niveau_urgence}</span>
                </td>
            </tr>
            """
        if self.location:
            ticket_info += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Lieu</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{self.location}</td>
            </tr>
            """
        if self.assignee:
            ticket_info += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Assigné à</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{", ".join(self.assignee.mapped("name"))}</td>
            </tr>
            """
        if self.date_fix:
            ticket_info += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Date d'échéance</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{self.date_fix}</td>
            </tr>
            """
        if self.user_ticket:
            ticket_info += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Étiquette créateur</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{self.user_ticket}</td>
            </tr>
            """
        responsible_name = self.directory.name if self.directory else 'Non défini'
        ticket_info += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">Responsable</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{responsible_name}</td>
        </tr>
        """
        state_label = dict(self._fields['kanban_state'].selection).get(self.kanban_state, '')
        ticket_info += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">Ticket</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{state_label}</td>
        </tr>
        """
        ticket_info += "</table>"

        # Création et envoi de l'email
        self.env['mail.mail'].create({
            'subject': subject,
            'email_from': smtp_user,
            'email_to': ', '.join(email_recipients),
            'body_html': f"""
            <div style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
                <h3 style="color: #2ECC71;">{subject}</h3>
                <p>{body}</p>
                {ticket_info}
            </div>
            """,
        }).send()


    @api.depends('kanban_state', 'statut')
    def _compute_statut(self):
        for ticket in self:
            if ticket.kanban_state == 'done':
                ticket.statut = 'résolu'
            elif ticket.kanban_state == 'cancelled':
                # Conserver le statut existant lors d'une annulation
                ticket.statut = ticket.statut or 'non-résolu'
            else:
                ticket.statut = 'non-résolu'


    
    @api.model
    def create(self, values):
        ticket = super(Ticket, self).create(values)

        # Générer un ID unique pour le ticket
        ticket.ticket_id = self._generate_unique_ticket_id()

        # Mettre à jour l'état kanban en fonction des assignations
        if ticket.assignee:
            ticket.write({'kanban_state': 'in_progress'})
        else:
            ticket.write({'kanban_state': 'new'})

        # Vérifiez si le champ `email_recipients` est rempli avant d'envoyer un email
        if ticket.email_recipients:
            subject = 'Nouveau ticket'
            body = f'Un nouveau ticket a été créé : {ticket.ticket_id}'
            ticket.send_email([], subject, body)

        return ticket

    def write(self, values):
        # Mettre à jour le statut en fonction du champ `kanban_state`
        if 'statut' in values and values['statut'] == 'résolu':
            values['kanban_state'] = 'done'

        # Mise à jour des données
        result = super(Ticket, self).write(values)

        # Vérifiez si le champ `email_recipients` est rempli avant d'envoyer un email
        if self.email_recipients:
            subject = 'Ticket mis à jour'
            body = f'Le ticket {self.ticket_id} a été mis à jour'
            self.send_email([], subject, body)

        return result

    @api.model
    def _ticket_deadline(self):
        today = date.today()
        # Rechercher les tickets dont la date d'échéance est dépassée
        expired_tickets = self.search([('date_fix', '<', today)])
        for ticket in expired_tickets:
            # Vérifiez si le champ `email_recipients` est rempli
            if ticket.email_recipients:
                # Préparer le sujet et le corps de l'email
                subject = 'Ticket dépassé'
                body = f'Le ticket {ticket.ticket_id} est passé à la date d\'échéance.'
                
                # Envoyer l'email aux destinataires spécifiés
                ticket.send_email([], subject, body)


    def _generate_unique_ticket_id(self):
        while True:
            # Générer 4 chiffres aléatoires
            digits = ''.join(random.choices(string.digits, k=4))

            # Générer 3 lettres aléatoires
            letters = ''.join(random.choices(string.ascii_uppercase, k=3))

            # Concaténer les chiffres et les lettres
            ticket_id = f'{digits}-{letters}'

            # Vérifier si l'identifiant est déjà utilisé
            existing_ticket = self.search([('ticket_id', '=', ticket_id)])
            if not existing_ticket:
                return ticket_id
            

    #comptage des tickets par mois
    @api.model
    def get_ticket_count_by_month(self):
        ticket_count = defaultdict(int)
        tickets = self.search([])

        for ticket in tickets:
            if ticket.create_date:
                month = ticket.create_date.month
                ticket_count[month] += 1

        return dict(ticket_count)

    #comptage des tickets
    @api.model
    def get_ticket_count_by_state(self):
        ticket_count = {
            'new_ticket_count': self.search_count([('kanban_state', '=', 'new')]),
            'in_progress_ticket_count': self.search_count([('kanban_state', '=', 'in_progress')]),
            'done_ticket_count': self.search_count([('kanban_state', '=', 'done')]),
            'cancelled_ticket_count': self.search_count([('kanban_state', '=', 'cancelled')]),
        }
        return ticket_count
    #decompte des tickets en fonction des jours
    @api.model
    def get_ticket_count_by_day(self):
        today = fields.Date.today()
        ticket_count = {
            'new_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', today),
                ('last_updated_on', '<=', today),
                ('kanban_state', '=', 'new')
                ]),
            'in_progress_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', today),
                ('last_updated_on', '<=', today),
                ('kanban_state', '=', 'in_progress')
            ]),
            'done_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', today),
                ('last_updated_on', '<=', today),
                ('kanban_state', '=', 'done')
            ]),
            'cancelled_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', today),
                ('last_updated_on', '<=', today),
                ('kanban_state', '=', 'cancelled')
            ])
        }
        return ticket_count

    @api.model
    def get_ticket_count_by_years(self):
        current_year = datetime.now().year
        ticket_count = {
            'new_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', f'{current_year}-01-01 00:00:00'),
                ('last_updated_on', '<=', f'{current_year}-12-31 23:59:59'),
                ('kanban_state', '=', 'new')
            ]),
            'in_progress_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', f'{current_year}-01-01 00:00:00'),
                ('last_updated_on', '<=', f'{current_year}-12-31 23:59:59'),
                ('kanban_state', '=', 'in_progress')
            ]),
            'done_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', f'{current_year}-01-01 00:00:00'),
                ('last_updated_on', '<=', f'{current_year}-12-31 23:59:59'),
                ('kanban_state', '=', 'done')
            ]),
            'cancelled_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', f'{current_year}-01-01 00:00:00'),
                ('last_updated_on', '<=', f'{current_year}-12-31 23:59:59'),
                ('kanban_state', '=', 'cancelled')
            ])
        }
        return ticket_count

    @api.model
    def get_ticket_count_by_month(self):
        current_date = fields.Date.today()
        start_date = current_date.replace(day=1)
        end_date = start_date + relativedelta(day=31)

        ticket_count = {
            'new_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'new')
            ]),
            'in_progress_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'in_progress')
            ]),
            'done_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'done')
            ]),
            'cancelled_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'cancelled')
            ])
        }
        return  ticket_count


    @api.model
    def get_ticket_count_by_week(self):
        current_date = fields.Date.today()

        # Trouver le premier jour de la semaine en cours (lundi)
        start_date = current_date - timedelta(days=current_date.weekday())

        # Trouver le dernier jour de la semaine en cours (dimanche)
        end_date = start_date + timedelta(days=6)

        ticket_count = {
            'new_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'new')
            ]),
            'in_progress_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'in_progress')
            ]),
            'done_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'done')
            ]),
            'cancelled_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'cancelled')
            ])
        }
        return ticket_count



    #methode pour compter les niveaux d'urgence non resolu
    @api.model
    def get_tickets_emergency(self):
        ticket_counts = {
            'moyen': 0,
            'urgent': 0,
            'très urgent': 0
        }

        tickets = self.search([('statut', '=', 'non-résolu')])

        for ticket in tickets:
            niveau_urgence = ticket.niveau_urgence
            ticket_counts[niveau_urgence] += 1

        return ticket_counts

    @api.model
    def get_tickets_emergency_day(self):
        today = fields.Date.today()
        ticket_counts = {
            'moyen': 0,
            'urgent': 0,
            'très urgent': 0,
        }
        tickets = self.search([
            ('last_updated_on', '>=', today),
            ('last_updated_on', '<=', today),
            ('statut', '=', 'non-résolu')
        ])
        for ticket in tickets :
            niveau_urgence = ticket.niveau_urgence
            ticket_counts[niveau_urgence] += 1

        return  ticket_counts

    @api.model
    def get_tickets_emergency_month(self):
        current_date = fields.Date.today()
        start_date = current_date.replace(day=1)
        end_date = start_date + relativedelta(day=31)

        ticket_counts = {
            'moyen': 0,
            'urgent': 0,
            'très urgent': 0,
        }
        tickets = self.search([
            ('last_updated_on', '>=', start_date),
            ('last_updated_on', '<=', end_date),
            ('statut', '=', 'non-résolu')
        ])
        for ticket in tickets:
            niveau_urgence = ticket.niveau_urgence
            ticket_counts[niveau_urgence] += 1

        return ticket_counts

    @api.model
    def get_tickets_emergency_years(self):
        current_year =  datetime.now().year

        ticket_counts = {
            'moyen': 0,
            'urgent': 0,
            'très urgent': 0,
        }
        tickets = self.search([
            ('last_updated_on', '>=', f'{current_year}-01-01 00:00:00'),
            ('last_updated_on', '<=', f'{current_year}-12-31 23:59:59'),
            ('statut', '=', 'non-résolu')
        ])
        for ticket in tickets:
            niveau_urgence = ticket.niveau_urgence
            ticket_counts[niveau_urgence] += 1

        return ticket_counts

    @api.model
    def get_tickets_emergency_week(self):
        current_date = fields.Date.today()

        # Trouver le premier jour de la semaine en cours (lundi)
        start_date = current_date - timedelta(days=current_date.weekday())

        # Trouver le dernier jour de la semaine en cours (dimanche)
        end_date = start_date + timedelta(days=6)

        ticket_counts = {
            'moyen': 0,
            'urgent': 0,
            'très urgent': 0,
        }
        tickets = self.env['ticket.ticket'].search([
            ('last_updated_on', '>=', start_date),
            ('last_updated_on', '<=', end_date),
            ('statut', '=', 'non-résolu')
        ])
        for ticket in tickets:
            niveau_urgence = ticket.niveau_urgence
            ticket_counts[niveau_urgence] += 1

        return  ticket_counts



    #methode pour afficher les statuts des tickets
    @api.model
    def get_tickets_stats(self):
        ticket_counts = self.get_ticket_count_by_state()
        resolved_count = ticket_counts['done_ticket_count']
        unresolved_count = sum(ticket_counts.values()) - resolved_count

        steps = ['Nouveaux tickets', 'Tickets en cours', 'Tickets terminés', 'Tickets annulés']
        ticket_counts = [ticket_counts['new_ticket_count'], ticket_counts['in_progress_ticket_count'],
                         ticket_counts['done_ticket_count'], ticket_counts['cancelled_ticket_count']]

        return {
            'resolved_count': resolved_count,
            'unresolved_count': unresolved_count,
            'steps': steps,
            'ticket_counts': ticket_counts,
        }

    #responsables et agents avec leurs nombres de tickets solved
    @api.model
    def get_agents_stats(self):
        user_stats = []

        # Recherche des responsables avec des tickets
        users_with_tickets = self.env['res.partner'].search([
            ('id', 'in', self.env['ticket.ticket'].sudo().search([('directory', '!=', False)]).mapped('directory.id'))
        ])
        for user in users_with_tickets:
            resolved_count = self.env['ticket.ticket'].search_count([
                '|',
                ('directory', '=', user.id),
                ('assignee', '=', user.id),
                ('kanban_state', '=', 'done')
            ])
            user_stats.append({
                'user_name': user.name,
                'resolved_count': resolved_count,
            })

        # Recherche des agents avec des tickets
        employees_with_tickets = self.env['res.partner'].search([
            ('id', 'in', self.env['ticket.ticket'].sudo().search([('assignee', '!=', False)]).mapped('assignee.id'))
        ])
        for employee in employees_with_tickets:
            if employee not in users_with_tickets:
                resolved_count = self.env['ticket.ticket'].search_count([
                    ('assignee', '=', employee.id),
                    ('kanban_state', '=', 'done')
                ])
                user_stats.append({
                    'user_name': employee.name,
                    'resolved_count': resolved_count,
                })

        return user_stats

    #get years
    @api.model
    def get_years(self):
        current_year = datetime.now().year

        resolved_count = self.env['ticket.ticket'].search_count([
            ('last_updated_on', '>=', f'{current_year}-01-01 00:00:00'),
            ('last_updated_on', '<=', f'{current_year}-12-31 23:59:59'),
            ('kanban_state', '=', 'done')
        ])

        ticket_counts = {
            'new_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', f'{current_year}-01-01 00:00:00'),
                ('last_updated_on', '<=', f'{current_year}-12-31 23:59:59'),
                ('kanban_state', '=', 'new')
            ]),
            'in_progress_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', f'{current_year}-01-01 00:00:00'),
                ('last_updated_on', '<=', f'{current_year}-12-31 23:59:59'),
                ('kanban_state', '=', 'in_progress')
            ]),
            'done_ticket_count': resolved_count,
            'cancelled_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', f'{current_year}-01-01 00:00:00'),
                ('last_updated_on', '<=', f'{current_year}-12-31 23:59:59'),
                ('kanban_state', '=', 'cancelled')
            ])
        }

        unresolved_count = sum(count for key, count in ticket_counts.items() if key != 'done_ticket_count')

        steps = ['Nouveaux tickets', 'Tickets en cours', 'Tickets terminés', 'Tickets annulés']
        ticket_counts = [ticket_counts['new_ticket_count'], ticket_counts['in_progress_ticket_count'],
                         ticket_counts['done_ticket_count'], ticket_counts['cancelled_ticket_count']]

        result = {
            'resolved_count': resolved_count,
            'unresolved_count': unresolved_count,
            'steps': steps,
            'ticket_counts': ticket_counts,
        }

        return result

    #tickets au cours du mois
    @api.model
    def get_month(self):
        current_date = fields.Date.today()

        start_date = current_date.replace(day=1)
        end_date = start_date + relativedelta(day=31)

        resolved_count = self.env['ticket.ticket'].search_count([
            ('last_updated_on', '>=', start_date),
            ('last_updated_on', '<=', end_date),
            ('kanban_state', '=', 'done')
        ])

        ticket_counts = {
            'new_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'new')
            ]),
            'in_progress_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'in_progress')
            ]),
            'done_ticket_count': resolved_count,
            'cancelled_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'cancelled')
            ])
        }

        unresolved_count = sum(count for key, count in ticket_counts.items() if key != 'done_ticket_count')

        steps = ['Nouveaux tickets', 'Tickets en cours', 'Tickets terminés', 'Tickets annulés']
        ticket_counts = [ticket_counts['new_ticket_count'], ticket_counts['in_progress_ticket_count'],
                         ticket_counts['done_ticket_count'], ticket_counts['cancelled_ticket_count']]

        result = {
            'resolved_count': resolved_count,
            'unresolved_count': unresolved_count,
            'steps': steps,
            'ticket_counts': ticket_counts,
        }

        return result

    #tickets au cours de la semaine
    @api.model
    def get_week(self):
        current_date = fields.Date.today()

        # Trouver le premier jour de la semaine en cours (lundi)
        start_date = current_date - timedelta(days=current_date.weekday())

        # Trouver le dernier jour de la semaine en cours (dimanche)
        end_date = start_date + timedelta(days=6)

        resolved_count = self.env['ticket.ticket'].search_count([
            ('last_updated_on', '>=', start_date),
            ('last_updated_on', '<=', end_date),
            ('kanban_state', '=', 'done')
        ])

        ticket_counts = {
            'new_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'new')
            ]),
            'in_progress_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'in_progress')
            ]),
            'done_ticket_count': resolved_count,
            'cancelled_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', start_date),
                ('last_updated_on', '<=', end_date),
                ('kanban_state', '=', 'cancelled')
            ])
        }

        unresolved_count = sum(count for key, count in ticket_counts.items() if key != 'done_ticket_count')

        steps = ['Nouveaux tickets', 'Tickets en cours', 'Tickets terminés', 'Tickets annulés']
        ticket_counts = [ticket_counts['new_ticket_count'], ticket_counts['in_progress_ticket_count'],
                         ticket_counts['done_ticket_count'], ticket_counts['cancelled_ticket_count']]

        result = {
            'resolved_count': resolved_count,
            'unresolved_count': unresolved_count,
            'steps': steps,
            'ticket_counts': ticket_counts,
        }

        return result

    #tickets au cours de la journéé
    @api.model
    def get_today(self):
        today = date.today()

        resolved_count = self.env['ticket.ticket'].search_count([
            ('last_updated_on', '>=', today),
            ('last_updated_on', '<=', today),
            ('kanban_state', '=', 'done')
        ])

        ticket_counts = {
            'new_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', today),
                ('last_updated_on', '<=', today),
                ('kanban_state', '=', 'new')
            ]),
            'in_progress_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', today),
                ('last_updated_on', '<=', today),
                ('kanban_state', '=', 'in_progress')
            ]),
            'done_ticket_count': resolved_count,
            'cancelled_ticket_count': self.env['ticket.ticket'].search_count([
                ('last_updated_on', '>=', today),
                ('last_updated_on', '<=', today),
                ('kanban_state', '=', 'cancelled')
            ])
        }

        unresolved_count = sum(count for key, count in ticket_counts.items() if key != 'done_ticket_count')

        steps = ['Nouveaux tickets', 'Tickets en cours', 'Tickets terminés', 'Tickets annulés']
        ticket_counts = [ticket_counts['new_ticket_count'], ticket_counts['in_progress_ticket_count'],
                         ticket_counts['done_ticket_count'], ticket_counts['cancelled_ticket_count']]

        result = {
            'resolved_count': resolved_count,
            'unresolved_count': unresolved_count,
            'steps': steps,
            'ticket_counts': ticket_counts,
        }
        return result