from odoo import models


class IrHttp(models.AbstractModel):

    _inherit = "ir.http"

    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------
    
    def _get_sidebar_colors(self):
        """Dummy method to prevent QWeb error during transition."""
        return {
            'color_sidebar_text': '#DEE2E6',
            'color_sidebar_active': '#5D8DA8',
            'color_sidebar_background': '#111827',
        }

    def session_info(self):
        result = super().session_info()
        if self.env.user._is_internal():
            for company in self.env.user.company_ids.with_context(bin_size=True):
                result['user_companies']['allowed_companies'][company.id].update({
                    'has_sidebar_image': bool(company.sidebar_image),
                })
        return result
