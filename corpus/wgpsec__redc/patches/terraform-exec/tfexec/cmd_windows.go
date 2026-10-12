// Copyright (c) HashiCorp, Inc.
// SPDX-License-Identifier: MPL-2.0

//go:build windows
// +build windows

package tfexec

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
	"sync"
	"syscall"
)

func (tf *Terraform) runTerraformCmd(ctx context.Context, cmd *exec.Cmd) error {
	var errBuf strings.Builder

	// HideWindow prevents cmd.exe console windows from flashing on screen
	// when terraform is called from a GUI application (no console parent).
	// Without this, Windows allocates a new visible console for every terraform
	// subprocess. See: https://github.com/hashicorp/terraform-exec/issues/570
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow: true,
	}

	// check for early cancellation
	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
	}

	// Read stdout / stderr logs from pipe instead of setting cmd.Stdout and
	// cmd.Stderr because it can cause hanging when killing the command
	// https://github.com/golang/go/issues/23019
	stdoutWriter := mergeWriters(cmd.Stdout, tf.stdout)
	stderrWriter := mergeWriters(tf.stderr, &errBuf)

	cmd.Stderr = nil
	cmd.Stdout = nil

	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return err
	}

	stderrPipe, err := cmd.StderrPipe()
	if err != nil {
		return err
	}

	err = cmd.Start()
	if ctx.Err() != nil {
		return cmdErr{
			err:    err,
			ctxErr: ctx.Err(),
		}
	}
	if err != nil {
		return err
	}

	var errStdout, errStderr error
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		errStdout = tf.writeOutput(ctx, stdoutPipe, stdoutWriter)
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		errStderr = tf.writeOutput(ctx, stderrPipe, stderrWriter)
	}()

	// Reads from pipes must be completed before calling cmd.Wait(). Otherwise
	// can cause a race condition
	wg.Wait()

	err = cmd.Wait()
	if ctx.Err() != nil {
		return cmdErr{
			err:    err,
			ctxErr: ctx.Err(),
		}
	}
	if err != nil {
		return fmt.Errorf("%w\n%s", err, errBuf.String())
	}

	// Return error if there was an issue reading the std out/err
	if errStdout != nil && ctx.Err() != nil {
		return fmt.Errorf("%w\n%s", errStdout, errBuf.String())
	}
	if errStderr != nil && ctx.Err() != nil {
		return fmt.Errorf("%w\n%s", errStderr, errBuf.String())
	}

	return nil
}
