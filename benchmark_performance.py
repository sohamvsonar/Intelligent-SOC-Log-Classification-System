#!/usr/bin/env python3
"""
Performance Benchmarking Tool for Log Classification System
Compares standard vs high-performance processing across different dataset sizes
"""

import sys
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import json
from typing import List, Dict, Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def benchmark_processors():
    """Compare performance between standard and high-performance processors"""
    
    print("Log Classification System - Performance Benchmark")
    print("=" * 60)
    
    # Test dataset sizes
    test_sizes = [100, 500, 1000, 2000, 5000]
    results = {
        'dataset_sizes': test_sizes,
        'standard_times': [],
        'high_performance_times': [],
        'standard_throughput': [],
        'high_performance_throughput': [],
        'speedup_ratios': []
    }
    
    # Load test data
    print("Loading test datasets...")
    try:
        large_df = pd.read_csv("resources/synthetic_test_data_large.csv")
        print(f"Loaded {len(large_df)} test records")
    except FileNotFoundError:
        print("Error: Test data not found. Run 'python generate_test_data.py' first")
        return
    
    for size in test_sizes:
        print(f"\n{'='*40}")
        print(f"Benchmarking with {size} logs")
        print(f"{'='*40}")
        
        # Sample data for this test size
        test_df = large_df.sample(n=min(size, len(large_df))).reset_index(drop=True)
        logs = list(zip(test_df['source'], test_df['log_message']))
        
        # Test 1: Standard Processor
        print(f"Testing Standard Processor...")
        try:
            from processors.enhanced_processor import EnhancedLogProcessor
            
            processor = EnhancedLogProcessor()
            
            start_time = time.time()
            standard_results = []
            
            for source, log_message in logs:
                result = processor.classify_and_store(source, log_message, store_in_db=False)
                standard_results.append(result)
            
            standard_time = time.time() - start_time
            processor.close()
            
            print(f"  Standard Time: {standard_time:.2f}s")
            print(f"  Standard Throughput: {len(logs)/standard_time:.1f} logs/sec")
            
            results['standard_times'].append(standard_time)
            results['standard_throughput'].append(len(logs)/standard_time)
            
        except Exception as e:
            print(f"  Standard Processor Error: {e}")
            results['standard_times'].append(None)
            results['standard_throughput'].append(None)
        
        # Test 2: High-Performance Processor
        print(f"Testing High-Performance Processor...")
        try:
            from processors.high_performance_processor import HighPerformanceLogProcessor
            
            # Test different worker configurations
            max_workers = min(4, os.cpu_count()) if size > 500 else 2
            batch_size = min(100, size // 4) if size > 100 else 50
            
            processor = HighPerformanceLogProcessor(
                max_workers=max_workers,
                batch_size=batch_size,
                use_database=False
            )
            
            start_time = time.time()
            hp_results = processor.process_large_dataset(logs, store_in_db=False)
            hp_time = time.time() - start_time
            
            processor.close()
            
            print(f"  High-Performance Time: {hp_time:.2f}s")
            print(f"  High-Performance Throughput: {len(logs)/hp_time:.1f} logs/sec")
            
            results['high_performance_times'].append(hp_time)
            results['high_performance_throughput'].append(len(logs)/hp_time)
            
            # Calculate speedup ratio
            if standard_time and hp_time:
                speedup = standard_time / hp_time
                print(f"  Speedup: {speedup:.1f}x faster")
                results['speedup_ratios'].append(speedup)
            else:
                results['speedup_ratios'].append(None)
            
        except Exception as e:
            print(f"  High-Performance Processor Error: {e}")
            results['high_performance_times'].append(None)
            results['high_performance_throughput'].append(None)
            results['speedup_ratios'].append(None)
        
        # Brief pause between tests
        time.sleep(1)
    
    return results

def create_performance_report(results: Dict[str, List]):
    """Create performance report with charts"""
    
    print(f"\n{'='*60}")
    print("PERFORMANCE BENCHMARK RESULTS")
    print(f"{'='*60}")
    
    # Summary table
    print(f"{'Size':<8} {'Standard(s)':<12} {'HiPerf(s)':<12} {'Speedup':<10} {'Standard(l/s)':<15} {'HiPerf(l/s)':<15}")
    print("-" * 80)
    
    for i, size in enumerate(results['dataset_sizes']):
        std_time = results['standard_times'][i]
        hp_time = results['high_performance_times'][i]
        speedup = results['speedup_ratios'][i]
        std_throughput = results['standard_throughput'][i]
        hp_throughput = results['high_performance_throughput'][i]
        
        print(f"{size:<8} {std_time:<12.2f} {hp_time:<12.2f} {speedup:<10.1f} "
              f"{std_throughput:<15.1f} {hp_throughput:<15.1f}")
    
    # Key insights
    print(f"\nKEY INSIGHTS:")
    
    valid_speedups = [s for s in results['speedup_ratios'] if s is not None]
    if valid_speedups:
        avg_speedup = sum(valid_speedups) / len(valid_speedups)
        max_speedup = max(valid_speedups)
        print(f"  Average Speedup: {avg_speedup:.1f}x")
        print(f"  Maximum Speedup: {max_speedup:.1f}x")
    
    valid_hp_throughput = [t for t in results['high_performance_throughput'] if t is not None]
    if valid_hp_throughput:
        max_throughput = max(valid_hp_throughput)
        print(f"  Peak Throughput: {max_throughput:.1f} logs/second")
    
    # Recommendations
    print(f"\nRECOMMendations:")
    print(f"  - Use high-performance processor for datasets > 500 logs")
    print(f"  - Optimal batch size: 100-200 logs per batch")
    print(f"  - Recommended workers: {min(4, os.cpu_count())} (based on CPU cores)")
    
    # Save results to JSON
    results_file = "benchmark_results.json"
    with open(results_file, 'w') as f:
        # Convert None values to null for JSON serialization
        json_results = {}
        for key, values in results.items():
            json_results[key] = [v if v is not None else None for v in values]
        
        json.dump({
            'benchmark_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_info': {
                'cpu_count': os.cpu_count(),
                'platform': sys.platform
            },
            'results': json_results
        }, f, indent=2)
    
    print(f"\nResults saved to: {results_file}")
    
    # Create visualization if matplotlib available
    try:
        create_performance_charts(results)
    except ImportError:
        print("Matplotlib not available - skipping charts")
    except Exception as e:
        print(f"Chart creation failed: {e}")

def create_performance_charts(results: Dict[str, List]):
    """Create performance visualization charts"""
    
    # Filter out None values for plotting
    sizes = []
    std_times = []
    hp_times = []
    speedups = []
    
    for i, size in enumerate(results['dataset_sizes']):
        if (results['standard_times'][i] is not None and 
            results['high_performance_times'][i] is not None):
            sizes.append(size)
            std_times.append(results['standard_times'][i])
            hp_times.append(results['high_performance_times'][i])
            speedups.append(results['speedup_ratios'][i])
    
    if not sizes:
        print("No valid data for charts")
        return
    
    # Create subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Log Classification Performance Benchmark', fontsize=16)
    
    # Chart 1: Processing Time Comparison
    ax1.plot(sizes, std_times, 'o-', label='Standard Processor', linewidth=2, markersize=8)
    ax1.plot(sizes, hp_times, 's-', label='High-Performance Processor', linewidth=2, markersize=8)
    ax1.set_xlabel('Dataset Size (logs)')
    ax1.set_ylabel('Processing Time (seconds)')
    ax1.set_title('Processing Time Comparison')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')
    
    # Chart 2: Throughput Comparison
    std_throughput = [results['standard_throughput'][i] for i, _ in enumerate(sizes)]
    hp_throughput = [results['high_performance_throughput'][i] for i, _ in enumerate(sizes)]
    
    ax2.plot(sizes, std_throughput, 'o-', label='Standard Processor', linewidth=2, markersize=8)
    ax2.plot(sizes, hp_throughput, 's-', label='High-Performance Processor', linewidth=2, markersize=8)
    ax2.set_xlabel('Dataset Size (logs)')
    ax2.set_ylabel('Throughput (logs/second)')
    ax2.set_title('Throughput Comparison')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Chart 3: Speedup Factor
    ax3.plot(sizes, speedups, 'ro-', linewidth=2, markersize=8)
    ax3.set_xlabel('Dataset Size (logs)')
    ax3.set_ylabel('Speedup Factor (x)')
    ax3.set_title('Performance Speedup')
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=1, color='k', linestyle='--', alpha=0.5, label='No improvement')
    ax3.legend()
    
    # Chart 4: Efficiency Comparison (Bar Chart)
    x_pos = range(len(sizes))
    width = 0.35
    
    ax4.bar([x - width/2 for x in x_pos], std_throughput, width, label='Standard', alpha=0.8)
    ax4.bar([x + width/2 for x in x_pos], hp_throughput, width, label='High-Performance', alpha=0.8)
    ax4.set_xlabel('Dataset Size')
    ax4.set_ylabel('Throughput (logs/second)')
    ax4.set_title('Throughput Comparison (Bar Chart)')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels([f'{s} logs' for s in sizes])
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # Save chart
    chart_file = "performance_benchmark.png"
    plt.savefig(chart_file, dpi=300, bbox_inches='tight')
    print(f"Performance charts saved to: {chart_file}")
    
    # Try to display if running interactively
    try:
        plt.show()
    except:
        pass  # Running in non-interactive environment

