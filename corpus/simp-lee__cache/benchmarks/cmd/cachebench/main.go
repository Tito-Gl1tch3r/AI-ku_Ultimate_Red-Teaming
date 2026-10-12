package main

import (
	"bufio"
	"bytes"
	"crypto/sha1"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

const cacheModule = "github.com/simp-lee/cache"

type module struct {
	Path    string
	Version string
	Sum     string
	Replace *module
}

type sample struct {
	NS     float64
	Bytes  float64
	Allocs float64
}

type runMetadata struct {
	Mode             string            `json:"mode"`
	CreatedAt        time.Time         `json:"createdAt"`
	DriverSHA256     string            `json:"driverSHA256"`
	BaselinePath     string            `json:"baselinePath,omitempty"`
	CandidatePath    string            `json:"candidatePath"`
	BaselineCommit   string            `json:"baselineCommit,omitempty"`
	CandidateCommit  string            `json:"candidateCommit,omitempty"`
	CandidateTree    string            `json:"candidateTree,omitempty"`
	BaselineSource   string            `json:"baselineSourceSHA256,omitempty"`
	CandidateSource  string            `json:"candidateSourceSHA256"`
	GoVersion        string            `json:"goVersion"`
	Dependencies     map[string]string `json:"dependencies"`
	Count            int               `json:"count"`
	Completed        int               `json:"completed"`
	BenchmarkTime    string            `json:"benchmarkTime"`
	CanonicalHostReq bool              `json:"canonicalHostRequired"`
}

func main() {
	mode := flag.String("mode", "canonical", "prepare, canonical, or scaling")
	baseline := flag.String("baseline", "", "immutable baseline product source")
	candidate := flag.String("candidate", "..", "candidate product source")
	out := flag.String("out", "../.pi-work/evidence/cachebench-results", "output directory")
	count := flag.Int("count", 10, "independent repetitions")
	benchTime := flag.String("benchtime", "1s", "Go benchmark duration")
	requireHost := flag.Bool("require-host", true, "enforce canonical host checks in benchmark binaries")
	resume := flag.Bool("resume", false, "resume a matching incomplete scaling run")
	batch := flag.Int("batch", 0, "maximum scaling repetitions in this invocation; zero runs all remaining")
	flag.Parse()
	if *count < 10 {
		fatalf("acceptance requires at least 10 repetitions, got %d", *count)
	}
	if *batch < 0 {
		fatalf("-batch cannot be negative")
	}
	if (*resume || *batch != 0) && *mode != "scaling" {
		fatalf("-resume and -batch are only valid in scaling mode")
	}
	if *mode == "canonical" || *mode == "scaling" {
		if !*requireHost {
			fatalf("%s acceptance cannot disable canonical host validation", *mode)
		}
		if *benchTime != "1s" {
			fatalf("%s acceptance requires -benchtime=1s, got %q", *mode, *benchTime)
		}
	}
	moduleDir, err := findBenchmarkModule()
	must(err)
	candidatePath, err := resolvePath(moduleDir, *candidate)
	must(err)
	if *mode == "canonical" || *mode == "scaling" {
		requireCleanCandidate(candidatePath)
	}
	candidateSource, err := hashProductSource(candidatePath)
	must(err)
	outPath, err := resolvePath(moduleDir, *out)
	must(err)
	must(os.MkdirAll(outPath, 0o755))
	driverHash, err := hashDriver(moduleDir)
	must(err)

	temporary, err := os.MkdirTemp("", "cachebench-driver-")
	must(err)
	defer os.RemoveAll(temporary)

	candidateBinary, candidateDeps := buildDriver(moduleDir, filepath.Join(temporary, "candidate"), candidatePath)
	metadataPath := filepath.Join(outPath, "metadata.json")
	metadata := runMetadata{
		Mode:             *mode,
		CreatedAt:        time.Now().UTC(),
		DriverSHA256:     driverHash,
		CandidatePath:    candidatePath,
		CandidateCommit:  gitValue(candidatePath, "rev-parse", "HEAD"),
		CandidateTree:    gitValue(candidatePath, "rev-parse", "HEAD^{tree}"),
		CandidateSource:  candidateSource,
		GoVersion:        goValue("env", "GOVERSION"),
		Dependencies:     candidateDeps,
		Count:            *count,
		BenchmarkTime:    *benchTime,
		CanonicalHostReq: *requireHost,
	}

	environment := withoutEnv(os.Environ(), "CACHE_REQUIRE_CANONICAL_HOST")
	if *requireHost {
		environment = append(environment, "CACHE_REQUIRE_CANONICAL_HOST=1")
	}
	switch *mode {
	case "prepare":
		if *baseline == "" {
			fatalf("-baseline is required in prepare mode")
		}
		baselinePath, pathErr := resolvePath(moduleDir, *baseline)
		must(pathErr)
		verifyBaselineSource(baselinePath)
		metadata.BaselineSource, pathErr = hashProductSource(baselinePath)
		must(pathErr)
		_, baselineDeps := buildDriver(moduleDir, filepath.Join(temporary, "baseline"), baselinePath)
		if !equalStringMap(baselineDeps, candidateDeps) {
			fatalf("baseline and candidate dependency manifests differ")
		}
		metadata.BaselinePath = baselinePath
		metadata.BaselineCommit = "383227a99fb3f48eead637f16e189d71887f2383"
	case "canonical":
		if *baseline == "" {
			fatalf("-baseline is required in canonical mode")
		}
		baselinePath, pathErr := resolvePath(moduleDir, *baseline)
		must(pathErr)
		verifyBaselineSource(baselinePath)
		metadata.BaselineSource, pathErr = hashProductSource(baselinePath)
		must(pathErr)
		baselineBinary, baselineDeps := buildDriver(moduleDir, filepath.Join(temporary, "baseline"), baselinePath)
		if !equalStringMap(baselineDeps, candidateDeps) {
			fatalf("baseline and candidate dependency manifests differ")
		}
		metadata.BaselinePath = baselinePath
		metadata.BaselineCommit = "383227a99fb3f48eead637f16e189d71887f2383"
		baselineOutput := filepath.Join(outPath, "baseline.txt")
		candidateOutput := filepath.Join(outPath, "candidate.txt")
		writeMetadata(metadataPath, metadata)
		must(os.WriteFile(baselineOutput, nil, 0o644))
		must(os.WriteFile(candidateOutput, nil, 0o644))
		args := []string{
			"-test.run=^$",
			"-test.bench=^Benchmark(CacheComparisonV2|TTLUpdateComparisonV2)/ShardedCache",
			"-test.benchmem",
			"-test.benchtime=" + *benchTime,
			"-test.count=1",
			"-test.cpu=8",
		}
		for repetition := 1; repetition <= *count; repetition++ {
			runBinary(baselineBinary, args, environment, baselineOutput, repetition)
			runBinary(candidateBinary, args, environment, candidateOutput, repetition)
			metadata.Completed = repetition
			writeMetadata(metadataPath, metadata)
		}
		baselineSamples := parseSamples(baselineOutput)
		candidateSamples := parseSamples(candidateOutput)
		checkCanonical(baselineSamples, candidateSamples, *count)
	case "scaling":
		output := filepath.Join(outPath, "scaling.txt")
		if *resume {
			stored := readMetadata(metadataPath)
			if !sameMetadataIdentity(stored, metadata) {
				fatalf("existing scaling metadata does not match this run")
			}
			metadata.CreatedAt = stored.CreatedAt
			metadata.Completed = stored.Completed
			if metadata.Completed < 0 || metadata.Completed > *count {
				fatalf("existing scaling completion %d is outside [0,%d]", metadata.Completed, *count)
			}
			if headers := countRepetitionHeaders(output); headers != metadata.Completed {
				fatalf("scaling output has %d repetition headers, metadata records %d", headers, metadata.Completed)
			}
			requireScalingSamples(parseSamples(output), metadata.Completed)
		} else {
			must(os.WriteFile(output, nil, 0o644))
			writeMetadata(metadataPath, metadata)
		}
		args := []string{
			"-test.run=^$",
			"-test.bench=^BenchmarkShardedScaling$",
			"-test.benchmem",
			"-test.benchtime=" + *benchTime,
			"-test.count=1",
			"-test.cpu=1,4,8",
		}
		end := *count
		if *batch > 0 && metadata.Completed+*batch < end {
			end = metadata.Completed + *batch
		}
		for repetition := metadata.Completed + 1; repetition <= end; repetition++ {
			runBinary(candidateBinary, args, environment, output, repetition)
			metadata.Completed = repetition
			writeMetadata(metadataPath, metadata)
		}
		if metadata.Completed == *count {
			checkScaling(parseSamples(output), *count)
		} else {
			fmt.Printf("scaling progress=%d/%d; resume with -resume\n", metadata.Completed, *count)
		}
	default:
		fatalf("unknown mode %q", *mode)
	}
	writeMetadata(metadataPath, metadata)
	fmt.Printf("driver_sha256=%s\nresults=%s\n", driverHash, outPath)
}

func findBenchmarkModule() (string, error) {
	current, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		data, readErr := os.ReadFile(filepath.Join(current, "go.mod"))
		if readErr == nil && strings.Contains(string(data), "module github.com/simp-lee/cache/benchmarks") {
			return current, nil
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", fmt.Errorf("benchmark module not found")
		}
		current = parent
	}
}

