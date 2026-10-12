package dynamodb

import (
	"testing"

	"github.com/ace-teknologi/memzy"
	"github.com/aws/aws-sdk-go/service/dynamodb"
)

var (
	anItem = map[string]*dynamodb.AttributeValue{
		"beer": &dynamodb.AttributeValue{
			S: str("yum"),
		}}

	keyItem = map[string]*dynamodb.AttributeValue{
		"whiskey": &dynamodb.AttributeValue{
			S: str("yum"),
		}}

	singlePageResponse = dynamodb.ScanOutput{
		Items: []map[string]*dynamodb.AttributeValue{
			anItem,
		},
	}

	multiPageResponse = dynamodb.ScanOutput{
		Items: []map[string]*dynamodb.AttributeValue{
			anItem,
			anItem,
			keyItem,
		},
		LastEvaluatedKey: keyItem,
	}
)

func TestIterImplementsMemzy(t *testing.T) {
	i := &Iter{}
	if _, ok := interface{}(i).(memzy.Iter); !ok {
		t.Errorf("Iter does not implement memzy.Iter")
	}
}

func TestIter_singlePage(t *testing.T) {
	c := testClient("single-page-test-table")

	mock.ExpectScan().Table("single-page-test-table").WillReturns(singlePageResponse)

	it := c.NewIter().(*Iter)
	if it.err != nil {
		t.Error(it.err)
	}

	testNextItemExists(it, t)
	testBeer(it, t)
	testFinished(it, t)
}

func TestIter_multiPage(t *testing.T) {
	c := testClient("multi-page-test-table")

	mock.ExpectScan().Table("multi-page-test-table").WillReturns(multiPageResponse)
	mock.ExpectScan().Table("multi-page-test-table").WillReturns(singlePageResponse)

	it := c.NewIter().(*Iter)
	if it.err != nil {
		t.Error(it.err)
	}

	testNextItemExists(it, t)
	testBeer(it, t)
	testNextItemExists(it, t)
	testBeer(it, t)
	testNextItemExists(it, t)
	testWhiskey(it, t)

	testNextItemExists(it, t)
	testBeer(it, t)

	testFinished(it, t)
}

func TestIter_nullClient(t *testing.T) {
	var c *Client

	it := c.NewIter()
	if it.Err() != ErrNullClient {
		t.Errorf("Expected a null client error, got %v", it.Err())
	}
}

type TestObject struct {
	Beer    string `json:"beer"`
	Whiskey string `json:"whiskey"`
}

func testBeer(it *Iter, t *testing.T) {
	var beer TestObject
	err := it.Current(&beer)
	if err != nil {
		t.Error(err)
	}
	if beer.Beer != "yum" {
		t.Errorf("Expected beer to be yum, but it was %v", beer.Beer)
	}
}

func testFinished(it *Iter, t *testing.T) {
	if it.Next() {
		t.Errorf("Expected the items to be finished, but got one more!")
	}

	if it.Err() != nil {
		t.Errorf("Didn't finish cleanly: %v", it.Err())
	}
}

func testWhiskey(it *Iter, t *testing.T) {
	var whiskey TestObject
	err := it.Current(&whiskey)
	if err != nil {
		t.Error(err)
	}
	if whiskey.Whiskey != "yum" {
		t.Errorf("Expected whiskey to be yum, but it was %v", whiskey.Whiskey)
	}
}

func testNextItemExists(it *Iter, t *testing.T) {
	if !it.Next() {
		t.Errorf("Expecting an item, but there was none! %v", it.Err())
	}
}

func str(s string) *string {
	return &s
}
