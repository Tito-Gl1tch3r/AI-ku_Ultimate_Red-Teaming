package sshutil

import (
	"fmt"
	"io"
	"os"
	"path"
	"time"

	"github.com/pkg/sftp"
)

// FileInfo 文件信息
type FileInfo struct {
	Name    string    `json:"name"`
	Size    int64     `json:"size"`
	Mode    string    `json:"mode"`
	ModTime time.Time `json:"modTime"`
	IsDir   bool      `json:"isDir"`
	IsLink  bool      `json:"isLink"`
}

// ListFiles 列出目录下的文件
func (c *Client) ListFiles(remotePath string) ([]FileInfo, error) {
	sftpClient, err := sftp.NewClient(c.Client)
	if err != nil {
		return nil, fmt.Errorf("SFTP 建立失败: %v", err)
	}
	defer sftpClient.Close()

	files, err := sftpClient.ReadDir(remotePath)
	if err != nil {
		return nil, fmt.Errorf("读取目录失败: %v", err)
	}

	result := make([]FileInfo, 0, len(files))
	for _, f := range files {
		result = append(result, FileInfo{
			Name:    f.Name(),
			Size:    f.Size(),
			Mode:    f.Mode().String(),
			ModTime: f.ModTime(),
			IsDir:   f.IsDir(),
			IsLink:  f.Mode()&os.ModeSymlink != 0,
		})
	}

	return result, nil
}

// CreateDirectory 创建目录
func (c *Client) CreateDirectory(remotePath string) error {
	sftpClient, err := sftp.NewClient(c.Client)
	if err != nil {
		return fmt.Errorf("SFTP 建立失败: %v", err)
	}
	defer sftpClient.Close()

	return sftpClient.MkdirAll(remotePath)
}

// DeleteFile 删除文件或目录
func (c *Client) DeleteFile(remotePath string) error {
	sftpClient, err := sftp.NewClient(c.Client)
	if err != nil {
		return fmt.Errorf("SFTP 建立失败: %v", err)
	}
	defer sftpClient.Close()

	// 检查是否是目录
	stat, err := sftpClient.Stat(remotePath)
	if err != nil {
		return fmt.Errorf("获取文件信息失败: %v", err)
	}

	if stat.IsDir() {
		// 递归删除目录
		return c.removeDir(sftpClient, remotePath)
	}

	return sftpClient.Remove(remotePath)
}

// removeDir 递归删除目录
func (c *Client) removeDir(sftpClient *sftp.Client, remotePath string) error {
	files, err := sftpClient.ReadDir(remotePath)
	if err != nil {
		return err
	}

	for _, f := range files {
		fullPath := path.Join(remotePath, f.Name())
		if f.IsDir() {
			if err := c.removeDir(sftpClient, fullPath); err != nil {
				return err
			}
		} else {
			if err := sftpClient.Remove(fullPath); err != nil {
				return err
			}
		}
	}

	return sftpClient.RemoveDirectory(remotePath)
}

// RenameFile 重命名文件或目录
func (c *Client) RenameFile(oldPath, newPath string) error {
	sftpClient, err := sftp.NewClient(c.Client)
	if err != nil {
		return fmt.Errorf("SFTP 建立失败: %v", err)
	}
	defer sftpClient.Close()

	return sftpClient.Rename(oldPath, newPath)
}

// GetFileContent 获取文件内容（用于小文件预览）
func (c *Client) GetFileContent(remotePath string, maxSize int64) ([]byte, error) {
	sftpClient, err := sftp.NewClient(c.Client)
	if err != nil {
		return nil, fmt.Errorf("SFTP 建立失败: %v", err)
	}
	defer sftpClient.Close()

	// 检查文件大小
	stat, err := sftpClient.Stat(remotePath)
	if err != nil {
		return nil, fmt.Errorf("获取文件信息失败: %v", err)
	}

	if stat.Size() > maxSize {
		return nil, fmt.Errorf("文件太大 (%.2f MB)，请使用下载功能", float64(stat.Size())/1024/1024)
	}

	file, err := sftpClient.Open(remotePath)
	if err != nil {
		return nil, fmt.Errorf("打开文件失败: %v", err)
	}
	defer file.Close()

	return io.ReadAll(file)
}

// WriteFileContent 写入文件内容
func (c *Client) WriteFileContent(remotePath string, content []byte) error {
	sftpClient, err := sftp.NewClient(c.Client)
	if err != nil {
		return fmt.Errorf("SFTP 建立失败: %v", err)
	}
	defer sftpClient.Close()

	// 确保父目录存在
	parentDir := path.Dir(remotePath)
	if err := sftpClient.MkdirAll(parentDir); err != nil {
		return fmt.Errorf("创建父目录失败: %v", err)
	}

	file, err := sftpClient.Create(remotePath)
	if err != nil {
		return fmt.Errorf("创建文件失败: %v", err)
	}
	defer file.Close()

	_, err = file.Write(content)
	return err
}

// GetFileStats 获取文件统计信息
func (c *Client) GetFileStats(remotePath string) (*FileInfo, error) {
	sftpClient, err := sftp.NewClient(c.Client)
	if err != nil {
		return nil, fmt.Errorf("SFTP 建立失败: %v", err)
	}
	defer sftpClient.Close()

	stat, err := sftpClient.Stat(remotePath)
	if err != nil {
		return nil, fmt.Errorf("获取文件信息失败: %v", err)
	}

	return &FileInfo{
		Name:    stat.Name(),
		Size:    stat.Size(),
		Mode:    stat.Mode().String(),
		ModTime: stat.ModTime(),
		IsDir:   stat.IsDir(),
		IsLink:  stat.Mode()&os.ModeSymlink != 0,
	}, nil
}
