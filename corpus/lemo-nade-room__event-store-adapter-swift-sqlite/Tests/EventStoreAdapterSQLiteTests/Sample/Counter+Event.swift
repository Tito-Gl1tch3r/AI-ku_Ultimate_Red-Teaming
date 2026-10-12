import EventStoreAdapter
import EventStoreAdapterSupport
import Foundation

extension Counter {
  @EventSupport
  enum Event: EventStoreAdapter.Event {
    case created(Created)
    case incremented(Incremented)
    case decremented(Decremented)

    typealias Id = UUID
    typealias AID = Counter.AID

    struct Created: EventStoreAdapter.Event {
      var id: UUID
      var aid: Counter.AID
      var seqNr: Int
      var occurredAt: Date
      var isCreated: Bool
    }

    struct Incremented: EventStoreAdapter.Event {
      var id: UUID
      var aid: Counter.AID
      var seqNr: Int
      var occurredAt: Date
      var isCreated: Bool
    }

    struct Decremented: EventStoreAdapter.Event {
      var id: UUID
      var aid: Counter.AID
      var seqNr: Int
      var occurredAt: Date
      var isCreated: Bool
    }
  }
}
