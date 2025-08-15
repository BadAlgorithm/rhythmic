#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { runLearnCommand } from '../src/js/cli/commands/learn.js';
import { generateK6Script } from '../src/js/cli/commands/generate.js';
import { runFullAnalysis } from '../src/js/cli/commands/analyze.js';
import { runSetupCommand } from '../src/js/cli/commands/setup.js';

const program = new Command();

program
  .name('rhythmic')
  .description('🎵 Match the rhythm of production - Transform Prometheus metrics into K6 load tests')
  .version('1.0.0');

// Setup command - Auto-install dependencies
program
  .command('setup')
  .description('Auto-install Python dependencies and verify environment')
  .option('--verbose', 'Show detailed setup output', false)
  .action(async (options) => {
    try {
      await runSetupCommand(options);
    } catch (error) {
      console.error(chalk.red(`❌ Setup failed: ${error.message}`));
      process.exit(1);
    }
  });

// Learn command - Python analysis
program
  .command('learn')
  .description('Learn traffic patterns from Prometheus metrics')
  .option('-p, --prometheus <url>', 'Prometheus server URL', 'http://localhost:9090')
  .option('-m, --metric <name>', 'Metric name to analyze', 'http_requests_total')
  .option('-d, --duration <time>', 'Lookback duration (e.g., 7d, 24h)', '7d')
  .option('-s, --step <seconds>', 'Data resolution in seconds', '60')
  .option('-o, --output <file>', 'Output model file', 'traffic-model.json')
  .option('--verbose', 'Show detailed analysis', false)
  .option('--wavelet <type>', 'Wavelet type for decomposition', 'db4')
  .option('--spike-threshold <sigma>', 'Spike detection threshold in std deviations', '3.0')
  .action(async (options) => {
    try {
      options.step = parseInt(options.step);
      options.spikeThreshold = parseFloat(options.spikeThreshold);
      await runLearnCommand(options);
    } catch (error) {
      console.error(chalk.red(`❌ Learn command failed: ${error.message}`));
      process.exit(1);
    }
  });

// Generate command - Node.js K6 generation
program
  .command('generate')
  .description('Generate K6 test from learned patterns')
  .option('-i, --input <file>', 'Input model file', 'traffic-model.json')
  .option('-t, --target <url>', 'Target URL for load test', 'http://localhost:8080')
  .option('-o, --output <file>', 'Output K6 script file', 'load-test.js')
  .option('--scale <factor>', 'Scale traffic amplitude (e.g., 0.5, 2, 10)', '1')
  .option('--time-scale <factor>', 'Time compression factor (e.g., 24 = 24h in 1h)', '1')
  .option('--duration <time>', 'Test duration (e.g., 1h, 30m)', '1h')
  .option('--headers <headers>', 'HTTP headers (JSON or key:value format)')
  .option('--verbose', 'Show detailed output', false)
  .action(async (options) => {
    try {
      await generateK6Script(options);
    } catch (error) {
      console.error(chalk.red(`❌ Generate command failed: ${error.message}`));
      process.exit(1);
    }
  });

// Analyze command - Full pipeline
program
  .command('analyze')
  .description('One-shot: learn patterns and generate K6 test')
  .option('-p, --prometheus <url>', 'Prometheus server URL', 'http://localhost:9090')
  .option('-m, --metric <name>', 'Metric to analyze', 'http_requests_total')
  .option('-t, --target <url>', 'Target URL for test', 'http://localhost:8080')
  .option('-o, --output <file>', 'Output K6 script', 'load-test.js')
  .option('--lookback <time>', 'Analysis period', '7d')
  .option('--scale <factor>', 'Traffic amplitude scale factor', '1')
  .option('--time-scale <factor>', 'Time compression factor', '1')
  .option('--model <file>', 'Intermediate model file', 'traffic-model.json')
  .option('--keep-model', 'Keep intermediate model file', false)
  .option('--verbose', 'Show detailed output', false)
  .action(async (options) => {
    try {
      await runFullAnalysis(options);
    } catch (error) {
      console.error(chalk.red(`❌ Analyze command failed: ${error.message}`));
      process.exit(1);
    }
  });

// Global error handling
process.on('unhandledRejection', (reason, promise) => {
  console.error(chalk.red('❌ Unhandled promise rejection:'), reason);
  process.exit(1);
});

process.on('uncaughtException', (error) => {
  console.error(chalk.red('❌ Uncaught exception:'), error);
  process.exit(1);
});

// Parse command line arguments
program.parse();