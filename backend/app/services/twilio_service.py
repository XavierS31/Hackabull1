"""
Thin wrapper around the Twilio REST API.
All functions are synchronous — run them via asyncio.run_in_executor when
calling from an async FastAPI handler.
"""
def initiate_call(
    account_sid: str,
    auth_token: str,
    from_number: str,
    to_number: str,
    webhook_url: str,
    status_callback_url: str,
) -> str:
    """Dial `to_number` and return the new CallSid."""
    from twilio.rest import Client  # lazy — only needed when a call is placed

    client = Client(account_sid, auth_token)
    call = client.calls.create(
        to=to_number,
        from_=from_number,
        url=webhook_url,
        status_callback=status_callback_url,
        status_callback_method="POST",
    )
    return call.sid
