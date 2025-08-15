import fs from 'fs/promises';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export class ModelReader {
  constructor() {
    this.ajv = new Ajv();
    addFormats(this.ajv);
    this.schema = null;
  }
  
  async loadSchema() {
    if (!this.schema) {
      const schemaPath = join(__dirname, '../../../schemas/traffic-model.json');
      const schemaData = await fs.readFile(schemaPath, 'utf8');
      this.schema = JSON.parse(schemaData);
    }
    return this.schema;
  }
  
  async load(filePath) {
    try {
      const data = await fs.readFile(filePath, 'utf8');
      const model = JSON.parse(data);
      
      // Validate against schema
      await this.validate(model);
      
      return model;
    } catch (error) {
      if (error.code === 'ENOENT') {
        throw new Error(`Model file not found: ${filePath}`);
      } else if (error.name === 'SyntaxError') {
        throw new Error(`Invalid JSON in model file: ${filePath}`);
      }
      throw new Error(`Failed to load model from ${filePath}: ${error.message}`);
    }
  }
  
  async validate(model) {
    const schema = await this.loadSchema();
    const validate = this.ajv.compile(schema);
    const valid = validate(model);
    
    if (!valid) {
      const errors = validate.errors.map(err => 
        `${err.instancePath || 'root'}: ${err.message}`
      ).join(', ');
      throw new Error(`Invalid model format: ${errors}`);
    }
    
    // Additional business logic validation
    this._validateBusinessLogic(model);
    
    return true;
  }
  
  _validateBusinessLogic(model) {
    // Check for reasonable values
    if (model.baseline.mean < 0) {
      throw new Error('Baseline mean cannot be negative');
    }
    
    if (model.statistics.min > model.statistics.max) {
      throw new Error('Invalid statistics: min > max');
    }
    
    // Check timestamps are reasonable
    const now = Date.now();
    const oneYear = 365 * 24 * 60 * 60 * 1000;
    
    for (const event of model.spikes.events) {
      if (event.timestamp < now - oneYear || event.timestamp > now) {
        console.warn(`Warning: Spike timestamp may be invalid: ${new Date(event.timestamp)}`);
      }
    }
    
    // Check pattern confidence
    if (model.pattern.confidence < 0 || model.pattern.confidence > 1) {
      throw new Error('Pattern confidence must be between 0 and 1');
    }
  }
  
  getModelSummary(model) {
    return {
      version: model.version,
      patternType: model.pattern.type,
      confidence: model.pattern.confidence,
      baselineMean: model.baseline.mean,
      spikeCount: model.spikes.events.length,
      samples: model.metadata.samples,
      duration: model.metadata.duration,
      timestamp: model.metadata.timestamp
    };
  }
}