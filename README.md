# InfiniteQ Planning Harness

An AI-powered project planning system that transforms rough ideas into detailed, actionable plans through an intelligent multi-model interview process.

## Overview

InfiniteQ uses multiple Vultr Serverless Inference models to conduct an adaptive interview that progressively refines a project concept into a comprehensive specification. The system maintains a compact plan state and tracks coverage across key dimensions (problem, users, features, architecture, etc.), ensuring thorough exploration without context overflow.

### Key Features

- **Multi-Model Interview**: Leverages multiple LLMs (reasoning, coding, strategy, synthesis) to ask better questions
- **Infinite Questioning**: Maintains compact state to enable endless refinement without context limits
- **Coverage-Driven**: Automatically identifies and explores weak areas in your plan
- **Output for AI Agents**: Generates both JSON and Markdown formats ready for Cursor, ClaudeCode, Windsurf, etc.
- **Real-time Progress**: Visual coverage tracking shows planning completeness

## Architecture

### Backend (Python + FastAPI)

- **Session Manager**: Handles interview lifecycle and state persistence
- **Model Registry**: Discovers and categorizes Vultr models by capability
- **Question Engine**: Parallel multi-model question generation
- **Plan Reducer**: Incrementally updates plan state based on answers
- **Plan Synthesizer**: Generates final build-ready specifications

### Frontend (React + TypeScript + Vite)