func resolvePath(moduleDir, path string) (string, error) {
	if !filepath.IsAbs(path) {
		path = filepath.Join(moduleDir, path)
	}
	return filepath.Abs(path)
}

func hashDriver(moduleDir string) (string, error) {
	entries, err := os.ReadDir(moduleDir)
	if err != nil {
		return "", err
	}
	var names []string
	for _, entry := range entries {
		if !entry.IsDir() && (strings.HasSuffix(entry.Name(), ".go") || entry.Name() == "go.mod" || entry.Name() == "go.sum") {
			names = append(names, entry.Name())
		}
	}
	sort.Strings(names)
	hash := sha256.New()
	for _, name := range names {
		data, readErr := os.ReadFile(filepath.Join(moduleDir, name))
		if readErr != nil {
			return "", readErr
		}
		fmt.Fprintf(hash, "%s\x00%d\x00", name, len(data))
		hash.Write(data)
	}
	return hex.EncodeToString(hash.Sum(nil)), nil
}

func hashProductSource(directory string) (string, error) {
	entries, err := os.ReadDir(directory)
	if err != nil {
		return "", err
	}
	var names []string
	for _, entry := range entries {
		if !entry.IsDir() && (strings.HasSuffix(entry.Name(), ".go") || entry.Name() == "go.mod" || entry.Name() == "go.sum") {
			names = append(names, entry.Name())
		}
	}
	sort.Strings(names)
	hash := sha256.New()
	for _, name := range names {
		data, readErr := os.ReadFile(filepath.Join(directory, name))
		if readErr != nil {
			return "", readErr
		}
		fmt.Fprintf(hash, "%s\x00%d\x00", name, len(data))
		hash.Write(data)
	}
	return hex.EncodeToString(hash.Sum(nil)), nil
}

