"""add phase 14 enterprise saas billing and monetization models

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-10-17 18:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.db.guid import GUID


# revision identifiers, used by Alembic.
revision: str = '9c0d1e2f3a4b'
down_revision: Union[str, None] = '8b9c0d1e2f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_platform_admin column to users table
    op.add_column(
        'users',
        sa.Column('is_platform_admin', sa.Boolean(), server_default=sa.text('false'), nullable=False)
    )

    # 2. subscription_plans
    op.create_table(
        'subscription_plans',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('tier', sa.String(length=50), nullable=False),
        sa.Column('billing_interval', sa.String(length=20), nullable=False),
        sa.Column('price_inr', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('price_usd', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('max_active_jobs', sa.Integer(), server_default='2', nullable=False),
        sa.Column('max_recruiters', sa.Integer(), server_default='1', nullable=False),
        sa.Column('max_candidates_monthly', sa.Integer(), server_default='50', nullable=False),
        sa.Column('max_resume_storage_mb', sa.Integer(), server_default='250', nullable=False),
        sa.Column('max_ai_tokens_monthly', sa.Integer(), server_default='50000', nullable=False),
        sa.Column('max_interviews_monthly', sa.Integer(), server_default='10', nullable=False),
        sa.Column('max_workflow_runs_monthly', sa.Integer(), server_default='0', nullable=False),
        sa.Column('features_json', sa.Text(), server_default='{}', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_subscription_plans_slug'), 'subscription_plans', ['slug'], unique=True)
    op.create_index(op.f('ix_subscription_plans_tier'), 'subscription_plans', ['tier'], unique=False)

    # 3. agency_subscriptions
    op.create_table(
        'agency_subscriptions',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('plan_id', GUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('billing_interval', sa.String(length=20), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('payment_gateway', sa.String(length=50), nullable=False),
        sa.Column('gateway_customer_id', sa.String(length=255), nullable=True),
        sa.Column('gateway_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id')
    )
    op.create_index(op.f('ix_agency_subscriptions_agency_id'), 'agency_subscriptions', ['agency_id'], unique=True)
    op.create_index(op.f('ix_agency_subscriptions_plan_id'), 'agency_subscriptions', ['plan_id'], unique=False)
    op.create_index(op.f('ix_agency_subscriptions_status'), 'agency_subscriptions', ['status'], unique=False)
    op.create_index('ix_agency_subscriptions_status_period', 'agency_subscriptions', ['status', 'current_period_end'], unique=False)

    # 4. subscription_histories
    op.create_table(
        'subscription_histories',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('from_plan_id', GUID(), nullable=True),
        sa.Column('to_plan_id', GUID(), nullable=False),
        sa.Column('status_before', sa.String(length=50), nullable=True),
        sa.Column('status_after', sa.String(length=50), nullable=False),
        sa.Column('change_reason', sa.String(length=255), nullable=True),
        sa.Column('changed_by_user_id', GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['from_plan_id'], ['subscription_plans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['to_plan_id'], ['subscription_plans.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscription_histories_agency_id'), 'subscription_histories', ['agency_id'], unique=False)

    # 5. feature_entitlements
    op.create_table(
        'feature_entitlements',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('feature_key', sa.String(length=100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('max_limit', sa.Integer(), server_default='-1', nullable=False),
        sa.Column('current_usage', sa.Integer(), server_default='0', nullable=False),
        sa.Column('reset_frequency', sa.String(length=50), server_default='MONTHLY', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', 'feature_key', name='uq_agency_feature_entitlement')
    )
    op.create_index(op.f('ix_feature_entitlements_agency_id'), 'feature_entitlements', ['agency_id'], unique=False)
    op.create_index(op.f('ix_feature_entitlements_feature_key'), 'feature_entitlements', ['feature_key'], unique=False)

    # 6. entitlement_overrides
    op.create_table(
        'entitlement_overrides',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('override_limit', sa.Integer(), nullable=False),
        sa.Column('is_unlimited', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('granted_by_user_id', GUID(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', 'resource_type', name='uq_agency_resource_override')
    )
    op.create_index(op.f('ix_entitlement_overrides_agency_id'), 'entitlement_overrides', ['agency_id'], unique=False)
    op.create_index(op.f('ix_entitlement_overrides_resource_type'), 'entitlement_overrides', ['resource_type'], unique=False)

    # 7. usage_meters
    op.create_table(
        'usage_meters',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_usage', sa.Integer(), server_default='0', nullable=False),
        sa.Column('soft_limit', sa.Integer(), server_default='0', nullable=False),
        sa.Column('hard_limit', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_unlimited', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', 'resource_type', 'period_start', name='uq_agency_resource_meter_period')
    )
    op.create_index(op.f('ix_usage_meters_agency_id'), 'usage_meters', ['agency_id'], unique=False)
    op.create_index(op.f('ix_usage_meters_resource_type'), 'usage_meters', ['resource_type'], unique=False)
    op.create_index('ix_usage_meters_agency_resource', 'usage_meters', ['agency_id', 'resource_type'], unique=False)

    # 8. usage_records
    op.create_table(
        'usage_records',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('operation_reference', sa.String(length=255), nullable=True),
        sa.Column('user_id', GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_records_agency_id'), 'usage_records', ['agency_id'], unique=False)
    op.create_index(op.f('ix_usage_records_idempotency_key'), 'usage_records', ['idempotency_key'], unique=False)
    op.create_index(op.f('ix_usage_records_resource_type'), 'usage_records', ['resource_type'], unique=False)
    op.create_index('ix_usage_records_agency_created', 'usage_records', ['agency_id', 'created_at'], unique=False)

    # 9. usage_reservations
    op.create_table(
        'usage_reservations',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('reserved_quantity', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('is_committed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_released', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index(op.f('ix_usage_reservations_agency_id'), 'usage_reservations', ['agency_id'], unique=False)

    # 10. payment_transactions
    op.create_table(
        'payment_transactions',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('gateway', sa.String(length=50), nullable=False),
        sa.Column('gateway_transaction_id', sa.String(length=255), nullable=True),
        sa.Column('gateway_order_id', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('receipt_url', sa.String(length=500), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key'),
        sa.UniqueConstraint('gateway_transaction_id')
    )
    op.create_index(op.f('ix_payment_transactions_agency_id'), 'payment_transactions', ['agency_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_gateway'), 'payment_transactions', ['gateway'], unique=False)
    op.create_index(op.f('ix_payment_transactions_status'), 'payment_transactions', ['status'], unique=False)

    # 11. payment_webhook_events
    op.create_table(
        'payment_webhook_events',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('gateway', sa.String(length=50), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('signature_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index(op.f('ix_payment_webhook_events_event_id'), 'payment_webhook_events', ['event_id'], unique=True)
    op.create_index(op.f('ix_payment_webhook_events_gateway'), 'payment_webhook_events', ['gateway'], unique=False)

    # 12. billing_invoices
    op.create_table(
        'billing_invoices',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_rate_pct', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('customer_name', sa.String(length=255), nullable=False),
        sa.Column('customer_email', sa.String(length=255), nullable=False),
        sa.Column('customer_address', sa.Text(), nullable=True),
        sa.Column('customer_gstin', sa.String(length=20), nullable=True),
        sa.Column('is_domestic_india', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('download_token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number'),
        sa.UniqueConstraint('download_token')
    )
    op.create_index(op.f('ix_billing_invoices_agency_id'), 'billing_invoices', ['agency_id'], unique=False)
    op.create_index(op.f('ix_billing_invoices_customer_gstin'), 'billing_invoices', ['customer_gstin'], unique=False)
    op.create_index(op.f('ix_billing_invoices_invoice_number'), 'billing_invoices', ['invoice_number'], unique=True)
    op.create_index(op.f('ix_billing_invoices_status'), 'billing_invoices', ['status'], unique=False)
    op.create_index('ix_billing_invoices_agency_created', 'billing_invoices', ['agency_id', 'created_at'], unique=False)

    # 13. invoice_line_items
    op.create_table(
        'invoice_line_items',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('invoice_id', GUID(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_line_items_invoice_id'), 'invoice_line_items', ['invoice_id'], unique=False)

    # 14. credit_notes
    op.create_table(
        'credit_notes',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('invoice_id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('credit_number', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('issued_by_user_id', GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['issued_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('credit_number')
    )
    op.create_index(op.f('ix_credit_notes_agency_id'), 'credit_notes', ['agency_id'], unique=False)
    op.create_index(op.f('ix_credit_notes_credit_number'), 'credit_notes', ['credit_number'], unique=True)

    # 15. refund_records
    op.create_table(
        'refund_records',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('payment_transaction_id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('gateway_refund_id', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_transaction_id'], ['payment_transactions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gateway_refund_id')
    )
    op.create_index(op.f('ix_refund_records_agency_id'), 'refund_records', ['agency_id'], unique=False)

    # 16. agency_billing_profiles
    op.create_table(
        'agency_billing_profiles',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('billing_email', sa.String(length=255), nullable=False),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state_province', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=10), server_default='IN', nullable=False),
        sa.Column('gstin', sa.String(length=20), nullable=True),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id')
    )
    op.create_index(op.f('ix_agency_billing_profiles_agency_id'), 'agency_billing_profiles', ['agency_id'], unique=True)
    op.create_index(op.f('ix_agency_billing_profiles_gstin'), 'agency_billing_profiles', ['gstin'], unique=False)

    # 17. billing_audit_logs
    op.create_table(
        'billing_audit_logs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('agency_id', GUID(), nullable=False),
        sa.Column('actor_user_id', GUID(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_audit_logs_agency_id'), 'billing_audit_logs', ['agency_id'], unique=False)
    op.create_index('ix_billing_audit_agency_created', 'billing_audit_logs', ['agency_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('billing_audit_logs')
    op.drop_table('agency_billing_profiles')
    op.drop_table('refund_records')
    op.drop_table('credit_notes')
    op.drop_table('invoice_line_items')
    op.drop_table('billing_invoices')
    op.drop_table('payment_webhook_events')
    op.drop_table('payment_transactions')
    op.drop_table('usage_reservations')
    op.drop_table('usage_records')
    op.drop_table('usage_meters')
    op.drop_table('entitlement_overrides')
    op.drop_table('feature_entitlements')
    op.drop_table('subscription_histories')
    op.drop_table('agency_subscriptions')
    op.drop_table('subscription_plans')
    op.drop_column('users', 'is_platform_admin')
