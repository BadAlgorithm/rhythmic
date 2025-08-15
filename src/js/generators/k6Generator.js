import { parseDuration, formatTimestamp } from '../utils/timeUtils.js';

export class K6Generator {
  constructor() {
    this.defaultOptions = {
      target: 'http://localhost:8080',
      duration: '1h',
      scale: 1,
      timeScale: 1,
      headers: {}
    };
  }
  
  async generate(model, options = {}) {
    const opts = { ...this.defaultOptions, ...options };
    
    // Build scenarios based on pattern
    const scenarios = this._buildScenarios(model, opts.scale, opts.timeScale, opts.duration);
    
    // Generate complete K6 script
    return this._generateScript(model, scenarios, opts.target, opts.headers, opts.scale, opts.timeScale);
  }
  
  _buildScenarios(model, scale, timeScale, duration) {
    const scenarios = {};
    
    // Always add baseline scenario
    scenarios.baseline = this._generateBaselineScenario(
      model.baseline,
      scale,
      timeScale,
      duration
    );
    
    // Add spike scenario if spikes detected
    if (model.spikes.events.length > 0) {
      scenarios.spikes = this._generateSpikeScenario(
        model.spikes,
        scale,
        timeScale
      );
    }
    
    // Add pattern-specific scenarios
    switch (model.pattern.type) {
      case 'business-hours-heavy':
        scenarios.rushHour = this._generateRushHourScenario(model, scale, timeScale);
        break;
      case 'business-hours-normal':
        scenarios.businessHours = this._generateBusinessHoursScenario(model, scale, timeScale);
        break;
      case 'bursty':
        scenarios.bursts = this._generateBurstScenario(model, scale, timeScale);
        break;
      case 'weekly-batch':
        scenarios.weeklyBatch = this._generateWeeklyBatchScenario(model, scale, timeScale);
        break;
    }
    
    return scenarios;
  }
  
  _generateBaselineScenario(baseline, scale, timeScale, duration) {
    const durationMinutes = parseDuration(duration);
    const stagesPerHour = 60; // One stage per minute
    const totalStages = Math.min(durationMinutes, stagesPerHour * 24);
    
    const stages = [];
    
    // Calculate stage duration based on time compression
    const stageDuration = timeScale > 1 ? 
      Math.max(1, Math.round(60 / timeScale)) : 60; // seconds
    const stageDurationStr = stageDuration >= 60 ? 
      `${Math.round(stageDuration / 60)}m` : `${stageDuration}s`;
    
    for (let i = 0; i < totalStages; i++) {
      // Compressed time progression - timeScale hours of production in 1 hour of test
      const compressedTime = (i / 60) * timeScale;
      const t = compressedTime % 24; // Time in hours (0-24), but accelerated
      
      let rate = baseline.mean * scale;
      
      // Apply Fourier coefficients with time compression
      baseline.coefficients.forEach(coeff => {
        // Frequency is scaled by time compression factor
        const compressedFreq = coeff.frequency * 60 * timeScale;
        const component = coeff.amplitude * Math.sin(
          2 * Math.PI * compressedFreq * (i / 60) + coeff.phase
        ) * scale;
        rate += component;
      });
      
      stages.push({
        duration: stageDurationStr,
        target: Math.max(1, Math.round(rate))
      });
    }
    
    return {
      executor: 'ramping-arrival-rate',
      startRate: Math.round(baseline.mean * scale),
      timeUnit: '1s',
      stages: stages,
      preAllocatedVUs: Math.ceil(baseline.mean * scale * 2),
      maxVUs: Math.ceil(Math.max(...stages.map(s => s.target)) * 2)
    };
  }
  
  _generateSpikeScenario(spikes, scale, timeScale) {
    if (spikes.events.length === 0) return null;
    
    const avgMagnitude = spikes.events.reduce(
      (sum, e) => sum + e.magnitude, 0
    ) / spikes.events.length;
    
    // Compress spike timing based on time scale
    const compressedDuration = Math.max(1, Math.round(10 / timeScale));
    const durationStr = compressedDuration >= 60 ? 
      `${Math.round(compressedDuration / 60)}m` : `${compressedDuration}m`;
    
    return {
      executor: 'shared-iterations',
      exec: 'generateSpike',
      vus: Math.ceil(avgMagnitude * scale / 10),
      iterations: Math.round(spikes.events.length * scale * timeScale),
      startTime: '30s',
      maxDuration: durationStr
    };
  }
  
