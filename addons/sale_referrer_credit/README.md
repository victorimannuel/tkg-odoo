# Referrer Credit System for Odoo 19

This module allows businesses to manage a referrer program where partners earn credits from sales they refer.

## Key Features

1.  **Referrer Selection on Sales Orders**:
    *   Easily select a "Referrer Partner" on the Sales Order form.
    *   Validation prevents selecting the customer as their own referrer.

2.  **Automated Credit Calculation**:
    *   Credits are calculated as a percentage of the untaxed invoice amount.
    *   **Crucial**: Credits are ONLY granted when the customer invoice is fully **PAID**.
    *   Commission percentage is globally configurable in Settings.

3.  **Ledger-Based Tracking**:
    *   All credits are stored in an immutable ledger (`referrer.credit.ledger`).
    *   Full audit trail: Source Invoice, Sales Order, Date, Amount.
    *   Supports "Earned" (Positive) and "Redeemed" (Negative) entries.
    *   Handles Refunds: Automatically creates adjustment entries if a paid invoice is refunded.

4.  **Partner Integration**:
    *   View current "Referrer Credit Balance" directly on the Partner form.
    *   Smart button to drill down into the credit history ledger.

## Configuration

1.  Go to **Sales > Configuration > Settings**.
2.  Scroll to the **Referrer Program** section.
3.  Set the **Referrer Commission %** (default is 5.0%).

## Usage Workflow

1.  **Create Sale**: Create a Sales Order and set the `Referrer` field.
2.  **Invoice & Pay**: Confirm the order, create the invoice, and register payment.
3.  **Credit Grant**: Once the invoice is Paid, a credit entry is automatically created for the referrer.
4.  **View Balance**: Go to the Referrer's partner form to see their accumulated balance.

## Technical Details

*   **Models**:
    *   `referrer.credit.ledger`: Stores credit history.
    *   `sale.order`: Extended to link Referrer.
    *   `account.move`: Hooks into payment status to trigger credit grant.
    *   `res.partner`: Computed balance field.
*   **Security**:
    *   `account.group_account_manager`: Can manage ledger entries (though they are mostly automated).
    *   `base.group_user`: Can view ledgers.

## Future Enhancements (Extension Points)

*   **Redemption Logic**: Currently, the system tracks accumulation. Logic to "spend" credits on new orders can be added by creating negative ledger entries when a referrer pays using credits.
*   **Tiered Commissions**: Override `_get_referrer_commission_percentage` in `account.move` to implement complex rules (e.g., product-specific rates).
