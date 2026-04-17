from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    state = fields.Selection(selection_add=[
        ('05_pending', 'Pending'),
    ], ondelete={'05_pending': 'set default'})

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == '05_pending':
            return self.env.ref('project_task_state.mt_task_pending')
        return super()._track_subtype(init_values)
