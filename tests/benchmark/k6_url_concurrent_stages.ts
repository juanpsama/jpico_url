import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

// ── LCG: same algorithm used by UrlMapService for short code generation ──

const BASE62_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
const MAX_VAL = 62 ** 4;   // 14 776 336
const PRIME = 748_361;

// Must match seeded_db fixture values
const COUNTER_START = 1;
const COUNTER_END = 500_000;

const BASE_URL = 'http://127.0.0.1:8080';

const shortCodeTrend = new Trend('short_code_duration');
const errorRate = new Rate('error_rate');

function encodeBase62(num: number): string {
  if (num === 0) return BASE62_ALPHABET[0].repeat(4);
  const chars: string[] = [];
  while (num > 0) {
    chars.push(BASE62_ALPHABET[num % 62]);
    num = Math.floor(num / 62);
  }
  while (chars.length < 4) chars.push(BASE62_ALPHABET[0]);
  return chars.reverse().join('');
}

function generateShortCode(counter: number): string {
  return encodeBase62((counter * PRIME) % MAX_VAL);
}

function randomShortCode(): string {
  const counter = Math.floor(Math.random() * (COUNTER_END - COUNTER_START + 1)) + COUNTER_START;
  return generateShortCode(counter);
}

// ── k6 configuration ──

export const options = {
  stages: [
    { duration: '10s', target: 10 },   // Warm-up
    { duration: '10s', target: 50 },   // Ramp-up
    { duration: '20s', target: 100 },  // Peak load
    { duration: '10s', target: 0 },    // Cool-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    error_rate: ['rate<0.01'],
  },
};

export default function () {
  const shortCode = randomShortCode();
  const res = http.get(`${BASE_URL}/${shortCode}`);
  shortCodeTrend.add(res.timings.duration);
  errorRate.add(res.status !== 302);

  check(res, {
    'status is 302': (response: Response) => response.status === 302,
  });

  sleep(0.1);
}
