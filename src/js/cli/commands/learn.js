import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { Logger } from '../../utils/logger.js';
import ora from 'ora';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export async function runLearnCommand(options) {
  const logger = new Logger(options.verbose);
  const spinner = ora();
  
  return new Promise((resolve, reject) => {
    spinner.start('🐍 Starting Python analysis...');
    
    const pythonScript = join(__dirname, '../../../python/main.py');
    const args = [
      'learn',
      '--prometheus', options.prometheus,
      '--metric', options.metric,
      '--duration', options.duration,
      '--step', options.step.toString(),
      '--output', options.output
    ];
    
    if (options.verbose) args.push('--verbose');
    if (options.wavelet) args.push('--wavelet', options.wavelet);
    if (options.spikeThreshold) args.push('--spike-threshold', options.spikeThreshold.toString());
    
    logger.debug(`Executing: python3 ${pythonScript} ${args.join(' ')}`);
    
    const python = spawn('python3', [pythonScript, ...args], {
      stdio: options.verbose ? 'inherit' : 'pipe'
    });
    
    let output = '';
    let errorOutput = '';
    
    if (!options.verbose) {
      python.stdout?.on('data', (data) => {
        output += data.toString();
      });
      
      python.stderr?.on('data', (data) => {
        errorOutput += data.toString();
      });
    }
    
    python.on('close', (code) => {
      spinner.stop();
      
      if (code === 0) {
        logger.success('✅ Python analysis completed successfully');
        
        // Show output if not in verbose mode
        if (!options.verbose && output) {
          console.log(output);
        }
        
        resolve();
      } else {
        logger.error(`❌ Python analysis failed (exit code: ${code})`);
        
        if (errorOutput) {
          logger.error('Error output:');
          console.error(errorOutput);
        }
        
        reject(new Error(`Python analysis failed with exit code ${code}`));
      }
    });
    
    python.on('error', (error) => {
      spinner.fail('❌ Failed to start Python analysis');
      
      if (error.code === 'ENOENT') {
        logger.error('Python 3 not found. Please ensure Python 3 is installed and in PATH.');
        logger.error('You can install Python dependencies with: pip install -r requirements.txt');
      } else {
        logger.error(`Process error: ${error.message}`);
      }
      
      reject(error);
    });
  });
}