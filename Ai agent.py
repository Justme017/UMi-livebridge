#!/usr/bin/env python3
"""
UMI AI Agent - LiveKit VAD Edition
===================================

Intelligent voice assistant with:
- Automatic voice activity detection (VAD)
- Real-time transcription
- Conversational AI (GPT-4 or Ollama)
- Natural TTS responses
- Session-based memory

Install:
  pip install livekit-agents
  pip install livekit-plugins-deepgram
  pip install livekit-plugins-openai  
  pip install livekit-plugins-silero
"""

import logging
from typing import Annotated
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import deepgram, openai, silero

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIG ====================

# AI Provider Selection
USE_CLOUD_AI = True  # True = OpenAI/Deepgram, False = Local (requires setup)

# API Keys (if using cloud)
OPENAI_API_KEY = "sk-..."      # https://platform.openai.com
DEEPGRAM_API_KEY = "..."       # https://console.deepgram.com

# Assistant Personality
SYSTEM_PROMPT = """You are UMI, an intelligent meeting assistant.

Your capabilities:
- Take detailed notes during conversations
- Summarize key discussion points
- Extract action items and decisions
- Answer questions about the conversation
- Provide helpful insights

Guidelines:
- Be concise but thorough
- Use bullet points for summaries
- Always identify speakers when possible
- Highlight important deadlines or commitments
- Ask clarifying questions when needed

When the user says "summarize", provide:
1. Main topics discussed
2. Key decisions made
3. Action items with owners
4. Next steps
"""

# ==================== AI AGENT ====================

async def entrypoint(ctx: JobContext):
    """Main AI agent entry point"""
    
    logger.info(f"🤖 Agent joining room: {ctx.room.name}")
    
    # Connect to room (auto-subscribe to audio only)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    logger.info(f"✅ Connected to room")
    
    # Configure AI providers
    if USE_CLOUD_AI:
        # Cloud AI (recommended for production)
        vad_provider = silero.VAD.load(
            min_speech_duration=0.3,    # Minimum 300ms of speech
            min_silence_duration=0.5,   # 500ms silence = end of speech
            padding_duration=0.1,       # 100ms padding
        )
        
        stt_provider = deepgram.STT(
            api_key=DEEPGRAM_API_KEY,
            model="nova-2",             # Latest model
            language="en",
            interim_results=True        # Real-time partial transcripts
        )
        
        llm_provider = openai.LLM(
            api_key=OPENAI_API_KEY,
            model="gpt-4-turbo-preview", # or "gpt-4o" for newer
            temperature=0.7,
        )
        
        tts_provider = openai.TTS(
            api_key=OPENAI_API_KEY,
            voice="alloy",              # Options: alloy, echo, fable, onyx, nova, shimmer
            speed=1.0,
        )
    else:
        # Local AI (requires additional setup)
        logger.error("❌ Local AI not fully implemented yet")
        logger.info("💡 Set USE_CLOUD_AI = True to use OpenAI/Deepgram")
        return
    
    # Create conversation context
    initial_context = llm.ChatContext(
        messages=[
            llm.ChatMessage(
                role="system",
                content=SYSTEM_PROMPT
            )
        ]
    )
    
    # Create voice assistant
    assistant = VoiceAssistant(
        vad=vad_provider,
        stt=stt_provider,
        llm=llm_provider,
        tts=tts_provider,
        chat_ctx=initial_context,
        
        # Important settings
        allow_interruptions=True,       # User can interrupt AI
        interrupt_speech_duration=0.5,  # 500ms of speech interrupts
        interrupt_min_words=2,          # Need 2+ words to interrupt
        
        # Transcription settings  
        transcription=VoiceAssistant.TranscriptionSettings(
            user_transcription=True,    # Show user's speech
            agent_transcription=True,   # Show AI's speech
        ),
    )
    
    # Event handlers
    @assistant.on("user_started_speaking")
    def on_user_started_speaking():
        logger.info("👤 User started speaking")
    
    @assistant.on("user_stopped_speaking")
    def on_user_stopped_speaking():
        logger.info("🔇 User stopped speaking")
    
    @assistant.on("agent_started_speaking")
    def on_agent_started_speaking():
        logger.info("🤖 Agent started speaking")
    
    @assistant.on("agent_stopped_speaking")
    def on_agent_stopped_speaking():
        logger.info("✅ Agent stopped speaking")
    
    @assistant.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage):
        logger.info(f"📝 User (final): {msg.content}")
    
    @assistant.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage):
        logger.info(f"🤖 Agent (final): {msg.content}")
    
    # Handle function calls (optional - for advanced features)
    @assistant.on("function_calls_finished")
    def on_function_calls_finished(called_functions):
        if called_functions:
            logger.info(f"🔧 Function calls: {[f.name for f in called_functions]}")
    
    # Start the assistant
    assistant.start(ctx.room)
    
    logger.info("✅ Voice assistant started!")
    logger.info("🎙️ Listening for speech...")
    logger.info("\n💡 Try saying:")
    logger.info("  • 'Hello UMI, can you hear me?'")
    logger.info("  • 'Summarize what we've discussed'")
    logger.info("  • 'What are the action items?'")
    logger.info("  • 'Who is responsible for X?'\n")
    
    # Register custom functions (optional)
    @assistant.llm.register_function(
        description="Get the current date and time"
    )
    async def get_current_time(
        timezone: Annotated[str, "Timezone (e.g. 'America/New_York')"] = "UTC"
    ):
        from datetime import datetime
        import pytz
        
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        return f"Current time in {timezone}: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    
    @assistant.llm.register_function(
        description="Save important notes or action items"
    )
    async def save_note(
        content: Annotated[str, "The note content to save"],
        priority: Annotated[str, "Priority level: high, medium, low"] = "medium"
    ):
        # In production, save to database
        logger.info(f"📝 Saving note ({priority}): {content}")
        return f"Note saved with priority: {priority}"

