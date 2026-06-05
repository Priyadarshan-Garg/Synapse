
# SYNAPSE: Distributed Edge-Cloud AI Assistant Architecture
**Powering *Naina* | Built from Scratch with Linux Environments**

<div align="center">
  <img src="https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black" />
  <img src="https://img.shields.io/badge/GNU%20Bash-4EAA25?style=for-the-badge&logo=GNU%20Bash&logoColor=white" />
  <img src="https://img.shields.io/badge/Raspberry%20Pi-A22846?style=for-the-badge&logo=Raspberry%20Pi&logoColor=white" />
  <img src="https://img.shields.io/badge/ZeroMQ-DF0000?style=for-the-badge&logo=ZeroMQ&logoColor=white" />
  <img src="https://img.shields.io/badge/NVIDIA-76B900?style=for-the-badge&logo=nvidia&logoColor=white" />
  <img src="https://img.shields.io/badge/CUDA-76B900?style=for-the-badge&logo=nvidia&logoColor=white" />
</div>

<br>

Synapse is the robust, multi-threaded distributed architecture built from scratch to power **Naina**, a highly dynamic personal AI assistant. 

Unlike standard API wrappers, Synapse solves the heavy-compute problem of modern LLMs and vision models by splitting the workload: a **Raspberry Pi 3** acts as the sensory edge device (mouth, eyes and ears) written purely in raw poer (C++), while a powerful **Local PC** acts as the brain (inference server) fully leveraging **NVIDIA CUDA** for parallel GPU computing.


<img src="https://cdn.pixabay.com/photo/2024/04/08/19/56/neural-network-8684318_1280.jpg">


