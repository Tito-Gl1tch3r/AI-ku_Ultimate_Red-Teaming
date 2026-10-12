import { nanoid } from "nanoid";

import type { EventID, TinyBusEvent } from "types/tiny-bus";

/**
 * ### Event Store
 *
 * The event store is a simple in-memory store for events. It is used by the
 * the `TinyBus` class to store events that have been emitted if no custom
 * `onRestore` and `onPersist` functions are provided.
 */
export default class EventStore<T extends object = any> {
  constructor(private readonly events = new Map<string, TinyBusEvent>()) {}

  /**
   * Allows you to persist an event to the store. This is used by the `TinyBus`
   * class when no custom `onPersist` function is provided.
   */
  public persist<A extends any[] = any[]>(
    event: Omit<TinyBusEvent<T, A>, "id">,
  ): EventID {
    const id = nanoid();
    if (this.events.has(id)) throw new Error(`Event ${id} already exists.`);
    this.events.set(id, { ...event, id });
    return id;
  }

  /**
   * Allows you to restore an event from the store. This is used by the `TinyBus`
   * class when no custom `onRestore` function is provided.
   */
  public restore<A extends any[] = any[]>(id: EventID): TinyBusEvent<T, A> {
    const event = this.events.get(id);
    if (!event) throw new Error(`Event with id ${id} not found.`);
    return event as TinyBusEvent<T, A>;
  }
}
