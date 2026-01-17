#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <driver/i2s.h>

/*
 * UMI - LiveKit VAD Edition
 * ==========================
 * 
 * Button pressed = Start new chat session
 * LiveKit VAD handles voice detection
 * Continuous streaming until button pressed again
 */

/* ==================== CONFIG ==================== */

const char* WIFI_SSID = "Your-WiFi-Name";
const char* WIFI_PASSWORD = "Your-WiFi-Password";
const char* BRIDGE_HOST = "192.168.1.100";
const uint16_t BRIDGE_PORT = 8765;

#define BUTTON_PIN 7
#define LED_PIN 21

// I2S Microphone (INMP441)
#define I2S_MIC_SCK  1
#define I2S_MIC_WS   2
#define I2S_MIC_SD   3

// I2S Speaker (MAX98357A)
#define I2S_SPK_BCK  5
#define I2S_SPK_WS   6
#define I2S_SPK_DOUT 8

#define SAMPLE_RATE 16000
#define CHUNK_SIZE 480  // 30ms chunks
#define MIC_GAIN 3

/* ==================== STATE ==================== */

WebSocketsClient webSocket;

enum State { DISCONNECTED, IDLE, IN_SESSION, SPEAKING };
State currentState = DISCONNECTED;

int16_t audioBuffer[CHUNK_SIZE];
String currentSessionId = "";
bool isSpeakerMode = false;

/* ==================== I2S SETUP ==================== */

void setupI2SMic() {
  i2s_driver_uninstall(I2S_NUM_0);
  delay(100);
  
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  
  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_MIC_SCK,
    .ws_io_num = I2S_MIC_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_MIC_SD
  };
  
  i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin_config);
  i2s_zero_dma_buffer(I2S_NUM_0);
  
  isSpeakerMode = false;
  Serial.println("✅ Mic ready");
}

void setupI2SSpeaker() {
  i2s_driver_uninstall(I2S_NUM_0);
  delay(100);
  
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  
  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SPK_BCK,
    .ws_io_num = I2S_SPK_WS,
    .data_out_num = I2S_SPK_DOUT,
    .data_in_num = I2S_PIN_NO_CHANGE
  };
  
  i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin_config);
  i2s_zero_dma_buffer(I2S_NUM_0);
  
  isSpeakerMode = true;
  Serial.println("🔊 Speaker ready");
}

/* ==================== WEBSOCKET HANDLERS ==================== */

void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("❌ Disconnected from bridge");
      currentState = DISCONNECTED;
      digitalWrite(LED_PIN, LOW);
      break;
      
    case WStype_CONNECTED:
      {
        Serial.println("✅ Connected to bridge");
        currentState = IDLE;
        digitalWrite(LED_PIN, HIGH);
        
        // Send device info
        StaticJsonDocument<200> doc;
        doc["type"] = "device_info";
        doc["device_id"] = "umi-" + String((uint32_t)ESP.getEfuseMac(), HEX);
        doc["sample_rate"] = SAMPLE_RATE;
        doc["channels"] = 1;
        
        String json;
        serializeJson(doc, json);
        webSocket.sendTXT(json);
      }
      break;
      
    case WStype_TEXT:
      {
        Serial.printf("📝 Message: %s\n", payload);
        
        StaticJsonDocument<512> doc;
        DeserializationError error = deserializeJson(doc, payload, length);
        
        if (!error) {
          const char* msgType = doc["type"];
          
          if (strcmp(msgType, "session_started") == 0) {
            currentSessionId = doc["session_id"].as<String>();
            Serial.printf("🆕 Session started: %s\n", currentSessionId.c_str());
            digitalWrite(LED_PIN, HIGH);
          }
          else if (strcmp(msgType, "session_ended") == 0) {
            Serial.println("✅ Session ended");
            currentSessionId = "";
            currentState = IDLE;
            digitalWrite(LED_PIN, LOW);
          }
          else if (strcmp(msgType, "vad_speech_start") == 0) {
            Serial.println("🎤 VAD: Speech detected");
          }
          else if (strcmp(msgType, "vad_speech_end") == 0) {
            Serial.println("🔇 VAD: Speech ended");
          }
          else if (strcmp(msgType, "transcript") == 0) {
            const char* text = doc["text"];
            bool isFinal = doc["is_final"] | false;
            Serial.printf("📝 %s: %s\n", isFinal ? "FINAL" : "Partial", text);
          }
          else if (strcmp(msgType, "agent_speaking_start") == 0) {
            Serial.println("🤖 AI started speaking");
            currentState = SPEAKING;
          }
          else if (strcmp(msgType, "agent_speaking_end") == 0) {
            Serial.println("✅ AI finished speaking");
            if (currentState == SPEAKING) {
              currentState = IN_SESSION;
            }
          }
        }
      }
      break;
      
    case WStype_BIN:
      // Received TTS audio from bridge
      if (currentState == SPEAKING) {
        playAudioChunk(payload, length);
      }
      break;
  }
}

/* ==================== AUDIO FUNCTIONS ==================== */

