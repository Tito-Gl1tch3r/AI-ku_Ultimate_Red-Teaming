#!/usr/bin/env node

/**
 * Rate Limiter for Bug Bounty Hunting
 * Ensures compliance with program rate limits (max 2 requests/sec)
 */

class RateLimiter {
  constructor(maxRequestsPerSecond = 2) {
    this.maxRequestsPerSecond = maxRequestsPerSecond;
    this.delayBetweenRequests = 1000 / maxRequestsPerSecond; // 500ms for 2 req/sec
    this.lastRequestTime = 0;
    this.queue = [];
    this.processing = false;
  }

  /**
   * Wait for the appropriate delay before making a request
   */
  async wait() {
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    
    if (timeSinceLastRequest < this.delayBetweenRequests) {
      const waitTime = this.delayBetweenRequests - timeSinceLastRequest;
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    this.lastRequestTime = Date.now();
  }

  /**
   * Execute a function with rate limiting
   */
  async execute(fn) {
    await this.wait();
    return await fn();
  }

  /**
   * Execute multiple functions with rate limiting
   */
  async executeAll(functions) {
    const results = [];
    for (const fn of functions) {
      const result = await this.execute(fn);
      results.push(result);
    }
    return results;
  }
}

module.exports = RateLimiter;


