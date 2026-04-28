from odoo import models, fields, api

class GymTrainer(models.Model):
    _name = 'gym.trainer'
    _description = 'Fitness Trainer'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']

    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')
    
    firstname = fields.Char(string='First Name', required=True)
    surname = fields.Char(string='Last Name')
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')

    def _capitalize_name(self, value):
        if not value:
            return value
        return " ".join(part.capitalize() for part in value.split())

    def _split_name(self, value):
        parts = (value or '').split()
        if not parts:
            return False, False
        firstname = parts[0]
        surname = " ".join(parts[1:]) or False
        return firstname, surname

    @api.onchange('firstname', 'surname')
    def _onchange_complete_name(self):
        if self.firstname:
            self.firstname = self._capitalize_name(self.firstname)
        if self.surname:
            self.surname = self._capitalize_name(self.surname)
        names = [n for n in [self.firstname, self.surname] if n]
        self.name = " ".join(names)

    @api.depends('firstname', 'surname')
    def _compute_complete_name(self):
        for trainer in self:
            names = [n for n in [trainer.firstname, trainer.surname] if n]
            full_name = " ".join(names)
            trainer.name = full_name
            trainer.complete_name = full_name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('firstname'):
                vals['firstname'] = self._capitalize_name(vals['firstname'])
            if vals.get('surname'):
                vals['surname'] = self._capitalize_name(vals['surname'])
            if not vals.get('firstname') and vals.get('name'):
                firstname, surname = self._split_name(vals['name'])
                vals['firstname'] = firstname
                if surname and not vals.get('surname'):
                    vals['surname'] = surname
            if not vals.get('name'):
                firstname = vals.get('firstname') or ''
                surname = vals.get('surname') or ''
                name = f"{firstname} {surname}".strip()
                vals['name'] = name or 'New Trainer'
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if vals.get('firstname'):
            vals['firstname'] = self._capitalize_name(vals['firstname'])
        if vals.get('surname'):
            vals['surname'] = self._capitalize_name(vals['surname'])
        if not vals.get('firstname') and vals.get('name'):
            firstname, surname = self._split_name(vals['name'])
            vals['firstname'] = firstname
            if surname and not vals.get('surname'):
                vals['surname'] = surname
        return super().write(vals)

    specialty_ids = fields.Many2many('gym.trainer.specialty', string='Specialties')
    bio = fields.Text(string='Biography')
    
    availability_ids = fields.One2many('gym.trainer.availability', 'trainer_id', string='Availability')
    session_ids = fields.One2many('gym.trainer.session', 'trainer_id', string='Sessions')

class GymTrainerSpecialty(models.Model):
    _name = 'gym.trainer.specialty'
    _description = 'Trainer Specialty'
    
    name = fields.Char(required=True)

class GymTrainerAvailability(models.Model):
    _name = 'gym.trainer.availability'
    _description = 'Trainer Schedule'
    
    trainer_id = fields.Many2one('gym.trainer', required=True)
    day_of_week = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], required=True)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)

class GymTrainerSession(models.Model):
    _name = 'gym.trainer.session'
    _description = 'Personal Training Session'
    
    trainer_id = fields.Many2one('gym.trainer', required=True)
    member_id = fields.Many2one('gym.member', string='Member', required=True)
    start_datetime = fields.Datetime(required=True)
    duration = fields.Float(string='Duration (Hours)', default=1.0)
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled')
    ], default='scheduled')
    notes = fields.Text()