func verifyBaselineSource(source string) {
	manifestPath := filepath.Join(filepath.Dir(source), "tree.tsv")
	data, err := os.ReadFile(manifestPath)
	if err != nil {
		fatalf("read baseline manifest: %v", err)
	}
	expected := make(map[string]string)
	for _, line := range strings.Split(strings.TrimSpace(string(data)), "\n") {
		metadata, name, found := strings.Cut(line, "\t")
		fields := strings.Fields(metadata)
		if !found || len(fields) != 3 || fields[0] != "100644" || fields[1] != "blob" {
			fatalf("invalid baseline manifest line %q", line)
		}
		expected[name] = fields[2]
	}
	actual := 0
	err = filepath.WalkDir(source, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() {
			return nil
		}
		relative, relErr := filepath.Rel(source, path)
		if relErr != nil {
			return relErr
		}
		relative = filepath.ToSlash(relative)
		want, found := expected[relative]
		if !found {
			return fmt.Errorf("baseline export has extra file %q", relative)
		}
		contents, readErr := os.ReadFile(path)
		if readErr != nil {
			return readErr
		}
		hash := sha1.New()
		fmt.Fprintf(hash, "blob %d\x00", len(contents))
		hash.Write(contents)
		if got := hex.EncodeToString(hash.Sum(nil)); got != want {
			return fmt.Errorf("baseline blob %q = %s, want %s", relative, got, want)
		}
		actual++
		return nil
	})
	if err != nil {
		fatalf("verify baseline source: %v", err)
	}
	if actual != len(expected) {
		fatalf("baseline export has %d files, manifest has %d", actual, len(expected))
	}
}

