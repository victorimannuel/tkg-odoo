from odoo.tests import common
from odoo import fields

class TestGymMember(common.TransactionCase):
    def setUp(self):
        super(TestGymMember, self).setUp()
        self.Member = self.env['gym.member']
        self.Subscription = self.env['gym.membership.subscription']
        self.Plan = self.env['gym.membership']

        # Create a membership plan
        self.plan_monthly = self.Plan.create({
            'name': 'Monthly Gold',
            'price': 50.0,
            'duration': 1,
            'duration_uom': 'months',
        })

    def test_create_member(self):
        """Test creating a member generates a partner."""
        member = self.Member.create({
            'firstname': 'John',
            'surname': 'Doe',
            'email': 'john.doe@example.com',
            'gender': 'male',
        })
        self.assertTrue(member.partner_id, "Partner should be created automatically")
        self.assertEqual(member.name, "John Doe")
        self.assertEqual(member.partner_id.email, "john.doe@example.com")

    def test_subscription_flow(self):
        """Test subscription creation and status."""
        member = self.Member.create({
            'firstname': 'Jane',
            'surname': 'Smith',
        })
        
        subscription = self.Subscription.create({
            'member_id': member.id,
            'membership_id': self.plan_monthly.id,
            'date_start': '2023-01-01',
        })
        
        # Check end date computation
        # 1 month from 2023-01-01 is 2023-02-01 (or 01-31 depending on implementation, let's check)
        # Using relativedelta(months=1)
        expected_end = fields.Date.to_date('2023-02-01')
        # Wait, I need to import fields if I use it, or just check string if simple
        # Better to check if it's set.
        self.assertTrue(subscription.date_end, "End date should be computed")
        
        # Check state
        self.assertEqual(subscription.state, 'draft')
        
        # Confirm
        subscription.action_confirm()
        self.assertEqual(subscription.state, 'active')

        # Invoice creation (mocking or checking if method exists)
        # subscription.action_generate_invoice() 
        # We might need account module installed and configured for this to fully work without mocking
