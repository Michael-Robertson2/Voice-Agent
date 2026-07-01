import os

import uvicorn

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse
from pipecat.runner.types import WebSocketRunnerArguments


from bot import bot

app = FastAPI()

# These values are placeholders and should be replaced with real Twilio configuration.
to_number = "[INSERT_TARGET_NUMBER]"
from_number = "[INSERT_SOURCE_NUMBER]"
local_server_url = "[INSERT_FORWARDING_URL]"

# Create an outbound Twilio call and point it at the TwiML endpoint.
@app.post("/call")
async def call():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    client = Client(account_sid, auth_token)
    print(f"Making call from {from_number} to {to_number}...")
    call = client.calls.create(to=to_number, from_=from_number, url=f"https://{local_server_url}/twiml", method="POST", record=True)

# Return the TwiML instructions that connect the call to the WebSocket stream.
@app.post("/twiml")
async def make_twiml():
    twiml_content = VoiceResponse()
    connect = Connect()
    stream = Stream(url=f"wss://{local_server_url}/ws")

    stream.parameter(name="to_number", value=to_number)
    stream.parameter(name="from_number", value=from_number)

    connect.append(stream)
    twiml_content.append(connect)
    twiml_content.pause(length=20)

    return HTMLResponse(content = str(twiml_content), media_type ="application/xml")

# Accept the Twilio media stream and hand it off to the bot runner.
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("Waiting to accept WebSocket connection...")
    await websocket.accept()
    print("WebSocket connection accepted. Starting bot...")

    try:
        runner_args = WebSocketRunnerArguments(websocket=websocket)
        await bot(runner_args)
    except Exception as e:
        print(f"Error in WebSocket endpoint: {e}")
        await websocket.close()

if __name__ == "__main__":
    print("Starting Twilio outbound chatbot server on port 5050")
    uvicorn.run(app, host="127.0.0.1", port=5050)