"""Bounded business-SMTP delivery for the durable purchase invoice outbox."""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime
import logging
import re
import smtplib
import ssl

from pymongo import ReturnDocument

try:
    from .purchase_invoices import SUPPORT, email_address
except ImportError:
    from purchase_invoices import SUPPORT, email_address

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
LEASE_SECONDS = 300


@dataclass(frozen=True)
class SMTPConfig:
    username: str
    password: str = field(repr=False)
    sender: str = SUPPORT
    host: str = 'smtp.gmail.com'
    port: int = 587


def configuration(env):
    enabled = env.get('PURCHASE_INVOICE_EMAIL_ENABLED', 'false').strip().lower()
    if enabled == 'false':
        return None
    if enabled != 'true':
        raise ValueError('PURCHASE_INVOICE_EMAIL_ENABLED must be true or false')
    username = email_address(env.get('PURCHASE_INVOICE_SMTP_USER', SUPPORT))
    password = env.get('PURCHASE_INVOICE_SMTP_PASSWORD', '').replace(' ', '')
    if username != SUPPORT or not re.fullmatch('[A-Za-z0-9]{16}', password):
        raise ValueError('The business mailbox and its Google app password are required')
    return SMTPConfig(username=username, password=password)


def message_for(row, config):
    recipient = email_address(row['recipient'])
    msg = EmailMessage()
    msg['From'] = f'Earnalism <{config.sender}>'
    msg['To'] = recipient
    msg['Reply-To'] = SUPPORT
    msg['Subject'] = f"Your Earnalism invoice — {row['invoice_number']}"
    msg['Message-ID'] = f"<invoice-{row['_id']}@reoenterprise.org>"
    msg['Date'] = format_datetime(row['created_at'])
    msg['Auto-Submitted'] = 'auto-generated'
    total = f"INR {row['amount_paise'] // 100}.{row['amount_paise'] % 100:02d}"
    msg.set_content(f"Your Reading Pass purchase was successful.\n\n"
        f"Invoice: {row['invoice_number']}\nReading Pass: {row['minutes']} minutes\n"
        f"Paid: {total}\nPayment reference: {row['payment_id']}\n\n"
        f"{row['tax_note']}\n\nThe complete printable invoice is attached.\n"
        f"Questions? {SUPPORT}\n")
    msg.add_alternative(row['html'], subtype='html')
    msg.add_attachment(row['html'].encode('utf-8'), maintype='text', subtype='html',
        filename=f"Earnalism-Invoice-{row['_id']}.html")
    return msg


def _failure_stage(exc):
    value = getattr(exc, '_invoice_smtp_stage', None)
    return value if type(value) is str and value in {'CONNECT', 'EHLO', 'STARTTLS', 'TLS_EHLO', 'AUTH'} else 'SUBMIT'


def _failure_code(exc):
    value = getattr(exc, 'smtp_code', None)
    return value if type(value) is int and 100 <= value <= 599 else None


def _connection(config):
    smtp = None
    stage = 'CONNECT'
    try:
        smtp = smtplib.SMTP(config.host, config.port, timeout=5)
        stage = 'EHLO'
        smtp.ehlo()
        stage = 'STARTTLS'
        smtp.starttls(context=ssl.create_default_context())
        stage = 'TLS_EHLO'
        smtp.ehlo()
        stage = 'AUTH'
        # One SASL mechanism over verified TLS. SMTP.login() can retry a
        # rejected password using another mechanism and obscure the first error.
        smtp.auth('PLAIN', lambda challenge=None: '\0' + config.username + '\0' + config.password,
                  initial_response_ok=True)
    except BaseException as exc:
        if isinstance(exc, Exception):
            exc._invoice_smtp_stage = stage
        if smtp is not None:
            smtp.close()
        raise
    return smtp


def _close(smtp):
    try:
        smtp.quit()
    except Exception:
        smtp.close()


def verify_smtp(config):
    """TLS/login only. No message, invoice, database or payment operation."""
    smtp = _connection(config)
    _close(smtp)


def send_invoice(row, config):
    """One SMTP submission. Credentials and recipient never enter logs."""
    msg = message_for(row, config)
    smtp = _connection(config)
    try:
        refused = smtp.send_message(msg)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
    finally:
        # A QUIT failure after DATA acceptance does not change that acceptance.
        _close(smtp)


async def deliver_one(db, config, *, send=send_invoice, now=None):
    now = now or datetime.now(timezone.utc)
    collection = db['purchase_invoices']
    row = await collection.find_one_and_update(
        {'$or': [
            {'delivery_status': 'pending', 'next_attempt_at': {'$lte': now}},
            {'delivery_status': 'sending', 'lease_expires_at': {'$lte': now}},
        ], 'attempts': {'$lt': MAX_ATTEMPTS}, 'payment_mode': 'live'},
        {'$set': {'delivery_status': 'sending', 'lease_expires_at': now+timedelta(seconds=LEASE_SECONDS)},
         '$inc': {'attempts': 1}}, sort=[('created_at', 1)], return_document=ReturnDocument.AFTER)
    if not row:
        return False
    claim = {'_id': row['_id'], 'delivery_status': 'sending', 'attempts': row['attempts']}
    try:
        await asyncio.to_thread(send, row, config)
    except asyncio.CancelledError:
        # Keep the lease after shutdown/crash. A later worker may retry the
        # SAME immutable invoice and Message-ID, never credit the wallet again.
        raise
    except Exception as exc:
        await collection.update_one(claim, {'$set': {
            'delivery_status': 'pending' if row['attempts'] < MAX_ATTEMPTS else 'failed',
            'next_attempt_at': now+timedelta(seconds=60*row['attempts']),
            'last_error_code': type(exc).__name__[:80]}})
        logger.warning('Purchase invoice delivery attempt failed: %s', type(exc).__name__)
    else:
        await collection.update_one(claim, {'$set': {
            'delivery_status': 'sent', 'sent_at': datetime.now(timezone.utc)}})
    return True


async def prepare_outbox(db):
    collection = db['purchase_invoices']
    await collection.create_index([('delivery_status', 1), ('next_attempt_at', 1), ('created_at', 1)],
                                  name='invoice_pending_delivery')
    await collection.create_index([('delivery_status', 1), ('lease_expires_at', 1), ('created_at', 1)],
                                  name='invoice_delivery_recovery')


async def delivery_loop(db, config):
    """One dispatcher per app process; Mongo claims serialize replicas."""
    try:
        await asyncio.to_thread(verify_smtp, config)
        logger.info('Purchase invoice SMTP authentication verified')
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning('Purchase invoice SMTP authentication unavailable: %s stage=%s code=%s; delivery held',
                       type(exc).__name__, _failure_stage(exc), _failure_code(exc))
        return  # No queue claim or delivery-attempt consumption without SMTP readiness.
    while True:
        worked = False
        try:
            worked = await deliver_one(db, config)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning('Purchase invoice queue unavailable: %s', type(exc).__name__)
        await asyncio.sleep(1 if worked else 15)
