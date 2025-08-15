# 🎵 Rhythmic

> Match the rhythm of production - Transform Prometheus metrics into realistic K6 load tests using signal processing

[![npm version](https://img.shields.io/npm/v/rhythmic.svg)](https://www.npmjs.com/package/rhythmic)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is Rhythmic?

Rhythmic learns your production traffic patterns from Prometheus metrics and generates realistic K6 load tests. Using wavelet transforms and Fourier analysis, it detects periodicities, spikes, and trends in your traffic - then creates load tests that actually match production behavior.

## Why Rhythmic?

- **No more guessing** - Load tests based on real production patterns
- **Automatic pattern detection** - Finds daily, weekly, and seasonal patterns  
- **Spike modeling** - Captures and replays traffic bursts
- **Zero production impact** - Works from metrics, not live traffic
- **K6 native** - Generates standard K6 scripts you can customize

## Solution Comparison

| Feature | Rhythmic | Raw Data Replay | AI/ML Solutions | Manual Testing |
|---------|----------|-----------------|-----------------|----------------|
| **Data Security** | ✅ Mathematical patterns only | ❌ Raw production data | ⚠️ Training data dependent | ✅ No production data |
| **Scalability** | ✅ Multi-dimensional scaling | ❌ Fixed to recorded load | ⚠️ Model dependent | ❌ Manual adjustments |
| **Time Compression** | ✅ Days/weeks in hours | ❌ Real-time only | ❌ Real-time only | ✅ Any duration |
| **Pattern Discovery** | ✅ Automatic (Fourier/wavelet) | ❌ Manual analysis needed | ✅ Learned patterns | ❌ Manual definition |
| **Setup Complexity** | ✅ Simple (auto-setup) | ✅ Simple | ❌ Complex | ✅ Simple |

## Quick Start

### Installation

**Option 1: Quick Install (Recommended)**
```bash
npm install -g rhythmic
rhythmic setup  # Auto-installs Python dependencies
```

**Option 2: Manual Install**
```bash
npm install -g rhythmic
pip install -r requirements.txt
```

**Option 3: Docker (Zero Setup)**
```bash
docker run --rm -v $(pwd):/work rhythmic/rhythmic analyze \
  --prometheus http://host.docker.internal:9090 \
  --target https://api.example.com
```

### Basic Usage

1. **Learn patterns from Prometheus:**
```bash
rhythmic learn --prometheus http://localhost:9090 --metric http_requests_total
```

2. **Generate K6 test:**
```bash
rhythmic generate --target https://api.example.com --output load-test.js
```

3. **Run the test:**
```bash
k6 run load-test.js
```

### One-Shot Mode

```bash
rhythmic analyze \
  --prometheus http://localhost:9090 \
  --metric http_requests_total \
  --target https://staging.api.com \
  --output realistic-load-test.js
```

## How It Works

1. **Fetch** - Retrieves time-series data from Prometheus
2. **Decompose** - Uses wavelet transforms to separate baseline from spikes  
3. **Analyze** - Applies Fourier analysis to find periodic patterns
4. **Model** - Creates mathematical model of your traffic
5. **Generate** - Produces K6 script that replays these patterns

## Data Security & Privacy

Rhythmic is designed with **security-first principles** to protect your production data:

### 🔒 No Raw Data Exposure
- **Only statistical patterns** are extracted from your metrics
- **No actual request data** or sensitive information is stored
- Traffic models contain only mathematical coefficients and timing patterns
- Original metric values are aggregated and anonymized

### 🏢 Enterprise-Safe Workflow
```bash
# Production environment (CI/CD or secure environment)
rhythmic learn --prometheus http://internal-prometheus:9090 --output model.json

# Development environment (no production access needed)
rhythmic generate --input model.json --target https://staging.api.com
```

### 📁 Portable Models
- **Models are JSON files** containing only pattern analysis
- Can be safely shared across teams and environments
- No production credentials or raw data included
- Version control friendly for tracking pattern changes over time

### 🛡️ What's NOT Included in Models
- ❌ Raw metric values or time series data
- ❌ Server names, IPs, or infrastructure details  
- ❌ Authentication tokens or credentials
- ❌ Business logic or application code
- ❌ User data or personally identifiable information

### ✅ What IS Included in Models
- ✅ Mathematical pattern coefficients (Fourier analysis)
- ✅ Statistical summaries (mean, percentiles, variance)
- ✅ Timing patterns (daily/weekly cycles)
- ✅ Spike frequency distributions
- ✅ Metadata (metric name, duration, sample count)

## Advanced Features

### Scale Testing

**Amplitude Scaling** - Test with 2x your normal traffic:
```bash
rhythmic generate --scale 2 --output stress-test.js
```

**Time Compression** - Test 2 weeks of production load in 2 hours:
```bash
rhythmic generate --time-scale 84 --duration 2h --output compressed-test.js
```

**Combined Scaling** - 3x traffic + 7 days compressed to 1 hour:
```bash
rhythmic generate --scale 3 --time-scale 168 --duration 1h --output intense-test.js
```

#### Time Scale Examples

| Time Scale | Production Period | Test Duration | Use Case |
|------------|------------------|---------------|----------|
| `1` | Real-time | Real-time | Normal load testing |
| `24` | 24 hours | 1 hour | Daily cycle in 1 hour |
| `168` | 1 week | 1 hour | Weekly patterns in 1 hour |
| `720` | 1 month | 1 hour | Monthly trends in 1 hour |
| `0.5` | 30 minutes | 1 hour | Slow-motion analysis |

### Custom Metrics

Analyze any Prometheus metric:
```bash
rhythmic learn --metric 'sum(rate(api_requests_total{service="checkout"}[1m]))'
```

### CI/CD Integration

```yaml
# .github/workflows/load-test-patterns.yml
- name: Extract Traffic Patterns
  run: |
    rhythmic learn \
      --prometheus ${{ secrets.PROMETHEUS_URL }} \
      --metric http_requests_total \
      --output traffic-patterns.json

- name: Upload Pattern Model
  uses: actions/upload-artifact@v3
  with:
    name: traffic-patterns
    path: traffic-patterns.json
```

### Pattern Types Detected

- **Business hours** - Daily patterns with morning/evening peaks
- **Weekly cycles** - Different weekday vs weekend patterns  
- **Bursty** - Random spikes and traffic bursts
- **Seasonal** - Monthly or quarterly patterns
- **Flash traffic** - Sudden spike patterns (sales, campaigns)

## Requirements

- Node.js 18+
- Python 3.9+
- Prometheus with metrics history
- K6 for running generated tests

## License

MIT

## Contributing

Contributions welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

## Support

- 📖 [Documentation](https://github.com/yourusername/rhythmic/wiki)
- 💬 [Discussions](https://github.com/yourusername/rhythmic/discussions)  
- 🐛 [Issues](https://github.com/yourusername/rhythmic/issues)
