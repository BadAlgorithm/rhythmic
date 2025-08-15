import fs from 'fs/promises';
import { runLearnCommand } from './learn.js';
import { generateK6Script } from './generate.js';
import { Logger } from '../../utils/logger.js';
import ora from 'ora';

export async function runFullAnalysis(options) {
  const logger = new Logger(options.verbose);
  const tempModelFile = options.model || 'temp-traffic-model.json';
  
  try {
    logger.info('🚀 Starting full analysis pipeline...');
    logger.info(`   Prometheus: ${options.prometheus}`);
    logger.info(`   Metric: ${options.metric}`);
    logger.info(`   Target: ${options.target}`);
    logger.info(`   Output: ${options.output}`);
    
    // Step 1: Learn patterns (Python)
    logger.step('\\n📊 Step 1: Learning traffic patterns from Prometheus...');
    
    const learnOptions = {
      prometheus: options.prometheus,
      metric: options.metric,
      duration: options.lookback,
      step: 60, // Default step
      output: tempModelFile,
      verbose: options.verbose
    };
    
    await runLearnCommand(learnOptions);
    
    // Verify model file was created
    try {
      await fs.access(tempModelFile);
    } catch (error) {
      throw new Error(`Model file was not created: ${tempModelFile}`);
    }
    
    // Step 2: Generate K6 script (Node.js)
    logger.step('\\n🔧 Step 2: Generating K6 load test script...');
    
    const generateOptions = {
      input: tempModelFile,
      target: options.target,
      output: options.output,
      scale: options.scale,
      timeScale: options.timeScale,
      duration: '1h', // Default duration for generated test
      verbose: options.verbose
    };
    
    await generateK6Script(generateOptions);
    
    // Step 3: Cleanup temporary files (unless user wants to keep them)
    if (!options.keepModel && tempModelFile.startsWith('temp-')) {
      try {
        await fs.unlink(tempModelFile);
        logger.debug(`🗑️  Cleaned up temporary model file: ${tempModelFile}`);
      } catch (error) {
        logger.warning(`⚠️  Could not clean up temp file: ${tempModelFile}`);
      }
    }
    
    // Summary
    logger.success('\\n🎉 Full analysis completed successfully!');
    logger.info('\\n📋 What was done:');
    logger.info('   1. ✅ Fetched metrics from Prometheus');
    logger.info('   2. ✅ Analyzed traffic patterns using wavelets & Fourier transforms');
    logger.info('   3. ✅ Detected periodic cycles and traffic spikes');
    logger.info('   4. ✅ Generated realistic K6 load test script');
    
    logger.info('\\n🚀 Next steps:');
    logger.info(`   • Review the generated script: ${options.output}`);
    logger.info(`   • Run the load test: k6 run ${options.output}`);
    logger.info('   • Adjust scale factor if needed (--scale option)');
    
    if (!options.keepModel && !tempModelFile.startsWith('temp-')) {
      logger.info(`   • Traffic model saved to: ${tempModelFile}`);
    }
    
  } catch (error) {
    logger.error(`❌ Full analysis failed: ${error.message}`);
    
    // Cleanup on failure
    if (tempModelFile.startsWith('temp-')) {
      try {
        await fs.unlink(tempModelFile);
      } catch (cleanupError) {
        // Ignore cleanup errors
      }
    }
    
    if (options.verbose) {
      logger.error(error.stack);
    }
    
    process.exit(1);
  }
}