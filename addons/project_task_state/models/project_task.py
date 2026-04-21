from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    state = fields.Selection(selection_add=[
        ('05_pending', 'Pending'),
        ('06_waiting_validation', 'Waiting Validation'),
    ], ondelete={'05_pending': 'set default', '06_waiting_validation': 'set default'})

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values:
            if self.state == '05_pending':
                return self.env.ref('project_task_state.mt_task_pending')
            if self.state == '06_waiting_validation':
                return self.env.ref('project_task_state.mt_task_waiting_validation')
        return super()._track_subtype(init_values)