func requireCleanCandidate(directory string) {
	command := exec.Command("git", "-C", directory, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none")
	output, err := command.CombinedOutput()
	if err != nil {
		fatalf("inspect candidate worktree: %v\n%s", err, output)
	}
	if len(bytes.TrimSpace(output)) != 0 {
		fatalf("candidate worktree is not clean:\n%s", output)
	}
}

func buildDriver(sourceDir, destination, product string) (string, map[string]string) {
	must(os.MkdirAll(destination, 0o755))
	entries, err := os.ReadDir(sourceDir)
	must(err)
	for _, entry := range entries {
		name := entry.Name()
		if entry.IsDir() || (!strings.HasSuffix(name, ".go") && name != "go.mod" && name != "go.sum") {
			continue
		}
		data, readErr := os.ReadFile(filepath.Join(sourceDir, name))
		must(readErr)
		if name == "go.mod" {
			lines := strings.Split(string(data), "\n")
			for index, line := range lines {
				if strings.HasPrefix(strings.TrimSpace(line), "replace "+cacheModule+" =>") {
					lines[index] = "replace " + cacheModule + " => " + filepath.ToSlash(product)
				}
			}
			data = []byte(strings.Join(lines, "\n"))
		}
		must(os.WriteFile(filepath.Join(destination, name), data, 0o644))
	}
	dependencies := listModules(destination)
	binary := filepath.Join(destination, "benchmarks.test")
	command := exec.Command("go", "test", "-mod=readonly", "-c", "-o", binary, ".")
	command.Dir = destination
	command.Env = append(os.Environ(), "GOWORK=off", "GOTOOLCHAIN=local")
	output, err := command.CombinedOutput()
	if err != nil {
		fatalf("build benchmark driver for %s: %v\n%s", product, err, output)
	}
	return binary, dependencies
}

func listModules(directory string) map[string]string {
	command := exec.Command("go", "list", "-mod=readonly", "-m", "-json", "all")
	command.Dir = directory
	command.Env = append(os.Environ(), "GOWORK=off", "GOTOOLCHAIN=local")
	output, err := command.Output()
	must(err)
	decoder := json.NewDecoder(bytes.NewReader(output))
	result := make(map[string]string)
	for {
		var current module
		if err := decoder.Decode(&current); err != nil {
			if err == io.EOF {
				break
			}
			must(err)
		}
		version, sum := current.Version, current.Sum
		if current.Replace != nil {
			version, sum = current.Replace.Version, current.Replace.Sum
		}
		if current.Path == "github.com/simp-lee/cache/benchmarks" || current.Path == cacheModule {
			continue
		}
		result[current.Path] = version + " " + sum
	}
	return result
}

func runBinary(binary string, args, environment []string, outputPath string, repetition int) {
	command := exec.Command(binary, args...)
	command.Env = append(withoutEnv(environment, "GOMAXPROCS"), "GOMAXPROCS=8")
	output, err := command.CombinedOutput()
	file, openErr := os.OpenFile(outputPath, os.O_APPEND|os.O_WRONLY, 0o644)
	must(openErr)
	if _, writeErr := fmt.Fprintf(file, "# repetition %d\n", repetition); writeErr != nil {
		file.Close()
		fatalf("write benchmark repetition header: %v", writeErr)
	}
	if _, writeErr := file.Write(output); writeErr != nil {
		file.Close()
		fatalf("write benchmark repetition output: %v", writeErr)
	}
	if closeErr := file.Close(); closeErr != nil {
		fatalf("close benchmark repetition output: %v", closeErr)
	}
	if err != nil {
		fatalf("benchmark repetition %d failed: %v\n%s", repetition, err, output)
	}
}

func parseSamples(path string) map[string][]sample {
	file, err := os.Open(path)
	must(err)
	defer file.Close()
	result := make(map[string][]sample)
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		fields := strings.Fields(scanner.Text())
		if len(fields) < 4 || !strings.HasPrefix(fields[0], "Benchmark") {
			continue
		}
		current := sample{}
		for index := 2; index < len(fields); index++ {
			switch fields[index] {
			case "ns/op":
				current.NS = parseFloat(fields[index-1])
			case "B/op":
				current.Bytes = parseFloat(fields[index-1])
			case "allocs/op":
				current.Allocs = parseFloat(fields[index-1])
			}
		}
		if current.NS != 0 {
			result[fields[0]] = append(result[fields[0]], current)
		}
	}
	must(scanner.Err())
	return result
}

