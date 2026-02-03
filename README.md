# Synapse AI Assistant

**Synapse** is an advanced AI-powered voice assistant and computer vision system that combines real-time audio/video streaming, speech recognition, natural language processing, text-to-speech, face recognition, and music playback capabilities.

## 🌟 Features

### Core Capabilities
- **Voice Interaction**: Real-time speech-to-text (STT) and text-to-speech (TTS)
- **Conversational AI**: Powered by LLM (Qwen2.5:3b-instruct via Ollama)
- **Face Recognition**: Advanced face detection and recognition using InsightFace
- **Object Detection**: Real-time object detection using YOLOv8
- **Music Playback**: YouTube music search and streaming using yt-dlp
- **Live Streaming**: Real-time video and audio streaming over network

### AI Components
1. **Vision Pro Engine**: Face recognition and object detection
2. **Speech-to-Text (STT)**: Using Faster-Whisper (distil-large-v3)
3. **Text-to-Speech (TTS)**: Using Kokoro ONNX for natural voice synthesis
4. **LLM Brain**: Conversational AI with context awareness
5. **Music Engine**: YouTube-based music search and playback

## 🏗️ Architecture

The project consists of two main components:

### 1. C++ Streaming Component (Trinetra Vision)
Located in `/src` and `/include`, this component handles:
- **Camera Capture**: Real-time video capture using OpenCV
- **Audio Recording**: Microphone input using miniaudio
- **Network Streaming**: ZeroMQ-based streaming on ports 5555 (video) and 5556 (audio)

**Key Files:**
- `src/main.cpp` - Main streaming application
- `src/CameraHandler.cpp` - Camera initialization and frame capture
- `src/AudioHandler.cpp` - Audio recording and streaming
- `src/NetworkHandler.cpp` - ZeroMQ network communication

### 2. Python AI Engine
Located in `/python/engine`, this component provides:
- **main.py**: Main Synapse AI engine orchestrator
- **vision_pro.py**: Face recognition and object detection
- **stt_engine.py**: Speech-to-text using Faster-Whisper
- **tts_engine.py**: Text-to-speech using Kokoro ONNX
- **llm_engine.py**: Conversational AI using Ollama
- **music_engine.py**: Music playback using yt-dlp and pygame

## 🚀 Getting Started

### Prerequisites

#### C++ Dependencies (via vcpkg)
- OpenCV
- ZeroMQ
- cppzmq
- miniaudio
- nlohmann-json

#### Python Dependencies
Install using pip:
```bash
pip install -r python/requirements.txt
```

Key Python packages:
- `faster-whisper` - Speech recognition
- `ollama` - LLM backend
- `yt-dlp` - YouTube download
- `pygame` - Audio playback
- `opencv-python` - Computer vision
- `ultralytics` - YOLO object detection
- `insightface` - Face recognition
- `edge-tts` - Text-to-speech (alternative)

#### System Requirements
- **GPU**: CUDA-capable GPU recommended for AI models
- **FFmpeg**: Required for audio processing
- **Ollama**: Install and run `ollama pull qwen2.5:3b-instruct`

### Building the C++ Component

```bash
# Using CMake
mkdir build
cd build
cmake ..
cmake --build .
```

### Running the System

#### 1. Start the Video/Audio Streaming Server (C++)
```bash
./Trinetra_Vision
```
This will:
- Initialize camera (default: device 0)
- Start video streaming on port 5555
- Start audio streaming on port 5556

#### 2. Start the Python AI Engine
```bash
cd python/engine
python main.py
```

#### 3. (Optional) Start the Receiver for Remote Viewing
```bash
cd python
python reciever.py
```
This will receive and display the video stream with real-time Whisper transcription.

## 💬 Usage Examples

### Voice Commands

**General Conversation:**
- "Hello Sarah"
- "How are you?"
- "What's the weather like?"

**Music Playback:**
- "Play [song name]"
- "Bajao [song name]" (Hindi)
- "Play Alan Walker Faded"

**Face Recognition:**
- "Who is this?"
- "Remember this person"
- "Do you know me?"

**Vision/Object Detection:**
- "What do you see?"
- "Identify this"

**Exit:**
- "Exit"
- "Goodbye"
- "Quit"

## 📁 Project Structure

```
Synapse/
├── CMakeLists.txt          # C++ build configuration
├── vcpkg.json              # C++ dependencies
├── include/                # C++ header files
│   ├── AudioHandler.h
│   ├── CameraHandler.hpp
│   └── NetworkHandler.h
├── src/                    # C++ source files
│   ├── main.cpp
│   ├── AudioHandler.cpp
│   ├── CameraHandler.cpp
│   └── NetworkHandler.cpp
├── python/
│   ├── requirements.txt    # Python dependencies
│   ├── reciever.py         # Video/audio receiver
│   ├── play.py             # Audio playback utility
│   └── engine/             # AI engine components
│       ├── main.py         # Main orchestrator
│       ├── vision_pro.py   # Computer vision
│       ├── stt_engine.py   # Speech-to-text
│       ├── tts_engine.py   # Text-to-speech
│       ├── llm_engine.py   # Language model
│       └── music_engine.py # Music playback
└── test_music.py           # Music engine tests
```

## 🔧 Configuration

### Audio Settings
- **Sample Rate**: 16000 Hz (configured in AudioHandler.cpp)
- **Channels**: Mono
- **Format**: Float32

### Network Ports
- **Video Stream**: TCP port 5555
- **Audio Stream**: TCP port 5556

### AI Models
- **STT Model**: distil-large-v3 (Faster-Whisper)
- **LLM Model**: qwen2.5:3b-instruct (Ollama)
- **Object Detection**: YOLOv8n
- **Face Recognition**: buffalo_l (InsightFace)
- **TTS**: Kokoro ONNX (af_sarah voice)

## 🧪 Testing

Run the music engine test:
```bash
python test_music.py
```

## 🛠️ Technologies Used

### C++
- **OpenCV**: Computer vision and camera handling
- **ZeroMQ**: High-performance networking
- **miniaudio**: Cross-platform audio capture
- **CMake**: Build system

### Python
- **PyTorch**: Deep learning framework
- **Ultralytics YOLO**: Object detection
- **InsightFace**: Face recognition
- **Faster-Whisper**: Speech recognition
- **Ollama**: Local LLM inference
- **yt-dlp**: YouTube integration
- **Pygame**: Audio playback
- **OpenCV**: Video processing

## 📝 Notes

- The project uses Hinglish (Hindi + English) for voice commands
- Face recognition data is stored in SQLite database (`vision_pro.db`)
- Music files are temporarily stored in system temp directory
- GPU acceleration is recommended for optimal performance
- The system is designed for real-time, low-latency operation

## 🤝 Contributing

This is a personal AI assistant project. Feel free to fork and customize for your needs.

## 📄 License

This project is provided as-is for educational and personal use.

## 🔮 Future Enhancements

- Multi-language support
- Advanced emotion detection
- Smart home integration
- Cloud synchronization
- Mobile app companion

---

**Developed by Priyadarshan Garg**
