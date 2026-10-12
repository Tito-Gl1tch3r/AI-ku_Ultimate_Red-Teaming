import { beforeEach, describe, it } from 'node:test'
import { expect } from 'chai'
import pg from 'pg'
import { newDb } from 'pg-mem'
import { JsonRepository } from '../src/repository.js'
import { MANAGED } from '../src/models.js'
import { withTx } from '../src/query.js'
import { handleTransaction } from './utils.js'

type Entity = {
	id: string
	name: string
}
class TestRepository extends JsonRepository<Entity> {
	constructor(pool: pg.Pool) {
		super('table1', pool)
	}

	protected clone(): this {
		return new TestRepository(this.pgPool) as this
	}
}

describe('JsonRepository', () => {
	let repo: TestRepository
	let db: ReturnType<typeof newDb>

	beforeEach(() => {
		db = newDb()
		db.public.interceptQueries(handleTransaction(db))

		db.public.query(`
			create table table1 (
				id varchar(255) primary key,
				created timestamp not null default now(),
				updated timestamp not null default now(),
				tenant_id varchar(255),
				data jsonb 
		);`)
		const { Pool } = db.adapters.createPg()
		repo = new TestRepository(new Pool())
	})

	it('should create a new instance', async () => {
		const saved = await repo.insert({ id: '1', name: 'test' })
		expect(saved).to.include({ id: '1', name: 'test' })
		expect(saved.created).to.be.a('date')
		expect(saved.updated).to.be.a('date')
		expect(saved[MANAGED]).to.be.true
	})

	it('should update an existing instance', async () => {
		const saved = await repo.insert({ id: '1', name: 'test' })
		const updated = await repo.update({ ...saved, name: 'updated' })

		expect(updated).to.include({ id: '1', name: 'updated' })
		expect(updated.created).to.deep.equal(saved.created)
		expect(updated.updated).to.be.a('date')
		expect(updated.updated.getTime()).to.be.above(saved.updated.getTime())
	})

	it('should fetch an existing instance', async () => {
		const saved = await repo.insert({ id: '1', name: 'test' })
		const fetched = await repo.fetch('1')

		expect(fetched).to.deep.equal(saved)
		expect(fetched?.[MANAGED]).to.be.true
	})

	it('should return null for non-existing instance', async () => {
		const fetched = await repo.fetch('non-existing-id')
		expect(fetched).to.be.null
	})

	it('should delete an existing instance by instance', async () => {
		const saved = await repo.insert({ id: '1', name: 'test' })
		const deleted = await repo.delete(saved)

		expect(deleted).to.include({ id: '1', name: 'test' })
		expect(deleted[MANAGED]).to.be.false

		const fetched = await repo.fetch('1')
		expect(fetched).to.be.null
	})

	it('should delete an existing instance by id', async () => {
		const saved = await repo.insert({ id: '1', name: 'test' })
		const deletedCount = await repo.deleteById('1')

		expect(deletedCount).to.equal(1)

		const fetched = await repo.fetch('1')
		expect(fetched).to.be.null
	})

	it('should handle transaction rollbacks', async () => {
		const { Client } = db.adapters.createPg()
		await withTx(new Client(), async tx => {
			const txRepo = repo.withTx(tx)
			const saved = await txRepo.insert({ id: '1', name: 'test' })
			expect(saved).to.include({ id: '1', name: 'test' })

			const fetched = await txRepo.fetch('1')
			expect(fetched).to.deep.equal(saved)

			throw new Error('Simulated error to test rollback')
		}).catch(err => {
			//Ignore the error, we just want to test rollback
		})

		const fetchedAfterTx = await repo.fetch('1')
		expect(fetchedAfterTx).to.be.null
	})

	it('should handle transaction commits', async () => {
		const { Client } = db.adapters.createPg()
		let saved: Entity | null = null
		await withTx(new Client(), async tx => {
			const txRepo = repo.withTx(tx)
			saved = await txRepo.insert({ id: '1', name: 'test' })
			expect(saved).to.include({ id: '1', name: 'test' })

			const fetched = await txRepo.fetch('1')
			expect(fetched).to.deep.equal(saved)
		})

		const fetchedAfterTx = await repo.fetch('1')
		expect(fetchedAfterTx).to.deep.equal(saved)
	})
})
