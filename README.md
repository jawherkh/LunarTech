# LunarTech AI Interviewer System Documentation

## Overview

The LunarTech AI Interviewer System is a real-time, AI-powered interview platform that conducts mock interviews for Data Science positions. The system uses LiveKit for real-time communication, Google's Gemini AI for natural language processing, and provides comprehensive analysis and transcript generation.

## Architecture

The system consists of two main components:

### 1. `main.py` - Entry Point & Session Management
### 2. `InterviewerAgent.py` - Core Interview Agent Logic

---

## File: `main.py`

### Purpose
The main entry point that sets up the LiveKit session, creates the interview room, and orchestrates the interview process.

### Key Features

#### Environment Setup
- Loads environment variables for API keys and configuration
- Sets up logging for debugging
- Configures LiveKit WebSocket URL, API key, and secret

#### Required Environment Variables
```bash
LIVEKIT_WS_URL=ws://localhost:7880          # LiveKit WebSocket URL
LIVEKIT_API_KEY=devkey                      # LiveKit API key
LIVEKIT_API_SECRET=secret                   # LiveKit API secret
LIVEKIT_ROOM_NAME=interview-room-{uuid}     # Optional room name
LIVEKIT_URL=http://localhost:3000           # Frontend URL for joining
GOOGLE_API_KEY=your_google_api_key          # Google AI API key
TAVILY_API_KEY=your_tavily_api_key          # Optional: For web search
```

#### Job Description Template
Contains a predefined Data Science job description including:
- Required skills (Python/R, ML, SQL, etc.)
- Experience requirements (2+ years)
- Salary range ($95,000-$130,000)
- Benefits and work arrangements

#### Room Creation & Management
```python
async def entrypoint(ctx: agents.JobContext):
    # Creates LiveKit room with:
    # - 10-minute empty timeout
    # - Maximum 2 participants (interviewer + candidate)
    # - Unique room name generation
```

#### Session Configuration
- **LLM**: Google Gemini 2.5 Flash with native audio dialog
- **Voice**: "Puck" voice model
- **STT**: Google Speech-to-Text with latest_long model
- **Temperature**: 0.7 for balanced creativity

#### Transcript Capture System
The system captures conversation in real-time using two event handlers:

1. **User Input Transcription**: Captures candidate responses
2. **Conversation Item Added**: Captures interviewer responses

Each entry includes:
- Timestamp
- Speaker role (user/assistant)
- Transcribed text
- Speaker ID

### Interview Flow
1. Room creation and participant invitation
2. Agent initialization with job description
3. Structured question sequence:
   - Name and background
   - Interest in position
   - Experience with data science/ML/AI
   - Career goals
   - Availability
4. Follow-up questions based on responses
5. Interview conclusion via `end_interview` function

---

## File: `InterviewerAgent.py`

### Purpose
Implements the core AI interviewer agent that conducts interviews, manages conversation flow, and generates comprehensive analysis.

### Class: `InterviewAgent`

#### Initialization
```python
def __init__(self, *args, **kwargs):
    # Flexible constructor supporting:
    # - InterviewAgent(name, jd)
    # - InterviewAgent(jd=jd)
    # - InterviewAgent(name=name, jd=jd)
```

#### Key Attributes
- `name`: Candidate name (default: "Candidate")
- `jd`: Job description (default: "Undefined Position")
- `interview_start_time`: UTC timestamp of interview start
- `interview_transcript`: Raw conversation log
- `questions_asked`: Tracking of asked questions
- `is_interview_completed`: Interview completion status
- `interview_summary`: Structured summary data

#### Core Methods

##### `async def on_enter(self)`
- Triggered when agent enters the room
- Records interview start time in UTC

##### `async def on_message(self, message: str, participant_identity: str)`
- Logs all messages to internal transcript
- Maintains conversation history with timestamps

##### `@function_tool() async def end_interview(self, summary_notes: str = "")`
**Purpose**: Concludes the interview and generates comprehensive documentation

**Process**:
1. Saves interview data to JSON and text files
2. Triggers AI analysis of the conversation
3. Provides natural conclusion message
4. Schedules graceful session shutdown

**Output Files**:
- `interview_{name}_{timestamp}_transcript.json`: Complete interview data
- `interview_{name}_{timestamp}_summary.txt`: Human-readable summary

##### `async def _save_interview_data(self)`
**Purpose**: Handles file generation and data persistence

**Generated Files**:
1. **JSON Transcript**: Structured data including:
   - Candidate information
   - Interview metadata (duration, status)
   - Complete conversation transcript
   - Summary notes

2. **Text Summary**: Human-readable format with:
   - Interview overview
   - Chronological transcript
   - Interviewer notes

##### `async def analyze_interview_with_ai(self, session)`
**Purpose**: Advanced AI analysis using Google Gemini

**Analysis Components**:
1. **Candidate Assessment**:
   - Interest level (Low/Medium/High)
   - Readiness for role (Not Ready/Somewhat Ready/Ready/Very Ready)
   - Experience level (Junior/Mid-level/Senior)

