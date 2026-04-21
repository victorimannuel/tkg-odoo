from odoo.tests.common import TransactionCase


class TestFathomSync(TransactionCase):
    def test_mapping_upsert_created_and_skipped(self):
        service = self.env['fathom.sync']
        payload = {'id': 'abc', 'name': 'Demo'}

        result_1 = service._upsert_mapping('fathom.master_data', 'abc', 0, payload)
        result_2 = service._upsert_mapping('fathom.master_data', 'abc', 0, payload)

        self.assertEqual(result_1, 'created')
        self.assertEqual(result_2, 'skipped')

    def test_log_start(self):
        service = self.env['fathom.sync']
        log = service._log_start('manual', request_path='/x')
        self.assertTrue(log)
        self.assertEqual(log.status, 'running')
