import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Counter, Trend } from "k6/metrics";

const jobCreationRate = new Rate("job_creation_success");
const jobStatusRate = new Rate("job_status_success");
const jobCompletionRate = new Rate("job_completion_rate");
const apiErrors = new Counter("api_errors");
const responseTime = new Trend("response_time_ms");

export const options = {
  stages: [
    { duration: "10s", target: 50 }, // Ramp up to 50 users
    { duration: "40s", target: 200 }, // Stay at 200 users for 40s
    { duration: "10s", target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"], // 95% of requests under 2s
    http_req_failed: ["rate<0.1"], // Error rate under 10%
    job_creation_success: ["rate>0.95"], // 95% job creation success
    job_status_success: ["rate>0.95"], // 95% status check success
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

let createdJobs = [];

export default function () {
  const scenario = Math.random();

  if (scenario < 0.7) {
    createJob();
  } else {
    checkJobStatus();
  }

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

  if (success && response.status === 200) {
    try {
      const body = JSON.parse(response.body);
      if (body.request_id) {
        createdJobs.push({
          id: body.request_id,
          created_at: Date.now(),
          vendor: payload.vendor,
        });

        // Keep only recent jobs (last 30 seconds) to avoid memory issues
        const cutoff = Date.now() - 30000;
        createdJobs = createdJobs.filter((job) => job.created_at > cutoff);
      }
    } catch (e) {
      console.error("Failed to parse job creation response:", e);
      apiErrors.add(1);
    }
  } else {
    apiErrors.add(1);
  }
}

function checkJobStatus() {
  const now = Date.now();

  const eligibleJobs = createdJobs.filter((job) => now - job.created_at > 3000);

  if (eligibleJobs.length === 0) {
    createJob();
    return;
  }

  const job = eligibleJobs[Math.floor(Math.random() * eligibleJobs.length)];

  const response = http.get(`${BASE_URL}/jobs/${job.id}`);

  const success = check(response, {
    "status check status is 200": (r) => r.status === 200,
    "status check has valid response": (r) => {
      try {
        console.log("Status check response:", response.body);
        const body = JSON.parse(r.body);
        return (
          body.status &&
          ["pending", "processing", "complete", "failed"].includes(body.status)
        );
      } catch (e) {
        return false;
      }
    },
    "status check response time < 500ms": (r) => r.timings.duration < 500,
  });

  jobStatusRate.add(success);
  responseTime.add(response.timings.duration);

  if (success && response.status === 200) {
    try {
      const body = JSON.parse(response.body);
      if (body.status === "complete") {
        jobCompletionRate.add(1);
        check(response, {
          "completed job has result": (r) => {
            const parsed = JSON.parse(r.body);
            return parsed.result !== undefined;
          },
        });
      } else {
        jobCompletionRate.add(0);
      }
    } catch (e) {
      console.error("Failed to parse status response:", e);
      apiErrors.add(1);
    }
  } else {
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

export const statusCheckLoad = {
  executor: "per-vu-iterations",
  vus: 20,
  iterations: 50,
  maxDuration: "60s",
  exec: "checkStatusOnly",
};

export function createJobOnly() {
  createJob();
  sleep(0.1);
}

export function checkStatusOnly() {
  checkJobStatus();
  sleep(0.5);
}