## Demo Video 

 [![Watch Synapse Demo](https://img.youtube.com/vi/U6jmOxHk3mE/maxresdefault.jpg)](https://www.youtube.com/watch?v=U6jmOxHk3mE)
 

## High Level Design 

<img src="assets/synapse-hld-nodes-based.png" width="100%">

## Low Level Design Of Server

<img src="assets/lld-synapse.svg" width="100%">

## Minimum System Requirements

Before you try to clone and run it locally, let me be clear this project needs minimum these specifications to run on your local machine
* Minimum 8 GB VRam 3060 GPU, preferably 4060
* 16 GB Ram
* i7 CPU of 12th Gen or later. Google it's an equivalent for AMD
* Please download cuda to run it. I'll upload a full procedure **How To SETUP** in future. 

## Key Capabilities

* **Real-Time Edge Perception:** RPi 3 directly captures video (V2 Camera) and audio, applies raw OpenCV MPEG compression, and streams it over LAN with nearly zero latency.
* **CUDA-Accelerated Conversational AI:** Heavy lifting is done entirely on the GPU. Powered by OpenAI's **Whisper** (distil-large-v3) for real-time transcription and **Ollama (Qwen 2.5 - 3B)** for insanely fast, context-aware, and chatty responses.
* **Dynamic Action Execution:** Naina doesn't just talk; she acts. Ask for the current weather, and she dynamically fetches the real-time API data to tell you if you need a jacket.
* **Long-Term RAG Memory:** "Remember Ankit, he is a DSA legend." Synapse embeds and stores user-defined facts in **ChromaDB**. Ask about Ankit weeks later, and Naina will instantly recall.
* **Hardcoded Facial Recognition:** Utilizes **InsightFace** to scan incoming frames and match them against a pre-indexed directory of labeled images, identifying exactly who is standing in front of the camera.
* **Human-like Voice:** Text responses are synthesized through **Kokoro TTS** and streamed back to the RPi speaker for a seamless conversational loop.

## System Architecture

The system is strictly divided into two independent nodes communicating over a Local Area Network (LAN). 

### 1. The Edge Node (Raspberry Pi 3)
* **Environment:** Bare-metal execution.
* **Tech Stack:** Pure C++, OpenCV, SDL2, Miniaudio, ZeroMQ.
* **Function:** Captures raw video frames (V2 Camera) and audio. To prevent the RPi from choking, it applies real-time OpenCV MPEG compression in C++ before transmitting the data over the network.

### 2. The Core Server (Local Machine / GPU Node)
* **Environment:** Linux-native daemon processes.
* **Tech Stack:** Python, ZeroMQ, cuDNN (12.3), OpenAI Whisper (distil-large-v3), Ollama (Qwen 2.5 - 3B), Kokoro TTS, InsightFace, ChromaDB.
* **Function:** A multi-threaded Python backend that accepts the socket stream asynchronously. It handles word detection, pushes audio and vision tasks to the GPU for inference, generates RAG-backed responses, synthesizes speech, and streams the audio back to the Rpi.

### Network & Shell Orchestration
* **ZeroMQ (ZMQ):** Used for asynchronous, high-throughput, low-latency Inter-Process Communication (IPC) and network socket streaming between the C++ client and Python server.
* **Bash/Shell Scripting:** The entire startup sequence, network binding, environment variable management, and process daemonization on both the RPi and the server are heavily automated using pipelines of processing.


## The Developer Diaries: Building Synapse

Building this wasn't a walk in the park. Bridging low-level C++ with modern Python AI stacks is an absolute bloodbath. 

*We will be documenting this entire engineering journey as a multi-part "Web Series" style Devlog on Medium. (Links dropping soon).*

* **Episode 1: The Edge Struggle.** Why we chose pure C++ for the Pi, fighting with SDL2/Miniaudio, and writing custom OpenCV MPEG compression to kill latency.
* **Episode 2: Networking Hell.** Tying the Pi and PC together. Why standard HTTP failed and how ZeroMQ + pipelining saved the day.
* **Episode 3: The GPU Brain Transplant.** Managing VRAM limits and tuning the Whisper -> Qwen 2.5 -> Kokoro TTS pipeline for sub-second conversational speeds using CUDA.
* **Episode 4: Memory & Vision.** The transition from a tedious dynamic face-saving approach to a rock-solid hardcoded InsightFace directory, and plugging in ChromaDB for permanent memory.

## System Performance & Telemetry (Local Inference)

Synapse is built with a heavy focus on **Low-Latency Edge-to-Core Architecture**. All AI models (STT, LLM, TTS, Vision) run locally on the core PC, ensuring 100% data privacy without relying on cloud APIs.

Here is the micro-profiling breakdown of a standard voice interaction loop.

### 1. Software Processing Pipeline
*Metrics collected via `time.perf_counter()` on the core processing server.*

| Sub-System | Technology Stack | Average Latency | Notes |
| :--- | :--- | :--- | :--- |
| **Speech-to-Text (STT)** | Faster-Whisper (CUDA) | **~700 - 1000 ms** | Variable based on sentence length. |
| **Agentic Brain (LLM)** | Local LLM Engine | **~500 - 2500 ms** | ~500ms for direct Q&A; up to 2.5s for complex DB searches. |
| **Text-to-Speech (TTS)** | Kokoro ONNX (CPU) | **~600 - 900 ms** | Time to First Byte (TTFB) using audio streaming. |

### 2. End-to-End Acoustic Latency (Real-World)
While software processing is highly optimized, real-world physical latency includes hardware and network propagation. 

* **Total Physical Turnaround Time: ~4.5 to 5.0 Seconds**
*(Measured from the moment the user stops speaking to the first audio output from the Raspberry Pi speaker).*

**Where does the extra time go?**
- **VAD Pause Threshold:** ~0.5s - 0.8s (Mic waits to ensure the user has completely finished speaking).
- **Network Routing:** ~0.1s (TCP socket transmission between Raspberry Pi and Core PC).
- **Hardware Buffering:** ~0.2s (ALSA sound card and Pygame audio buffer initialization).

### 3. Token/sec generated form LLM
* By the internal clock counter of LLM we derived the tokens generated per second are around 105. Here is the log reference.

<img src="assets/token_per_min.png">

* As we know, **1 English Word =~ 3.1 tokens**. So it makes **~80 words** per second.

### Architectural Highlights
* **Perceived Latency Optimization:** To prevent users from waiting for the full LLM response to generate, the TTS engine uses **Sentence-by-Sentence Chunking**. As soon as the LLM generates the first sentence (~390ms), the TTS begins streaming the audio. The rest of the LLM generation happens asynchronously in the background.
* **Fallback Mechanism:** The Agentic framework dynamically measures vector-search distances. If a database match is too weak (`Distance > 1.5`), it smoothly falls back to its base General Knowledge seamlessly without crashing.

---
**Proof of Execution (Telemetry Logs):**

<img src="assets/performance-metrics.jpeg">

## Resources Usage
* **GPU** <img src="assets/gpu.png">

* **CPU**

<img src="assets/cpu.png">

## 🛣️ Roadmap

- [x] Publish comprehensive latency and resource utilization metrics (RPi CPU vs. PC GPU/VRAM).
- [x] Intensively documenting every file.
- [x] Make a script/bat file for running as background service.

---
*Built with grit, C++, python and lots of tea ☕.*