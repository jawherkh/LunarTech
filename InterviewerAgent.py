import logging
import os
import uuid
import dotenv
import json
import asyncio
from datetime import datetime, timezone
from livekit import agents, rtc
from livekit import api as livekit_api
from livekit.agents import Agent, AgentSession, function_tool
from livekit.api.room_service import CreateRoomRequest
from livekit.plugins import google
from tavily import TavilyClient
from google import genai

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

class InterviewAgent(Agent):
    def __init__(self, *args, **kwargs) -> None:
        name = kwargs.get("name")
        jd = kwargs.get("jd")
        if len(args) == 2:
            name, jd = args[0], args[1]
        elif len(args) == 1:
            if 'name' in kwargs and not jd:
                jd = args[0]
            elif 'jd' in kwargs and not name:
                name = args[0]
            else:
                jd = args[0]

        name = name or "Candidate"
        jd = jd or "Undefined Position"

        self.name = name
        self.jd = jd
        self.interview_start_time = None
        self.interview_transcript = []
        self.questions_asked = []
        self.is_interview_completed = False
        self.interview_summary = {}
        self.current_question_index = 0
        self.room_name = None  
        self.structured_questions = [
            
        ]

        super().__init__(
            instructions=(
                f"You are a professional interviewer conducting a Mock Interview with the job "
                f"description: {self.jd}. The candidate's name is {self.name}. "
                f"IMPORTANT: Ask questions ONE AT A TIME and WAIT for the candidate's complete response "
                f"before asking the next question. Be patient and give candidates time to think and respond fully. "
                f"Listen carefully to their entire answer and only proceed when they have finished speaking. "
                f"When you feel the interview is complete (after getting sufficient information), "
                f"call the end_interview function to conclude and summarize the session."
            )
        )

    async def on_enter(self):
        self.interview_start_time = datetime.now(timezone.utc)

    async def on_message(self, message: str, participant_identity: str):
        """Log all messages to the transcript"""
        timestamp = datetime.now(timezone.utc)
        self.interview_transcript.append({
            "timestamp": timestamp.isoformat(),
            "speaker": participant_identity,
            "message": message,
            "type": "speech"
        })
        
       

    @function_tool()
    async def end_interview(self, summary_notes: str = "") -> str:
        """
        End the interview and generate a comprehensive summary.
        
        Args:
            summary_notes: Optional summary notes about the candidate's performance
        """
        # Save transcript to file
        await self._save_interview_data()

        # Run AI analysis if session is available
        if hasattr(self, 'session') and self.session:
            try:
                await self.analyze_interview_with_ai(self.session)
            except Exception as e:
                print(f"⚠️ AI analysis failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️ Session or room name not available for AI analysis")
            print(f"  - Has session: {hasattr(self, 'session') and self.session is not None}")
            print(f"  - Has room_name: {hasattr(self, 'room_name') and self.room_name is not None}")
        
        # Return conclusion message that the agent will naturally speak
        conclusion_message = (
            f"Thank you for your time, This concludes our interview session. "
            f"We have recorded your responses and will be in touch regarding next steps. "
            f"Have a great day!"
        )
        
        # Schedule session shutdown after a brief delay to allow the final message to be spoken
        async def delayed_shutdown():
            await asyncio.sleep(3)  # Give time for the final message
            if hasattr(self, 'session') and self.session and hasattr(self.session, '_activity') and self.session._activity:
                await self.session._activity.drain()
        
        asyncio.create_task(delayed_shutdown())
        
        return conclusion_message

    async def _save_interview_data(self):
        """Save interview transcript and summary to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"interview_{self.name.replace(' ', '_')}_{timestamp}"
        
        # Get conversation data from the session if available
        conversation_data = getattr(self.session, '_conversation_transcript', [])
        
        # Calculate interview duration
        duration_minutes = 0
        if self.interview_start_time:
            duration = datetime.now(timezone.utc) - self.interview_start_time
            duration_minutes = duration.total_seconds() / 60
        
        # Populate interview summary with actual data
        self.interview_summary = {
            "candidate_name": self.name,
            "job_description": self.jd,
            "start_time": self.interview_start_time.isoformat() if self.interview_start_time else None,
            "duration_minutes": duration_minutes,
            "interview_status": "completed",
            "transcript": conversation_data,
            "summary_notes": "Interview completed via AI interviewer"
        }
        
        # Save full transcript as JSON
        transcript_file = f"{filename_base}_transcript.json"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(self.interview_summary, f, indent=2, ensure_ascii=False)
        
        # Save readable summary as text
        summary_file = f"{filename_base}_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"INTERVIEW SUMMARY\n")
            f.write(f"================\n\n")
            f.write(f"Candidate: {self.name}\n")
            f.write(f"Date: {self.interview_start_time.strftime('%Y-%m-%d %H:%M:%S UTC') if self.interview_start_time else 'Unknown'}\n")
            f.write(f"Duration: {duration_minutes:.1f} minutes\n\n")
            
            f.write(f"TRANSCRIPT\n")
            f.write(f"==========\n\n")
            
            # Use the conversation data from the session if available
            if conversation_data:
                for entry in conversation_data:
                    timestamp_str = entry.get('timestamp', 'Unknown')
                    role = entry.get('role', 'unknown')
                    text = entry.get('text', '')
                    speaker = "Interviewer" if role == "assistant" else "Candidate"
                    f.write(f"[{timestamp_str}] {speaker}: {text}\n\n")
            else:
                # Fallback to the old method if no conversation data
                for entry in self.interview_transcript:
                    timestamp_entry = datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
                    speaker = "Interviewer" if entry['speaker'] == "agent" else "Candidate"
                    f.write(f"[{timestamp_entry}] {speaker}: {entry['message']}\n\n")
            
            if self.interview_summary.get('summary_notes'):
                f.write(f"INTERVIEWER NOTES\n")
                f.write(f"================\n\n")
                f.write(f"{self.interview_summary['summary_notes']}\n")
        
        print(f"\\nInterview data saved:")
        print(f"  - Transcript: {transcript_file}")
        print(f"  - Summary: {summary_file}")
        
        # Store file paths on session for use by AI analysis
        if hasattr(self, 'session') and self.session:
            self.session._agent_transcript_file = transcript_file
            self.session._agent_summary_file = summary_file

    async def analyze_interview_with_ai(self, session):
        """Analyze interview transcript using Google Gemini and generate enhanced summary"""
        try:
            # Load environment variables
            dotenv.load_dotenv()
            
            # Initialize Google GenAI client with API key from environment
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                print("⚠️ GOOGLE_API_KEY not found. Skipping AI analysis.")
                return
            
            client = genai.Client(api_key=api_key)
            
            # Get conversation data from session
            conversation_data = getattr(session, '_conversation_transcript', [])
            if not conversation_data:
                print("⚠️ No conversation data found. Skipping AI analysis.")
                return
            
            # Prepare transcript text for AI analysis
            transcript_text = ""
            for entry in conversation_data:
                role = entry.get('role', 'unknown')
                text = entry.get('text', '')
                speaker = "Interviewer" if role == "assistant" else "Candidate"
                transcript_text += f"{speaker}: {text}\n"
            
            if not transcript_text.strip():
                print("⚠️ Empty transcript. Skipping AI analysis.")
                return
            
            print("🤖 Analyzing interview with AI...")
            
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze the following job interview transcript and extract key information about the candidate.
            
            Position being interviewed for: {self.jd}
            
            Interview Transcript:
            {transcript_text}
            
            Please analyze the candidate's responses and provide the following information in a structured format:
            
            1. Candidate's full name (if mentioned)
            2. Interest level in the position (Scale: Low/Medium/High) - based on enthusiasm, questions asked, and engagement
            3. Readiness for the role (Scale: Not Ready/Somewhat Ready/Ready/Very Ready) - based on experience and skills mentioned
            4. Experience level (Junior/Mid-level/Senior) - based on years of experience and complexity of projects mentioned
            5. Technical skills mentioned (list)
            6. Soft skills demonstrated (list)
            7. Key strengths (paragraph summary)
            8. Areas for improvement (paragraph summary)
            9. Overall assessment and recommendation (paragraph summary)
            10. Notable quotes or responses from the candidate
            
            Please respond in valid JSON format only, using these exact keys:
            {{
                "candidate_name": "string",
                "interest_level": "string",
                "readiness": "string", 
                "experience_level": "string",
                "technical_skills": ["array", "of", "strings"],
                "soft_skills": ["array", "of", "strings"],
                "key_strengths": "string",
                "areas_for_improvement": "string",
                "overall_assessment": "string",
                "notable_quotes": ["array", "of", "strings"]
            }}
            """
            
            # Generate analysis
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=analysis_prompt
            )
            
            # Parse JSON response
            try:
                analysis_result = json.loads(response.text)
            except json.JSONDecodeError:
                # If response is not valid JSON, try to extract it
                text = response.text.strip()
                if text.startswith('```json'):
                    text = text[7:-3]  # Remove ```json and ```
                elif text.startswith('```'):
                    text = text[3:-3]   # Remove ``` markers
                
                analysis_result = json.loads(text)
            
            # Generate enhanced files with AI analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            candidate_name = analysis_result.get('candidate_name', self.name)
            filename_base = f"interview_{candidate_name.replace(' ', '_')}_{timestamp}_AI_ANALYSIS"
            
            # Save enhanced JSON file
            enhanced_json_file = f"{filename_base}.json"
            enhanced_data = {
                "interview_metadata": {
                    "candidate": candidate_name,
                    "position": self.jd,
                    "interview_date": timestamp,
                    "duration_minutes": self.interview_summary.get('duration_minutes', 0)
                },
                "ai_analysis": analysis_result,
                "transcript": conversation_data,
                "agent_summary": self.interview_summary
            }
            
            with open(enhanced_json_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
            
            # Save enhanced summary file
            enhanced_summary_file = f"{filename_base}.txt"
            with open(enhanced_summary_file, 'w', encoding='utf-8') as f:
                f.write(f"🤖 AI-ENHANCED INTERVIEW ANALYSIS\n")
                f.write(f"==================================\n\n")
                f.write(f"Candidate: {candidate_name}\n")
                f.write(f"Position: {self.jd}\n")
                f.write(f"Interview Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duration: {enhanced_data['interview_metadata']['duration_minutes']:.1f} minutes\n\n")
                
                # AI Analysis Section
                f.write(f"🧠 AI ANALYSIS RESULTS\n")
                f.write(f"======================\n\n")
                f.write(f"📊 CANDIDATE ASSESSMENT:\n")
                f.write(f"  • Interest Level: {analysis_result.get('interest_level', 'Unknown')}\n")
                f.write(f"  • Readiness: {analysis_result.get('readiness', 'Unknown')}\n")
                f.write(f"  • Experience Level: {analysis_result.get('experience_level', 'Unknown')}\n\n")
                
                f.write(f"🔧 TECHNICAL SKILLS:\n")
                for skill in analysis_result.get('technical_skills', []):
                    f.write(f"  • {skill}\n")
                f.write(f"\n")
                
                f.write(f"🤝 SOFT SKILLS:\n")
                for skill in analysis_result.get('soft_skills', []):
                    f.write(f"  • {skill}\n")
                f.write(f"\n")
                
                if analysis_result.get('key_strengths'):
                    f.write(f"💪 KEY STRENGTHS:\n")
                    f.write(f"{analysis_result['key_strengths']}\n\n")
                
                if analysis_result.get('areas_for_improvement'):
                    f.write(f"📈 AREAS FOR IMPROVEMENT:\n")
                    f.write(f"{analysis_result['areas_for_improvement']}\n\n")
                
                if analysis_result.get('overall_assessment'):
                    f.write(f"🎯 OVERALL ASSESSMENT:\n")
                    f.write(f"{analysis_result['overall_assessment']}\n\n")
                
                if analysis_result.get('notable_quotes'):
                    f.write(f"💬 NOTABLE QUOTES:\n")
                    for quote in analysis_result.get('notable_quotes', []):
                        f.write(f"  • \"{quote}\"\n")
                    f.write(f"\n")
                
                # Transcript Section
                f.write(f"📝 FULL TRANSCRIPT\n")
                f.write(f"==================\n\n")
                for entry in conversation_data:
                    timestamp = entry.get('timestamp', 'Unknown')
                    role = entry.get('role', 'unknown')
                    text = entry.get('text', '')
                    speaker = "🤖 Interviewer" if role == "assistant" else "👤 Candidate"
                    f.write(f"[{timestamp}] {speaker}: {text}\n\n")
            
            print(f"\\n🤖 AI Analysis completed!")
            print(f"  📄 Enhanced JSON: {enhanced_json_file}")
            print(f"  📋 Enhanced Summary: {enhanced_summary_file}")
            
        except Exception as e:
            print(f"❌ Error during AI analysis: {e}")
            # Create fallback analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fallback_file = f"interview_analysis_failed_{timestamp}.txt"
            with open(fallback_file, 'w') as f:
                f.write(f"AI Analysis Failed\n")
                f.write(f"==================\n\n")
                f.write(f"Error: {str(e)}\n")
                f.write(f"Timestamp: {datetime.now()}\n")
            print(f"⚠️ Fallback error log saved: {fallback_file}")

    @function_tool()
    async def web_search(self, query: str) -> str:
        if not TAVILY_API_KEY:
            return "Tavily API key is not set. Please set the TAVILY_API_KEY environment variable."
        
        try:
            tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
            response = tavily_client.search(query=query, search_depth="basic")
            if response.get('answer'):
                return response['answer']
            return str(response.get('results', 'No results found.'))
        except Exception as e:
            return f"An error occurred during web search: {e}"
        finally:
            # Ensure any HTTP connections are closed
            try:
                if hasattr(tavily_client, 'close'):
                    await tavily_client.close()
            except:
                pass  # Ignore cleanup errors

    