#!/usr/bin/env python3
"""
UMI Bridge Server - LiveKit VAD Edition
========================================

Features:
- Session-based chat (button starts/ends session)
- LiveKit VAD handles voice detection
- Continuous streaming during session
- Real-time feedback to ESP32

Install:
  pip install websockets livekit livekit-api numpy
"""

import asyncio
import websockets
import json
import numpy as np
from livekit import rtc, api
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIG ====================

# LiveKit credentials
LIVEKIT_URL = "wss://your-project.livekit.cloud"
LIVEKIT_API_KEY = "APIxxxxxxxxxx"
LIVEKIT_API_SECRET = "xxxxxxxxxxxxxxxxxxxxxx"

WS_HOST = "0.0.0.0"
WS_PORT = 8765

SAMPLE_RATE = 16000
CHANNELS = 1

# ==================== DEVICE SESSION ====================

class DeviceSession:
    """Manages a single device's LiveKit session"""
    
    def __init__(self, device_id: str, websocket):
        self.device_id = device_id
        self.websocket = websocket
        self.session_id = None
        self.room = None
        self.audio_source = None
        self.is_active = False
        self.audio_frames_sent = 0
        
    async def start_session(self, session_id: str, livekit_url: str, token: str):
        """Start a new chat session"""
        self.session_id = session_id
        self.is_active = True
        self.audio_frames_sent = 0
        
        logger.info(f"🆕 Starting session: {session_id}")
        
        # Create room
        self.room = rtc.Room()
        
        # Connect to LiveKit
        try:
            await self.room.connect(livekit_url, token)
            logger.info(f"🔗 Connected to LiveKit room: {session_id}")
        except Exception as e:
            logger.error(f"❌ LiveKit connection failed: {e}")
            raise
        
        # Create audio source
        self.audio_source = rtc.AudioSource(SAMPLE_RATE, CHANNELS)
        track = rtc.LocalAudioTrack.create_audio_track("microphone", self.audio_source)
        
        # Publish track
        options = rtc.TrackPublishOptions()
        options.source = rtc.TrackSource.SOURCE_MICROPHONE
        await self.room.local_participant.publish_track(track, options)
        
        logger.info(f"🎤 Published mic track")
        
        # Subscribe to AI agent audio
        @self.room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication, participant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info(f"🔊 AI agent audio track subscribed")
                asyncio.create_task(self._forward_agent_audio(track))
        
        # Notify ESP32
        await self.send_message({
            'type': 'session_started',
            'session_id': session_id
        })
        
        return self.room
    
    async def end_session(self):
        """End current session"""
        if not self.is_active:
            return
        
        logger.info(f"✅ Ending session: {self.session_id}")
        
        self.is_active = False
        
        # Disconnect from LiveKit
        if self.room:
            await self.room.disconnect()
            self.room = None
        
        self.audio_source = None
        
        # Notify ESP32
        await self.send_message({
            'type': 'session_ended',
            'session_id': self.session_id,
            'frames_sent': self.audio_frames_sent
        })
        
        self.session_id = None
    
    async def process_audio_chunk(self, audio_data: bytes):
        """Send audio chunk to LiveKit"""
        if not self.is_active or not self.audio_source:
            return
        
        try:
            # Convert to PCM
            pcm = np.frombuffer(audio_data, dtype=np.int16)
            
            # Create audio frame
            frame = rtc.AudioFrame.create(SAMPLE_RATE, CHANNELS, len(pcm))
            frame_data = np.frombuffer(frame.data, dtype=np.int16)
            frame_data[:] = pcm
            
            # Send to LiveKit
            await self.audio_source.capture_frame(frame)
            
            self.audio_frames_sent += 1
            
            # Log progress every second
            if self.audio_frames_sent % 33 == 0:  # ~33 frames = 1 second @ 30ms chunks
                duration = self.audio_frames_sent * 0.03
                logger.info(f"🎙️ Streaming: {duration:.1f}s")
        
        except Exception as e:
            logger.error(f"❌ Error processing audio: {e}")
    
    async def _forward_agent_audio(self, track: rtc.Track):
        """Forward AI agent's audio to ESP32"""
        logger.info("🔊 Starting agent audio playback")
        
        # Notify ESP32 that agent is speaking
        await self.send_message({'type': 'agent_speaking_start'})
        
        try:
            audio_stream = rtc.AudioStream(track)
            
            async for frame_event in audio_stream:
                frame = frame_event.frame
                
                # Convert to mono int16
                samples = np.frombuffer(frame.data, dtype=np.int16)
                
                if frame.num_channels == 2:
                    # Stereo to mono
                    samples = samples[::2]
                
                # Send to ESP32
                try:
                    await self.websocket.send(samples.tobytes())
                except websockets.exceptions.ConnectionClosed:
                    logger.info("❌ WebSocket closed during playback")
                    break
        
        except Exception as e:
            logger.error(f"❌ Error forwarding audio: {e}")
        
        finally:
            # Notify ESP32 that agent finished speaking
            await self.send_message({'type': 'agent_speaking_end'})
            logger.info("✅ Agent finished speaking")
    
    async def send_message(self, msg: dict):
        """Send JSON message to ESP32"""
        try:
            await self.websocket.send(json.dumps(msg))
        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")

