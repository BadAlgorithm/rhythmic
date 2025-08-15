import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs/promises';
import { Logger } from '../../utils/logger.js';
import ora from 'ora';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export async function runSetupCommand(options) {
  const logger = new Logger(options.verbose);
  const spinner = ora();
  
  logger.info('🚀 Setting up Rhythmic environment...');
  
  try {
    // 1. Check Python installation
    spinner.start('🐍 Checking Python installation...');
    await checkPython();
    spinner.succeed('✅ Python 3 found');
    
    // 2. Check pip installation
    spinner.start('📦 Checking pip installation...');
    await checkPip();
    spinner.succeed('✅ pip found');
    
    // 3. Install Python dependencies
    spinner.start('⬇️ Installing Python dependencies...');
    const requirementsPath = join(__dirname, '../../../../requirements.txt');
    await installPythonDependencies(requirementsPath, options.verbose);
    spinner.succeed('✅ Python dependencies installed');
    
    // 4. Verify installation
    spinner.start('🔍 Verifying installation...');
    await verifyInstallation();
    spinner.succeed('✅ Installation verified');
    
    // 5. Test basic functionality
    spinner.start('🧪 Testing basic functionality...');
    await testBasicFunctionality();
    spinner.succeed('✅ Basic functionality test passed');
    
    logger.success('\\n🎉 Setup completed successfully!');
    logger.info('\\n📋 What was installed:');
    logger.info('   • numpy (numerical computing)');
    logger.info('   • scipy (signal processing)');
    logger.info('   • PyWavelets (wavelet transforms)');
    logger.info('   • scikit-learn (machine learning)');
    logger.info('   • requests (HTTP client)');
    logger.info('   • pandas (data manipulation)');
    logger.info('   • matplotlib (plotting - optional)');
    
    logger.info('\\n🚀 You can now run:');
    logger.info('   rhythmic analyze --prometheus http://localhost:9090 --target https://api.example.com');
    
  } catch (error) {
    spinner.fail(`❌ Setup failed: ${error.message}`);
    
    logger.error('\\n🔧 Troubleshooting tips:');
    logger.error('   • Ensure Python 3.9+ is installed: python3 --version');
    logger.error('   • Ensure pip is available: pip3 --version');
    logger.error('   • Try manual install: pip install -r requirements.txt');
    logger.error('   • On macOS: brew install python3');
    logger.error('   • On Ubuntu: sudo apt install python3 python3-pip');
    logger.error('   • On Windows: Download from python.org');
    
    throw error;
  }
}

async function checkPython() {
  return new Promise((resolve, reject) => {
    const python = spawn('python3', ['--version'], { stdio: 'pipe' });
    
    python.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error('Python 3 not found. Please install Python 3.9 or higher.'));
      }
    });
    
    python.on('error', () => {
      reject(new Error('Python 3 not found. Please install Python 3.9 or higher.'));
    });
  });
}

async function checkPip() {
  return new Promise((resolve, reject) => {
    const pip = spawn('pip3', ['--version'], { stdio: 'pipe' });
    
    pip.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error('pip not found. Please install pip.'));
      }
    });
    
    pip.on('error', () => {
      reject(new Error('pip not found. Please install pip.'));
    });
  });
}

async function installPythonDependencies(requirementsPath, verbose) {
  // Check if requirements.txt exists
  try {
    await fs.access(requirementsPath);
  } catch (error) {
    throw new Error(`Requirements file not found: ${requirementsPath}`);
  }
  
  return new Promise((resolve, reject) => {
    const args = ['install', '-r', requirementsPath];
    
    const pip = spawn('pip3', args, {
      stdio: verbose ? 'inherit' : 'pipe'
    });
    
    let errorOutput = '';
    
    if (!verbose) {
      pip.stderr?.on('data', (data) => {
        errorOutput += data.toString();
      });
    }
    
    pip.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        const errorMsg = verbose ? 
          'Failed to install Python dependencies' :
          `Failed to install Python dependencies: ${errorOutput}`;
        reject(new Error(errorMsg));
      }
    });
    
    pip.on('error', (error) => {
      reject(new Error(`Failed to run pip: ${error.message}`));
    });
  });
}

async function verifyInstallation() {
  const requiredPackages = [
    'numpy',
    'scipy', 
    'pywt',      // PyWavelets
    'sklearn',   // scikit-learn
    'requests',
    'pandas'
  ];
  
  for (const pkg of requiredPackages) {
    await checkPythonPackage(pkg);
  }
}

async function checkPythonPackage(packageName) {
  return new Promise((resolve, reject) => {
    const python = spawn('python3', ['-c', `import ${packageName}; print("${packageName} OK")`], {
      stdio: 'pipe'
    });
    
    python.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Package ${packageName} not properly installed`));
      }
    });
    
    python.on('error', () => {
      reject(new Error(`Failed to verify package ${packageName}`));
    });
  });
}

async function testBasicFunctionality() {
  return new Promise((resolve, reject) => {
    const testScript = `
import numpy as np
import scipy
import pywt
from sklearn import __version__ as sklearn_version
import requests
import pandas as pd

# Test basic operations
arr = np.array([1, 2, 3, 4, 5])
coeffs = pywt.dwt(arr, 'db1')
fft_result = np.fft.fft(arr)

print("All packages working correctly")
`;
    
    const python = spawn('python3', ['-c', testScript], { stdio: 'pipe' });
    
    python.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error('Basic functionality test failed'));
      }
    });
    
    python.on('error', () => {
      reject(new Error('Failed to run basic functionality test'));
    });
  });
}