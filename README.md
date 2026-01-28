# UMI Voice AI - Personal Assistant & Companion

**Version 2.0** | **Updated: January 13, 2026**

A professional WiFi-based Voice AI Personal Assistant for Xiao ESP32-S3 Sense with E-Ink display.

---

## 🎯 Features

- 🎤 **Voice Input**: Onboard PDM microphone (MSM261S4030H0)
- 🧠 **AI Processing**: OpenAI GPT-4o-mini / Groq LLM with web search
- 🔊 **Voice Output**: OpenAI TTS-1 with professional Nova voice
- 📟 **Visual Feedback**: 1.54" E-Ink display (200×200) with auto font sizing
- 💬 **STT Services**: Deepgram (primary) or ElevenLabs for speech-to-text
- 🎯 **Personality**: Professional yet warm assistant
- ⚡ **Smart Display**: Auto-adjusts font size, paginates long responses
- 🔘 **Simple Control**: One-button operation

---

## 📦 Hardware Requirements

### Core Components
| Component | Specification |
|-----------|---------------|
| **Microcontroller** | Xiao ESP32-S3 Sense (8MB PSRAM required) |
| **Display** | 1.54" E-Paper Expansion Board (200×200) |
| **Microphone** | Onboard PDM MSM261S4030H0 (GPIO41/42 internal) |
| **Speaker Amplifier** | MAX98357A I2S Audio Amplifier |
| **Speaker** | 4Ω or 8Ω, 3W recommended |
| **Button** | Push button for recording control |
| **Power** | USB-C cable (5V) |

### GPIO Pin Assignments

#### Display (E-Paper Expansion Board - Fixed)
```
GPIO1  - Display pin
GPIO2  - Display pin
GPIO3  - Display pin
GPIO4  - Display DC
GPIO7  - Display SCK (SPI)
GPIO9  - Display pin
```

#### Speaker (MAX98357A I2S)
```
GPIO5  - I2S BCLK (Bit Clock)
GPIO6  - I2S LRC (Word Select)
GPIO44 - I2S DOUT (Data Output)
```

#### Microphone (Onboard PDM - Internal)
```
GPIO41 - PDM CLK (internal)
GPIO42 - PDM DATA (internal)
```

#### Button
```
GPIO43 - Record button (D6)
```

---

## 🔌 Hardware Connections

### 1. E-Paper Display
- Connect **XIAO E-Paper Expansion Board** directly to ESP32-S3
- All GPIO connections are pre-configured on the expansion board

### 2. MAX98357A Speaker Amplifier
```
MAX98357A Pin    →    Xiao ESP32-S3 Pin
────────────────────────────────────────
BCLK             →    GPIO5
LRC              →    GPIO6
DIN              →    GPIO44
GND              →    GND
VIN              →    5V (or 3.3V)
SD (Shutdown)    →    Not connected (always on)
GAIN             →    Not connected (15dB default)
```

### 3. Speaker
```
Connect 4Ω or 8Ω speaker to MAX98357A amplifier:
- Speaker (+) → Amplifier Speaker(+)
- Speaker (-) → Amplifier Speaker(-)
```

### 4. Button
```
Button           →    Xiao ESP32-S3
────────────────────────────────────
One side         →    GPIO43 (D6)
Other side       →    GND
```

---

## 📚 API Keys Required

### 1. OpenAI (Required)
- **Purpose**: LLM (GPT-4o-mini) + TTS (Nova voice)
- **Get key**: https://platform.openai.com/api-keys
- **Cost**: ~$0.10-0.50 per 100 conversations
- **Format**: `sk-proj-...`

### 2. Deepgram (Recommended)
- **Purpose**: Speech-to-text (primary)
- **Get key**: https://console.deepgram.com/
- **Free tier**: 45,000 minutes/year
- **Format**: `83b1cb8d...`

### 3. Groq (Optional - for faster LLM)
- **Purpose**: Alternative LLM (2-3x faster than OpenAI)
- **Get key**: https://console.groq.com/
- **Free tier**: Generous limits
- **Format**: `gsk_...`

### 4. ElevenLabs (Optional - backup STT)
- **Purpose**: Alternative speech-to-text
- **Get key**: https://elevenlabs.io/
- **Free tier**: 300 minutes/month
- **Format**: `sk_...`