# ==================== BRIDGE SERVER ====================

class UMIBridge:
    def __init__(self):
        self.devices = {}  # device_id -> DeviceSession
        self.livekit_url = LIVEKIT_URL
        self.api_key = LIVEKIT_API_KEY
        self.api_secret = LIVEKIT_API_SECRET
    
    async def handle_device(self, websocket, path):
        """Handle WebSocket connection from ESP32"""
        device_id = id(websocket)
        session = DeviceSession(device_id, websocket)
        self.devices[device_id] = session
        
        logger.info(f"📱 Device connected: {device_id}")
        
        try:
            # Main message loop
            async for message in websocket:
                await self._handle_message(session, message)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"❌ Device disconnected: {device_id}")
        
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup
            if session.is_active:
                await session.end_session()
            
            if device_id in self.devices:
                del self.devices[device_id]
            
            logger.info(f"🧹 Cleaned up device: {device_id}")
    
    async def _handle_message(self, session: DeviceSession, message):
        """Handle message from ESP32"""
        
        # Binary = audio data
        if isinstance(message, bytes):
            await session.process_audio_chunk(message)
        
        # Text = JSON command
        elif isinstance(message, str):
            try:
                msg = json.loads(message)
                msg_type = msg.get('type')
                
                if msg_type == 'device_info':
                    device_id_str = msg.get('device_id')
                    logger.info(f"📱 Device info: {device_id_str}")
                    
                    # Send ready confirmation
                    await session.send_message({'type': 'ready'})
                
                elif msg_type == 'start_session':
                    # Create new LiveKit room for this session
                    session_id = msg.get('session_id')
                    room_name = f"umi-{session_id}"
                    
                    # Generate token
                    token = self._create_token(room_name, f"device-{session.device_id}")
                    
                    # Start session
                    await session.start_session(session_id, self.livekit_url, token)
                
                elif msg_type == 'end_session':
                    await session.end_session()
            
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Invalid JSON: {message}")
    
    def _create_token(self, room_name: str, participant_name: str) -> str:
        """Create LiveKit access token"""
        token = api.AccessToken(self.api_key, self.api_secret)
        token.with_identity(participant_name)
        token.with_name(participant_name)
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True
        ))
        
        return token.to_jwt()
    
    async def start(self):
        """Start WebSocket server"""
        logger.info(f"🌉 Starting bridge on ws://{WS_HOST}:{WS_PORT}")
        
        async with websockets.serve(
            self.handle_device,
            WS_HOST,
            WS_PORT,
            ping_interval=20,
            ping_timeout=10,
            max_size=10_000_000  # 10MB max message size
        ):
            logger.info("✅ Bridge ready!")
            logger.info(f"💡 ESP32 should connect to: ws://YOUR_IP:{WS_PORT}")
            logger.info("\n🎯 Features:")
            logger.info("  • Session-based conversations")
            logger.info("  • LiveKit VAD for voice detection")
            logger.info("  • Real-time audio streaming")
            logger.info("  • AI agent responses\n")
            
            await asyncio.Future()

# ==================== MAIN ====================

async def main():
    print("\n╔════════════════════════════════╗")
    print("║  UMI Bridge - VAD Edition      ║")
    print("╚════════════════════════════════╝\n")
    
    # Validate config
    if "your-project" in LIVEKIT_URL:
        print("❌ ERROR: Update LIVEKIT_URL!")
        print("💡 Get from: https://cloud.livekit.io\n")
        return
    
    if LIVEKIT_API_KEY.startswith("APIxx"):
        print("❌ ERROR: Update LIVEKIT_API_KEY and LIVEKIT_API_SECRET!")
        print("💡 Get from: https://cloud.livekit.io\n")
        return
    
    bridge = UMIBridge()
    
    try:
        await bridge.start()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")

if __name__ == "__main__":
    """
    SETUP:
    
    1. Install: pip install websockets livekit livekit-api numpy
    
    2. Update LiveKit credentials above
    
    3. Run: python bridge.py
    
    4. Update ESP32 with this computer's IP
    
    5. Start AI agent: python agent.py start
    
    6. Press button on ESP32!
    
    HOW IT WORKS:
    
    - Button press → Start new chat session
    - ESP32 streams audio continuously
    - LiveKit VAD detects speech
    - AI agent processes and responds
    - TTS plays on ESP32 speaker
    - Button press again → End session
    
    Each button press = fresh conversation
    """
    
    asyncio.run(main())