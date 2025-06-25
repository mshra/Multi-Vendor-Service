import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Counter, Trend } from "k6/metrics";

const jobCreationRate = new Rate("job_creation_success");
const apiErrors = new Counter("api_errors");
const responseTime = new Trend("response_time_ms");

export const options = {
  stages: [
    { duration: "10s", target: 50 },
    { duration: "40s", target: 200 },
    { duration: "10s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"],
    http_req_failed: ["rate<0.1"],
    job_creation_success: ["rate>0.95"],
  },
};

const BASE_URL = "http://localhost:8000";
const HEADERS = { "Content-Type": "application/json" };

const SAMPLE_PAYLOADS = [
  {
    vendor: "sync",
    data: {
      user_id: "12345",
      query: "product_info",
      parameters: { category: "electronics", limit: 10 },
    },
  },
  {
    vendor: "async",
    data: {
      user_id: "67890",
      query: "user_profile",
      parameters: { include_history: true, depth: "full" },
    },
  },
  {
    vendor: "sync",
    data: {
      user_id: "user_" + Math.random().toString(36).substr(2, 9),
      query: "recommendations",
      parameters: { count: 5, type: "trending" },
    },
  },
];

export default function () {
  createJob();
  sleep(Math.random() * 2);
}

function createJob() {
  const payload =
    SAMPLE_PAYLOADS[Math.floor(Math.random() * SAMPLE_PAYLOADS.length)];
  const response = http.post(`${BASE_URL}/jobs`, JSON.stringify(payload), {
    headers: HEADERS,
  });

  const success = check(response, {
    "job creation status is 201": (r) => r.status === 201,
    "job creation has request_id": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.request_id && body.request_id.length > 0;
      } catch (e) {
        return false;
      }
    },
    "job creation response time < 1000ms": (r) => r.timings.duration < 1000,
  });

  jobCreationRate.add(success);
  responseTime.add(response.timings.duration);

  if (!success) {
    apiErrors.add(1);
  }
}

export function webhookTest() {
  if (Math.random() < 0.05) {
    const mockWebhookPayload = {
      request_id: "test-webhook-" + Math.random().toString(36).substr(2, 9),
      status: "complete",
      result: {
        data: "mock vendor response data",
        processed_at: new Date().toISOString(),
      },
    };

    const response = http.post(
      `${BASE_URL}/vendor-webhook/async_vendor`,
      JSON.stringify(mockWebhookPayload),
      { headers: HEADERS },
    );

    check(response, {
      "webhook status is 200": (r) => r.status === 200,
    });
  }
}

export function setup() {
  const warmupResponse = http.get(`${BASE_URL}/health`);
  if (warmupResponse.status !== 200) {
    console.warn("Health check failed, service might not be ready");
  }
  return { startTime: Date.now() };
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`Test completed in ${duration} seconds`);
  console.log("Check the k6 summary for detailed metrics");
}

export const highCreateLoad = {
  executor: "constant-arrival-rate",
  rate: 100,
  timeUnit: "1s",
  duration: "30s",
  preAllocatedVUs: 50,
  maxVUs: 100,
  exec: "createJobOnly",
};

export function createJobOnly() {
  createJob();
  sleep(0.1);
}