def quick_performance_test():
    """Run a quick performance test with current system"""
    print("Quick Performance Test")
    print("=" * 30)
    
    try:
        # Load small dataset
        df = pd.read_csv("resources/quick_test.csv")
        logs = list(zip(df['source'], df['log_message']))
        
        print(f"Testing with {len(logs)} logs...")
        
        # Test high-performance processor
        from processors.high_performance_processor import process_logs_high_performance
        
        start_time = time.time()
        results = process_logs_high_performance(logs, store_in_db=False)
        end_time = time.time()
        
        processing_time = end_time - start_time
        throughput = len(results) / processing_time
        
        print(f"Results:")
        print(f"  Processing Time: {processing_time:.2f}s")
        print(f"  Throughput: {throughput:.1f} logs/second")
        print(f"  Average per log: {(processing_time * 1000) / len(results):.1f}ms")
        
        return True
        
    except Exception as e:
        print(f"Quick test failed: {e}")
        return False

def main():
    """Main benchmark function"""
    
    # Check if test data exists
    if not os.path.exists("resources/synthetic_test_data_large.csv"):
        print("Test data not found. Generating...")
        try:
            os.system("python generate_test_data.py")
        except:
            print("Failed to generate test data. Please run 'python generate_test_data.py' first")
            return
    
    # Ask user what they want to do
    print("Performance Benchmarking Options:")
    print("1. Quick test (100 logs)")
    print("2. Full benchmark (100, 500, 1000, 2000, 5000 logs)")
    
    choice = input("\nSelect option (1 or 2): ").strip()
    
    if choice == "1":
        quick_performance_test()
    elif choice == "2":
        results = benchmark_processors()
        if results:
            create_performance_report(results)
    else:
        print("Invalid choice. Running quick test...")
        quick_performance_test()

if __name__ == "__main__":
    main()