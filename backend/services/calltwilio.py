from twilio.rest import Client

# Your Twilio credentials (found in Twilio Console)
account_sid = 'account_sid'
auth_token = 'auth_token'

client = Client(account_sid, auth_token)

# Replace with your verified phone number

call = client.calls.create(
    to='+1xxxxxxxxxx',
    from_='+1xxxxxxxxxx',
    url='http://demo.twilio.com/docs/voice.xml'
)


print(f"📞 Call is on the way! Call SID: {call.sid}")