func checkCanonical(baseline, candidate map[string][]sample, count int) {
	type target struct {
		suffix string
		limit  float64
		zero   bool
	}
	targets := []target{
		{"BenchmarkCacheComparisonV2/ShardedCache/FIFO/GetHit-8", .75, true},
		{"BenchmarkCacheComparisonV2/ShardedCache/FIFO/GetMiss-8", .75, true},
		{"BenchmarkCacheComparisonV2/ShardedCache/LRU/GetHit-8", .90, true},
		{"BenchmarkCacheComparisonV2/ShardedCache/LRU/GetMiss-8", .90, true},
		{"BenchmarkCacheComparisonV2/ShardedCache/FIFO/SetExisting-8", .60, true},
		{"BenchmarkCacheComparisonV2/ShardedCache/LRU/SetExisting-8", .60, true},
		{"BenchmarkCacheComparisonV2/ShardedCache/FIFO/Mixed80Get20Set-8", 1.05, false},
		{"BenchmarkCacheComparisonV2/ShardedCache/LRU/Mixed80Get20Set-8", 1.05, false},
		{"BenchmarkTTLUpdateComparisonV2/ShardedCache/FIFO-8", .60, true},
		{"BenchmarkTTLUpdateComparisonV2/ShardedCache/LRU-8", .60, true},
	}
	failed := false
	for _, target := range targets {
		base := requireSamples(baseline, target.suffix, count)
		current := requireSamples(candidate, target.suffix, count)
		baseNS, currentNS := medianNS(base), medianNS(current)
		ratio := currentNS / baseNS
		p := mannWhitneyP(base, current)
		fmt.Printf("%s baseline=%.2f candidate=%.2f ratio=%.3f p=%.4g\n", target.suffix, baseNS, currentNS, ratio, p)
		if ratio > target.limit {
			fmt.Printf("FAIL ratio %.3f exceeds %.3f\n", ratio, target.limit)
			failed = true
		}
		if target.zero {
			for _, value := range current {
				if value.Bytes != 0 || value.Allocs != 0 {
					fmt.Printf("FAIL allocations %.0f B/op %.0f allocs/op\n", value.Bytes, value.Allocs)
					failed = true
					break
				}
			}
		}
	}
	if failed {
		fatalf("canonical acceptance failed")
	}
}

func checkScaling(samples map[string][]sample, count int) {
	requireScalingSamples(samples, count)
	failed := false
	for _, policy := range []string{"FIFO", "LRU"} {
		for _, operation := range []string{"GetHit", "GetMiss"} {
			one := medianOpsPerSecond(requireSamples(samples, scalingBenchmarkName(policy, 32, operation, 1), count))
			four := medianOpsPerSecond(requireSamples(samples, scalingBenchmarkName(policy, 32, operation, 4), count))
			speedup := four / one
			fmt.Printf("%s %s 1-to-4 speedup=%.3f\n", policy, operation, speedup)
			if speedup < 1.5 {
				failed = true
			}
		}
	}
	if failed {
		fatalf("scaling acceptance failed")
	}
}

func requireScalingSamples(samples map[string][]sample, count int) {
	policies := []string{"FIFO", "LRU"}
	operations := []string{"GetHit", "GetMiss", "SetExisting", "Mixed80Get20Set", "TTLUpdate1h"}
	for _, policy := range policies {
		for _, shards := range []int{1, 8, 32, 128} {
			for _, operation := range operations {
				for _, cpu := range []int{1, 4, 8} {
					requireSamples(samples, scalingBenchmarkName(policy, shards, operation, cpu), count)
				}
			}
		}
	}
}

func scalingBenchmarkName(policy string, shards int, operation string, cpu int) string {
	name := fmt.Sprintf("BenchmarkShardedScaling/%s/Shards%d/%s", policy, shards, operation)
	if cpu != 1 {
		name += fmt.Sprintf("-%d", cpu)
	}
	return name
}

func requireSamples(samples map[string][]sample, name string, count int) []sample {
	values := samples[name]
	if len(values) != count {
		fatalf("%s has %d samples, want %d", name, len(values), count)
	}
	return values
}