---

## 🚀 Quick Start

### Step 1: Configure API Keys & WiFi

Edit `src/main.ino` lines 28-35:

```cpp
// WiFi Credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// API Keys
const char* OPENAI_KEY = "sk-proj-...";        // Your OpenAI key
const char* GROQ_KEY = "gsk_...";              // Your Groq key (optional)
const char* ELEVENLABS_KEY = "sk_...";         // Your ElevenLabs key (optional)
const char* DEEPGRAM_KEY = "83b1...";          // Your Deepgram key
```

### Step 2: Install Required Libraries

PlatformIO will auto-install from `platformio.ini`:
- ESP32-audioI2S (v3.x)
- TFT_eSPI (for E-Paper)
- ESP_I2S (Seeed official for PDM mic)

### Step 3: Build & Upload

```bash
# In VS Code with PlatformIO:
1. Click "Build" (checkmark ✓)
2. Connect Xiao ESP32-S3 via USB-C
3. Click "Upload" (arrow →)
4. Click "Monitor" (plug icon) to see serial output
```

### Step 4: First Use

1. **Power on** - Display shows UMI logo
2. **WiFi connects** - "WiFi Connected" appears
3. **System ready** - Displays "Loading..." → "Ready!"
4. **Welcome message** - UMI says "Hi There i am UMI your personel Assistant"
5. **Ready to use** - Display shows "Hold button to speak"

---

## 🎮 How to Use

### Basic Operation

1. **Press & HOLD** button (GPIO43)
2. **Speak** your question (3-7 seconds max)
3. **Release** button
4. Display shows: "Listening..." → "Processing..." → Your question
5. Display shows: "Thinking..." → AI response text (auto-sized font)
6. **UMI speaks** the response (text stays on screen)
7. Display returns to "Hold button to speak"

### Web Search Mode

For questions needing current information, say "Google" in your question:

```
"Google what's the weather in Paris?"
"Google latest news about AI"
```

### Display Features

- **Auto Font Sizing**: Short text = large font, long text = small font
- **Pagination**: Very long responses split across multiple screens (4s each)
- **Page Indicators**: Shows "1/3", "2/3" etc. for multi-page responses
- **Readable Text**: Automatically wraps words, manages line spacing

---

## 🛠️ Project Structure

```
Umi S3sMAXSPK/
├── platformio.ini              # PlatformIO configuration
├── README.md                   # This file
├── src/
│   ├── main.ino               # Main application (226 lines)
│   ├── lib_audio_recording.ino    # PDM microphone recording (245 lines)
│   ├── lib_audio_transcription.ino # STT - Deepgram/ElevenLabs (268 lines)
│   ├── lib_openai_groq_chat.ino   # LLM chat completions (253 lines)
│   ├── lib_speaker.ino            # TTS & audio playback (75 lines)
│   ├── lib_display.ino            # E-Ink display control (130 lines)
│   ├── lib_button.ino             # Button handler & recording (86 lines)
│   ├── lib_Debug.ino              # Debug output system (51 lines)
│   ├── driver.h                   # Display driver config (7 lines)
│   └── image.h                    # UMI logo bitmap (342 lines)
└── wireless_serial_monitor.py  # Wireless debug tool (optional)
```

---

## ⚙️ Configuration Options

### Debug Mode

Edit `src/main.ino` line 13:

```cpp
#define DEBUG_MODE    // Comment out to disable debug output
```

When enabled: Shows detailed logs for button, audio, display operations  
When disabled: Shows only critical system messages

### Microphone Settings

Edit `src/lib_audio_recording.ino`:

```cpp
#define GAIN_BOOSTER_I2S 12        // Voice gain (8-16, default: 12)
const int SAMPLE_RATE = 16000;     // Sample rate (16kHz)
const int SAMPLE_BITS = 16;        // Bit depth (16-bit)
```

### TTS Voice & Speed

Edit `src/lib_openai_groq_chat.ino`:

```cpp
"tts-1",                          // Model: "tts-1" or "gpt-4o-mini-tts"
"nova",                           // Voice: alloy|ash|coral|echo|fable|onyx|nova|sage|shimmer
"1",                              // Speed: "0.25" to "4.0" (default: "1")
```

