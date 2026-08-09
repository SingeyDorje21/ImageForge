# IMAGEFLOW ⚡

![Architecture Banner](https://img.shields.io/badge/Architecture-Distributed_System-blue?style=for-the-badge) ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi) ![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB) ![RabbitMQ](https://img.shields.io/badge/Rabbitmq-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

**ImageFlow** (formerly ImageForge) is a high-performance, asynchronous, distributed image processing pipeline. Built with a neo-brutalist dark aesthetic, the system is designed to offload heavy image manipulations (resizing, format conversion) to a fleet of backend workers without blocking the main API thread.

---

## 🏗️ Architecture & Workflow

At its core, ImageFlow embraces a highly decoupled microservices architecture:

1. **The Client (React SPA)**: End-users upload images and processing instructions (e.g., "convert to WebP", "resize to 800x600") via a stunning, responsive landing page.
2. **API Hub (FastAPI)**: The central gateway. It intercepts uploads, enforces rate-limiting via **Redis**, saves the original file to disk, logs a `pending` job in **PostgreSQL**, and publishes the `job_id` to a message queue.
3. **Message Queue (RabbitMQ)**: Acts as the robust buffer. It guarantees message delivery and handles Dead Letter Queues (DLQ) for failed jobs.
4. **Worker Nodes (Python Async)**: Dedicated headless processors subscribe to the RabbitMQ queue. They pull the original image, perform the heavy CPU-bound image operations using **Pillow**, save the result, and update the PostgreSQL database state to `completed`.
5. **Real-time Sync**: The frontend continuously polls the API to visually represent the processing timeline and dynamically unlocks a download link the moment the worker node finishes the job.

### System Diagram

![alt text](<Screenshot 2026-08-09 140220.png>)

---

## 🛠️ Technology Stack

### Frontend (Client Tier)
- **Vite + React**: Blazing fast modern frontend build tool and UI library.
- **Tailwind CSS**: Utility-first CSS framework used to build the responsive, neo-brutalist UI.
- **Chart.js**: For visualizing system metrics and queue health in the Admin Portal.
- **Lucide React**: Crisp, modern SVG icon library.

### Backend (API Tier)
- **FastAPI**: Modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
- **Uvicorn**: Lightning-fast ASGI server implementation.
- **SQLAlchemy (Async)**: Python SQL toolkit and Object Relational Mapper for database interactions.

### Infrastructure & Data Tier
- **RabbitMQ**: AMQP-based message broker for reliable task distribution.
- **PostgreSQL**: Relational database for persistent job tracking and state management.
- **Redis**: In-memory data structure store used for API rate-limiting (10 uploads/min) and global system metrics caching.
- **Docker Compose**: Container orchestration to instantly spin up the infrastructure layer.

---

## 🚀 How to Run Locally

Follow these steps to launch the entire distributed architecture on your own machine.

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/) (Must be running on your system)
- [Python 3.10+](https://www.python.org/)
- [Node.js & npm](https://nodejs.org/)

### 1. Start the Infrastructure (Docker)
First, spin up PostgreSQL, Redis, and RabbitMQ using Docker Compose.

```bash
# From the project root directory
docker-compose up -d
```
> Wait a few seconds for the database and broker to initialize and report healthy.

### 2. Launch the API & Worker (Backend)
Open a terminal, navigate to the `backend` folder, and run the FastAPI server and the background worker.

```bash
cd backend

# Create a virtual environment and install dependencies
python -m venv venv
.\venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt

# Start the FastAPI Server (Port 8000)
uvicorn api.main:app --reload --port 8000
```

Open a **new terminal** for the worker:
```bash
cd backend
.\venv\Scripts\activate
# Start the asynchronous worker node
python -m worker.main
```

### 3. Launch the Client (Frontend)
Open a **third terminal**, navigate to the `frontend` folder, and start the React app.

```bash
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

### 4. Access the System
- **Public Landing Page**: Navigate to `http://localhost:5173/` to upload tasks and view the animated architecture pipeline.
- **Admin Portal**: Navigate to `http://localhost:5173/login` (Password: `imageforge_admin_123`) to view real-time metrics and manage the queue.
- **API Documentation**: Navigate to `http://localhost:8000/docs` to interact with the auto-generated Swagger UI.

---
*Developed as a showcase for high-performance, asynchronous system design.*