# ==================== MAIN ====================

if __name__ == "__main__":
    """
    SETUP:
    
    1. Install dependencies:
       pip install livekit-agents livekit-plugins-deepgram livekit-plugins-openai livekit-plugins-silero
    
    2. Get API keys:
       - OpenAI: https://platform.openai.com/api-keys
       - Deepgram: https://console.deepgram.com
    
    3. Update OPENAI_API_KEY and DEEPGRAM_API_KEY above
    
    4. Set LiveKit environment variables:
       export LIVEKIT_URL="wss://your-project.livekit.cloud"
       export LIVEKIT_API_KEY="APIxxxxxxxxxx"
       export LIVEKIT_API_SECRET="xxxxxxxxxxxxxx"
    
    5. Run the agent:
       python agent.py start
    
    FEATURES:
    
    ✅ Automatic voice detection (no button needed)
    ✅ Real-time transcription with Deepgram
    ✅ Intelligent responses with GPT-4
    ✅ Natural TTS with OpenAI voices
    ✅ Conversation memory within session
    ✅ Function calling for advanced features
    ✅ Interrupt support (can cut off AI)
    
    SESSION WORKFLOW:
    
    1. User presses button on ESP32
    2. New LiveKit session starts
    3. Agent joins room automatically
    4. User speaks → VAD detects → transcribed → AI responds
    5. Continuous conversation until button pressed again
    6. Session ends, memory cleared for next session
    
    ADVANCED:
    
    - Add custom functions for calendar, email, etc.
    - Integrate with databases for persistent memory
    - Add speaker diarization (who said what)
    - Export transcripts to PDF/Markdown
    - Integrate with Slack/Teams for notifications
    
    COST ESTIMATE:
    
    Per hour of conversation:
    - Deepgram STT: ~$0.26
    - OpenAI GPT-4: ~$0.50-1.00 (depends on responses)
    - OpenAI TTS: ~$0.30
    - LiveKit: Free tier (up to 10k mins/mo)
    
    Total: ~$1-2 per hour
    
    To reduce costs:
    - Use gpt-3.5-turbo instead of gpt-4
    - Use Whisper.cpp locally (free)
    - Self-host LiveKit (free)
    """
    
    # Validate config
    if USE_CLOUD_AI:
        if "sk-..." in OPENAI_API_KEY:
            print("\n❌ ERROR: Update OPENAI_API_KEY!")
            print("💡 Get from: https://platform.openai.com/api-keys\n")
            exit(1)
        
        if "..." in DEEPGRAM_API_KEY:
            print("\n❌ ERROR: Update DEEPGRAM_API_KEY!")
            print("💡 Get from: https://console.deepgram.com\n")
            exit(1)
    
    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            worker_type="room",  # Automatically join matching rooms
            request_timeout=30.0,
        )
    )