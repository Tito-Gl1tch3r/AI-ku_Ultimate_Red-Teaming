package shardedcache

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/gob"
	"errors"
	"fmt"
	"io"
	"os"
	"time"
)

const (
	persistenceVersion    = uint16(1)
	envelopeHeaderSize    = 76
	maxPersistencePayload = uint64(1 << 30)
	fileTypeManifest      = uint8(1)
	fileTypeShard         = uint8(2)
)

var persistenceMagic = [8]byte{'S', 'C', 'A', 'C', 'H', 'E', '0', '1'}

type envelopeMetadata struct {
	fileType   uint8
	generation uint64
	shardCount uint64
	shardID    int64
}

type manifestFile struct {
	Generation uint64
	ShardCount uint64
	Shards     []manifestEntry
}

type manifestEntry struct {
	ShardID    int
	Generation uint64
	File       string
	Size       int64
	Hash       [sha256.Size]byte
}

type persistedShard struct {
	Items []persistedItem
}

type persistedItem struct {
	Key       EntryKey
	Value     any
	ExpiresAt time.Time
	Ordinal   uint64
}

func encodeGob(value any) ([]byte, error) {
	var buffer bytes.Buffer
	if err := gob.NewEncoder(&buffer).Encode(value); err != nil {
		return nil, err
	}
	return buffer.Bytes(), nil
}

func decodeGob(data []byte, value any) error {
	decoder := gob.NewDecoder(bytes.NewReader(data))
	if err := decoder.Decode(value); err != nil {
		return err
	}
	var trailing any
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return errors.New("persistence payload contains trailing gob value")
		}
		return fmt.Errorf("decode persistence payload trailer: %w", err)
	}
	return nil
}

func encodeEnvelope(metadata envelopeMetadata, payload []byte) ([]byte, error) {
	if uint64(len(payload)) > maxPersistencePayload {
		return nil, fmt.Errorf("persistence payload length %d exceeds limit", len(payload))
	}
	data := make([]byte, envelopeHeaderSize+len(payload))
	copy(data[:8], persistenceMagic[:])
	binary.BigEndian.PutUint16(data[8:10], persistenceVersion)
	data[10] = metadata.fileType
	data[11] = 0
	binary.BigEndian.PutUint64(data[12:20], metadata.generation)
	binary.BigEndian.PutUint64(data[20:28], metadata.shardCount)
	binary.BigEndian.PutUint64(data[28:36], uint64(metadata.shardID))
	binary.BigEndian.PutUint64(data[36:44], uint64(len(payload)))
	copy(data[envelopeHeaderSize:], payload)
	checksum := sha256.New()
	_, _ = checksum.Write(data[:44])
	_, _ = checksum.Write(payload)
	copy(data[44:76], checksum.Sum(nil))
	return data, nil
}

func decodeEnvelope(data []byte, expectedType uint8) (envelopeMetadata, []byte, error) {
	var metadata envelopeMetadata
	if len(data) < envelopeHeaderSize {
		return metadata, nil, io.ErrUnexpectedEOF
	}
	if !bytes.Equal(data[:8], persistenceMagic[:]) {
		return metadata, nil, errors.New("persistence envelope has invalid magic")
	}
	version := binary.BigEndian.Uint16(data[8:10])
	if version != persistenceVersion {
		return metadata, nil, fmt.Errorf("%w: persistence version %d", ErrUnsupportedFormat, version)
	}
	metadata.fileType = data[10]
	if metadata.fileType != fileTypeManifest && metadata.fileType != fileTypeShard {
		return metadata, nil, fmt.Errorf("persistence envelope has unknown file type %d", metadata.fileType)
	}
	if expectedType != 0 && metadata.fileType != expectedType {
		return metadata, nil, fmt.Errorf("persistence envelope file type %d, expected %d", metadata.fileType, expectedType)
	}
	if data[11] != 0 {
		return metadata, nil, errors.New("persistence envelope has invalid reserved metadata")
	}
	metadata.generation = binary.BigEndian.Uint64(data[12:20])
	metadata.shardCount = binary.BigEndian.Uint64(data[20:28])
	metadata.shardID = int64(binary.BigEndian.Uint64(data[28:36]))
	payloadLength := binary.BigEndian.Uint64(data[36:44])
	if payloadLength > maxPersistencePayload {
		return metadata, nil, fmt.Errorf("persistence payload length %d exceeds limit", payloadLength)
	}
	if payloadLength != uint64(len(data)-envelopeHeaderSize) {
		return metadata, nil, fmt.Errorf("persistence payload length %d does not match file length %d", payloadLength, len(data)-envelopeHeaderSize)
	}
	payload := data[envelopeHeaderSize:]
	checksum := sha256.New()
	_, _ = checksum.Write(data[:44])
	_, _ = checksum.Write(payload)
	if !bytes.Equal(data[44:76], checksum.Sum(nil)) {
		return metadata, nil, errors.New("persistence envelope checksum mismatch")
	}
	return metadata, payload, nil
}

func readEnvelopeFile(path string, expectedType uint8) (envelopeMetadata, []byte, []byte, error) {
	var metadata envelopeMetadata
	file, err := os.Open(path)
	if err != nil {
		return metadata, nil, nil, err
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil {
		return metadata, nil, nil, err
	}
	if info.Size() < envelopeHeaderSize || uint64(info.Size()-envelopeHeaderSize) > maxPersistencePayload {
		return metadata, nil, nil, fmt.Errorf("persistence file length %d is invalid", info.Size())
	}
	data, err := io.ReadAll(file)
	if err != nil {
		return metadata, nil, nil, err
	}
	metadata, payload, err := decodeEnvelope(data, expectedType)
	if err != nil {
		return metadata, nil, nil, err
	}
	hash := sha256.Sum256(data)
	return metadata, payload, hash[:], nil
}
