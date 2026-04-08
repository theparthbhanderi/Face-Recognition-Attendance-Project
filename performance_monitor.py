import psutil
import time
import threading
from camera import get_camera

class PerformanceMonitor:
    def __init__(self):
        self.running = False
        self.cpu_usage = []
        self.memory_usage = []
        self.fps = []
        self.last_frame_time = time.time()
        self.frame_count = 0
        
    def start_monitoring(self):
        """Start performance monitoring"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            print("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1)
        print("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Get CPU and memory usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_percent = psutil.virtual_memory().percent
                
                self.cpu_usage.append(cpu_percent)
                self.memory_usage.append(memory_percent)
                
                # Keep only last 100 samples
                if len(self.cpu_usage) > 100:
                    self.cpu_usage.pop(0)
                    self.memory_usage.pop(0)
                
                # Calculate FPS
                current_time = time.time()
                if current_time - self.last_frame_time >= 1.0:
                    fps = self.frame_count / (current_time - self.last_frame_time)
                    self.fps.append(fps)
                    if len(self.fps) > 100:
                        self.fps.pop(0)
                    self.frame_count = 0
                    self.last_frame_time = current_time
                
                # Print stats every 5 seconds
                if int(current_time) % 5 == 0:
                    avg_cpu = sum(self.cpu_usage[-10:]) / len(self.cpu_usage[-10:]) if self.cpu_usage else 0
                    avg_memory = sum(self.memory_usage[-10:]) / len(self.memory_usage[-10:]) if self.memory_usage else 0
                    avg_fps = sum(self.fps[-5:]) / len(self.fps[-5:]) if self.fps else 0
                    
                    print(f"Performance Stats - CPU: {avg_cpu:.1f}%, Memory: {avg_memory:.1f}%, FPS: {avg_fps:.1f}")
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in performance monitoring: {e}")
                time.sleep(1)
    
    def increment_frame_count(self):
        """Increment frame counter for FPS calculation"""
        self.frame_count += 1
    
    def get_current_stats(self):
        """Get current performance statistics"""
        return {
            'cpu_usage': self.cpu_usage[-1] if self.cpu_usage else 0,
            'memory_usage': self.memory_usage[-1] if self.memory_usage else 0,
            'fps': self.fps[-1] if self.fps else 0,
            'avg_cpu': sum(self.cpu_usage[-10:]) / len(self.cpu_usage[-10:]) if len(self.cpu_usage) >= 10 else 0,
            'avg_memory': sum(self.memory_usage[-10:]) / len(self.memory_usage[-10:]) if len(self.memory_usage) >= 10 else 0,
            'avg_fps': sum(self.fps[-5:]) / len(self.fps[-5:]) if len(self.fps) >= 5 else 0
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def start_performance_monitoring():
    """Start the performance monitor"""
    performance_monitor.start_monitoring()

def stop_performance_monitoring():
    """Stop the performance monitor"""
    performance_monitor.stop_monitoring()

def get_performance_stats():
    """Get current performance statistics"""
    return performance_monitor.get_current_stats()
