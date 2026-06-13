import http from 'k6/http';
import { sleep } from 'k6';
import { Rate } from 'k6/metrics';


export const options = {
   stages: [
    { duration: '10s', target: 100 },  // Warm-up
    { duration: '10s', target: 500 },  // Ramp-up
    { duration: '10s', target: 1000 },  
    { duration: '20s', target: 5000},   // Peak load
    { duration: '10s', target: 0 },    // Cool-down
  ],
  // iterations: 1500,
  // vus: 200,
  // duration: '30s',
  threshold:{
    error_rate: ['rate<0.01'],
  }
};
const errorRate = new Rate('error_rate');

export default function () {
  // Make a GET request to the target URL
  const res = http.get('http://127.0.0.1:8000/no-cache/6hmG', {redirects : 0});
  errorRate.add(res.status != 302);

  sleep(0.5);
}
