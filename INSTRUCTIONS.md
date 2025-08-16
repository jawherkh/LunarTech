# LunarTech AI Interviewer System - Setup Instructions

## Prerequisites

Before setting up the LunarTech AI Interviewer System, ensure you have:
- Python 3.8 or higher installed
- Node.js 16+ installed (for LiveKit server)
- A stable internet connection
- Administrative privileges on your machine

---

## Step 1: Install and Run LiveKit Server

⚠️ **CRITICAL**: The LiveKit server MUST be running before starting the interview system. Without it, the application will not work.




1. **Download LiveKit Server**:
   ```bash
   # For macOS 
    brew update && brew install livekit

   # For Linux
   curl -sSL https://get.livekit.io | bash

   # For Windows
   Download from: https://github.com/livekit/livekit/releases/latest
   ```

2. **Run LiveKit Server**:
   ```bash
   ./livekit-server --dev
   ```

   

### Verify LiveKit Server is Running

You should see output similar to:
```
INFO    starting LiveKit server     {"version": "v1.x.x"}
INFO    server listening            {"address": ":7880", "protocol": "http"}
INFO    rtc server starting         {"address": ":7881"}
```

**Keep this terminal window open** - the LiveKit server must continue running while using the interview system.

---

## Step 2: Set Up Google Cloud Account and Authentication

The system requires Google Cloud services for Speech-to-Text and AI capabilities.

### 2.1 Create Google Cloud Account

1. **Go to Google Cloud Console**:
   - Visit [console.cloud.google.com](https://console.cloud.google.com)
   - Sign in with your Google account or create a new one

2. **Create a New Project**:
   - Click "Select a project" → "New Project"
   - Enter project name: `lunartech-interviewer` (or your preferred name)
   - Click "Create"

### 2.2 Enable Required APIs

1. **Enable Speech-to-Text API**:
   ```
   Navigation: APIs & Services → Library → Search "Speech-to-Text API" → Enable
   ```

2. **Enable Generative AI API**:
   ```
   Navigation: APIs & Services → Library → Search "Generative Language API" → Enable
   ```

### 2.3 Set Up Authentication


1. **Install Google Cloud CLI**:
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Windows
   # Download from: https://cloud.google.com/sdk/docs/install
   
   # Linux
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   ```

2. **Authenticate**:
   ```bash
   # Initialize and login
   gcloud init
   
   # Set up application default credentials
   gcloud auth application-default login
   
   # Set your project
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Verify Authentication**:
   ```bash
   gcloud auth list
   gcloud config list project
   ```

### 2.4 Get Google AI API Key

1. **Go to Google AI Studio**:
   - Visit [aistudio.google.com](https://aistudio.google.com)
   - Sign in with the same Google account

2. **Generate API Key**:
   - Click "Get API Key" or "Create API Key"
   - Select your Google Cloud project
   - Copy the generated API key
   - **Save it securely** - you'll need it for the `.env` file

---

## Step 3: Install Python Dependencies

1. **Navigate to Project Directory**:
   ```bash
   cd /path/to/LunarTech
   ```

2. **Create Virtual Environment** (Recommended):
   ```bash
   # Using venv
   python3 -m venv lunartech-env
   source lunartech-env/bin/activate  # On Windows: lunartech-env\Scripts\activate
   
   # Or using conda
   conda create -n lunartech python=3.10
   conda activate lunartech
   ```

3. **Install Required Packages**:
   ```bash
   pip install -r requirements.txt   
   ```

---

## Step 4: Configure Environment Variables

1. **Create `.env` File**:
   ```bash
   touch .env
   ```

2. **Add Configuration** (edit `.env` file):
   ```env
   # LiveKit Configuration
   LIVEKIT_WS_URL=ws://localhost:7880
   LIVEKIT_API_KEY=devkey
   LIVEKIT_API_SECRET=secret
   LIVEKIT_URL=http://localhost:3000
   
   # Google AI Configuration
   GOOGLE_API_KEY=your_google_ai_api_key_here
   
   # Optional: Web Search (Tavily)
   TAVILY_API_KEY=your_tavily_api_key_here
   
   GOOGLE_APPLICATION_CREDENTIALS=path/to/json/credentials/file
   ```