### Speaker Volume

Edit `src/lib_speaker.ino`:

```cpp
audio_play.setVolume(21);         // Volume: 0-21 (default: 21 = max)
```

### Assistant Personality

Edit `src/lib_openai_groq_chat.ino` (lines 18-36) to customize UMI's personality, welcome message, and system prompt.

---

## 🐛 Troubleshooting

### Display Issues

**Problem**: Display frozen at "Loading..." or blank
- **Solution**: Check GPIO connections (especially GPIO8 SCK)
- **Solution**: Ensure `#define EPAPER_ENABLE` in main.ino line 14
- **Solution**: Verify e-paper expansion board seated correctly

**Problem**: Text doesn't wrap correctly
- **Solution**: Already fixed with auto font sizing and pagination

### Audio Issues

**Problem**: Speaker crackling or distorted
- **Solution**: Already fixed with 200ms pre-delay + 250ms buffer delay
- **Solution**: Check speaker impedance (4Ω or 8Ω recommended)
- **Solution**: Ensure MAX98357A has clean 5V power

**Problem**: No audio output
- **Solution**: Check GPIO5, GPIO6, GPIO44 connections
- **Solution**: Verify speaker connected to MAX98357A terminals
- **Solution**: Try different speaker or check continuity

**Problem**: Microphone not recording
- **Solution**: Onboard PDM mic is automatic (GPIO41/42 internal)
- **Solution**: Check Serial Monitor for "Microphone initialized!" message

### Memory Issues

**Problem**: "Out of memory" or OOM errors
- **Solution**: Already optimized - PSRAM buffer set to 33% (2.7MB)
- **Solution**: Recording limited to 3-7 seconds to preserve memory
- **Solution**: System checks free PSRAM before TTS (needs 200KB minimum)

### WiFi Issues

**Problem**: Can't connect to WiFi
- **Solution**: Check SSID and password in main.ino
- **Solution**: Ensure 2.4GHz WiFi (ESP32-S3 doesn't support 5GHz)
- **Solution**: Move closer to router during initial setup

### Button Issues

**Problem**: Button auto-triggering
- **Solution**: Already fixed on GPIO43 with INPUT_PULLUP
- **Solution**: Check button is connected between GPIO43 and GND

---

## 📊 Performance Specs

- **Recording Duration**: 3-7 seconds per button press
- **Recording Buffer**: 2.7MB PSRAM (33% allocation)
- **Sample Rate**: 16kHz, 16-bit, Mono
- **Microphone Gain**: 12 (optimized for clarity)
- **STT Latency**: ~1-2 seconds (Deepgram)
- **LLM Latency**: ~2-4 seconds (OpenAI GPT-4o-mini)
- **TTS Latency**: ~1-2 seconds (OpenAI TTS-1)
- **Total Response Time**: ~5-8 seconds from question to answer
- **Display Refresh**: ~1 second per screen update (E-Ink)
- **Pagination Delay**: 4 seconds per screen for long responses

---

## 🎨 Customization

### Change Welcome Message

Edit `src/lib_openai_groq_chat.ino` line 24:

```cpp
"Hi There i am UMI your personel Assistant",
```

### Change Assistant Name

Edit `src/lib_openai_groq_chat.ino` line 18:

```cpp
"UMI",    // Change to any name
```

### Add Multiple Assistants

The code supports multiple assistant profiles. See `ASSISTANTS[]` array in `lib_openai_groq_chat.ino`.

---

## 📝 Credits

**Created by**: Shubham  
**Purpose**: To help make Earth a better place to live  
**Board**: Seeed Studio XIAO ESP32-S3 Sense  
**Display**: Seeed Studio XIAO E-Paper Expansion Board  
**AI Services**: OpenAI, Deepgram, Groq, ElevenLabs

---

## 📄 License

Open source project for educational and personal use.

---

## 🆘 Support

For issues, questions, or improvements:
1. Check this README thoroughly
2. Review code comments in each .ino file
3. Check Serial Monitor output for error messages
4. Verify all API keys are valid and have credits

---

**Last Updated**: January 13, 2026  
**Version**: 2.0  
**Status**: Production Ready ✅
