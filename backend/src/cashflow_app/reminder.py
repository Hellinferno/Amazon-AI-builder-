"""Collection reminder drafts.

The draft is produced from a fixed template and the invoice record only, so
every figure in it is traceable to the dataset. It is returned for review and
editing; nothing here can send a message.
"""

from dataclasses import dataclass
from datetime import date

from cashflow.models import Invoice
from cashflow.money import format_money

from .formatting import display_date, money

TONE_FRIENDLY = "friendly"
TONE_FIRM = "firm"
TONES = (TONE_FRIENDLY, TONE_FIRM)


@dataclass(frozen=True)
class ReminderDraft:
    invoice_id: str
    customer_name: str
    amount_outstanding: int
    currency: str
    due_date: date
    days_overdue: int  # negative when not yet due
    tone: str
    subject: str
    body: str

    def as_dict(self) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "customer_name": self.customer_name,
            "amount_outstanding": format_money(self.amount_outstanding),
            "currency": self.currency,
            "due_date": self.due_date.isoformat(),
            "days_overdue": self.days_overdue,
            "tone": self.tone,
            "subject": self.subject,
            "body": self.body,
            "status": "draft_not_sent",
            "sent": False,
        }


def draft_reminder(invoice: Invoice, as_of_date: date, tone: str, business_name: str) -> ReminderDraft:
    if tone not in TONES:
        raise ValueError(f"tone must be one of: {', '.join(TONES)}")
    amount = money(format_money(invoice.remaining_amount), invoice.currency)
    days = (as_of_date - invoice.due_date).days
    due = display_date(invoice.due_date)
    subject = f"Payment reminder: invoice {invoice.invoice_id} ({amount})"

    if days > 0:
        timing = f"was due on {due} and is now {days} day{'s' if days != 1 else ''} overdue"
    elif days == 0:
        timing = f"is due today, {due}"
    else:
        timing = f"is due on {due}"

    if tone == TONE_FRIENDLY:
        opening = f"Dear {invoice.customer_name},"
        ask = (
            f"This is a friendly reminder that invoice {invoice.invoice_id} for {amount} {timing}. "
            "If payment is already on its way, please ignore this note."
        )
        closing = (
            "Could you let us know when we can expect the payment? "
            "Thank you for your business."
        )
    else:
        opening = f"Dear {invoice.customer_name},"
        ask = (
            f"Invoice {invoice.invoice_id} for {amount} {timing}. "
            "We have not received payment or a confirmation of the payment date."
        )
        closing = (
            "Please arrange payment or confirm a firm payment date within the next 3 working days. "
            "Contact us if any part of this invoice is in dispute."
        )

    body = "\n\n".join([opening, ask, closing, f"Regards,\n{business_name}"])
    return ReminderDraft(
        invoice_id=invoice.invoice_id,
        customer_name=invoice.customer_name,
        amount_outstanding=invoice.remaining_amount,
        currency=invoice.currency,
        due_date=invoice.due_date,
        days_overdue=days,
        tone=tone,
        subject=subject,
        body=body,
    )
