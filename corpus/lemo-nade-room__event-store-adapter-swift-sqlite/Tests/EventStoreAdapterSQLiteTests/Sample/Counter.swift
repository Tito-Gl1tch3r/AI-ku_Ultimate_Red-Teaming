import Dependencies
import EventStoreAdapter
import Foundation

actor Counter {
  nonisolated let aid: AID
  var seqNr: Int
  nonisolated let version: Int
  var lastUpdatedAt: Date

  let uuid: UUIDGenerator
  let date: DateGenerator

  var count: Int

  init(
    aid: AID,
    seqNr: Int,
    version: Int,
    lastUpdatedAt: Date,
    uuid: UUIDGenerator,
    date: DateGenerator,
    count: Int
  ) {
    self.aid = aid
    self.seqNr = seqNr
    self.version = version
    self.lastUpdatedAt = lastUpdatedAt
    self.uuid = uuid
    self.date = date
    self.count = count
  }

  static func create(uuid: UUIDGenerator, date: DateGenerator) -> (counter: Counter, event: Counter.Event) {
    let event = Counter.Event.Created(
      id: uuid(),
      aid: .init(value: uuid()),
      seqNr: 1,
      occurredAt: date(),
      isCreated: true,
    )

    let counter = Counter(
      aid: event.aid,
      seqNr: event.seqNr,
      version: 1,
      lastUpdatedAt: event.occurredAt,
      uuid: uuid,
      date: date,
      count: 0
    )

    return (counter, event: .created(event))
  }

  func increment() -> Event {
    let event = decideIncrement()
    apply(incremented: event)
    return .incremented(event)
  }

  func decideIncrement() -> Event.Incremented {
    .init(id: uuid(), aid: aid, seqNr: seqNr + 1, occurredAt: date(), isCreated: false)
  }

  func apply(incremented: Event.Incremented) {
    self.count += 1
    self.seqNr = incremented.seqNr
    self.lastUpdatedAt = incremented.occurredAt
  }

  func decrement() -> Event {
    let event = decideDecrement()
    apply(decremented: event)
    return .decremented(event)
  }

  func decideDecrement() -> Event.Decremented {
    .init(id: uuid(), aid: aid, seqNr: seqNr + 1, occurredAt: date(), isCreated: false)
  }

  func apply(decremented: Event.Decremented) {
    self.count -= 1
    self.seqNr = decremented.seqNr
    self.lastUpdatedAt = decremented.occurredAt
  }

  func apply(_ event: Event) {
    switch event {
      case .created(_): break
      case .incremented(let event): apply(incremented: event)
      case .decremented(let event): apply(decremented: event)
    }
  }

  func apply(_ events: [Event]) {
    for event in events {
      apply(event)
    }
  }
}
