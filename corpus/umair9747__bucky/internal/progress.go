package internal

import (
	"fmt"
	"os"
	"strings"
	"sync"
)

// ProgressBar renders a dynamic progress bar on stderr using \r overwrites.
type ProgressBar struct {
	total   int
	current int
	width   int
	suffix  string
	mu      sync.Mutex
}

// NewProgressBar creates a new progress bar with the given total steps and bar width.
func NewProgressBar(total, width int) *ProgressBar {
	return &ProgressBar{total: total, width: width}
}

// Set updates the progress bar position and suffix text, then redraws.
func (p *ProgressBar) Set(current int, suffix string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.current = current
	p.suffix = suffix
	p.draw()
}

// Increment advances the bar by 1 and updates the suffix.
func (p *ProgressBar) Increment(suffix string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.current++
	p.suffix = suffix
	p.draw()
}

func (p *ProgressBar) draw() {
	if p.total <= 0 {
		return
	}
	filled := p.width * p.current / p.total
	if filled > p.width {
		filled = p.width
	}
	bar := strings.Repeat("█", filled) + strings.Repeat("░", p.width-filled)
	fmt.Fprintf(os.Stderr, "\r\033[K  [%s] %d/%d %s", bar, p.current, p.total, p.suffix)
}

// Finish fills the bar completely, prints the final suffix, and moves to a new line.
func (p *ProgressBar) Finish(suffix string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.suffix = suffix
	bar := strings.Repeat("█", p.width)
	fmt.Fprintf(os.Stderr, "\r\033[K  [%s] %d/%d %s\n", bar, p.total, p.total, p.suffix)
}

// PrintAbove clears the current bar line, prints a message, then redraws the bar.
// Use this to print found results above the bar while it continues updating.
func (p *ProgressBar) PrintAbove(msg string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	fmt.Fprintf(os.Stderr, "\r\033[K%s\n", msg)
	p.draw()
}
