import fs from 'fs/promises';
import { ModelReader } from '../../utils/modelReader.js';
import { K6Generator } from '../../generators/k6Generator.js';
import { Logger } from '../../utils/logger.js';
import ora from 'ora';

export async function generateK6Script(options) {
  const logger = new Logger(options.verbose);
  const spinner = ora();
  
  try {
    // 1. Load and validate model
    spinner.start('📖 Loading traffic model...');
    const modelReader = new ModelReader();
    
    try {
      await fs.access(options.input);
    } catch (error) {
      spinner.fail(`❌ Model file not found: ${options.input}`);
      process.exit(1);
    }
    
    const model = await modelReader.load(options.input);
    spinner.succeed('✅ Model loaded and validated');
    
    // Display model summary
    const summary = modelReader.getModelSummary(model);
    logger.info(`📊 Model Summary:`);
    logger.info(`   Pattern: ${summary.patternType} (confidence: ${summary.confidence.toFixed(2)})`);
    logger.info(`   Baseline: ${summary.baselineMean.toFixed(2)} req/s`);
    logger.info(`   Spikes: ${summary.spikeCount} events`);
    logger.info(`   Data: ${summary.samples} samples over ${summary.duration}`);
    
    // 2. Generate K6 script
    spinner.start('🔧 Generating K6 script...');
    const generator = new K6Generator();
    
    const generatorOptions = {
      target: options.target,
      duration: options.duration,
      scale: parseFloat(options.scale),
      timeScale: parseFloat(options.timeScale || 1),
      headers: parseHeaders(options.headers)
    };
    
    const script = await generator.generate(model, generatorOptions);
    spinner.succeed('✅ K6 script generated');
    
    // 3. Save script
    spinner.start(`💾 Saving script to ${options.output}...`);
    await fs.writeFile(options.output, script, 'utf8');
    spinner.succeed(`✅ Script saved to ${options.output}`);
    
    // 4. Display generation summary
    logger.success('\\n🎉 K6 script generation completed!');
    logger.info(`\\n📋 Test Configuration:`);
    logger.info(`   Target: ${options.target}`);
    logger.info(`   Duration: ${options.duration}`);
    logger.info(`   Amplitude Scale: ${options.scale}x`);
    logger.info(`   Time Scale: ${options.timeScale || 1}x (${formatTimeCompression(options.timeScale || 1)})`);
    logger.info(`   Output: ${options.output}`);
    
    logger.info(`\\n🚀 To run the test:`);
    logger.info(`   k6 run ${options.output}`);
    
    // Show scenarios that will be executed
    const scenarios = getScenarioSummary(model, parseFloat(options.scale));
    if (scenarios.length > 0) {
      logger.info(`\\n🎭 Test Scenarios:`);
      scenarios.forEach((scenario, i) => {
        logger.info(`   ${i + 1}. ${scenario}`);
      });
    }
    
  } catch (error) {
    spinner.fail(`❌ Generation failed: ${error.message}`);
    if (options.verbose) {
      logger.error(error.stack);
    }
    process.exit(1);
  }
}

function parseHeaders(headersOption) {
  if (!headersOption) return {};
  
  try {
    // Support JSON format: '{"Content-Type": "application/json"}'
    if (headersOption.startsWith('{')) {
      return JSON.parse(headersOption);
    }
    
    // Support key:value format: 'Content-Type:application/json,Authorization:Bearer token'
    const headers = {};
    headersOption.split(',').forEach(pair => {
      const [key, value] = pair.split(':');
      if (key && value) {
        headers[key.trim()] = value.trim();
      }
    });
    return headers;
  } catch (error) {
    throw new Error(`Invalid headers format: ${headersOption}. Use JSON or key:value format.`);
  }
}

function formatTimeCompression(timeScale) {
  if (timeScale === 1) return 'real-time';
  if (timeScale < 1) return `${1/timeScale}x slower`;
  
  if (timeScale >= 24 * 7) {
    const weeks = Math.round(timeScale / (24 * 7));
    return `${weeks} week${weeks > 1 ? 's' : ''} in 1 hour`;
  } else if (timeScale >= 24) {
    const days = Math.round(timeScale / 24);
    return `${days} day${days > 1 ? 's' : ''} in 1 hour`;
  } else {
    return `${timeScale}h in 1h`;
  }
}

function getScenarioSummary(model, scale) {
  const scenarios = [];
  
  // Always has baseline
  scenarios.push(`Baseline traffic following ${model.pattern.type} pattern`);
  
  // Spike scenario
  if (model.spikes.events.length > 0) {
    const spikeCount = Math.round(model.spikes.events.length * scale);
    scenarios.push(`Traffic spikes (${spikeCount} events)`);
  }
  
  // Pattern-specific scenarios
  switch (model.pattern.type) {
    case 'business-hours-heavy':
      scenarios.push('Rush hour traffic surge');
      break;
    case 'business-hours-normal':
      scenarios.push('Business hours traffic pattern');
      break;
    case 'bursty':
      scenarios.push('Burst traffic simulation');
      break;
    case 'weekly-batch':
      scenarios.push('Weekly batch processing load');
      break;
  }
  
  return scenarios;
}