# AI Software Engineering Agent 🚀

An autonomous, production-grade agentic AI software engineering system built to ingest software repositories, analyze issues, isolate changes, run regression tests, self-heal, and request human-in-the-loop approval before producing pull requests.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    User([User Task / Bug Report]) --> Supervisor[Supervisor Agent<br/>(LangGraph Dynamic Routing)]
    
    subgraph Discovery & Planning
        Supervisor --> RepoAgent[Repository Understanding Agent]
        RepoAgent --> CodeSearch[Code Search Agent<br/>AST + Semantic RAG]
        CodeSearch --> BugAnalysis[Bug Analysis Agent]
        BugAnalysis --> SolutionAgent[Solution Agent<br/>RAG Guidelines]
    end

    subgraph Sandbox Execution & Verification
        SolutionAgent --> SafetyPre[Safety Agent<br/>Pre-execution Check]
        SafetyPre --> CodingAgent[Coding Agent<br/>Isolated Sandbox / Git Branch]
        CodingAgent --> TestAgent[Test Agent<br/>Pytest / Test Gen]
        TestAgent --> Verification[Verification Agent]
        Verification -- "Failure / Regression" --> Supervisor
    end

    subgraph Human in the Loop & Finalization
        Verification -- "Success" --> SafetyFinal[Safety Agent]
        SafetyFinal --> HumanApproval{Human Approval<br/>Diff / Confidence / Tests}
        HumanApproval -- "Approved" --> PR[Git Patch / Pull Request]
        HumanApproval -- "Changes Requested" --> Supervisor
    end
```

---

## 📦 Project Structure

```text
ai-software-engineering-agent/
├── backend/
│   ├── app/
│   │   ├── config/          # Pydantic Settings & environment variables
│   │   ├── models/          # Data schemas (Repo metadata, diffs, tool results)
│   │   ├── tools/           # Repository tools, Git tools, Code tools, Security guards
│   │   ├── utils/           # Logging & utility helpers
│   │   └── llm.py           # Unified LLM client abstraction (OpenAI/Anthropic/Gemini/Ollama)
│   ├── scripts/             # Phase demonstration scripts
│   ├── tests/               # Pytest suite for security, tools, git, and LLM
│   └── requirements.txt     # Python backend dependencies
├── knowledge_base/          # Software engineering, security, and testing guidelines
├── workspace/
│   ├── repositories/        # Target repositories (including demo_fastapi_app fixture)
│   └── sandboxes/           # Ephemeral isolated sandboxes per task
├── .env.example             # Environment configuration template
└── README.md
```

---

## 🛠️ Phase 1 Implementation Summary

Phase 1 establishes the foundational infrastructure and safe repository interaction primitives:

1. **Repository Tools (`tools/repository_tools.py`)**:
   - `list_files()`: Recursive scan with depth bounds and metadata extraction.
   - `read_file()`: Line-numbered safe file inspection.
   - `get_repository_structure()`: ASCII tree visualization.
   - `detect_language()` & `detect_framework()`: Automatic tech stack identification.
   - `get_repository_metadata()`: Comprehensive structured summary for downstream agents.

2. **Security & Path Traversal Guard (`tools/security.py`)**:
   - Prevents path traversal outside the repository root.
   - Blocks access to sensitive patterns (`.env`, `.git/credentials`, `.ssh`, etc.).

3. **Git & Isolated Sandbox Tools (`tools/git_tools.py`)**:
   - `create_isolated_sandbox()`: Copies repositories to dedicated task sandboxes.
   - `get_git_diff()`: Generates unified diffs of all modifications.
   - `get_git_status()`: Tracks staged, unstaged, and untracked changes.

4. **Code Manipulation & AST (`tools/code_tools.py`)**:
   - `create_file()` & `edit_file()`: Safe file operations.
   - `search_code_regex()`: Regex and pattern search across code files.
   - `extract_python_ast_symbols()`: Python AST parsing of functions, classes, and imports.

5. **Unified LLM Interface (`llm.py`)**:
   - LangChain integration with support for OpenAI, Anthropic, Google Gemini, Ollama, and an intelligent offline mock client for testing.

6. **Demo Fixture (`workspace/repositories/demo_fastapi_app`)**:
   - Realistic FastAPI microservice with an intentional missing input validation bug for agent benchmarks.

---

## 🚀 How to Run & Test Phase 1

### 1. Prerequisites
Ensure Python 3.9+ and Git are installed.

```bash
cd /Users/apple/.gemini/antigravity-ide/scratch/ai-software-engineering-agent/backend
```

### 2. Configure Environment (Optional for Mock mode)
```bash
cp ../.env.example ../.env
```

### 3. Run the Unit Tests
```bash
python3 -m pytest tests/ -v
```

### 4. Run the Phase 1 Interactive Demo
```bash
python3 scripts/phase1_demo.py
```

---

## 🧭 Roadmap

- [x] **Phase 1**: Repository tools + basic LLM interaction
- [ ] **Phase 2**: LangGraph Supervisor Agent & dynamic state machine
- [ ] **Phase 3**: Repository understanding + code search agents (Tree-sitter / AST)
- [ ] **Phase 4**: Bug analysis agent with structured root cause evidence
- [ ] **Phase 5**: RAG system (Vector store + guidelines embeddings)
- [ ] **Phase 6**: Coding agent with branch isolation
- [ ] **Phase 7**: Test agent (Pytest execution & test generation)
- [ ] **Phase 8**: Verification agent & self-correction loop
- [ ] **Phase 9**: Safety agent & Human-in-the-loop approval system
- [ ] **Phase 10**: React + Vite UI dashboard
- [ ] **Phase 11**: LangSmith observability & tracing
- [ ] **Phase 12**: Docker containerization & cloud deployment
