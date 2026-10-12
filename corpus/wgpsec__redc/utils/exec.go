package utils

import (
	"bufio"
	"fmt"
	"golang.org/x/text/encoding/simplifiedchinese"
	"io"
	"log"
	"os"
	"os/exec"
	"sync"
)

// 参考 https://www.cnblogs.com/we8fans/p/14031109.html

type Charset string

const (
	UTF8    = Charset("UTF-8")
	GB18030 = Charset("GB18030")
)

func Command(cmd string) error {
	c := exec.Command("bash", "-c", cmd) // mac or linux
	stdout, err := c.StdoutPipe()
	if err != nil {
		return err
	}
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		reader := bufio.NewReader(stdout)
		for {
			readString, err := reader.ReadString('\n')
			if err != nil || err == io.EOF {
				return
			}
			byte2String := ConvertByte2String([]byte(readString), "GB18030")
			fmt.Print(byte2String)
		}
	}()
	err = c.Run()
	wg.Wait()
	return err
}

func CommandUTF(cmd string) error {
	c := exec.Command("bash", "-c", cmd) // mac or linux
	stdout, err := c.StdoutPipe()
	if err != nil {
		return err
	}
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		reader := bufio.NewReader(stdout)
		for {
			readString, err := reader.ReadString('\n')
			if err != nil || err == io.EOF {
				return
			}
			byte2String := ConvertByte2String([]byte(readString), "UTF-8")
			fmt.Print(byte2String)
		}
	}()
	err = c.Run()
	wg.Wait()
	return err
}

func NoPrintCommand(cmd string) error {
	c := exec.Command("bash", "-c", cmd) // mac or linux
	stdout, err := c.StdoutPipe()
	if err != nil {
		return err
	}
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		reader := bufio.NewReader(stdout)
		for {
			readString, err := reader.ReadString('\n')
			if err != nil || err == io.EOF {
				return
			}
			byte2String := ConvertByte2String([]byte(readString), "GB18030")
			f, err := os.OpenFile("log.log", os.O_CREATE|os.O_APPEND|os.O_RDWR, os.ModePerm)
			if err != nil {
				return
			}
			defer func() {
				f.Close()
			}()

			log.SetOutput(f)
			log.Println(byte2String)
		}
	}()
	err = c.Run()
	wg.Wait()
	return err
}

func ConvertByte2String(byte []byte, charset Charset) string {
	var str string
	switch charset {
	case GB18030:
		var decodeBytes, _ = simplifiedchinese.GB18030.NewDecoder().Bytes(byte)
		str = string(decodeBytes)
	case UTF8:
		fallthrough
	default:
		str = string(byte)
	}
	return str
}

func Command2(cmd string) string {
	c2 := exec.Command("bash", "-c", cmd)
	out, err := c2.Output()
	if err != nil {
		fmt.Printf("%s", cmd + " 运行失败")
		os.Exit(3)
	}
	return string(out)
}
