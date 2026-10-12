import type { DebugEventCallback } from "types/debug-logger";

export type EventID = string;
export type EventName = string;
export type SubscriberID = string;

export interface TinyBusEvent<T extends object = any, A extends any[] = any[]> {
  /**
   * The ID of the event.
   */
  id: EventID;
  /**
   * The name of the event.
   */
  name: EventName;
  /**
   * The context provided to TinyBus when the event was emitted.
   */
  context?: T;
  /**
   * The arguments passed to the event.
   */
  args?: A;
}

export interface TinyBusInterface<T extends object = any> {
  /**
   * Emits an event to all subscribers. If a subscriber throws an error, the
   * event will be retried up to the `maxRetries` option. If the event is still
   * not successful, the error will be passed to the error handler for that
   * subscriber. If the strategy is set to `exit-on-error`, the event will not
   * be retried for any other subscribers.
   */
  emit<A extends any[] = any[]>(
    eventName: EventName,
    ...args: A
  ): Promise<EventID | undefined>;

  /**
   * Subscribes a callback to an event. The callback will be called with the
   * subscriber id, context, and arguments passed to the event.
   */
  on<A extends any[] = any[]>(
    eventName: EventName,
    options: EventSubscriberOptions<T, A>,
  ): Promise<SubscriberID>;

  /**
   * Removes a subscriber from an event. If the subscriber is not found,
   * an error will be thrown.
   */
  remove(eventName: EventName, subscriberId: string): Promise<SubscriberID>;

  /**
   * Removes all subscribers for an event. If the event is not found, an error
   * will be thrown.
   */
  removeAll(eventName: EventName): Promise<EventName>;

  /**
   * Replays a specific event. This will emit the event to all subscribers
   * without duplicating the event in the event store.
   */
  replay(eventId: EventID): Promise<void>;
}

export interface TinyBusOptions<T extends object = any> {
  /**
   * If set to true, the event bus will log debug information for all
   * events emitted. Defaults to false.
   */
  debug?: boolean;
  /**
   * Called to replace the default debug logger. If not provided, the default
   * debug logger will be used.
   */
  onDebug?: DebugEventCallback;
  /**
   * The context of the subscriber that emitted the event.
   */
  context?: T;
  /**
   * The maximum number of times to retry an event before giving up.
   */
  maxRetries?: number;
  /**
   * The number of milliseconds to wait before retrying an event.
   */
  retryInterval?: number;
  /**
   * If set to false the event bus will not throw an error if an event is
   * emitted that has already been emitted. Defaults to true.
   */
  uniqueEvents?: boolean;
  /**
   * Determines if the event bus persists events to the event store. Defaults
   * to true. If disabled, the `emit` method will return undefined.
   */
  persistEvents?: boolean;
  /**
   * Called to retrieve the id of the subscriber. If not provided, a random
   * id via the `nanoid()` function will be generated.
   *
   * @see https://www.npmjs.com/package/nanoid
   */
  onIdentifier?: () => Promise<SubscriberID>;
  /**
   * The mode to use when subscribing to events. If set to `single`, the event
   * will cause the subscriber to exit after the first event is emitted. If set
   * to `multiple`, the subscriber will continue to listen for events until manually
   * removed via `unsubscribe`. Defaults to `single`.
   */
  subscriberMode?: "single" | "multiple";
  /**
   * The strategy to use when an event fails. If set to `exit-on-error`, the
   * event will not be retried for any other subscribers. If set to
   * `continue-on-error`, the event will be retried for all other subscribers
   * after the error handler is called.
   */
  errorStrategy?: "exit-on-error" | "continue-on-error";
  /**
   * Called when a unsubscribe event is emitted for a subscriber. This can be
   * used to clean up any resources that were created when the subscriber was
   * added.
   */
  onUnsubscribe?: (
    eventName: EventName,
    subscriberId: SubscriberID,
  ) => Promise<void>;
  /**
   * Called when a subscribe event is emitted for a subscriber. This can be
   * used to initialize any resources that are needed for the subscriber.
   */
  onSubscribe?: (
    eventName: EventName,
    subscriberId: SubscriberID,
  ) => Promise<void>;
  /**
   * Called to check if an event is unique. If not provided, the event name
   * and arguments will be used to determine if the event is unique.
   */
  onUniqueCheck?: (
    eventName: EventName,
    args: any[],
  ) => Promise<boolean> | boolean;
  /**
   * Called when an event is emitted. This can be used to persist the event
   * to a database or other storage mechanism.
   */
  onPersist?: <A extends any[] = any[]>(
    event: Omit<TinyBusEvent<T, A>, "id">,
  ) => Promise<EventID>;
  /**
   * Called when an event is restored. This can be used to restore the event
   * from a database or other storage mechanism.
   */
  onRestore?: <A extends any[] = any[]>(
    eventId: EventID,
  ) => Promise<TinyBusEvent<T, any[]>>;
}

export type EventCallback<T extends object = any, A extends any[] = any[]> = (
  /**
   * The ID of the subscriber that emitted the event.
   */
  subscriberId: SubscriberID,
  /**
   * The context of the subscriber that emitted the event.
   */
  context?: T,
  /**
   * The arguments passed to the event.
   */
  ...args: A
) => Promise<void> | void;

export interface EventSubscriber<
  T extends object = any,
  A extends any[] = any[],
> {
  /**
   * The ID of the subscriber.
   */
  subscriberId: SubscriberID;
  /**
   * The context of the subscriber.
   */
  context?: T;
  /**
   * The callback function that will be called when the event is emitted.
   */
  onCallback: EventCallback<T, A>;
}

export interface EventRetryError extends Error {
  /**
   * The error that caused the retry.
   */
  cause: Error[];
  /**
   * The name of the event that caused the retry.
   */
  eventName: EventName;
  /**
   * The ID of the subscriber that caused the retry.
   */
  subscriberId: SubscriberID;
}

export interface EventErrorPayload<E> {
  /**
   * The error that caused the retry error.
   */
  error: E;
  /**
   * The name of the event that caused the retry error.
   */
  eventName: EventName;
  /**
   * The ID of the subscriber that caused the retry error.
   */
  subscriberId: SubscriberID;
}

export type EventErrorCallback<E extends Error = Error> = (
  error: EventErrorPayload<E>,
) => void;

export interface PriorityEventSubscriber<
  T extends object = any,
  A extends any[] = any[],
> extends EventSubscriber<T, A> {
  /**
   * The priority of the subscriber, this is used to determine the order in
   * the PriorityQueue when emitting events. If two subscribers have the same
   * priority, they will be emitted in the order they were added.
   */
  priority: number;
}

export interface EventSubscriberOptions<
  T extends object = any,
  A extends any[] = any[],
> {
  /**
   * The priority of the subscriber, this is used to determine the order in
   * the PriorityQueue when emitting events. If two subscribers have the same
   * priority, they will be emitted in the order they were added.
   */
  priority?: number;
  /**
   * The callback function that will be called when the event is emitted. The
   * callback will be called with the subscriber id, context, and arguments.
   */
  onCallback: EventCallback<T, A>;
  /**
   * The error handler function that will be called when the event fails. Each
   * subscriber can have its own error handler. The error unique error handler.
   */
  onError?: EventErrorCallback;
}
