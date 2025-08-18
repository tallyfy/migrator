#!/usr/bin/env python3
"""
Migration Performance Testing Suite
Tests performance, memory usage, and scalability of migrators
"""

import time
import json
import psutil
import tracemalloc
import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import concurrent.futures
import matplotlib.pyplot as plt
import numpy as np


@dataclass
class PerformanceMetric:
    """Performance measurement result"""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    details: Dict[str, Any] = None


class MigrationPerformanceTester:
    """Performance testing for migration systems"""
    
    def __init__(self, vendor_name: str):
        """
        Initialize performance tester
        
        Args:
            vendor_name: Name of vendor being tested
        """
        self.vendor_name = vendor_name
        self.metrics: List[PerformanceMetric] = []
        self.test_id = f"{vendor_name}_perf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    # ============= DATA GENERATION =============
    
    def generate_test_data(self, size: str = "medium") -> Dict[str, Any]:
        """
        Generate test data of various sizes
        
        Args:
            size: small (100 items), medium (1000 items), large (10000 items), xlarge (100000 items)
        """
        sizes = {
            "small": {"users": 10, "templates": 5, "instances": 100, "fields": 20},
            "medium": {"users": 50, "templates": 20, "instances": 1000, "fields": 50},
            "large": {"users": 200, "templates": 50, "instances": 10000, "fields": 100},
            "xlarge": {"users": 1000, "templates": 200, "instances": 100000, "fields": 200}
        }
        
        config = sizes.get(size, sizes["medium"])
        
        # Generate users
        users = [
            {
                "id": f"u_{i}",
                "email": f"user{i}@example.com",
                "name": f"Test User {i}",
                "role": random.choice(["admin", "member", "guest"]),
                "metadata": {"created": datetime.now().isoformat()}
            }
            for i in range(config["users"])
        ]
        
        # Generate templates/workflows
        templates = []
        for t in range(config["templates"]):
            template = {
                "id": f"t_{t}",
                "name": f"Template {t}",
                "description": f"Test template {t} with various fields",
                "fields": [
                    {
                        "id": f"f_{t}_{f}",
                        "name": f"Field {f}",
                        "type": random.choice(["text", "number", "date", "dropdown", "checkbox"]),
                        "required": random.choice([True, False])
                    }
                    for f in range(random.randint(10, config["fields"]))
                ],
                "steps": [
                    {
                        "id": f"s_{t}_{s}",
                        "name": f"Step {s}",
                        "type": random.choice(["task", "approval", "notification"]),
                        "assignee": random.choice(users)["id"] if users else None
                    }
                    for s in range(random.randint(5, 20))
                ]
            }
            templates.append(template)
        
        # Generate instances
        instances = []
        for i in range(config["instances"]):
            template = random.choice(templates) if templates else None
            instance = {
                "id": f"i_{i}",
                "template_id": template["id"] if template else None,
                "status": random.choice(["active", "completed", "cancelled"]),
                "created": (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
                "data": {
                    f"field_{f}": f"value_{f}_{random.randint(0, 100)}"
                    for f in range(random.randint(5, 20))
                }
            }
            instances.append(instance)
        
        return {
            "users": users,
            "templates": templates,
            "instances": instances,
            "size": size,
            "totals": {
                "users": len(users),
                "templates": len(templates),
                "instances": len(instances),
                "total_items": len(users) + len(templates) + len(instances)
            }
        }
    
    # ============= PERFORMANCE TESTS =============
    
    def test_batch_processing(self, data: Dict[str, Any], batch_sizes: List[int] = None) -> Dict[str, Any]:
        """Test different batch processing sizes"""
        if not batch_sizes:
            batch_sizes = [10, 50, 100, 500, 1000]
        
        results = {}
        items = data.get("instances", [])
        
        for batch_size in batch_sizes:
            start_time = time.time()
            processed = 0
            
            # Process in batches
            for i in range(0, len(items), batch_size):
                batch = items[i:i+batch_size]
                # Simulate processing
                time.sleep(0.001 * len(batch))  # 1ms per item
                processed += len(batch)
            
            elapsed = time.time() - start_time
            throughput = processed / elapsed if elapsed > 0 else 0
            
            results[f"batch_{batch_size}"] = {
                "batch_size": batch_size,
                "total_items": processed,
                "elapsed_seconds": elapsed,
                "throughput_per_second": throughput,
                "optimal": False
            }
            
            metric = PerformanceMetric(
                metric_name=f"batch_processing_{batch_size}",
                value=throughput,
                unit="items/second",
                timestamp=datetime.now(),
                details=results[f"batch_{batch_size}"]
            )
            self.metrics.append(metric)
        
        # Find optimal batch size
        optimal = max(results.items(), key=lambda x: x[1]["throughput_per_second"])
        results[optimal[0]]["optimal"] = True
        
        return results
    
    def test_memory_usage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test memory usage during processing"""
        tracemalloc.start()
        
        # Get baseline memory
        baseline = tracemalloc.take_snapshot()
        
        # Process data
        processed_data = []
        for _ in range(3):  # Simulate multiple passes
            for item in data.get("instances", []):
                # Simulate data transformation
                transformed = {
                    **item,
                    "processed": True,
                    "timestamp": datetime.now().isoformat(),
                    "additional_data": "x" * 1000  # Add some bulk
                }
                processed_data.append(transformed)
        
        # Get peak memory
        peak = tracemalloc.take_snapshot()
        
        # Calculate memory usage
        top_stats = peak.compare_to(baseline, 'lineno')
        total_memory = sum(stat.size for stat in top_stats) / 1024 / 1024  # MB
        
        # Clear memory
        processed_data.clear()
        del processed_data
        
        # Get memory after cleanup
        after_cleanup = tracemalloc.take_snapshot()
        cleanup_stats = after_cleanup.compare_to(baseline, 'lineno')
        memory_after = sum(stat.size for stat in cleanup_stats) / 1024 / 1024  # MB
        
        tracemalloc.stop()
        
        results = {
            "peak_memory_mb": total_memory,
            "memory_after_cleanup_mb": memory_after,
            "memory_released_mb": total_memory - memory_after,
            "items_processed": len(data.get("instances", [])) * 3,
            "memory_per_item_kb": (total_memory * 1024) / (len(data.get("instances", [])) * 3) if data.get("instances") else 0
        }
        
        metric = PerformanceMetric(
            metric_name="memory_usage",
            value=total_memory,
            unit="MB",
            timestamp=datetime.now(),
            details=results
        )
        self.metrics.append(metric)
        
        return results
    
    def test_concurrent_processing(self, data: Dict[str, Any], max_workers: int = 5) -> Dict[str, Any]:
        """Test concurrent processing performance"""
        items = data.get("instances", [])
        
        def process_item(item):
            """Simulate processing an item"""
            time.sleep(random.uniform(0.01, 0.05))  # 10-50ms processing time
            return {"id": item["id"], "processed": True}
        
        # Sequential processing
        seq_start = time.time()
        seq_results = []
        for item in items[:100]:  # Test with first 100 items
            seq_results.append(process_item(item))
        seq_elapsed = time.time() - seq_start
        
        # Concurrent processing
        conc_start = time.time()
        conc_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_item, item) for item in items[:100]]
            conc_results = [f.result() for f in concurrent.futures.as_completed(futures)]
        conc_elapsed = time.time() - conc_start
        
        speedup = seq_elapsed / conc_elapsed if conc_elapsed > 0 else 0
        
        results = {
            "sequential_time": seq_elapsed,
            "concurrent_time": conc_elapsed,
            "speedup": speedup,
            "efficiency": speedup / max_workers,
            "max_workers": max_workers,
            "items_processed": 100
        }
        
        metric = PerformanceMetric(
            metric_name="concurrent_processing",
            value=speedup,
            unit="x speedup",
            timestamp=datetime.now(),
            details=results
        )
        self.metrics.append(metric)
        
        return results
    
    async def test_async_operations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test async operation performance"""
        
        async def async_api_call(item_id: str):
            """Simulate async API call"""
            await asyncio.sleep(random.uniform(0.05, 0.15))  # 50-150ms latency
            return {"id": item_id, "data": "processed"}
        
        items = data.get("instances", [])[:50]  # Test with 50 items
        
        # Synchronous simulation
        sync_start = time.time()
        for item in items:
            await async_api_call(item["id"])
        sync_time = time.time() - sync_start
        
        # Async batch
        async_start = time.time()
        tasks = [async_api_call(item["id"]) for item in items]
        await asyncio.gather(*tasks)
        async_time = time.time() - async_start
        
        improvement = (sync_time - async_time) / sync_time if sync_time > 0 else 0
        
        results = {
            "sync_time": sync_time,
            "async_time": async_time,
            "improvement_percent": improvement * 100,
            "items_processed": len(items),
            "avg_latency_sync": sync_time / len(items) if items else 0,
            "avg_latency_async": async_time / len(items) if items else 0
        }
        
        metric = PerformanceMetric(
            metric_name="async_operations",
            value=improvement * 100,
            unit="% improvement",
            timestamp=datetime.now(),
            details=results
        )
        self.metrics.append(metric)
        
        return results
    
    def test_api_rate_limiting(self, requests_per_second: List[int] = None) -> Dict[str, Any]:
        """Test API rate limiting strategies"""
        if not requests_per_second:
            requests_per_second = [1, 5, 10, 20, 50, 100]
        
        results = {}
        
        for rps in requests_per_second:
            delay = 1.0 / rps
            start_time = time.time()
            successful = 0
            failed = 0
            
            # Simulate API calls
            for i in range(100):  # Make 100 calls
                time.sleep(delay)
                
                # Simulate rate limit (fail if too fast)
                if random.random() > 0.95:  # 5% failure rate
                    failed += 1
                    time.sleep(1)  # Backoff
                else:
                    successful += 1
            
            elapsed = time.time() - start_time
            actual_rps = successful / elapsed if elapsed > 0 else 0
            
            results[f"rps_{rps}"] = {
                "target_rps": rps,
                "actual_rps": actual_rps,
                "successful": successful,
                "failed": failed,
                "elapsed": elapsed,
                "efficiency": actual_rps / rps if rps > 0 else 0
            }
        
        # Find optimal rate
        optimal = max(results.items(), 
                     key=lambda x: x[1]["actual_rps"] * (1 - x[1]["failed"]/100))
        
        return results
    
    def test_checkpoint_resume(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test checkpoint and resume performance"""
        items = data.get("instances", [])
        checkpoint_interval = 100
        
        # Simulate processing with checkpoints
        start_time = time.time()
        checkpoints = []
        
        for i in range(0, len(items), checkpoint_interval):
            batch = items[i:i+checkpoint_interval]
            
            # Process batch
            process_start = time.time()
            time.sleep(0.001 * len(batch))  # Simulate processing
            
            # Save checkpoint
            checkpoint_start = time.time()
            checkpoint = {
                "position": i + len(batch),
                "timestamp": datetime.now().isoformat(),
                "data": {"last_id": batch[-1]["id"] if batch else None}
            }
            checkpoints.append(checkpoint)
            checkpoint_time = time.time() - checkpoint_start
            
            process_time = time.time() - process_start
        
        total_time = time.time() - start_time
        
        # Simulate resume from checkpoint
        resume_position = len(items) // 2
        resume_start = time.time()
        
        # Find checkpoint
        checkpoint = next((c for c in checkpoints if c["position"] >= resume_position), None)
        
        # Resume processing
        if checkpoint:
            remaining = items[checkpoint["position"]:]
            time.sleep(0.001 * len(remaining))  # Simulate processing
        
        resume_time = time.time() - resume_start
        
        results = {
            "total_items": len(items),
            "checkpoint_interval": checkpoint_interval,
            "num_checkpoints": len(checkpoints),
            "processing_time": total_time,
            "checkpoint_overhead": sum(0.001 for _ in checkpoints),  # Rough estimate
            "resume_time": resume_time,
            "resume_efficiency": resume_time / (total_time/2) if total_time > 0 else 0
        }
        
        metric = PerformanceMetric(
            metric_name="checkpoint_resume",
            value=results["resume_efficiency"],
            unit="efficiency ratio",
            timestamp=datetime.now(),
            details=results
        )
        self.metrics.append(metric)
        
        return results
    
    # ============= SCALABILITY TESTS =============
    
    def test_scalability(self) -> Dict[str, Any]:
        """Test system scalability with increasing data sizes"""
        sizes = ["small", "medium", "large"]
        results = {}
        
        for size in sizes:
            print(f"Testing scalability with {size} dataset...")
            data = self.generate_test_data(size)
            
            start_time = time.time()
            
            # Simulate full migration
            for category in ["users", "templates", "instances"]:
                items = data.get(category, [])
                for item in items:
                    # Simulate processing
                    time.sleep(0.0001)  # 0.1ms per item
            
            elapsed = time.time() - start_time
            throughput = data["totals"]["total_items"] / elapsed if elapsed > 0 else 0
            
            results[size] = {
                "total_items": data["totals"]["total_items"],
                "elapsed_seconds": elapsed,
                "throughput": throughput,
                "breakdown": data["totals"]
            }
        
        # Calculate scalability factor
        if "small" in results and "large" in results:
            item_ratio = results["large"]["total_items"] / results["small"]["total_items"]
            time_ratio = results["large"]["elapsed_seconds"] / results["small"]["elapsed_seconds"]
            scalability_factor = item_ratio / time_ratio if time_ratio > 0 else 0
            
            results["scalability_factor"] = scalability_factor
            results["is_linear"] = 0.8 <= scalability_factor <= 1.2
        
        return results
    
    # ============= REPORTING =============
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "test_id": self.test_id,
            "vendor": self.vendor_name,
            "timestamp": datetime.now().isoformat(),
            "metrics": [
                {
                    "name": m.metric_name,
                    "value": m.value,
                    "unit": m.unit,
                    "timestamp": m.timestamp.isoformat(),
                    "details": m.details
                }
                for m in self.metrics
            ],
            "summary": self._generate_summary(),
            "recommendations": self._generate_recommendations()
        }
        
        # Save report
        report_dir = Path(f"performance_reports/{self.vendor_name}")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        with open(report_dir / f"{self.test_id}.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate performance summary"""
        if not self.metrics:
            return {}
        
        # Find key metrics
        batch_metrics = [m for m in self.metrics if "batch" in m.metric_name]
        memory_metrics = [m for m in self.metrics if "memory" in m.metric_name]
        concurrent_metrics = [m for m in self.metrics if "concurrent" in m.metric_name]
        
        summary = {
            "total_tests": len(self.metrics),
            "test_categories": len(set(m.metric_name.split("_")[0] for m in self.metrics))
        }
        
        if batch_metrics:
            best_batch = max(batch_metrics, key=lambda m: m.value)
            summary["optimal_batch_size"] = best_batch.details.get("batch_size")
            summary["max_throughput"] = best_batch.value
        
        if memory_metrics:
            summary["peak_memory_mb"] = max(m.value for m in memory_metrics)
        
        if concurrent_metrics:
            summary["concurrency_speedup"] = max(m.value for m in concurrent_metrics)
        
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Analyze metrics
        for metric in self.metrics:
            if "batch" in metric.metric_name and metric.details.get("optimal"):
                recommendations.append(
                    f"Use batch size of {metric.details['batch_size']} for optimal throughput"
                )
            
            if "memory" in metric.metric_name:
                if metric.value > 1000:  # Over 1GB
                    recommendations.append(
                        "High memory usage detected. Consider processing in smaller chunks"
                    )
            
            if "concurrent" in metric.metric_name:
                if metric.details.get("efficiency", 0) < 0.5:
                    recommendations.append(
                        "Low concurrency efficiency. Consider reducing worker count"
                    )
        
        return list(set(recommendations))
    
    def plot_performance_graphs(self):
        """Generate performance visualization graphs"""
        if not self.metrics:
            return
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Performance Analysis - {self.vendor_name}', fontsize=16)
        
        # Throughput by batch size
        batch_metrics = [m for m in self.metrics if "batch" in m.metric_name]
        if batch_metrics:
            batch_sizes = [m.details["batch_size"] for m in batch_metrics]
            throughputs = [m.value for m in batch_metrics]
            
            axes[0, 0].bar(batch_sizes, throughputs)
            axes[0, 0].set_xlabel('Batch Size')
            axes[0, 0].set_ylabel('Throughput (items/sec)')
            axes[0, 0].set_title('Throughput by Batch Size')
            axes[0, 0].set_xscale('log')
        
        # Memory usage
        memory_metrics = [m for m in self.metrics if "memory" in m.metric_name]
        if memory_metrics:
            categories = ['Peak', 'After Cleanup']
            values = [
                memory_metrics[0].details["peak_memory_mb"],
                memory_metrics[0].details["memory_after_cleanup_mb"]
            ]
            
            axes[0, 1].bar(categories, values, color=['red', 'green'])
            axes[0, 1].set_ylabel('Memory (MB)')
            axes[0, 1].set_title('Memory Usage')
        
        # Concurrency speedup
        concurrent_metrics = [m for m in self.metrics if "concurrent" in m.metric_name]
        if concurrent_metrics:
            labels = ['Sequential', 'Concurrent']
            times = [
                concurrent_metrics[0].details["sequential_time"],
                concurrent_metrics[0].details["concurrent_time"]
            ]
            
            axes[1, 0].bar(labels, times, color=['blue', 'orange'])
            axes[1, 0].set_ylabel('Time (seconds)')
            axes[1, 0].set_title(f'Concurrency Speedup: {concurrent_metrics[0].value:.2f}x')
        
        # Overall metrics
        all_values = [m.value for m in self.metrics]
        all_names = [m.metric_name.replace("_", " ").title()[:15] for m in self.metrics]
        
        axes[1, 1].barh(all_names, all_values)
        axes[1, 1].set_xlabel('Metric Value')
        axes[1, 1].set_title('All Metrics Summary')
        
        plt.tight_layout()
        
        # Save figure
        report_dir = Path(f"performance_reports/{self.vendor_name}")
        report_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(report_dir / f"{self.test_id}_graphs.png", dpi=100)
        plt.close()
    
    def print_summary(self):
        """Print performance summary to console"""
        print("\n" + "="*60)
        print(f"PERFORMANCE TEST SUMMARY - {self.vendor_name}")
        print("="*60)
        
        summary = self._generate_summary()
        
        for key, value in summary.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        
        print("\nRecommendations:")
        for rec in self._generate_recommendations():
            print(f"  • {rec}")
        
        print("="*60 + "\n")


# Example usage
async def run_performance_tests():
    """Run complete performance test suite"""
    tester = MigrationPerformanceTester("example_vendor")
    
    # Generate test data
    print("Generating test data...")
    data = tester.generate_test_data("medium")
    print(f"Generated {data['totals']['total_items']} test items")
    
    # Run tests
    print("\nRunning performance tests...")
    
    print("1. Testing batch processing...")
    batch_results = tester.test_batch_processing(data)
    
    print("2. Testing memory usage...")
    memory_results = tester.test_memory_usage(data)
    
    print("3. Testing concurrent processing...")
    concurrent_results = tester.test_concurrent_processing(data)
    
    print("4. Testing async operations...")
    async_results = await tester.test_async_operations(data)
    
    print("5. Testing checkpoint/resume...")
    checkpoint_results = tester.test_checkpoint_resume(data)
    
    print("6. Testing scalability...")
    scalability_results = tester.test_scalability()
    
    # Generate reports
    print("\nGenerating reports...")
    report = tester.generate_performance_report()
    tester.plot_performance_graphs()
    tester.print_summary()
    
    print(f"\nPerformance testing complete. Reports saved to performance_reports/")
    
    return report


if __name__ == "__main__":
    # Run async tests
    asyncio.run(run_performance_tests())