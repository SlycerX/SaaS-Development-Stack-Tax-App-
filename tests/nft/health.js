import http from "k6/http";
import { check } from "k6";

const p95 = Number(__ENV.P95_MS || 500);
const errorRate = Number(__ENV.ERROR_RATE || 0.01);

export const options = {
  vus: 5,
  duration: "30s",
  thresholds: {
    http_req_failed: [`rate<${errorRate}`],
    http_req_duration: [`p(95)<${p95}`],
  },
};

export default function () {
  const response = http.get(`${__ENV.BASE_URL}/health`);
  check(response, { "status is 200": (r) => r.status === 200 });
}
