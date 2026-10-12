/*
 * Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * Licensed under the Apache License, Version 2.0 (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */

import { CreateTableCommand, DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DeleteCommand, DynamoDBDocumentClient, GetCommand, PutCommand } from "@aws-sdk/lib-dynamodb";
import { mockClient } from "aws-sdk-client-mock";

import { expect } from 'chai';
import { DynamoDbPersistenceAdapter } from '../../../lib/attributes/persistence/DynamoDbPersistenceAdapter';
import { PartitionKeyGenerators } from '../../../lib/attributes/persistence/PartitionKeyGenerators';
import { JsonProvider } from '../../mocks/JsonProvider';

const dynamodb = new DynamoDBClient({ apiVersion: 'latest' });
const ddbMock = mockClient(DynamoDBDocumentClient);

describe('DynamoDbPersistenceAdapter', () => {
    const tableName = 'mockTableName';
    const defaultPartitionKeyName = 'id';
    const defaultPartitionKey = 'userId';
    const defaultAttributesName = 'attributes';
    const defaultAttributes = {
        defaultKey: 'defaultValue',
    };
    const defaultGetCommandOutput = {
        Item: {
            [defaultPartitionKeyName]: defaultPartitionKey,
            [defaultAttributesName]: defaultAttributes,
        }
    };

    const customPartitionKeyName = 'mockId';
    const customPartitionKey = 'deviceId';
    const customAttributesName = 'mockAttributes';
    const customAttributes = {
        customKey: 'customValue',
    };
    const customGetCommandOutput = {
        Item: {
            [customPartitionKeyName]: customPartitionKey,
            [customAttributesName]: customAttributes,
        }
    };

    const resourceNotFoundError = new Error('Requested resource not found');
    Object.defineProperty(resourceNotFoundError, 'code', {
        value: 'ResourceNotFoundException',
        writable: false,
    });

    const resourceInUseError = new Error('Requested resource in use');
    Object.defineProperty(resourceInUseError, 'code', {
        value: 'ResourceInUseException',
        writable: false,
    });

    const requestEnvelope = JsonProvider.requestEnvelope();
    requestEnvelope.context.System.device.deviceId = 'deviceId';
    requestEnvelope.context.System.user.userId = 'userId';

    before((done) => {
        ddbMock.reset();
        done();
    });

    after((done) => {
        ddbMock.restore();
        done();
    });

    it('should be able to get an item from table', async () => {
        const defaultPersistenceAdapter = new DynamoDbPersistenceAdapter({
            tableName,
        });
        const customPersistenceAdapter = new DynamoDbPersistenceAdapter({
            tableName,
            partitionKeyName: customPartitionKeyName,
            attributesName: customAttributesName,
            dynamoDBClient: dynamodb,
            partitionKeyGenerator: PartitionKeyGenerators.deviceId,
        });

        ddbMock.on(GetCommand).resolves(defaultGetCommandOutput);

        const defaultResult = await defaultPersistenceAdapter.getAttributes(requestEnvelope);
        expect(defaultResult[defaultPartitionKey]).equal(undefined);
        expect(defaultResult['defaultKey']).equal('defaultValue');

        ddbMock.on(GetCommand).resolves(customGetCommandOutput);

        const customResult = await customPersistenceAdapter.getAttributes(requestEnvelope);
        expect(customResult[customPartitionKeyName]).equal(undefined);
        expect(customResult['customKey']).equal('customValue');
    });

    it('should be able to put an item to table', async () => {
        const persistenceAdapter = new DynamoDbPersistenceAdapter({
            tableName,
        });
        ddbMock.on(PutCommand).resolves({});
        await persistenceAdapter.saveAttributes(requestEnvelope, {});
    });

    it('should be able to delete an item from table', async () => {
        const persistenceAdapter = new DynamoDbPersistenceAdapter({
            tableName,
        });
        ddbMock.on(DeleteCommand).resolves({});
        await persistenceAdapter.deleteAttributes(requestEnvelope);
    });

    it('should return an empty object when getting item that does not exist in table', async () => {
        const persistenceAdapter = new DynamoDbPersistenceAdapter({
            tableName,
        });

        const mockRequestEnvelope = JsonProvider.requestEnvelope();
        mockRequestEnvelope.context.System.user.userId = 'NonExistentKey';

        ddbMock.on(GetCommand).resolves({ Item: {} });

        const result = await persistenceAdapter.getAttributes(mockRequestEnvelope);
        expect(result).deep.equal({});
    });

    it('should throw an error when saving and the table does not exist', async () => {
        const persistenceAdapter = new DynamoDbPersistenceAdapter({
            tableName: 'NonExistentTable',
        });

        ddbMock.on(PutCommand).rejects('Requested resource not found');

        try {
            await persistenceAdapter.saveAttributes(requestEnvelope, {});
        } catch (err) {
            expect(err.name).equal('AskSdk.DynamoDbPersistenceAdapter Error');
            expect(err.message).equal('Could not save item (userId) to table (NonExistentTable): '
                + 'Requested resource not found');

            return;
        }
        throw new Error('should have thrown an error!');
    });

    it('should throw an error when deleting and the table does not exist', async () => {
        const persistenceAdapter = new DynamoDbPersistenceAdapter({
            tableName: 'NonExistentTable',
        });

        ddbMock.on(DeleteCommand).rejects('Requested resource not found');

        try {
            await persistenceAdapter.deleteAttributes(requestEnvelope);
        } catch (err) {
            expect(err.name).equal('AskSdk.DynamoDbPersistenceAdapter Error');
            expect(err.message).equal('Could not delete item (userId) from table (NonExistentTable): '
                + 'Requested resource not found');

            return;
        }
        throw new Error('should have thrown an error!');
    });

    describe('with AutoCreateTable', () => {
        it('should throw an error when create table returns error other than ResourceInUseException', () => {
            ddbMock.on(CreateTableCommand).rejects();

            try {
                const persistenceAdapter = new DynamoDbPersistenceAdapter({
                    tableName: 'CreateNewErrorTable',
                    createTable: true,
                });
            } catch (err) {
                expect(err.name).eq('AskSdk.DynamoDbPersistenceAdapter Error');
                expect(err.message).eq('Could not create table (CreateNewErrorTable): Unable to create table');
            }
        });

        it('should not throw any error if the table already exists', () => {
            ddbMock.on(CreateTableCommand).resolves({});
            const persistenceAdapter = new DynamoDbPersistenceAdapter({
                tableName,
                createTable: true,
            });
        });
    });

    describe('without AutoCreateTable', () => {
        it('should throw an error when reading and the table does not exist', async () => {
            const persistenceAdapter = new DynamoDbPersistenceAdapter({
                tableName: 'NonExistentTable',
                createTable: false,
            });

            ddbMock.on(GetCommand).rejects('Requested resource not found');

            try {
                const data = await persistenceAdapter.getAttributes(requestEnvelope);
            } catch (err) {
                expect(err.name).equal('AskSdk.DynamoDbPersistenceAdapter Error');
                expect(err.message).equal('Could not read item (userId) from table (NonExistentTable): '
                    + 'Requested resource not found');

                return;
            }
            throw new Error('should have thrown an error!');
        });
    });
});
