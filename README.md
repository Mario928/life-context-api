# Life Context API

> **A searchable memory of everything you say, so AI actually knows your context.**

An open-source pipeline for continuous audio lifelogging that lets you capture, process, and query your spoken life. Record audio continuously, transcribe it, and get context about your entire life, like a personal virtual memory of your life accessible via an API, which we call the 'Memory API'. Everything runs on your own infrastructure, giving you full control and complete data ownership.

## Problem

We lose context constantly. Conversations, ideas, commitments, they disappear unless we manually note them. AI assistants could help analyze our behavior and productivity, but they lack continuous, contextual data about our actual lives. While solutions like Meta glasses and Limitless exist, there's value in an open, customizable pipeline where researchers and developers can experiment with their own data and models.

## Solution

Build your own continuous audio lifelogging system. An open-source pipeline that:
- Records continuous audio using your own hardware
- Processes and transcribes everything automatically
- Extracts tasks, insights, and behavioral patterns
- Provides queryable API access to your life context
- **YOU own your data** - deploy on your own infrastructure

## Architecture

```
Collection → Storage → Preprocessing → Transcription → NLP Processing → API Layer
```

### 1. Collection
- Continuous audio recording (4 body mics)
- 24/7 for 7 days recording period
- GPS location tracking
- Automated chunked upload

### 2. Storage
- Cloud storage (AWS S3 / Google Cloud Storage)
- Chunked upload for reliability
- Raw audio + location data

### 3. Preprocessing
- Noise reduction
- Voice Activity Detection (VAD)
- Speaker diarization (you vs others)
- Audio normalization

### 4. Transcription
- Batch processing pipeline
- Multilingual support
- Timestamped transcripts
- Code-switching handling (e.g., English ↔ Hindi)

### 5. NLP Processing
- Task extraction (commitments you made)
- Entity recognition (people, places, topics)
- Pattern detection (productivity, behavior)

### 6. Integration
- Location correlation (where you were)
- Context tagging (home, work, gym, cafe)
- Timeline indexing
- Cross-validation across data sources

### 7. API Layer
- REST endpoints for data access
- Natural language query interface
- Analytics dashboard
- Search by time, location, or content

## API Endpoints

### 1. Transcript + Context Search
```
GET /api/search?date=2025-10-30
GET /api/search?location=cafe
GET /api/search?date=2025-10-30&location=cafe
GET /api/search?start=2025-10-30&end=2025-11-06
```
Search by date, time, or location. Returns transcripts with where you were and what was happening around you.

### 2. AI Query Interface
```
POST /api/query
{
  "question": "What did I discuss about X?"
}
```
Natural language queries ("What did I discuss about X?"). AI searches through data and generates responses.

### 3. Analytics Dashboard
```
GET /api/analytics?period=week
```
General insights: time tracking, task lists, behavioral patterns, productivity metrics.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Storage** | AWS S3 / Google Cloud Storage |
| **Compute** | AWS EC2 / Google Compute Engine |
| **Database** | PostgreSQL (metadata, transcripts) |
| **Search** | Elasticsearch (full-text search) |
| **Transcription** | OpenAI Whisper / Google Speech-to-Text |
| **NLP** | spaCy, transformers, custom models |
| **API** | FastAPI / Flask |
| **Frontend** | React (analytics dashboard) |

## Data Sources

1. **Continuous Audio** - External body mic or smartphone
2. **GPS Location** - Tracking app for spatial context
3. **Cross-validation** - Correlating audio with location and behavior

## Technical Challenges

**Multilingual Code-Switching** (English ↔ Hindi mid-sentence)

**Noisy Real-World Audio Quality** (cafes, traffic, music)

**Speaker Diarization Accuracy** (you vs others, overlapping speech)

**Battery & Storage Limitations** (continuous drain, device failures)

**Data Loss & Timeline Gaps** (network drops, upload failures)

