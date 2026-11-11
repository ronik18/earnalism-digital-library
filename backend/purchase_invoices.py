"""Immutable commercial invoices for newly credited Reading Pass purchases."""
from datetime import timedelta, timezone
from hashlib import sha256
from html import escape
from uuid import UUID

from email_validator import EmailNotValidError, validate_email

SELLER = 'REO ENTERPRISE'
SUPPORT = 'sales@reoenterprise.org'
ADDRESS = 'Nihar Bhawan, 73 Nandan Nagar, Kolkata 700083, North 24 Parganas, West Bengal, India'
TAX_NOTE = 'GST is not charged. The supplier is not registered for GST.'
IST = timezone(timedelta(hours=5, minutes=30))


def email_address(value):
    if not isinstance(value, str) or any(c in value for c in '\r\n'):
        raise ValueError('Invalid invoice recipient')
    try:
        return validate_email(value, check_deliverability=False).normalized
    except EmailNotValidError:
        raise ValueError('Invalid invoice recipient') from None


def invoice_record(intent, *, payment_id, transaction_id, now):
    """Called in the existing credit transaction; never sends mail.

    Invalid legacy billing data is held for review, without withholding the
    purchased time. Existing credited intents never enter this creation path.
    """
    identity = sha256(('earnalism-invoice:' + str(intent['id'])).encode()).hexdigest()
    row = dict(_id=identity, schema='earnalism.purchase-invoice.v1',
        user_id=intent['user_id'], intent_id=intent['id'],
        transaction_id=transaction_id, payment_id=payment_id,
        created_at=now, delivery_status='review_required', attempts=0,
        next_attempt_at=now, seller=SELLER, seller_address=ADDRESS,
        tax_note=TAX_NOTE)
    try:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('An exact invoice timestamp is required')
        number = 'EARN/' + str(now.astimezone(IST).year) + '/' + str(UUID(intent['id']))
        amount, minutes = intent['amount_paise'], intent['minutes']
        if (type(amount) is not int or amount <= 0 or type(minutes) is not int
                or minutes <= 0 or intent.get('currency') != 'INR'
                or not isinstance(payment_id, str) or not payment_id
                or len(payment_id) > 128 or any(c in payment_id for c in '\r\n')):
            raise ValueError('Invalid invoice purchase')
        recipient = email_address(intent.get('user_email'))
        if intent.get('mode') not in ('test', 'live'):
            raise ValueError('Unknown payment mode')
        row.update(invoice_number=number, recipient=recipient,
            amount_paise=amount, currency='INR', minutes=minutes,
            invoice_date=now.astimezone(IST).strftime('%d %B %Y'),
            delivery_status='pending' if intent['mode'] == 'live' else 'suppressed_test',
            payment_mode=intent['mode'])
        row['html'] = render_invoice(row)
    except (ValueError, TypeError, KeyError, AttributeError):
        row['billing_issue'] = 'INVOICE_DETAILS_REQUIRE_REVIEW'
    return row


def render_invoice(row):
    """Self-contained, printable HTML: no scripts, external images or tracking."""
    def e(key):
        return escape(str(row[key]), quote=True)
    total = f"INR {row['amount_paise'] // 100:,}.{row['amount_paise'] % 100:02d}"
    sample_notice = ('<p style="padding:12px;background:#fff3cd"><strong>TEST EXAMPLE — no real purchase.</strong></p>'
                     if row.get('payment_mode') == 'test' else '')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Earnalism invoice</title></head><body style="margin:0;background:#f5f6f8;color:#182536;font:16px Arial,sans-serif">
<main style="max-width:680px;margin:24px auto;padding:32px;background:white;border-top:6px solid #b58b35">
<h1 style="margin:0;color:#142c45">Earnalism</h1><p>Purchase invoice &amp; payment receipt</p>
{sample_notice}
<p><strong>PAID</strong></p><p>Invoice: {e('invoice_number')}<br>Date: {e('invoice_date')}</p>
<h2 style="font-size:18px">{e('seller')}</h2><p>{e('seller_address')}<br>{SUPPORT}</p>
<p><strong>Billed to:</strong> {e('recipient')}</p>
<table style="width:100%;border-collapse:collapse"><tr><th align="left">Description</th><th align="right">Paid</th></tr>
<tr><td style="padding:16px 0;border-top:1px solid #ddd">Reading Pass — {e('minutes')} minutes</td><td align="right" style="border-top:1px solid #ddd">{total}</td></tr>
<tr><th align="left" style="padding-top:16px;border-top:1px solid #ddd">Total paid</th><th align="right" style="border-top:1px solid #ddd">{total}</th></tr></table>
<p>{e('tax_note')}</p><p>Payment reference: {e('payment_id')}</p>
<p>Your purchased time has been credited to your Earnalism account. Keep this invoice for your records.</p>
<p>Questions? Contact {SUPPORT}.</p></main></body></html>'''
