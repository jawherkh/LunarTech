import logging
import os
import uuid
import asyncio
import dotenv
import json
from datetime import datetime
from livekit import agents, rtc
from livekit import api as livekit_api
from livekit.agents import Agent, AgentSession, function_tool
from livekit.api.room_service import CreateRoomRequest
from livekit.plugins import google
from tavily import TavilyClient
from InterviewerAgent import InterviewAgent as Interviewer
from livekit.agents import cli, WorkerOptions,RoomOutputOptions
from livekit.plugins import google
from livekit.agents import ConversationItemAddedEvent
from livekit.agents.llm import ImageContent, AudioContent 
from livekit.agents import UserInputTranscribedEvent
from google import genai

dotenv.load_dotenv()
logging.basicConfig(level=logging.DEBUG)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

LIVEKIT_WS_URL = os.getenv("LIVEKIT_WS_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")



async def entrypoint(ctx: agents.JobContext):
    print("\\n🎤 Welcome to your AI Interviewer for Data Science positions!\\n")
    
    jd = """
Data Scientist Position

We are seeking a skilled Data Scientist to join our team. The ideal candidate will have experience in:

- Statistical analysis and machine learning techniques
- Programming in Python and/or R
- Data visualization and storytelling
- Working with large datasets and databases (SQL)
- Experience with ML frameworks like scikit-learn, TensorFlow, or PyTorch
- Strong analytical and problem-solving skills
- Ability to communicate complex findings to non-technical stakeholders

Requirements:
- Bachelor's/Master's degree in Data Science, Statistics, Computer Science, or related field
- 2+ years of experience in data science or analytics
- Experience with cloud platforms (AWS, GCP, Azure) preferred
- Strong business acumen and understanding of how data drives business decisions

Additional Details & FAQ:
- The position is full-time, but flexible and remote options are available.
- The salary range is $95,000–$130,000 per year, depending on experience and location.
- Candidates do not need a formal technical background, but familiarity with programming and statistics is required.
- Part-time arrangements may be considered for exceptional candidates.
- The company provides ongoing training and support for professional development.
- Benefits include health insurance, paid time off, and a 401(k) plan.
"""
    
    room_name = os.getenv("LIVEKIT_ROOM_NAME") or f"interview-room-{uuid.uuid4().hex}"
    
    lkapi = livekit_api.LiveKitAPI(
        url=LIVEKIT_WS_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )
    
    try:
        req = CreateRoomRequest(
            name=room_name,
            empty_timeout=600,# keep the room alive 10m after empty
            max_participants=2,# interviewer + candidate
        )
        room = await lkapi.room.create_room(req)
        print(f"\\nRoom created! Join this link in your browser to start the interview: {os.getenv('LIVEKIT_URL')}/join/{room.name}\\n")
        
        # Create the interviewer agent
        interviewer_agent = Interviewer(jd=jd)
        
        # Create session
        session = AgentSession(
            llm=google.beta.realtime.RealtimeModel(
                model="gemini-2.5-flash-preview-native-audio-dialog", 
                voice="Puck",
                api_key=GOOGLE_API_KEY, 
                temperature=0.7, 
                instructions=f"You are a professional interviewer conducting an Interview with the job description: {jd}. Ask relevant interview questions ONE AT A TIME, listen carefully to complete answers, and wait for the candidate to finish speaking before asking the next question. Be patient and give candidates time to think and respond fully."
            ),
            stt=google.STT(
                model="latest_long",
                spoken_punctuation=False,
            )
        )
        await ctx.connect()
        
        # Add shutdown callback to save transcript when interview ends

        # Initialize conversation transcript storage on the session
        session._conversation_transcript = []

        

        await session.start(room=ctx.room, agent=interviewer_agent, room_output_options=RoomOutputOptions(sync_transcription=False))

        # Set up transcript capture events
        @session.on("user_input_transcribed")
        def on_user_input_transcribed(event: UserInputTranscribedEvent):
            if event.is_final:  # Only capture final transcriptions
                timestamp = datetime.now().strftime("%H:%M:%S")
                entry = {
                    'timestamp': timestamp,
                    'role': 'user',
                    'text': event.transcript,
                    'speaker_id': event.speaker_id
                }
                session._conversation_transcript.append(entry)
                print(f"👤 [{timestamp}] Candidate: {event.transcript}")
        
        @session.on("conversation_item_added")
        def on_conversation_item_added(event: ConversationItemAddedEvent):
            if event.item.role == "assistant" and event.item.text_content:
                timestamp = datetime.now().strftime("%H:%M:%S")
                entry = {
                    'timestamp': timestamp,
                    'role': 'assistant',
                    'text': event.item.text_content,
                    'speaker_id': None
                }
                session._conversation_transcript.append(entry)
                print(f"🤖 [{timestamp}] Interviewer: {event.item.text_content[:100]}{'...' if len(event.item.text_content) > 100 else ''}")
                
                if event.item.interrupted:
                    print(f"   ⚠️ Message was interrupted")

        # Give the agent a moment to initialize, then start the interview
        await asyncio.sleep(1)
        await session.generate_reply(
            instructions=f"""Greet the candidate warmly and conduct a professional interview for the Data Science position. 
            Ask these questions ONE AT A TIME, waiting for each complete response before moving to the next:
            1. What is your full name and background?
            2. Why are you interested in this Data Science position?
            3. What's your experience with data science, machine learning, or AI?
            4. What are your short-term and long-term career goals?
            5. Are you ready to start immediately? If not, when would you be available?
            
            After these questions, ask follow-up questions based on their responses and the job requirements.
            When you have sufficient information, or the user want to end the interview you MUST call the end_interview function."""
        )
        
    except Exception as e:
        print(f"Error during interview: {e}")
    finally:
        # Clean up the LiveKit API client to prevent unclosed session warnings
        try:
            await lkapi.aclose()
        except Exception as e:
            print(f"Error closing LiveKit API client: {e}")
            
if __name__ == "__main__":
    cli.run_app( WorkerOptions(entrypoint_fnc=entrypoint) )