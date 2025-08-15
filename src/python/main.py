#!/usr/bin/env python3

import argparse
import sys
import json
import time
from pathlib import Path
import logging

from collectors.prometheus_collector import PrometheusCollector
from models.traffic_modeler import TrafficModeler
from utils.logger import setup_logger

def main():
    """Main entry point for Python analysis component"""
    parser = argparse.ArgumentParser(
        description='Rhythmic Traffic Pattern Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py learn --prometheus http://localhost:9090 --metric http_requests_total
  python main.py learn --metric 'rate(api_requests_total[1m])' --duration 3d --verbose
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Learn command
    learn_parser = subparsers.add_parser('learn', help='Analyze traffic patterns from Prometheus')
    learn_parser.add_argument('--prometheus', 
                             default='http://localhost:9090',
                             help='Prometheus server URL (default: http://localhost:9090)')
    learn_parser.add_argument('--metric', 
                             default='http_requests_total',
                             help='Metric name to analyze (default: http_requests_total)')
    learn_parser.add_argument('--duration', 
                             default='7d',
                             help='Lookback duration: 1h, 7d, 1w, 1m (default: 7d)')
    learn_parser.add_argument('--step', 
                             type=int, 
                             default=60,
                             help='Data resolution in seconds (default: 60)')
    learn_parser.add_argument('--output', 
                             default='traffic-model.json',
                             help='Output model file (default: traffic-model.json)')
    learn_parser.add_argument('--verbose', 
                             action='store_true',
                             help='Show detailed analysis output')
    learn_parser.add_argument('--wavelet',
                             default='db4',
                             help='Wavelet type for decomposition (default: db4)')
    learn_parser.add_argument('--spike-threshold',
                             type=float,
                             default=3.0,
                             help='Spike detection threshold in standard deviations (default: 3.0)')
    
    args = parser.parse_args()
    
    if args.command == 'learn':
        return run_learn(args)
    else:
        parser.print_help()
        return 1

def run_learn(args):
    """Execute the learn command - analyze traffic patterns"""
    logger = setup_logger(verbose=args.verbose)
    start_time = time.time()
    
    try:
        # 1. Test Prometheus connection
        logger.info(f"🔗 Connecting to Prometheus at {args.prometheus}")
        collector = PrometheusCollector(args.prometheus)
        
        if not collector.test_connection():
            logger.error(f"❌ Cannot connect to Prometheus at {args.prometheus}")
            logger.error("   Please check the URL and ensure Prometheus is running")
            return 1
        
        logger.info("✅ Prometheus connection successful")
        
        # 2. Collect metrics
        logger.info(f"📊 Fetching metric: {args.metric}")
        logger.info(f"   Duration: {args.duration}, Step: {args.step}s")
        
        traffic_data = collector.fetch_metrics(args.metric, args.duration, args.step)
        
        logger.info(f"✅ Collected {len(traffic_data['values'])} data points")
        logger.info(f"   Time range: {traffic_data['start_time']} to {traffic_data['end_time']}")
        
        # 3. Validate data quality
        values = traffic_data['values']
        if len(values) < 50:
            logger.warning(f"⚠️  Low data point count ({len(values)}). Consider longer duration or smaller step.")
        
        if all(v == 0 for v in values):
            logger.warning("⚠️  All values are zero. Check metric name and time range.")
        
        # 4. Analyze patterns
        logger.info("🧠 Analyzing traffic patterns...")
        modeler = TrafficModeler(
            wavelet_type=args.wavelet,
            spike_threshold=args.spike_threshold
        )
        
        model = modeler.model(traffic_data)
        
        # 5. Validate model
        warnings = modeler.validate_model(model)
        if warnings:
            logger.warning("⚠️  Model validation warnings:")
            for warning in warnings:
                logger.warning(f"   • {warning}")
        
        # 6. Add timing metadata
        analysis_duration = (time.time() - start_time) * 1000
        model['metadata']['analysis_duration_ms'] = analysis_duration
        
        # 7. Save model
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(model, f, indent=2)
        
        # 8. Display results summary
        logger.info(f"💾 Model saved to {args.output}")
        logger.info(f"⚡ Analysis completed in {analysis_duration:.0f}ms")
        
        _display_model_summary(model, logger)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Analysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1

def _display_model_summary(model, logger):
    """Display a summary of the generated model"""
    logger.info("\n📈 Traffic Pattern Summary:")
    logger.info("=" * 50)
    
    # Pattern type and confidence
    pattern = model['pattern']
    logger.info(f"🎯 Pattern Type: {pattern['type']} (confidence: {pattern['confidence']:.2f})")
    
    # Baseline statistics
    baseline = model['baseline']
    stats = model['statistics']
    logger.info(f"📊 Baseline: {baseline['mean']:.2f} ± {baseline['std']:.2f} req/s")
    logger.info(f"📊 Range: {stats['min']:.2f} - {stats['max']:.2f} req/s")
    logger.info(f"📊 P95: {stats['p95']:.2f} req/s, P99: {stats['p99']:.2f} req/s")
    
    # Periodic patterns
    coeffs = baseline['coefficients']
    if coeffs:
        logger.info(f"🌊 Periodic Components: {len(coeffs)}")
        for i, coeff in enumerate(coeffs[:3]):  # Show top 3
            period_str = _format_period(coeff['period_minutes'])
            logger.info(f"   {i+1}. Period: {period_str}, Strength: {coeff['confidence']:.2f}")
    else:
        logger.info("🌊 No significant periodic patterns detected")
    
    # Spike events
    spikes = model['spikes']
    spike_count = len(spikes['events'])
    if spike_count > 0:
        logger.info(f"⚡ Spike Events: {spike_count}")
        if spike_count > 0:
            avg_magnitude = sum(e['magnitude'] for e in spikes['events']) / spike_count
            logger.info(f"   Average magnitude: {avg_magnitude:.2f} req/s")
            logger.info(f"   Distribution: {spikes['distribution']['type']}")
    else:
        logger.info("⚡ No significant spikes detected")
    
    # Pattern flags
    flags = []
    if pattern['daily']: flags.append('Daily')
    if pattern['weekly']: flags.append('Weekly')  
    if pattern['seasonal']: flags.append('Seasonal')
    
    if flags:
        logger.info(f"🔄 Detected Cycles: {', '.join(flags)}")
    
    logger.info("=" * 50)

def _format_period(period_minutes):
    """Format period in human-readable form"""
    if period_minutes < 60:
        return f"{period_minutes:.1f}m"
    elif period_minutes < 1440:  # < 24h
        hours = period_minutes / 60
        return f"{hours:.1f}h"
    else:  # >= 24h
        days = period_minutes / 1440
        return f"{days:.1f}d"

if __name__ == '__main__':
    sys.exit(main())