  _generateRushHourScenario(model, scale, timeScale) {
    const compressedDuration = Math.max(1, Math.round(120 / timeScale)); // 2h compressed
    const durationStr = compressedDuration >= 60 ? 
      `${Math.round(compressedDuration / 60)}h` : `${compressedDuration}m`;
    
    return {
      executor: 'constant-arrival-rate',
      exec: 'rushHourTraffic',
      rate: Math.round(model.statistics.p95 * scale),
      timeUnit: '1s',
      duration: durationStr,
      preAllocatedVUs: 100,
      maxVUs: 500,
      startTime: Math.max(1, Math.round(30 / timeScale)) + 'm'
    };
  }
  
  _generateBusinessHoursScenario(model, scale, timeScale) {
    const compressedStages = [
      { 
        duration: Math.max(1, Math.round(120 / timeScale)) + 'm', 
        target: Math.round(model.statistics.p95 * scale) 
      },
      { 
        duration: Math.max(1, Math.round(360 / timeScale)) + 'm', 
        target: Math.round(model.statistics.p95 * scale) 
      },
      { 
        duration: Math.max(1, Math.round(120 / timeScale)) + 'm', 
        target: Math.round(model.baseline.mean * 0.3 * scale) 
      }
    ];
    
    return {
      executor: 'ramping-arrival-rate',
      exec: 'businessHoursTraffic',
      startRate: Math.round(model.baseline.mean * 0.3 * scale),
      timeUnit: '1s',
      stages: compressedStages,
      preAllocatedVUs: 50,
      maxVUs: Math.round(model.statistics.p95 * scale * 2)
    };
  }
  
  _generateBurstScenario(model, scale, timeScale) {
    const compressedDuration = Math.max(1, Math.round(60 / timeScale)); // 1h compressed
    const durationStr = compressedDuration >= 60 ? 
      `${Math.round(compressedDuration / 60)}h` : `${compressedDuration}m`;
    
    return {
      executor: 'externally-controlled',
      exec: 'burstTraffic',
      duration: durationStr,
      maxVUs: Math.round(model.statistics.max * scale),
      startTime: Math.max(1, Math.round(15 / timeScale)) + 'm'
    };
  }
  
  _generateWeeklyBatchScenario(model, scale, timeScale) {
    const compressedDuration = Math.max(1, Math.round(30 / timeScale)); // 30m compressed
    const durationStr = compressedDuration >= 60 ? 
      `${Math.round(compressedDuration / 60)}h` : `${compressedDuration}m`;
    
    return {
      executor: 'constant-arrival-rate',
      exec: 'weeklyBatchTraffic',
      rate: Math.round(model.statistics.p99 * scale),
      timeUnit: '1s',
      duration: durationStr,
      preAllocatedVUs: 50,
      maxVUs: 200,
      startTime: Math.max(1, Math.round(60 / timeScale)) + 'm'
    };
  }
  
