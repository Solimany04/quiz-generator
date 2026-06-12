# Architecture Plan: Distributed Telegram AI Quiz Backend (BYOC & Local Compute)

## 1. System Overview & Objectives

The goal of this project is to architect a robust, asynchronous Django backend that orchestrates AI quiz generation. Moving beyond a single central GPU bottleneck, this architecture introduces a **Distributed "Bring Your Own Compute" (BYOC) Framework**.

This allows users to link their own local hardware (running LM Studio/Ollama) to the central Django server. Additionally, the system provides dynamic model management directly from the Django Admin panel.

### Core Stack & Paradigm

- **Web Framework:** Django 5.x + Django REST Framework (DRF)
    
- **Database:** PostgreSQL (Relational persistence of quiz runs, nodes, and metrics)
    
- **Message Broker:** Redis + Celery (Routing tasks between central servers and distributed nodes)
    
- **LLM Integration:** Agnostic API endpoints (OpenAI-compatible) targeting either central host GPUs or User-owned distributed nodes.
    

## 2. Distributed Infrastructure & Hardware Coordination

The architecture is split into Centralized API routing and Distributed AI processing. If a user has linked their own local node, their Telegram requests are routed to their personal hardware, saving central server costs.

```
                  ┌────────────────────────────────────────────────────────┐
                  │                   CENTRAL DJANGO CLOUD                 │
Telegram Webhook ─┼─► [ Django Web API ] ────► [ Redis / Celery Router ]   │
                  │        │        ▲                    │                 │
                  │        ▼        │                    ▼                 │
                  │   [ PostgreSQL DB ]        [ Central Celery Worker ]   │
                  └──────────────────────────────────────┼─────────────────┘
                                                         │ (Fallback / Premium)
                                                         ▼
                                                [ Central LM Studio ]

                        === DISTRIBUTED USER HARDWARE (BYOC) ===

                  ┌─────────────────────┐      ┌─────────────────────────┐
[ User PC ]       │ Lightweight Client  │ ◄──► │ User's Local LM Studio  │
[ User API Key] ──┤ (Polls Django API)  │      │ (Port 1234)             │
                  └─────────────────────┘      └─────────────────────────┘
```

### 2.1 The "Bring Your Own Compute" (BYOC) Client Node

To allow users to compute on their own devices:

- The backend exposes a set of REST endpoints specifically for **Worker Nodes** (`/api/v1/worker/tasks/`).
    
- The user downloads a lightweight companion script/client (e.g., a compiled Python CLI or an Electron app).
    
- The user inputs their unique `Node API Key` (generated via Telegram Bot).
    
- The client polls the Django server for pending tasks assigned to that specific user, processes the text against their local LM Studio instance, and POSTs the structured JSON back to Django.
    

### 2.2 Task Routing Logic

- **Central Compute Queue:** Used for users who do not have a local node connected (can be rate-limited or restricted to premium users).
    
- **Distributed Node Queue:** When a request comes in, the router checks if the user has an active heartbeat from a local Node. If yes, the task is flagged for `LOCAL_PULL` and sits in the database until the user's local client fetches it.
    

## 3. Data Modeling (Django ORM)

_(No code implementation, conceptual schemas for the coding agent to build)_

### `users.TelegramUser`

- Basic fields: `telegram_id`, `username`, `first_name`
    
- `is_premium`: Determines if they can use the Central GPU.
    

### `compute.UserComputeNode` (New)

- `user`: Relates to `TelegramUser`.
    
- `api_key`: Secure token for the user's local client to authenticate.
    
- `last_heartbeat`: Timestamp. If within the last 5 minutes, Django routes tasks to the user's local hardware instead of the central queue.
    
- `total_processed_tasks`: Gamification/tracking metric.
    

### `quizzes.QuizRequest` & `quizzes.GeneratedQuiz`

- Tracks `status` (`PENDING`, `DISPATCHED_TO_NODE`, `COMPLETED`, `FAILED`).
    
- Tracks `processed_by`: Indicates if it was processed by `CENTRAL_GPU` or `USER_NODE`.
    

### `llm.ModelRegistry` (Dynamic Admin Model)

- Designed to sync with LM Studio/Ollama's API.
    
- `model_identifier`: e.g., `google/gemma-4-e2b`.
    
- `is_downloaded`: Boolean.
    
- `file_size`: Metadata for admin visibility.
    
- `is_active_default`: Boolean. The fallback model for central compute.
    

## 4. Logical Execution Flow (Asynchronous Pipeline)

### Step 1: Webhook Ingestion

1. Telegram sends a message to the Django Webhook.
    
2. Django identifies the `TelegramUser`.
    
3. Django checks the `UserComputeNode` table. If the user has a node with a recent `last_heartbeat`, the task status is set to `WAITING_FOR_NODE`.
    
4. If no node exists, task is sent to the Central Celery Queue.
    
5. Django returns `200 OK` to Telegram instantly.
    

### Step 2: Processing Phase

**Scenario A: Central Compute (Celery)**

1. Celery worker picks up the task, chunks the text, queries the Central LM Studio via `httpx`.
    
2. JSON is validated and saved to the DB.
    

**Scenario B: User Compute (BYOC Polling)**

1. User's local client calls `GET /api/v1/worker/tasks/`.
    
2. Django locks the task and returns the raw text.
    
3. User's local PC processes the heavy LLM inference completely offline.
    
4. User's local client calls `POST /api/v1/worker/tasks/{id}/complete` with the JSON payload.
    
5. Django validates the incoming JSON and saves it to the DB.
    

### Step 3: Outgoing Telegram Dispatcher

1. Once marked `COMPLETED` (by either Celery or User Node), an IO-focused Celery worker triggers.
    
2. It applies strict rate-limiting (e.g., 20 messages/min) to avoid Telegram 429 errors.
    
3. Formats the JSON into Telegram `sendPoll` requests and dispatches them.
    

## 5. Advanced Admin Panel Features (Model Management)

The coding agent must implement custom Django Admin interfaces to handle dynamic LLM orchestration without backend code changes.

### 5.1 Dynamic Model Selection (Admin Dropdown)

- **Goal:** Instead of typing model IDs manually, the Admin UI provides a dropdown of available models.
    
- **Mechanism:** When the Admin page for `ModelRegistry` or `Settings` loads, Django makes an inline API call to the Central LM Studio (`GET /v1/models`). It populates a Choice/Dropdown field dynamically based on the actual models loaded in the local directory.
    

### 5.2 Admin-Triggered Model Downloads

- **Goal:** Allow admins to pull new models directly from HuggingFace/Ollama via the Django Admin panel.
    
- **Mechanism:** Add a custom Admin Action or Form button ("Download New Model").
    
- When submitted, Django dispatches an asynchronous Celery task that hits the LM Studio/Ollama API endpoint responsible for model pulling.
    
- The admin panel should display a status indicator (e.g., "Downloading mistral:latest... 45%") tracking the progress, potentially using WebSockets or simple meta-refresh polling for the admin UI.
    

### 5.3 Node Dashboard

- Provide admins a view of all connected `UserComputeNodes`.
    
- Visualize metrics: How much compute (in tokens/tasks) is being offloaded to user hardware vs. central server hardware.