func medianNS(samples []sample) float64 {
	values := make([]float64, len(samples))
	for index, current := range samples {
		values[index] = current.NS
	}
	return median(values)
}

func medianOpsPerSecond(samples []sample) float64 {
	values := make([]float64, len(samples))
	for index, current := range samples {
		values[index] = 1e9 / current.NS
	}
	return median(values)
}

func median(values []float64) float64 {
	sort.Float64s(values)
	if len(values)%2 == 0 {
		return (values[len(values)/2-1] + values[len(values)/2]) / 2
	}
	return values[len(values)/2]
}

func mannWhitneyP(left, right []sample) float64 {
	type ranked struct {
		value float64
		left  bool
	}
	combined := make([]ranked, 0, len(left)+len(right))
	for _, current := range left {
		combined = append(combined, ranked{value: current.NS, left: true})
	}
	for _, current := range right {
		combined = append(combined, ranked{value: current.NS})
	}
	sort.Slice(combined, func(i, j int) bool { return combined[i].value < combined[j].value })
	rankSum := 0.0
	tieAdjustment := 0.0
	for start := 0; start < len(combined); {
		end := start + 1
		for end < len(combined) && combined[end].value == combined[start].value {
			end++
		}
		rank := float64(start+1+end) / 2
		for index := start; index < end; index++ {
			if combined[index].left {
				rankSum += rank
			}
		}
		tieSize := float64(end - start)
		tieAdjustment += tieSize*tieSize*tieSize - tieSize
		start = end
	}
	n1, n2 := float64(len(left)), float64(len(right))
	if n1 == 0 || n2 == 0 {
		return 1
	}
	u := rankSum - n1*(n1+1)/2
	mean := n1 * n2 / 2
	total := n1 + n2
	variance := n1 * n2 / 12 * (total + 1 - tieAdjustment/(total*(total-1)))
	if variance == 0 {
		return 1
	}
	standard := math.Sqrt(variance)
	z := math.Abs(u-mean) / standard
	return math.Erfc(z / math.Sqrt2)
}

func readMetadata(path string) runMetadata {
	data, err := os.ReadFile(path)
	must(err)
	var metadata runMetadata
	must(json.Unmarshal(data, &metadata))
	return metadata
}

func writeMetadata(path string, metadata runMetadata) {
	encoded, err := json.MarshalIndent(metadata, "", "  ")
	must(err)
	temporary := path + ".tmp"
	must(os.WriteFile(temporary, append(encoded, '\n'), 0o644))
	must(os.Rename(temporary, path))
}

func sameMetadataIdentity(left, right runMetadata) bool {
	left.CreatedAt, right.CreatedAt = time.Time{}, time.Time{}
	left.Completed, right.Completed = 0, 0
	leftJSON, leftErr := json.Marshal(left)
	rightJSON, rightErr := json.Marshal(right)
	must(leftErr)
	must(rightErr)
	return bytes.Equal(leftJSON, rightJSON)
}

func countRepetitionHeaders(path string) int {
	file, err := os.Open(path)
	must(err)
	defer file.Close()
	count := 0
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if strings.HasPrefix(scanner.Text(), "# repetition ") {
			count++
		}
	}
	must(scanner.Err())
	return count
}

func withoutEnv(environment []string, name string) []string {
	prefix := name + "="
	filtered := make([]string, 0, len(environment))
	for _, value := range environment {
		if !strings.HasPrefix(value, prefix) {
			filtered = append(filtered, value)
		}
	}
	return filtered
}

func equalStringMap(left, right map[string]string) bool {
	if len(left) != len(right) {
		return false
	}
	for key, value := range left {
		if right[key] != value {
			return false
		}
	}
	return true
}

func gitValue(directory string, args ...string) string {
	command := exec.Command("git", append([]string{"-C", directory}, args...)...)
	output, err := command.Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(output))
}

func goValue(args ...string) string {
	output, err := exec.Command("go", args...).Output()
	must(err)
	return strings.TrimSpace(string(output))
}

func parseFloat(value string) float64 {
	parsed, err := strconv.ParseFloat(value, 64)
	must(err)
	return parsed
}

func must(err error) {
	if err != nil {
		fatalf("%v", err)
	}
}

func fatalf(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "cachebench: "+format+"\n", args...)
	os.Exit(1)
}