void streamAudioChunk() {
  if (currentState != IN_SESSION) return;
  
  size_t bytesRead = 0;
  esp_err_t result = i2s_read(
    I2S_NUM_0,
    audioBuffer,
    CHUNK_SIZE * sizeof(int16_t),
    &bytesRead,
    10 / portTICK_PERIOD_MS
  );
  
  if (result != ESP_OK || bytesRead == 0) return;
  
  int samplesRead = bytesRead / sizeof(int16_t);
  
  // Apply gain
  for (int i = 0; i < samplesRead; i++) {
    int32_t boosted = (int32_t)audioBuffer[i] * MIC_GAIN;
    audioBuffer[i] = (int16_t)constrain(boosted, -32768, 32767);
  }
  
  // Send to bridge (LiveKit VAD will handle detection)
  webSocket.sendBIN((uint8_t*)audioBuffer, bytesRead);
}

void playAudioChunk(uint8_t* data, size_t length) {
  // Switch to speaker if needed
  if (!isSpeakerMode) {
    setupI2SSpeaker();
  }
  
  int16_t* samples = (int16_t*)data;
  int numSamples = length / 2;
  
  // Convert mono to stereo
  int32_t stereoBuffer[CHUNK_SIZE];
  int chunks = (numSamples + CHUNK_SIZE - 1) / CHUNK_SIZE;
  
  for (int c = 0; c < chunks; c++) {
    int offset = c * CHUNK_SIZE;
    int chunkSize = min(CHUNK_SIZE, numSamples - offset);
    
    for (int i = 0; i < chunkSize; i++) {
      int16_t sample = samples[offset + i];
      stereoBuffer[i] = ((int32_t)sample << 16) | (sample & 0xFFFF);
    }
    
    size_t written;
    i2s_write(I2S_NUM_0, stereoBuffer, chunkSize * sizeof(int32_t), &written, portMAX_DELAY);
  }
}

/* ==================== SESSION MANAGEMENT ==================== */

void startNewSession() {
  if (currentState != IDLE) {
    Serial.println("⚠️ Already in session or not connected");
    return;
  }
  
  // Generate session ID
  currentSessionId = "session-" + String(millis());
  currentState = IN_SESSION;
  
  Serial.printf("🆕 Starting new session: %s\n", currentSessionId.c_str());
  
  // Make sure we're in mic mode
  if (isSpeakerMode) {
    setupI2SMic();
  }
  
  // Send session start to bridge
  StaticJsonDocument<200> doc;
  doc["type"] = "start_session";
  doc["session_id"] = currentSessionId;
  
  String json;
  serializeJson(doc, json);
  webSocket.sendTXT(json);
  
  digitalWrite(LED_PIN, HIGH);
}

void endSession() {
  if (currentState != IN_SESSION && currentState != SPEAKING) {
    Serial.println("⚠️ Not in session");
    return;
  }
  
  Serial.println("✅ Ending session");
  
  // Send session end to bridge
  StaticJsonDocument<200> doc;
  doc["type"] = "end_session";
  doc["session_id"] = currentSessionId;
  
  String json;
  serializeJson(doc, json);
  webSocket.sendTXT(json);
  
  currentSessionId = "";
  currentState = IDLE;
  digitalWrite(LED_PIN, LOW);
  
  // Switch back to mic mode if needed
  if (isSpeakerMode) {
    setupI2SMic();
  }
}

/* ==================== BUTTON HANDLING ==================== */

void handleButton() {
  static bool lastState = HIGH;
  static uint32_t pressStart = 0;
  static bool longPressHandled = false;
  
  bool btn = digitalRead(BUTTON_PIN);
  uint32_t now = millis();
  
  if (btn != lastState) {
    delay(50);  // Debounce
    btn = digitalRead(BUTTON_PIN);
    
    if (btn == LOW) {
      // Button pressed
      pressStart = now;
      longPressHandled = false;
      
      if (currentState == IDLE) {
        // Start new chat session
        startNewSession();
      }
      else if (currentState == IN_SESSION || currentState == SPEAKING) {
        // End current session
        endSession();
      }
    }
    
    lastState = btn;
  }
  
  // Long press = deep sleep
  if (btn == LOW && !longPressHandled && (now - pressStart) >= 3000) {
    Serial.println("😴 Long press - sleep mode");
    longPressHandled = true;
    
    if (currentState == IN_SESSION) {
      endSession();
    }
    
    delay(100);
    esp_deep_sleep_start();
  }
}

/* ==================== WIFI SETUP ==================== */

void setupWiFi() {
  Serial.printf("📡 Connecting to %s...\n", WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n✅ WiFi connected\n");
    Serial.printf("📍 IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n❌ WiFi failed!");
  }
}

/* ==================== MAIN ==================== */

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n╔═══════════════════════════════╗");
  Serial.println("║  UMI - LiveKit VAD Edition    ║");
  Serial.println("╚═══════════════════════════════╝\n");
  
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  setupWiFi();
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ FATAL: No WiFi");
    while(1) delay(1000);
  }
  
  setupI2SMic();
  
  Serial.printf("🌉 Connecting to bridge at %s:%d\n", BRIDGE_HOST, BRIDGE_PORT);
  webSocket.begin(BRIDGE_HOST, BRIDGE_PORT, "/");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
  
  Serial.println("\n✅ Ready!");
  Serial.println("🔘 Press button = Start new chat");
  Serial.println("🔘 Press again = End chat");
  Serial.println("⏸️ Hold 3s = Sleep\n");
}

void loop() {
  webSocket.loop();
  handleButton();
  
  // Continuous audio streaming when in session
  if (currentState == IN_SESSION && !isSpeakerMode) {
    streamAudioChunk();
  }
  else {
    delay(10);
  }
}