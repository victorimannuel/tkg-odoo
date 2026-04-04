from odoo.tests import common
from odoo import fields
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class TestGymFlows(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Member = cls.env['gym.member']
        cls.Subscription = cls.env['gym.membership.subscription']
        cls.Plan = cls.env['gym.membership']
        cls.Program = cls.env['gym.class']
        cls.Session = cls.env['gym.class.session']
        cls.Trainer = cls.env['gym.trainer']
        cls.Room = cls.env['gym.room']

        # 1. Setup Data
        cls.plan_monthly = cls.Plan.create({
            'name': 'Monthly Plan',
            'price': 100,
            'duration': 1,
            'duration_uom': 'months',
        })

        cls.trainer = cls.Trainer.create({
            'name': 'Coach Carter',
            'specialization': 'Strength'
        })

        cls.room = cls.Room.create({
            'name': 'Studio A',
            'capacity': 10
        })

        cls.program = cls.Program.create({
            'name': 'Yoga Class',
            'capacity': 2
        })

        cls.member = cls.Member.create({
            'firstname': 'Test',
            'surname': 'Member',
            'email': 'test@example.com'
        })

    def test_01_subscription_lifecycle(self):
        """Test subscription from draft to active to expired."""
        # Create a product for the plan
        product = self.env['product.product'].create({
            'name': 'Gym Service',
            'type': 'service',
            'list_price': 100
        })
        self.plan_monthly.product_id = product.id

        sub = self.Subscription.create({
            'member_id': self.member.id,
            'membership_id': self.plan_monthly.id,
            'date_start': fields.Date.today(),
        })
        self.assertEqual(sub.state, 'draft')
        self.assertEqual(self.member.membership_status, 'none')

        # Confirm
        sub.action_confirm()
        self.assertEqual(sub.state, 'running')
        self.assertEqual(self.member.membership_status, 'active')
        
        # Verify invoice was created
        self.assertTrue(sub.invoice_ids, "Invoice should be created on confirmation")
        self.assertEqual(sub.invoice_ids[0].amount_total, 100)

        # Test Expiry
        sub.date_end = fields.Date.today() - timedelta(days=1)
        self.env['gym.membership.subscription']._cron_check_expiry()
        self.assertEqual(sub.state, 'expired')
        
        # Re-verify member status
        self.member._compute_membership_status()
        self.assertEqual(self.member.membership_status, 'expired')

    def test_02_attendance_flow(self):
        """Test manual check-in and check-out with visitor log."""
        self.assertFalse(self.member.is_checked_in)

        self.member.action_checkin()
        self.assertTrue(self.member.is_checked_in)
        visits = self.env['gym.visitor'].search([('member_id', '=', self.member.id)])
        self.assertEqual(len(visits), 1)
        self.assertEqual(visits.status, 'active')

        self.member.action_checkout()
        self.assertFalse(self.member.is_checked_in)
        visits.refresh()
        self.assertEqual(visits.status, 'completed')

    def test_03_class_enrollment_and_capacity(self):
        """Test class enrollment and capacity constraints."""
        session = self.Session.create({
            'program_id': self.program.id,
            'trainer_id': self.trainer.id,
            'room_id': self.room.id,
            'start_datetime': datetime.now() + timedelta(days=1),
            'end_datetime': datetime.now() + timedelta(days=1, hours=1),
            'capacity': 2
        })

        # Enroll Member 1
        enroll1 = self.env['gym.class.enrollment'].create({
            'session_id': session.id,
            'member_id': self.member.id
        })
        self.assertEqual(enroll1.state, 'confirmed')
        self.assertEqual(session.enrollment_count, 1)

        # Enroll Member 2
        member2 = self.Member.create({'firstname': 'Member', 'surname': '2'})
        enroll2 = self.env['gym.class.enrollment'].create({
            'session_id': session.id,
            'member_id': member2.id
        })
        self.assertEqual(enroll2.state, 'confirmed')

        # Enroll Member 3 (Should be waitlisted)
        member3 = self.Member.create({'firstname': 'Member', 'surname': '3'})
        enroll3 = self.env['gym.class.enrollment'].create({
            'session_id': session.id,
            'member_id': member3.id
        })
        self.assertEqual(enroll3.state, 'waitlist', "Should be waitlisted when capacity is full")

    def test_04_room_conflict(self):
        """Test that two sessions cannot book the same room at the same time."""
        start = datetime.now() + timedelta(days=2)
        end = start + timedelta(hours=1)

        self.Session.create({
            'class_id': self.class_id.id,
            'trainer_id': self.trainer.id,
            'room_id': self.room.id,
            'start_datetime': start,
            'end_datetime': end,
        })

        with self.assertRaises(ValidationError):
            self.Session.create({
                'class_id': self.class_id.id,
                'trainer_id': self.trainer.id,
                'room_id': self.room.id,
                'start_datetime': start + timedelta(minutes=30),
                'end_datetime': end + timedelta(minutes=30),
            })