  _generateScript(model, scenarios, target, headers, scale = 1, timeScale = 1) {
    const headerString = Object.entries(headers)
      .map(([k, v]) => `    '${k}': '${v}'`)
      .join(',\\n');
    
    const avgSpikeSize = model.spikes.events.length > 0 
      ? Math.ceil(model.spikes.events.reduce((sum, e) => sum + e.magnitude, 0) / model.spikes.events.length)
      : 10;
    
    const timeCompressionInfo = timeScale > 1 ? 
      ` (${timeScale}x time compression)` : '';
    
    return `// Generated by Rhythmic v1.0.0
// Pattern learned from: ${model.metadata.metric}
// Pattern type: ${model.pattern.type} (confidence: ${model.pattern.confidence.toFixed(2)})
// Amplitude scale: ${scale}x, Time scale: ${timeScale}x${timeCompressionInfo}
// Generated: ${formatTimestamp(Date.now())}

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');

// Test configuration
export const options = {
  scenarios: ${JSON.stringify(scenarios, null, 2)},
  
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'http_req_failed': ['rate<0.05'],
    'errors': ['rate<0.05'],
    'response_time': ['p(95)<500']
  },
  
  tags: {
    pattern_type: '${model.pattern.type}',
    source_metric: '${model.metadata.metric}',
    scale_factor: '${(scenarios.baseline?.startRate / model.baseline.mean || 1).toFixed(2)}',
    model_confidence: '${model.pattern.confidence.toFixed(2)}'
  }
};

// Request headers
const headers = {${headerString ? '\\n' + headerString + '\\n' : ''}};

// Main scenario - baseline traffic following learned patterns
export default function() {
  const startTime = Date.now();
  const response = http.get('${target}', { headers });
  const duration = Date.now() - startTime;
  
  // Record metrics
  responseTime.add(duration);
  
  // Checks
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
    'no errors': (r) => r.status < 400
  });
  
  errorRate.add(!success);
  
  // Realistic think time based on pattern type
  const thinkTime = getThinkTime('${model.pattern.type}');
  sleep(thinkTime);
}

// Spike generator - recreates detected traffic spikes
export function generateSpike() {
  const burstSize = ${avgSpikeSize};
  const batch = [];
  
  for (let i = 0; i < burstSize; i++) {
    batch.push(['GET', '${target}', null, { headers }]);
  }
  
  const responses = http.batch(batch);
  
  check(responses[0], {
    'spike burst successful': (r) => r && r.status === 200
  });
  
  sleep(0.1 + Math.random() * 0.5); // Small delay between spike batches
}

// Rush hour traffic pattern
export function rushHourTraffic() {
  const response = http.get('${target}', { 
    headers,
    tags: { scenario: 'rush_hour' }
  });
  
  check(response, {
    'rush hour response OK': (r) => r.status === 200
  });
  
  // Shorter think time during peak hours
  sleep(0.3 + Math.random() * 0.7);
}

// Business hours traffic pattern
export function businessHoursTraffic() {
  const response = http.get('${target}', { 
    headers,
    tags: { scenario: 'business_hours' }
  });
  
  check(response, {
    'business hours response OK': (r) => r.status === 200
  });
  
  // Normal business hours think time
  sleep(1 + Math.random() * 2);
}

// Burst traffic pattern for bursty workloads
export function burstTraffic() {
  const burstSize = 3 + Math.floor(Math.random() * 8);
  const requests = [];
  
  for (let i = 0; i < burstSize; i++) {
    requests.push(['GET', '${target}', null, { headers }]);
  }
  
  const responses = http.batch(requests);
  
  check(responses[0], {
    'burst response OK': (r) => r && r.status === 200
  });
  
  // Random pause between bursts
  sleep(Math.random() * 10);
}

// Weekly batch processing pattern
export function weeklyBatchTraffic() {
  const response = http.get('${target}', { 
    headers,
    tags: { scenario: 'weekly_batch' }
  });
  
  check(response, {
    'batch processing OK': (r) => r.status === 200
  });
  
  // Minimal think time for batch processing
  sleep(0.1 + Math.random() * 0.3);
}

// Helper function to determine think time based on pattern type
function getThinkTime(patternType) {
  switch (patternType) {
    case 'business-hours-heavy':
    case 'business-hours-normal':
      return 0.5 + Math.random() * 1.5; // 0.5-2s
    case 'bursty':
      return Math.random() * 3; // 0-3s
    case 'steady':
      return 1 + Math.random(); // 1-2s
    case 'weekly-batch':
      return 0.2 + Math.random() * 0.5; // 0.2-0.7s
    default:
      return 1 + Math.random() * 2; // 1-3s
  }
}

// Summary handler
export function handleSummary(data) {
  const summary = {
    'summary.json': JSON.stringify(data, null, 2),
    stdout: generateTextSummary(data)
  };
  
  return summary;
}

function generateTextSummary(data) {
  const { metrics } = data;
  let summary = '\\n' + '='.repeat(60) + '\\n';
  summary += '🎵 RHYTHMIC LOAD TEST SUMMARY\\n';
  summary += '='.repeat(60) + '\\n';
  summary += \`📊 Pattern: ${model.pattern.type} (confidence: ${model.pattern.confidence.toFixed(2)})\\n\`;
  summary += \`⏱️  Duration: \${Math.round(data.state.testRunDurationMs / 1000)}s\\n\`;
  summary += \`🔄 Iterations: \${metrics.iterations?.values?.count || 0}\\n\`;
  summary += \`❌ Error Rate: \${((metrics.errors?.values?.rate || 0) * 100).toFixed(2)}%\\n\`;
  summary += \`📈 Avg Response Time: \${Math.round(metrics.http_req_duration?.values?.avg || 0)}ms\\n\`;
  summary += \`🏆 P95 Response Time: \${Math.round(metrics.http_req_duration?.values?.['p(95)'] || 0)}ms\\n\`;
  summary += \`🎯 Target: ${target}\\n\`;
  summary += '='.repeat(60) + '\\n';
  
  return summary;
}`;
  }
}