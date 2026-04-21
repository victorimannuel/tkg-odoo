import base64
from io import BytesIO

import xlsxwriter

from odoo import fields, models


class GymPaymentDetailsReportWizard(models.TransientModel):
    _name = 'gym.payment.details.report.wizard'
    _description = 'Gym Payment Details Report Wizard'

    report_date = fields.Date(
        string='Report Date',
        required=True,
        default=fields.Date.context_today,
    )
    file_data = fields.Binary(string='File', readonly=True)
    file_name = fields.Char(string='Filename', readonly=True)

    def _get_sales_details(self, order):
        details = []
        for line in order.lines:
            product_name = line.product_id.display_name or line.product_id.name or '-'
            details.append(f"{product_name} x {line.qty:g}")
        return ", ".join(details)

    def action_export_xlsx(self):
        self.ensure_one()

        payments = self.env['pos.payment'].sudo().search(
            [
                ('payment_date', '=', self.report_date),
            ],
            order='payment_date, id',
        )

        partner_ids = payments.mapped('pos_order_id.partner_id').ids
        members = self.env['gym.member'].sudo().search([('partner_id', 'in', partner_ids)])
        member_by_partner = {member.partner_id.id: member for member in members}

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Payment Details')

        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        amount_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

        headers = [
            'Payment Date',
            'Member',
            'Sales Details',
            'Payment Method',
            'Payment Amount',
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        sheet.set_column(0, 0, 16)
        sheet.set_column(1, 1, 26)
        sheet.set_column(2, 2, 60)
        sheet.set_column(3, 3, 24)
        sheet.set_column(4, 4, 18)

        row = 1
        for payment in payments:
            order = payment.pos_order_id
            partner = order.partner_id
            member = member_by_partner.get(partner.id) if partner else False
            member_name = member.name if member else ''
            sales_details = self._get_sales_details(order) if order else ''
            payment_method = payment.payment_method_id.name or ''

            payment_date = payment.payment_date
            if payment_date:
                payment_date = fields.Date.to_string(payment_date)
            else:
                payment_date = ''

            sheet.write(row, 0, payment_date, text_format)
            sheet.write(row, 1, member_name, text_format)
            sheet.write(row, 2, sales_details, text_format)
            sheet.write(row, 3, payment_method, text_format)
            sheet.write_number(row, 4, payment.amount or 0.0, amount_format)
            row += 1

        workbook.close()
        xlsx_data = output.getvalue()
        output.close()

        filename = 'gym_payment_details_%s.xlsx' % self.report_date.strftime('%Y%m%d')
        self.write(
            {
                'file_data': base64.b64encode(xlsx_data),
                'file_name': filename,
            }
        )

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=%s&id=%s&field=file_data&filename_field=file_name&download=true'
            % (self._name, self.id),
            'target': 'self',
        }
