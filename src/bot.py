import os
import wave
import datetime
import aiofiles
import io

from pipecat.runner.types import RunnerArguments
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import BaseTransport
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    AssistantTurnStoppedMessage,
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
    UserTurnStoppedMessage,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.workers.runner import WorkerRunner
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from bug_logger import bug_logger


prompt = '''You are going to call a phone number, and there will be another AI agent on the other end. That agent's job is to act as a receptionist for a medical facility. 
            Your job is to act as a patient and to test the system - finding bugs, evaluating quality, and stress-testing edge cases. Try a variety of scenarios, such as scheduling appointments, canceling
            or rescheduling appointments, refilling medications, and any other interactions you can think of. You may or not try interrupting the receptionist, as well.'''

async def bot(runner_args: RunnerArguments):
    transport_params = {
        "twilio": lambda: FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args.handle_sigint)

async def run_bot(transport: BaseTransport, handle_sigint: bool):
    # Set up the language model, speech services, and conversation context.
    llm = OpenAILLMService(
        api_key = os.getenv("OPENAI_API_KEY"),
        settings = OpenAILLMService.Settings(
            system_instruction = prompt
        )
    )

    transcript_log = []
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        settings=CartesiaTTSService.Settings(
            voice="71a7ad14-091c-4e8e-a314-022ece01c121"
        ),
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer()
        )
    )

    audiobuffer = AudioBufferProcessor(
        num_channels=1,
        enable_turn_audio=False,
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            audiobuffer,
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
            enable_usage_metrics=True,
        )
    )

    # Start recording audio as soon as the client connects.
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        print("Starting Converstation")
        await audiobuffer.start_recording()

    # Save the conversation artifacts and stop the worker when the call ends.
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        print("Call ended")
        await save_transcript(transcript_log, timestamp)
        await bug_logger(timestamp)
        await worker.cancel()
    
    @user_aggregator.event_handler("on_user_turn_stopped")
    async def on_user_turn_stopped(aggregator, strategy, message: UserTurnStoppedMessage):
        transcript_log.append(f"[{message.timestamp}] receptionist: {message.content}")
    
    @assistant_aggregator.event_handler("on_assistant_turn_stopped")
    async def on_assistant_turn_stopped(aggregator, message: AssistantTurnStoppedMessage):
        transcript_log.append(f"[{message.timestamp}] patient: {message.content}")

    # Persist incoming audio chunks to a wav file for later review.
    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        filename = f"recordings/conversation_{timestamp}.wav"
        if not os.path.exists("recordings"):
            os.makedirs("recordings")
        
        await save_audio_file(audio, filename, sample_rate, num_channels)
        

    runner = WorkerRunner(handle_sigint=handle_sigint)

    await runner.add_workers(worker)
    await runner.run()

async def save_audio_file(audio: bytes, filename: str, sample_rate: int, num_channels: int):
    if len(audio) > 0:
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wf:
                wf.setsampwidth(2)
                wf.setnchannels(num_channels)
                wf.setframerate(sample_rate)
                wf.writeframes(audio)
            async with aiofiles.open(filename, "wb") as file:
                await file.write(buffer.getvalue())

async def save_transcript(transcript_log, timestamp):
    if not os.path.exists("transcripts"):
        os.makedirs("transcripts")
    
    with open(f"transcripts/transcript_{timestamp}.txt", "w") as file:
        for entry in transcript_log:
            file.write(f"{entry}\n")

if __name__ == "__main__":
    from pipecat.runner.run import main

    main()

