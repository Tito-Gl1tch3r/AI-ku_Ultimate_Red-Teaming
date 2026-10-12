package dynamodb

import (
	"fmt"

	"github.com/ace-teknologi/memzy"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
)

var (
	// ErrNullClient is returned if you try to create an iterator with a null client
	ErrNullClient = fmt.Errorf("Cannot create an Iter with a null client")
)

// Iter provides a convenient interface for iterating over the elements returned
// from paginated list API calls. Successive calls to the Next method will step
// through each item in the list, fetching pages of items as needed. Iterators
// are not thread-safe, so they should not be consumed across multiple
// goroutines.
type Iter struct {
	c            *Client
	cur          map[string]*dynamodb.AttributeValue
	err          error
	nextStartKey map[string]*dynamodb.AttributeValue
	values       []map[string]*dynamodb.AttributeValue
}

// NewIter returns a pointer to an Iter. It also performs an initial scan so it
// is ready to go, this probably should be avoided.
func (c *Client) NewIter(args ...interface{}) memzy.Iter {
	// Ensure we didn't get a null client
	if c == nil {
		return &Iter{
			err: ErrNullClient,
		}
	}

	it := &Iter{c: c}

	it.getNextPage()

	return it
}

// Current returns the most recent item visited by a call to Next.
func (it *Iter) Current(v interface{}) error {
	return dynamodbattribute.UnmarshalMap(it.cur, v)
}

// Err returns the error, if any, that caused the Iter to stop. It must be
// inspected after Next returns false.
func (it *Iter) Err() error {
	return it.err
}

// Next advances the Iter to the next item in the list, which will then be
// available through the Current method. It returns false when the iterator
// stops at the end of the list.
func (it *Iter) Next() bool {
	if len(it.values) == 0 && it.nextStartKey != nil {
		// get more pages
		it.getNextPage()
	}

	if len(it.values) == 0 {
		// we are finished here
		return false
	}

	it.cur = it.values[0]
	it.values = it.values[1:]

	return true
}

func (it *Iter) getNextPage() {
	input := &dynamodb.ScanInput{
		ExclusiveStartKey: it.nextStartKey,
		TableName:         it.c.TableName,
	}

	out, err := it.c.Service.Scan(input)
	if err != nil {
		it.err = err
		return
	}

	it.nextStartKey = out.LastEvaluatedKey
	it.values = out.Items
}
