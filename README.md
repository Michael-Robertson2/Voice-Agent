Setup: 

In order to run this bot, you'll need the following:

Python installed in your environment along with the following libraries and frameworks:
    - FastAPI (https://fastapi.tiangolo.com/)
    - aiofiles (https://pypi.org/project/aiofiles/)
    - Pipecat (https://github.com/pipecat-ai/pipecat)
    - Twilio (https://github.com/twilio/twilio-python)

The following tools:
    - ngrok (https://ngrok.com/)
    - Uvicorn (https://uvicorn.dev/)

API Keys from the following services:
    - OpenAI (https://openai.com/api/)
    - Deepgram (https://deepgram.com/)
    - Cartesia (https://www.cartesia.ai/)

An API Key and usable phone number from Twilio (https://www.twilio.com/en-us)

Once you have all these, make sure you've set each API Key as an environment variable on your machine.

Open a terminal on your machine, and run the command 'ngrok http 5050'. You'll receive a forwarding URL. Remove the 'https://' portion and copy the rest. Keep this terminal open.

Pull this repository, and make the following modifications to the server.py file:
    - On line 17, fill in the source phone number you purchased from Twilio in 0123456789 format.
    - On line 18, fill in the target number again 0123456789 format.
    - On line 19, fill in the forwarding url you got from ngrok.

Open a second terminal, navigate to the /src folder for this project, and run the following command: "uvicorn server:app --reload --port 5050". This will start up a FastAPI server.

Run:

Once you've done all the above, open a third terminal window also in the /src folder and simply execute "python run.py"

The run script triggers an API call that starts the phone conversation between the two agents.