- Clean, responsive UI for the interview process
- Real-time coverage visualization
- Multiple-choice questions with "Other" option
- Final plan display with copy/download capabilities

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Vultr Serverless Inference API Key** ([Get one here](https://www.vultr.com/))

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd InfiniteQ
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your VULTR_INFERENCE_API_KEY

# Run the server
python -m app.main
```

The backend will start on `http://localhost:8000`

### 3. Frontend Setup

In a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# (Optional) Configure API URL
cp .env.example .env

# Run the development server
npm run dev
```

The frontend will start on `http://localhost:3000`

### 4. Use the Application

1. Open `http://localhost:3000` in your browser
2. Enter your project idea (e.g., "A web app for NYC landlords to manage receiverships")
3. Answer the multiple-choice questions
4. Hit "Continue" to get more questions or "Finish" to generate your plan
5. Copy the plan and paste into your AI coding assistant!

## API Endpoints

### POST `/api/v1/session`

Create a new planning session.

**Request:**
```json
{
  "idea": "Your project idea",
  "mode": "software" | "story" | "process" | "other"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "first_questions": [...],
  "coverage": {...}
}
```

### POST `/api/v1/session/{id}/answer`

Submit answers and get next questions.

**Request:**
```json
{
  "answers": [
    {
      "question_id": "Q_001",
      "choice_id": "A",
      "free_text": "optional additional context"
    }
  ]
}
```

**Response:**
```json
{
  "next_questions": [...],
  "coverage": {...},
  "plan_preview": {...}
}
```

### POST `/api/v1/session/{id}/finish`

Finish the session and generate final plan.

**Response:**
```json
{
  "json_plan": {...},
  "markdown_brief": "# Project Plan\n..."
}
```

### GET `/api/v1/session/{id}/status`

Get session status and metadata.

## Configuration

### Backend Environment Variables

Create `backend/.env`:

```env
# Required
VULTR_INFERENCE_API_KEY=your_api_key_here

# Optional
PORT=8000
LOG_LEVEL=INFO
```

### Frontend Environment Variables

Create `frontend/.env`:

```env
# Optional - defaults to /api/v1 (uses Vite proxy)
VITE_API_URL=http://localhost:8000/api/v1
```

## Model Selection Strategy

InfiniteQ automatically discovers available Vultr models and categorizes them:

- **Reasoning**: Models like `deepseek-r1-distill-qwen-32b` for deep analysis
- **Code/Tech**: Models like `qwen2.5-coder-32b-instruct` for technical questions
- **Synthesis**: Large models like `llama-3.3-70b-instruct-fp8` for final synthesis
- **Strategy**: Models like `kimi-k2-instruct` for high-level planning

The system rotates through models across interview rounds to leverage diverse perspectives.

## Coverage Dimensions

The system tracks coverage across 8 dimensions:

1. **Problem**: What are we solving and why?
2. **Users**: Who will use this and in what context?
3. **Constraints**: Time, budget, technical, compliance limits
4. **Features**: What functionality is needed?
5. **Architecture**: How should it be built?
6. **Operations**: Deployment, monitoring, maintenance
7. **Risks**: What could go wrong and how to mitigate?
8. **Deliverables**: What should the AI agent build?

Questions automatically target the lowest-coverage areas to ensure comprehensive planning.

## Development

### Backend Development

```bash
cd backend
source venv/bin/activate

# Run with auto-reload
uvicorn app.main:app --reload --port 8000

# Run tests (when available)
pytest tests/
```

### Frontend Development

```bash
cd frontend

# Development server with hot reload
npm run dev

# Type checking
npm run build

# Linting
npm run lint
```

## Project Structure

```
InfiniteQ/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py          # FastAPI endpoints
│   │   ├── models/
│   │   │   └── schema.py          # Pydantic models
│   │   ├── services/
│   │   │   ├── vultr_client.py    # Vultr API wrapper
│   │   │   ├── model_registry.py  # Model discovery & selection
│   │   │   ├── session_manager.py # Session lifecycle
│   │   │   ├── question_engine.py # Question generation
│   │   │   ├── plan_reducer.py    # State updates
│   │   │   └── plan_synthesizer.py # Final plan generation
│   │   ├── prompts/
│   │   │   └── templates.py       # LLM prompts
│   │   └── main.py                # FastAPI app
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── IdeaInput.tsx      # Initial idea form
│   │   │   ├── QuestionCard.tsx   # MC question display
│   │   │   ├── CoverageDisplay.tsx # Coverage bars
│   │   │   ├── InterviewSession.tsx # Main interview flow
│   │   │   └── FinalPlan.tsx      # Results display
│   │   ├── services/
│   │   │   └── api.ts             # Backend API client
│   │   ├── types/
│   │   │   └── index.ts           # TypeScript types
│   │   ├── App.tsx                # Main app component
│   │   ├── App.css                # Styles
│   │   └── main.tsx               # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
└── README.md
```

## How It Works

### 1. Idea Normalization

When you submit an idea, the system uses a strategy model to extract:
- Normalized summary
- Project type (software, story, process, etc.)
- Key entities mentioned
- Initial scope hints

### 2. Question Generation

For each round:
1. Select 2-4 models based on round number and coverage gaps
2. Each model proposes 2-4 questions in parallel
3. An aggregator model deduplicates and selects the best questions
4. Questions target the lowest-coverage dimensions

### 3. Plan Updates

After each answer:
1. A reasoning model updates the canonical JSON plan
2. Coverage scores increase for addressed dimensions
3. The system stores a compact Q&A history (last 20 pairs)

### 4. Synthesis

On "Finish":
1. A large synthesis model (70B+) processes the final plan state
2. Generates two outputs:
   - **JSON Plan**: Structured data with all details
   - **Markdown Brief**: Human-readable spec for AI agents
3. Both are ready to paste into Cursor, ClaudeCode, etc.

## Use Cases

### Software Projects
- Web applications
- Mobile apps
- CLI tools
- APIs and microservices
- Data pipelines

### Other Project Types
- Story/narrative development
- Process documentation
- Research planning
- Content strategy
- Workflow automation

## Tips for Best Results

1. **Be Specific**: Start with concrete details rather than vague ideas
2. **Use "Other"**: Don't hesitate to provide custom answers when options don't fit
3. **Go Deep**: More rounds = more comprehensive plans (the system won't run out of memory)
4. **Finish Anytime**: You can generate a plan at any point; it will work with what it has
5. **Iterate**: Run multiple sessions to explore different approaches

## Troubleshooting

### Backend won't start
- Verify your `VULTR_INFERENCE_API_KEY` is set in `.env`
- Check that port 8000 is available
- Ensure Python 3.9+ is installed

### Frontend can't connect to backend
- Verify backend is running on port 8000
- Check Vite proxy configuration in `vite.config.ts`
- Try setting `VITE_API_URL` explicitly in `.env`

### Models not discovered
- Check your Vultr API key has access to Serverless Inference
- Review backend logs for API errors
- System will fall back to hardcoded models if discovery fails

### Questions seem repetitive
- This can happen if coverage isn't updating properly
- Check that answers are being submitted correctly
- Review plan state in `/session/{id}/status` endpoint

## Future Enhancements

- [ ] Redis/PostgreSQL persistence for session recovery
- [ ] WebSocket support for real-time updates
- [ ] Team collaboration features
- [ ] Plan comparison and versioning
- [ ] Export to project management tools
- [ ] Custom question templates
- [ ] Fine-tuned models for specific domains

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

Built with ❤️ using Vultr Serverless Inference, FastAPI, and React
