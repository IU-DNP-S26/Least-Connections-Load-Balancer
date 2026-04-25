# Least Connections Load Balancer System

## About

This project demonstrates a **Least-Connections Load Balancing system** implemented for the *Distributed and Network Programming* course (Innopolis University, S26).

The system simulates a real-world distributed architecture consisting of:
- multiple backend services (`converter1`, `converter2`, `converter3`)
- a custom **reverse proxy (load balancer)** using the *least-connections* strategy
- monitoring stack with **Prometheus + Grafana**

The backend service is a CPU-intensive Markdown-to-PDF converter (**Konvertik**), which is used to simulate long-running requests and observe load distribution effects.

---

## Tech Stack

- Docker & Docker Compose
- Custom HTTP Reverse Proxy (Least-Connections Load Balancer)
- Markdown-to-PDF converter service (Konvertik backend)
- Prometheus (metrics collection)
- Grafana (visualization & dashboards)

---

## Architecture

- **Reverse Proxy (8080)** → entry point, distributes requests
- **Backend Services**
  - converter1 → `8081`
  - converter2 → `8082`
  - converter3 → `8083`
- **Prometheus** → `9090`
- **Grafana** → `3000`

All services are connected via:
```bash
proxy-network (Docker bridge network)
```

---

## How to Run

### 1. Clone repository

```bash
git clone https://github.com/IU-DNP-S26/Least-Connections-Load-Balancer.git
cd Least-Connections-Load-Balancer
```

### 2. Start system

```bash
docker compose up --build
```

This will start:

* Reverse Proxy → [http://localhost:8080](http://localhost:8080)
* Backend instances → 8081 / 8082 / 8083
* Prometheus → [http://localhost:9090](http://localhost:9090)
* Grafana → [http://localhost:3000](http://localhost:3000)

---

## API Usage

### Convert Markdown to PDF (via Load Balancer)

```bash
cd /directory/with/markdown/file
zip test.zip -r .
```

```bash
curl -X POST http://127.0.0.1:8080/convert/md/to-pdf \
  -F "archive=@test.zip" \
  --output result.pdf
```

Request will be routed by **least-connections load balancer** to one of the backend instances.

---

### Direct Backend Access (for testing)

```bash
curl -X POST http://127.0.0.1:8081/convert/md/to-pdf -F "archive=@test.zip" --output result.pdf
curl -X POST http://127.0.0.1:8082/convert/md/to-pdf -F "archive=@test.zip" --output result.pdf
curl -X POST http://127.0.0.1:8083/convert/md/to-pdf -F "archive=@test.zip" --output result.pdf
```

---

## Backend Service (Konvertik)

Each backend instance provides:

* REST API for Markdown-to-PDF conversion
* Web frontend interface for manual conversion and testing
* accepts ZIP archive with Markdown files
* processes CPU-intensive PDF generation
* returns generated PDF

Frontend is available directly via each backend container port (`8081–8083`).

---

## Monitoring

### Prometheus

UI:
[http://localhost:9090](http://localhost:9090)

Used for:

* scraping reverse proxy metrics
* observing request distribution

---

### Grafana

UI:
[http://localhost:3000](http://localhost:3000)

Login:

* username: admin
* password: admin

Used for:

* request rate visualization
* backend load comparison
* latency tracking

---

## Reverse Proxy Endpoint

Main entry point:
[http://localhost:8080](http://localhost:8080)

Optional health check (if implemented):

```http
GET /health
```

---

## Volumes

Persistent storage:

* `prometheus-data` → Prometheus time-series DB
* `grafana-data` → Grafana dashboards & state

---

## Notes

This project demonstrates:

* implementation of **least-connections scheduling algorithm**
* load balancing in HTTP-based distributed systems
* performance behavior under concurrent load
* observability using Prometheus + Grafana
* hybrid system with both **API + frontend backend interface**