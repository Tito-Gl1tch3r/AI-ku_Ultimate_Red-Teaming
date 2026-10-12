package dynamodb

import (
	"fmt"

	"github.com/ace-teknologi/memzy"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbiface"
)

// Client provides a connection to dynamo
type Client struct {
	Service   dynamodbiface.DynamoDBAPI
	TableName *string
}

// New returns a pointer to a Client
func New(t string) *Client {
	sess := session.New()
	return &Client{
		Service:   dynamodb.New(sess),
		TableName: &t,
	}
}

// GetItem retrieves a go object from the table, using a consistent read
func (c *Client) GetItem(v interface{}, key map[string]interface{}) error {
	var primaryKey = make(map[string]*dynamodb.AttributeValue)
	for k, val := range key {
		valAttr, err := dynamodbattribute.Marshal(val)
		if err != nil {
			return fmt.Errorf("Could not marshal primary key: %v", err)
		}
		primaryKey[k] = valAttr
	}
	in := &dynamodb.GetItemInput{
		ConsistentRead: aws.Bool(true),
		Key:            primaryKey,
		TableName:      c.TableName,
	}
	out, err := c.Service.GetItem(in)
	if err != nil {
		return fmt.Errorf("Could not GetItem from DynamoDB: %v", err)
	}

	if out.Item == nil {
		return memzy.ErrNotFound
	}

	err = dynamodbattribute.UnmarshalMap(out.Item, v)
	if err != nil {
		return fmt.Errorf("Could not unmarshal: %v", err)
	}

	return nil
}

// PutItem stores your go object in the table
func (c *Client) PutItem(v interface{}) error {
	item, err := dynamodbattribute.MarshalMap(v)
	if err != nil {
		return err
	}

	_, err = c.Service.PutItem(&dynamodb.PutItemInput{
		Item:      item,
		TableName: c.TableName,
	})
	return err
}
