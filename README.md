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
│ • Metadata      │                          │ • Async Vendor  │
│ • Job State     │                          │ • Sync Vendor   │
│ • Results       │                          │                 │
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
   docker-compose up --build -d
   ```

3. **Verify the setup**

   ```bash
   curl http://localhost:8000/health
   ```

4. **For running load test**

   ```bash
   k6 run loadtest.js
   ```

# Load Test Insights

- Duration: 60s load + 30s ramp down
- Concurrent Users: Ramped up to 200 VUs
- Total Requests: 6,280 (6280 POST /jobs)
- Success Rate: 100% (job_creation_success)
- Failures: 0% (http_req_failed)
- 95th Percentile Latency: 29.56ms
- Max Latency: 85.16ms
- Throughput: ~102 req/sec

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