2. **Skills Analysis**:
   - Technical skills mentioned
   - Soft skills demonstrated

3. **Evaluation**:
   - Key strengths summary
   - Areas for improvement
   - Overall assessment and recommendation
   - Notable quotes extraction

**AI Analysis Output**:
- `interview_{name}_{timestamp}_AI_ANALYSIS.json`: Structured AI analysis
- `interview_{name}_{timestamp}_AI_ANALYSIS.txt`: Enhanced human-readable report

**Analysis Prompt Structure**:
The AI receives the complete transcript and job description, then extracts:
```json
{
  "candidate_name": "string",
  "interest_level": "string",
  "readiness": "string", 
  "experience_level": "string",
  "technical_skills": ["array"],
  "soft_skills": ["array"],
  "key_strengths": "string",
  "areas_for_improvement": "string",
  "overall_assessment": "string",
  "notable_quotes": ["array"]
}
```

##### `@function_tool() async def web_search(self, query: str)`
**Purpose**: Optional web search capability using Tavily API

**Features**:
- Real-time information lookup during interviews
- Fact-checking capabilities
- Industry-specific information retrieval

---

## System Workflow

### 1. Initialization Phase
```
Environment Setup → Room Creation → Agent Initialization → Session Start
```

### 2. Interview Phase
```
Welcome Message → Structured Questions → Follow-up Questions → Natural Conversation
```

### 3. Conclusion Phase
```
End Interview Function → Data Saving → AI Analysis → File Generation → Session Cleanup
```

### 4. Output Generation
```
Basic Transcript → AI Analysis → Enhanced Reports → File Persistence
```

---

## Technical Stack

### Core Technologies
- **LiveKit**: Real-time communication platform
- **Google Gemini**: AI language model for conversation and analysis
- **Google STT**: Speech-to-text conversion
- **Tavily**: Web search API (optional)

### Python Libraries
- `livekit`: Real-time communication
- `google-genai`: Google AI integration
- `tavily-python`: Web search capabilities
- `asyncio`: Asynchronous programming
- `json`: Data serialization
- `datetime`: Timestamp management
- `dotenv`: Environment variable management

---

## File Outputs

### Basic Interview Files
1. **`interview_{name}_{timestamp}_transcript.json`**
   - Complete interview metadata
   - Raw conversation transcript
   - Interview summary data

2. **`interview_{name}_{timestamp}_summary.txt`**
   - Human-readable interview summary
   - Chronological conversation log
   - Basic interviewer notes

### AI-Enhanced Files (when AI analysis succeeds)
3. **`interview_{name}_{timestamp}_AI_ANALYSIS.json`**
   - Complete AI analysis data
   - Structured candidate assessment
   - Enhanced metadata

4. **`interview_{name}_{timestamp}_AI_ANALYSIS.txt`**
   - Professional interview report
   - AI-generated insights
   - Structured assessment sections
   - Complete transcript with enhanced formatting

### Error Handling Files
5. **`interview_analysis_failed_{timestamp}.txt`**
   - Generated when AI analysis fails
   - Contains error details and timestamp

---

## Configuration & Setup

### 1. Environment Variables
Create a `.env` file with required API keys and configuration.

### 2. Dependencies Installation
```bash
pip install livekit-agents google-generativeai tavily-python python-dotenv
```

### 3. LiveKit Server
Ensure LiveKit server is running and accessible.

### 4. Frontend Integration
The system generates join URLs for browser-based interview participation.

---

## Error Handling

### Graceful Degradation
- AI analysis failure doesn't prevent basic transcript generation
- Missing API keys result in feature-specific warnings
- Session cleanup prevents resource leaks

### Logging & Debugging
- Comprehensive logging throughout the system
- Error tracking with stack traces
- Fallback file generation for failed operations

---

## Security Considerations

### API Key Management
- Environment variable storage for sensitive data
- No hardcoded credentials in source code

### Data Privacy
- Local file storage for interview data
- UTC timestamps for consistency
- Structured data formats for easy processing

---

## Future Enhancement Opportunities

### 1. Multi-Position Support
- Dynamic job description loading
- Position-specific question sets
- Industry-tailored analysis

### 2. Advanced Analytics
- Sentiment analysis
- Communication pattern recognition
- Performance benchmarking

### 3. Integration Features
- ATS (Applicant Tracking System) integration
- Calendar scheduling
- Email notification system

### 4. Real-time Features
- Live coaching suggestions
- Real-time performance metrics
- Dynamic question adaptation

---

## Usage Examples

### Basic Interview Setup
```python
# Create interviewer agent
interviewer = InterviewAgent(jd=job_description)

# Start interview session
session = AgentSession(llm=model, stt=speech_to_text)
await session.start(room=room, agent=interviewer)
```

### Custom Configuration
```python
# With specific candidate name
interviewer = InterviewAgent(name="John Doe", jd=job_description)

# End interview with custom notes
await interviewer.end_interview("Excellent technical skills, needs soft skill development")
```

This documentation provides a comprehensive overview of the LunarTech AI Interviewer System, covering both the technical implementation and practical usage aspects of the codebase.
