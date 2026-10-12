import { nanoid } from "nanoid";
import { expect, it } from "bun:test";

import TinyBus from "classes/tiny-bus";
import type { TinyBusEvent } from "dist";

/**
 * Multiple run-through mode allows subscribers to be called multiple times
 * for the same event. This is useful for things like logging or metrics.
 */

it('Mode "multiple" with unique events works as expected', async () => {
  const tinyBus = new TinyBus({
    uniqueEvents: true,
    subscriberMode: "multiple",
    context: { test: "test" },
    onIdentifier: async () => "test",
  });

  const subscriberId = await tinyBus.on("multiple::sub::args", {
    onCallback: (id, context, ...args) => {
      expect(id).toBe("test");
      expect(context).toEqual({ test: "test" });
      expect(args).toEqual(["test"]);
    },
  });

  await tinyBus.emit("multiple::sub::args", "test");

  try {
    await tinyBus.emit("multiple::sub::args", "test");
  } catch (error: any) {
    expect(error.message).toBe(
      'Event multiple::sub::args with args ["test"] was already emitted.',
    );
  }

  const unsubscribeId = await tinyBus.remove(
    "multiple::sub::args",
    subscriberId,
  );

  expect(unsubscribeId).toBe(subscriberId);
});

it('Mode "multiple" without unique events works as expected', async () => {
  const tinyBus = new TinyBus({
    uniqueEvents: false,
    subscriberMode: "multiple",
    context: { test: "test" },
    onIdentifier: async () => "test",
  });

  const subscriberId = await tinyBus.on("multiple::sub::args", {
    onCallback: (id, context, ...args) => {
      expect(id).toBe("test");
      expect(context).toEqual({ test: "test" });
      expect(args).toEqual(["test"]);
    },
  });

  await tinyBus.emit("multiple::sub::args", "test");
  await tinyBus.emit("multiple::sub::args", "test");

  const unsubscribeId = await tinyBus.remove(
    "multiple::sub::args",
    subscriberId,
  );

  expect(unsubscribeId).toBe(subscriberId);
});

it("Removing all subscribers works as expected", async () => {
  const tinyBus = new TinyBus({
    uniqueEvents: false,
    subscriberMode: "multiple",
    context: { test: "test" },
    onIdentifier: async () => "test",
  });

  await tinyBus.on("multiple::sub::args", {
    onCallback: (id, context, ...args) => {},
  });

  await tinyBus.on("multiple::sub::args", {
    onCallback: (id, context, ...args) => {},
  });

  await tinyBus.emit("multiple::sub::args", "test");
  await tinyBus.emit("multiple::sub::args", "test");

  await tinyBus.removeAll("multiple::sub::args");

  try {
    await tinyBus.emit("multiple::sub::args", "test");
  } catch (error: any) {
    expect(error.message).toBe("No subscribers for event multiple::sub::args");
  }
});

/**
 * Single run-through mode allows subscribers to be called only once for the
 * same event. This is useful for things like sending emails or text messages.
 */

it('Mode "single" with unique events works as expected', async () => {
  const tinyBus = new TinyBus({
    uniqueEvents: true,
    subscriberMode: "single",
    context: { test: "test" },
    onIdentifier: async () => "test",
  });

  await tinyBus.on("single::sub::args", {
    onCallback: (subscriberId, context, ...args) => {
      expect(subscriberId).toBe("test");
      expect(context).toEqual({ test: "test" });
      expect(args).toEqual(["test"]);
    },
  });

  await tinyBus.emit("single::sub::args", "test");

  try {
    await tinyBus.emit("single::sub::args", "test");
  } catch (error: any) {
    expect(error.message).toBe(
      'Event single::sub::args with args ["test"] was already emitted.',
    );
  }
});

it('Mode "single" without unique events works as expected', async () => {
  const tinyBus = new TinyBus({
    uniqueEvents: false,
    subscriberMode: "single",
    context: { test: "test" },
    onIdentifier: async () => "test",
  });

  await tinyBus.on("single::sub::args", {
    onCallback: (subscriberId, context, ...args) => {
      expect(subscriberId).toBe("test");
      expect(context).toEqual({ test: "test" });
      expect(args).toEqual(["test"]);
    },
  });

  await tinyBus.emit("single::sub::args", "test");

  try {
    await tinyBus.emit("single::sub::args", "test");
  } catch (error: any) {
    expect(error.message).toBe("No subscribers for event single::sub::args");
  }
});

/**
 * Event replays allow subscribers to be called for events that were emitted
 * before the subscriber was added.
 */
it("Replayed events work as expected and are not persisted", async () => {
  const store = new Map<string, TinyBusEvent>();

  const tinyBus = new TinyBus({
    subscriberMode: "multiple",
    onPersist: async event => {
      const id = nanoid();
      store.set(id, { id, ...event });
      return id;
    },
    onRestore: async id => {
      return store.get(id)!;
    },
  });

  await tinyBus.on("test", { onCallback: () => {} });
  await tinyBus.on("test", { onCallback: () => {} });

  const eventId = await tinyBus.emit("test", "test");
  expect(store.size).toBe(1);
  await tinyBus.replay(eventId!);
  expect(store.size).toBe(1);
  expect(store.get(eventId!)?.name).toBe("test");
});

it("Custom event replay strategies work as expected", async () => {
  const store = new Map<string, TinyBusEvent>();

  const tinyBus = new TinyBus({
    uniqueEvents: true,
    context: { test: "test" },
    subscriberMode: "multiple",
    onPersist: async event => {
      const id = nanoid();
      expect(event.name).toBe("custom::sub::args");
      store.set(id, { id, ...event });
      return id;
    },
    onRestore: async eventId => {
      return store.get(eventId)!;
    },
  });

  await tinyBus.on("custom::sub::args", { onCallback: () => {} });
  const eventId = await tinyBus.emit("custom::sub::args", "test");

  await tinyBus.replay(eventId!);
});
