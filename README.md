# DuCO-Agent: Dual Coverage AI Orchestrator

DuCO-Agent is an enterprise-grade Agentic AI application built for HCL assessments. The system orchestrates multiple specialist AI agents using the Google ADK and Gemini to parse complex medical documents (PDFs, images, text), perform Coordination of Benefits (COB) reasoning for dual insurance coverage, calculate out-of-pocket expenses, and generate insurer pre-authorization letters alongside cost flow visualizations and audio summaries.

## Repository Architecture

This project is structured as a monorepo containing a React frontend and a Python FastAPI backend orchestrating the agent workflows.

```text
duco-agent-ai-assessment/
│
├── frontend/               # React (TypeScript) + Vite Web Application
│   ├── src/                # Frontend application source code
│   ├── public/             # Static assets
│   ├── package.json        # Frontend dependencies and npm scripts
│   ├── vite.config.ts      # Vite build configuration
│   └── tsconfig.json       # TypeScript configuration
│
├── backend/                # Python FastAPI + Google ADK Orchestrator
│   ├── app/                # FastAPI web server and route controllers
│   ├── agents/             # Specialist AI agents (Intake, Medical Coding, COB, etc.)
│   ├── tools/              # Integrations & Utilities (OCR, CPT Lookup, Cost Calculator, etc.)
│   ├── workflows/          # Orchestration runs and coordination patterns
│   ├── services/           # Backend middleware and system integrations
│   ├── models/             # Data schemas (Pydantic / type-safe representations)
│   ├── mock_data/          # Mock insurance policies and sample data
│   ├── outputs/            # Generated outputs (letters, diagrams, audio files)
│   ├── tests/              # Unit and integration test suites
│   └── requirements.txt    # Python dependencies
│
├── docs/                   # Architectural decisions, schemas, and design documents
│
├── .gitignore              # Global workspace ignore configurations
└── README.md               # Main workspace entry documentation
```

## Getting Started

### Prerequisites
*   Node.js (v18+)
*   Python (v3.10+)

### Frontend Setup
To run the React application:
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

### Backend Setup (Upcoming)
Backend instructions will be provided upon FastAPI and dependency initialization.
