#include <iostream>
#include <chrono>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <sched.h>
#include <signal.h>

/**
 * Benchmark RT Loop Jitter
 * Measures the precision of a 1000Hz (1ms) loop.
 */

volatile bool g_stop = false;
void handle_sig(int) { g_stop = true; }

int main() {
    signal(SIGINT, handle_sig);

#ifndef __APPLE__
    struct sched_param param;
    param.sched_priority = 90;
    if (sched_setscheduler(0, SCHED_FIFO, &param) == -1) {
        std::cerr << "Warning: Failed to set SCHED_FIFO. Jitter results will be poor." << std::endl;
    }
#endif

    const int iterations = 5000; // 5 seconds at 1000Hz
    const auto interval = std::chrono::microseconds(1000);
    std::vector<double> jitters;
    jitters.reserve(iterations);

    auto next_tick = std::chrono::steady_clock::now();
    
    std::cout << "Starting 1kHz Jitter Benchmark (" << iterations << " iterations)..." << std::endl;

    for (int i = 0; i < iterations && !g_stop; ++i) {
        auto t1 = std::chrono::steady_clock::now();
        
        next_tick += interval;
        std::this_thread::sleep_until(next_tick);
        
        auto t2 = std::chrono::steady_clock::now();
        auto actual_dt = std::chrono::duration_cast<std::chrono::microseconds>(t2 - t1).count();
        double jitter = std::abs(static_cast<double>(actual_dt) - 1000.0);
        jitters.push_back(jitter);
    }

    if (jitters.empty()) return 0;

    double sum = std::accumulate(jitters.begin(), jitters.end(), 0.0);
    double avg = sum / jitters.size();
    
    std::sort(jitters.begin(), jitters.end());
    double p50 = jitters[jitters.size() * 0.5];
    double p95 = jitters[jitters.size() * 0.95];
    double p99 = jitters[jitters.size() * 0.99];
    double max_j = jitters.back();

    std::cout << "\n--- Benchmark Results (microseconds) ---" << std::endl;
    printf("Average Jitter: %7.2f us\n", avg);
    printf("50th Percentile: %7.2f us\n", p50);
    printf("95th Percentile: %7.2f us\n", p95);
    printf("99th Percentile: %7.2f us\n", p99);
    printf("Max Jitter:     %7.2f us\n", max_j);
    std::cout << "-----------------------------------------" << std::endl;

    return 0;
}
