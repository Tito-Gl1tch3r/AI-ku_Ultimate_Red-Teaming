import pg, { QueryConfig, QueryResult, QueryResultRow } from 'pg'
import {
	TenantId,
	Entity,
	Id,
	SavedEntity,
	MANAGED,
	MaybeManaged,
	Managed,
} from './models.js'

const buildQueries = (table: string) =>
	({
		__table: table,
		fetchById: `SELECT * FROM ${table} WHERE id=$1`,
		deleteById: `DELETE FROM ${table} WHERE id=$1`,
		insert: `INSERT INTO ${table} (id, tenant_id, data) VALUES ($1, $2, $3) RETURNING *`,
		update: `UPDATE ${table} SET updated=NOW(), data=$2 WHERE id=$1 RETURNING *`,
		_upsert: `INSERT INTO ${table}
    (id, created, updated, tenant_id, data) VALUES ($1, $2, $3, $4, $5)
    ON CONFLICT (uuid) DO UPDATE SET updated=$3, data=$4
		RETURNING *
  `,
	}) as const
type Queries = ReturnType<typeof buildQueries>

export abstract class Repository {
	protected pgPool: pg.Pool
	protected tx?: pg.ClientBase
	protected tenantId?: TenantId

	constructor(pgPool: pg.Pool) {
		this.pgPool = pgPool
	}

	/**
	 * Create a new instance of the repository with the same configuration.
	 * Will be used for withTx and withTenant methods.
	 */
	protected abstract clone(): this

	public withTenant(tenantId: TenantId): this {
		const repo = this.clone()
		repo.tx = this.tx
		repo.tenantId = tenantId
		return repo as this
	}
	public withTx(tx: pg.ClientBase): this {
		const repo = this.clone()
		repo.tenantId = this.tenantId
		repo.tx = tx
		return repo as this
	}

	// biome-ignore lint/suspicious/noExplicitAny: We cannot predict the type of user queries
	protected async execute<T extends QueryResultRow = any>(
		query: string,
		...args: unknown[]
	): Promise<QueryResult<T>>
	// biome-ignore lint/suspicious/noExplicitAny: We cannot predict the type of user queries
	protected async execute<T extends QueryResultRow = any>(
		config: QueryConfig
	): Promise<QueryResult<T>>
	protected async execute<T>(
		fn: (client: pg.ClientBase) => Promise<T>
	): Promise<T>
	protected async execute<T>(
		fnOrQuery: ((client: pg.ClientBase) => Promise<T>) | string | QueryConfig,
		...args: unknown[]
	): Promise<T> {
		const releaseClient = !this.tx
		const client = this.tx || (await this.pgPool.connect())

		try {
			if (this.tenantId)
				await client.query(
					`set "app.current_tenant"=${client.escapeLiteral(this.tenantId)}`
				)
			else {
				await client.query('set "app.current_tenant" to default')
			}

			if (typeof fnOrQuery === 'string') {
				return (await client.query(fnOrQuery, args)) as T
			} else if (typeof fnOrQuery === 'object') {
				return (await client.query(fnOrQuery)) as T
			} else {
				return await fnOrQuery(client)
			}
		} finally {
			try {
				await client.query('set "app.current_tenant" to default')
			} finally {
				if (releaseClient) {
					await (client as pg.PoolClient).release()
				}
			}
		}
	}
}

export type JsonData<R extends Entity> = Omit<R, 'id' | 'created' | 'updated'>
export type JsonRow<D> = {
	id: Id
	created: Date
	updated: Date
	tenant_id: TenantId
	data: D
}
export abstract class JsonRepository<
	T extends Entity,
	R = JsonData<T>,
> extends Repository {
	private query: Queries

	constructor(tableNameOrQueries: string | Queries, pool: pg.Pool) {
		super(pool)
		if (typeof tableNameOrQueries === 'string') {
			this.query = buildQueries(tableNameOrQueries)
		} else {
			this.query = tableNameOrQueries
		}
	}

	protected deserialize(row: JsonRow<R>): SavedEntity<T> {
		return {
			...row.data,
			created: row.created,
			updated: row.updated,
			[MANAGED]: true,
		} as unknown as SavedEntity<T>
	}

	protected serialize(data: T | SavedEntity<T>): R {
		const {
			created: _created,
			updated: _updated,
			...rest
		} = data as SavedEntity<T>
		return rest as R
	}

	async fetch(id: Id): Promise<T | null> {
		const { rows } = await this.execute(client =>
			client.query(this.query.fetchById, [id])
		)
		if (rows.length === 0) {
			return null
		} else {
			const entity = rows.map(this.deserialize)[0]
			entity[MANAGED] = true
			return entity
		}
	}

	async delete(entity: SavedEntity<T>): Promise<T>
	async delete(id: Id): Promise<number>
	async delete(idOrEntity: Id | SavedEntity<T>): Promise<number | T> {
		if (typeof idOrEntity === 'string') {
			return this.deleteById(idOrEntity)
		} else {
			const res = await this.execute(client =>
				client.query(this.query.deleteById, [idOrEntity.id])
			)
			if ((res.rowCount = 0)) {
				throw new Error(
					`Entity with id ${idOrEntity.id} not found in ${this.query.__table}`
				)
			} else if (res.rowCount > 1) {
				throw new Error(
					`More than one entity with id ${idOrEntity.id} found in ${this.query.__table}`
				)
			} else {
				const copy = { ...idOrEntity }
				copy[MANAGED] = false
				return copy
			}
		}
	}

	async deleteById(id: Id): Promise<number> {
		const res = await this.execute(client =>
			client.query(this.query.deleteById, [id])
		)
		return res.rowCount || 0
	}

	async save(entity: T | SavedEntity<T>): Promise<SavedEntity<T>> {
		if (isManaged(entity as SavedEntity<T>)) {
			return this.update(entity as SavedEntity<T>)
		} else {
			return this.insert(entity)
		}
	}

	async insert(entity: T): Promise<SavedEntity<T>> {
		const serialized = this.serialize(entity)
		const res = await this.execute(client =>
			client.query(this.query.insert, [entity.id, this.tenantId, serialized])
		)
		if (res.rowCount !== 1) {
			throw new Error('Insert failed')
		}
		return this.deserialize(res.rows[0])
	}

	async update(entity: SavedEntity<T>): Promise<SavedEntity<T>> {
		const serialized = this.serialize(entity)
		const res = await this.execute(client =>
			client.query(this.query.update, [entity.id, serialized])
		)

		if (res.rowCount !== 1) {
			throw new Error('Update failed')
		}
		return this.deserialize(res.rows[0])
	}
}

export const isManaged = (entity: MaybeManaged): entity is Managed =>
	!!entity[MANAGED]

export const validateIsManaged = <T extends MaybeManaged>(
	entity: T
): Omit<T, '[MANAGED_MARKER]'> & Managed => {
	if (!isManaged(entity)) {
		// biome-ignore lint/suspicious/noExplicitAny: Just log if we know the id
		throw new Error('Item is not managed:' + (entity as any)?.id)
	}

	return entity as Omit<T, '[MANAGED_MARKER]'> & Managed
}

export const validateIsUnmanaged = <T>(entity: T): T => {
	if ((entity as MaybeManaged)[MANAGED]) {
		// biome-ignore lint/suspicious/noExplicitAny: Just log if we know the id
		throw new Error('Item is not managed:' + (entity as any)?.id)
	}
	return entity
}