We won't know actual failure rates until we try. The goal is to identify what breaks and why - that itself is valuable learning.

## Expected Insights

- **Time Tracking**: What did I actually work on today? (actual time spent vs perceived)
- **Commitment Tracking**: What tasks did I promise to do? (promise tracking)
- **Productivity Patterns**: When and where am I most productive?
- **Context Recovery**: Search past conversations
- **Behavioral Analysis**: Procrastination markers, focus patterns

## Privacy & Ethics

- **Consent Required**: Always inform others when recording
- **Speaker Separation**: Diarization to isolate your voice
- **Data Ownership**: You control your data completely
- **Local Processing**: Option to run everything locally
- **Selective Deletion**: Delete any recordings on demand

## Hardware & Privacy Thinking

So we wanted to figure out the hardware situation. The whole point of this project is that anyone can do it with their own setup, we don't want some heavily customized device because that defeats the purpose. People should be able to use what they have or get something cheap.

Started thinking about options. Mobile phone mic is obvious, everyone has one. Could try AirPods too, see how that works. But here's the thing, we need something we can actually wear all day without thinking about it. Can't be holding a phone constantly, that's impractical. And we don't want anything wired or connected to the phone the whole time because that's annoying and we're students, can't afford fancy gear.

What we're probably going with: those small audio recorders. You know, the ones reporters or lecturers use? About 4 inches, fits in your pocket. Quality is decent enough, battery lasts at least a day. Key thing is you forget it's there. If I'm constantly aware I'm recording, the whole thing falls apart. It needs to just sit in my pocket and capture everything naturally.

We'll test different mics, see what works. Worst case, these pocket recorders are like $30-50, which is doable for 4 people. No auto-upload feature, but that's fine - we can manually transfer files in batches at the end of the day. Simple.

Now the privacy part got me thinking. Initially thought maybe we'd mask sensitive stuff - passwords, PINs, whatever. But if we start masking normal conversations, aren't we defeating the purpose? The whole idea is to capture context from regular life.

Then I realized, this is open source. People deploy it for themselves. It's YOUR data, YOUR infrastructure. Like... it's basically a journal, right? People write personal journals all the time. They don't encrypt every other word because someone might read it. It's private by default because it's yours.

The goal isn't to prove what someone said or use recordings against anyone. It's personal memory augmentation for yourself only. You're not building evidence, you're building context for your own AI to understand you better.

So here's what makes sense: we process the audio, extract transcripts, get the insights we need... then delete the raw audio immidiately. Keep the text, keep the analytics, but the actual voice recordings? Gone. Reduces storage costs anyway, and removes the "proof" aspect entirely. This way it really is just for you, searchable memory, not a surveillance system.

It's like writing in a diary versus recording someone without consent. The diary is yours, for your benefit, to remember and reflect. That's what this is. We're not trying to catch anyone saying something or create permanent evidence. We're trying to remember what WE did, what happened in our life and get memory and context for our life.  

This perception was important because when we present it or open source it, people need to understand, this isn't a like a cool surveillance tool. It's a memory/context tool. You wouldn't feel weird about writing "had coffee with Sarah, discussed project deadlines" in your journal. This is the same thing, just more detailed and queryable.

## Project Structure

```
life-context-api/
├── collectors/          # Audio and location collection
├── storage/            # Cloud storage handlers
├── preprocessing/      # Audio cleaning and VAD
├── transcription/      # Speech-to-text pipeline
├── nlp/               # Task extraction and NLP
├── api/               # REST API endpoints
├── analytics/         # Insights and patterns
├── dashboard/         # Web interface
├── scripts/           # Setup and utilities
└── tests/             # Test suite
```

## Contributing

This is an open-source project! We welcome contributions from the community.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

 
## License

MIT License - See [LICENSE](LICENSE) file for details

## Team

Built by a passion about personal data ownership and AI-augmented memory.

---

**Remember**: Your memory, your data, your control.
