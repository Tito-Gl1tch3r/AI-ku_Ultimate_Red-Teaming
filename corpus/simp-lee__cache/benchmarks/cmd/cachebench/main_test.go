package main

import (
	"math"
	"path/filepath"
	"testing"
)

func TestResolvePathForRunnerArguments(t *testing.T) {
	moduleDir := t.TempDir()
	absoluteRoot := t.TempDir()
	for _, argument := range []string{"candidate", "baseline", "out"} {
		t.Run(argument+"/absolute", func(t *testing.T) {
			input := filepath.Join(absoluteRoot, argument)
			got, err := resolvePath(moduleDir, input)
			if err != nil {
				t.Fatalf("resolvePath() error = %v", err)
			}
			if got != input {
				t.Fatalf("resolvePath(%q, %q) = %q, want %q", moduleDir, input, got, input)
			}
		})

		t.Run(argument+"/relative", func(t *testing.T) {
			input := filepath.Join("relative", argument)
			want := filepath.Join(moduleDir, input)
			got, err := resolvePath(moduleDir, input)
			if err != nil {
				t.Fatalf("resolvePath() error = %v", err)
			}
			if got != want {
				t.Fatalf("resolvePath(%q, %q) = %q, want %q", moduleDir, input, got, want)
			}
		})
	}
}

func TestScalingGateUsesMedianOperationsPerSecond(t *testing.T) {
	samples := []sample{{NS: 1}, {NS: 10}}
	if got, want := medianOpsPerSecond(samples), 550_000_000.0; got != want {
		t.Fatalf("median operations/second = %v, want %v", got, want)
	}
}

func TestMannWhitneyPAdjustsVarianceForTies(t *testing.T) {
	left := samplesWithNS(1, 1, 1, 1, 1, 1, 1, 1, 1, 1)
	right := samplesWithNS(1, 1, 1, 1, 1, 2, 2, 2, 2, 2)

	const want = 0.011848940928347484
	if got := mannWhitneyP(left, right); math.Abs(got-want) > 1e-12 {
		t.Fatalf("mannWhitneyP() = %.15g, want %.15g", got, want)
	}
}

func TestMannWhitneyPAllValuesTied(t *testing.T) {
	if got := mannWhitneyP(samplesWithNS(1, 1), samplesWithNS(1, 1)); got != 1 {
		t.Fatalf("mannWhitneyP() = %v, want 1", got)
	}
}

func samplesWithNS(values ...float64) []sample {
	samples := make([]sample, len(values))
	for index, value := range values {
		samples[index].NS = value
	}
	return samples
}

func TestScalingBenchmarkNamesMatchGoCPUSuffixes(t *testing.T) {
	tests := []struct {
		cpu  int
		want string
	}{
		{cpu: 1, want: "BenchmarkShardedScaling/FIFO/Shards32/GetHit"},
		{cpu: 4, want: "BenchmarkShardedScaling/FIFO/Shards32/GetHit-4"},
		{cpu: 8, want: "BenchmarkShardedScaling/FIFO/Shards32/GetHit-8"},
	}
	for _, test := range tests {
		if got := scalingBenchmarkName("FIFO", 32, "GetHit", test.cpu); got != test.want {
			t.Errorf("CPU %d name = %q, want %q", test.cpu, got, test.want)
		}
	}
}
