import logging
import base64

from odoo import fields, models, api, _
from odoo.tools import misc, file_path

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------

    sidebar_image = fields.Binary(
        related='company_id.sidebar_image',
        readonly=False
    )

    theme_color_sidebar_text = fields.Char(
        string='Sidebar Text Color'
    )

    theme_color_sidebar_active = fields.Char(
        string='Sidebar Active Color'
    )

    theme_color_sidebar_background = fields.Char(
        string='Sidebar Background Color'
    )

    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------

    def _get_scss_color_data(self):
        return {
            'sidebar-text': self.theme_color_sidebar_text or '#DEE2E6',
            'sidebar-active': self.theme_color_sidebar_active or '#5D8DA8',
            'sidebar-background': self.theme_color_sidebar_background or '#111827',
        }

    def _save_scss_attachment(self):
        colors = self._get_scss_color_data()
        
        # Read the template SCSS from disk
        path = file_path('imeco_web_sidebar/static/src/scss/colors.scss')
        with misc.file_open(path, 'rb') as f:
            content = f.read().decode('utf-8')
            
        # Replace variables in the content
        new_content = content
        for key, value in colors.items():
            # Match $key: ... ;
            import re
            pattern = re.compile(rf'\${key}:\s*[^;]+;')
            new_content = pattern.sub(f'${key}: {value};', new_content)

        # Create/Update attachment
        url = '/_custom/assets/web._assets_primary_variables/imeco_web_sidebar/static/src/scss/colors.scss'
        Attachment = self.env['ir.attachment'].sudo()
        attachment = Attachment.search([('url', '=', url)], limit=1)
        
        data = base64.b64encode(new_content.encode('utf-8'))
        if attachment:
            attachment.write({'datas': data})
        else:
            attachment = Attachment.create({
                'name': 'Sidebar Colors Custom',
                'type': 'binary',
                'datas': data,
                'url': url,
                'public': True,
            })

        # Ensure ir.asset exists to replace the original
        Asset = self.env['ir.asset'].sudo()
        original_path = 'imeco_web_sidebar/static/src/scss/colors.scss'
        asset = Asset.search([
            ('target', '=', original_path),
            ('bundle', '=', 'web._assets_primary_variables'),
            ('directive', '=', 'replace')
        ], limit=1)
        
        if asset:
            asset.write({'path': url})
        else:
            Asset.create({
                'name': 'Sidebar Colors Override',
                'bundle': 'web._assets_primary_variables',
                'directive': 'replace',
                'path': url,
                'target': original_path,
            })
            
        # Clear cache to force recompilation
        self.env.registry.clear_cache()

    def get_values(self):
        res = super().get_values()
        IrParam = self.env['ir.config_parameter'].sudo()
        res.update(
            theme_color_sidebar_text=IrParam.get_param('imeco_web_sidebar.color_sidebar_text', '#DEE2E6'),
            theme_color_sidebar_active=IrParam.get_param('imeco_web_sidebar.color_sidebar_active', '#5D8DA8'),
            theme_color_sidebar_background=IrParam.get_param('imeco_web_sidebar.color_sidebar_background', '#111827'),
        )
        return res

    def set_values(self):
        super().set_values()
        IrParam = self.env['ir.config_parameter'].sudo()
        IrParam.set_param('imeco_web_sidebar.color_sidebar_text', self.theme_color_sidebar_text)
        IrParam.set_param('imeco_web_sidebar.color_sidebar_active', self.theme_color_sidebar_active)
        IrParam.set_param('imeco_web_sidebar.color_sidebar_background', self.theme_color_sidebar_background)
        self._save_scss_attachment()
