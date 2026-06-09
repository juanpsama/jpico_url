import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  iterations: 1500,
  vus: 200,
  // duration: '30s',
};

// The default exported function is gonna be picked up by k6 as the entry point for the test script. It will be executed repeatedly in "iterations" for the whole duration of the test.
export default function () {
  // Make a GET request to the target URL
  http.get('http://127.0.0.1:8080/6hmG');

  sleep(0.5);
}
