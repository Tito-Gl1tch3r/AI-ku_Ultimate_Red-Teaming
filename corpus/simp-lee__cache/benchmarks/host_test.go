package benchmarks

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"testing"
)

const canonicalCPUModel = "Intel(R) Core(TM) i7-6700T CPU @ 2.80GHz"

func requireCanonicalHost(tb testing.TB, expectedGOMAXPROCS int) {
	tb.Helper()
	if os.Getenv("CACHE_REQUIRE_CANONICAL_HOST") != "1" {
		return
	}
	if runtime.GOOS != "linux" || runtime.GOARCH != "amd64" {
		tb.Fatalf("canonical host requires linux/amd64, got %s/%s", runtime.GOOS, runtime.GOARCH)
	}
	if runtime.Version() != "go1.26.0" {
		tb.Fatalf("canonical host requires Go 1.26.0, got %s", runtime.Version())
	}
	if runtime.NumCPU() < 4 {
		tb.Fatalf("canonical host requires at least 4 schedulable CPUs, got %d", runtime.NumCPU())
	}
	if expectedGOMAXPROCS > 0 && runtime.GOMAXPROCS(0) != expectedGOMAXPROCS {
		tb.Fatalf("canonical run requires GOMAXPROCS=%d, got %d", expectedGOMAXPROCS, runtime.GOMAXPROCS(0))
	}
	cpuInfo, err := os.ReadFile("/proc/cpuinfo")
	if err != nil {
		tb.Fatalf("read canonical CPU model: %v", err)
	}
	if !strings.Contains(string(cpuInfo), "model name\t: "+canonicalCPUModel) {
		tb.Fatalf("canonical host requires CPU %q", canonicalCPUModel)
	}
	quota, limited, err := effectiveCPUQuota()
	if err != nil {
		tb.Fatalf("read cgroup CPU quota: %v", err)
	}
	if limited && quota < 4 {
		tb.Fatalf("canonical host requires cgroup quota of at least 4 CPUs, got %.2f", quota)
	}
}

func effectiveCPUQuota() (float64, bool, error) {
	data, err := os.ReadFile("/proc/self/cgroup")
	if err != nil {
		return 0, false, err
	}
	var relative string
	for _, line := range strings.Split(strings.TrimSpace(string(data)), "\n") {
		parts := strings.SplitN(line, ":", 3)
		if len(parts) == 3 && parts[0] == "0" && parts[1] == "" {
			relative = parts[2]
			break
		}
	}
	if relative == "" {
		return 0, false, fmt.Errorf("cgroup v2 membership not found")
	}
	root := "/sys/fs/cgroup"
	current := filepath.Join(root, filepath.Clean("/"+relative))
	minimum := 0.0
	limited := false
	for {
		contents, readErr := os.ReadFile(filepath.Join(current, "cpu.max"))
		if readErr != nil {
			if !os.IsNotExist(readErr) {
				return 0, false, readErr
			}
		} else {
			fields := strings.Fields(string(contents))
			if len(fields) != 2 {
				return 0, false, fmt.Errorf("invalid %s/cpu.max", current)
			}
			if fields[0] != "max" {
				quota, quotaErr := strconv.ParseFloat(fields[0], 64)
				period, periodErr := strconv.ParseFloat(fields[1], 64)
				if quotaErr != nil || periodErr != nil || period <= 0 {
					return 0, false, fmt.Errorf("invalid %s/cpu.max", current)
				}
				cpus := quota / period
				if !limited || cpus < minimum {
					minimum = cpus
				}
				limited = true
			}
		}
		if current == root {
			break
		}
		parent := filepath.Dir(current)
		if len(parent) < len(root) {
			break
		}
		current = parent
	}
	return minimum, limited, nil
}
