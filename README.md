# Multi Vendor Fetch Service

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   RabbitMQ      │    │   Worker Pool   │
│                 │    │                 │    │                 │
│ • REST API      │───▶│ • Job Queue     │───▶│ • Job Processing│
│ • Webhook       │    │ • Message Broker│    │ • Vendor Calls  │
│ • Health Check  │    │                 │    │ • Retry Logic   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         ▼                                              ▼
┌─────────────────┐                          ┌─────────────────┐
│    MongoDB      │                          │  Mock Vendors   │
│                 │                          │                 │
│ • Job State     │                          │ • Sync Vendor   │
│ • Results       │                          │ • Async Vendor  │
│ • Metadata      │                          │ • Test Endpoints│
└─────────────────┘                          └─────────────────┘
```

## Quick Start

### Prerequisites

- docker and docker compose
- k6 installed for load testing

### Using Docker (Recommended)

1. **Clone the repository**

   ```bash
   git clone https://github.com/mshra/Multi-Vendor-Service
   cd Multi-Vendor-Service
   ```

2. **Start all services**

   ```bash
   docker-compose up --build
   ```

3. **Verify the setup**

   ```bash
   curl http://localhost:8000/health
   ```

4. **For running load test**

```bash
k6 run loadtest.js
```

## Job Lifecycle

1. **Creation**: Job submitted via API
2. **Queuing**: Job added to RabbitMQ queue
3. **Processing**: Worker picks up job
4. **Vendor Call**: Request sent to appropriate vendor
5. **Completion**:
   - Sync: Immediate result storage
   - Async: Webhook updates status
6. **Retrieval**: Client polls for results

## Error Handling

The service handles various error scenarios:

- **Validation Errors**: Invalid request data (400)
- **Not Found**: Non-existent job IDs (404)
- **Vendor Errors**: Vendor unavailable/timeout (500)
- **Rate Limiting**: Too many requests (429)
- **Internal Errors**: Internal Server Error(500)

## Monitoring

### Database Monitoring

Access MongoDB Express at: `http://localhost:8081`

### Queue Monitoring

Access RabbitMQ Management at: `http://localhost:15672`

- Username: `guest`
- Password: `guest`
