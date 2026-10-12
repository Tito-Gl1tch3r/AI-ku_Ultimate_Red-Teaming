import { expect, it } from "bun:test";

import PriorityQueue from "classes/priority-queue";

it("Creation works as expected", () => {
  const pq = new PriorityQueue<number>();
  expect(pq).toBeInstanceOf(PriorityQueue);
  // push 3 items
  pq.push(22);
  pq.push(33);
  pq.push(11);
  // ordering is 33, 22, 11
  expect(pq.pop()).toEqual(11);
  expect(pq.pop()).toEqual(22);
  expect(pq.pop()).toEqual(33);
});

it("Comparator creation works as expected", () => {
  const pq = new PriorityQueue<number>((a, b) => a > b);
  expect(pq).toBeInstanceOf(PriorityQueue);
  // push 3 items
  pq.push(22);
  pq.push(33);
  pq.push(11);
  // ordering is 11, 22, 33
  expect(pq.pop()).toEqual(11);
  expect(pq.pop()).toEqual(22);
  expect(pq.pop()).toEqual(33);
});

it('Method "iterator” works as expected', () => {
  const pq = new PriorityQueue<number>((a, b) => a < b);
  expect(pq).toBeInstanceOf(PriorityQueue);
  // push 3 items
  pq.push(22);
  pq.push(33);
  pq.push(11);
  // ordering is 33, 22, 11
  const iterator = pq.iterator();
  expect(iterator.next().value).toEqual(33);
  expect(iterator.next().value).toEqual(22);
  expect(iterator.next().value).toEqual(11);
});

it("Method ”top” works as expected", () => {
  const pq = new PriorityQueue<number>((a, b) => a < b);
  expect(pq).toBeInstanceOf(PriorityQueue);
  // push 3 items
  pq.push(22);
  pq.push(33);
  pq.push(11);
  // ordering is 33, 22, 11
  expect(pq.top()).toEqual(33);
  // pop 1 item
  pq.pop();
  // ordering is 22, 11
  expect(pq.top()).toEqual(22);
  // pop 1 item
  pq.pop();
  // ordering is 11
  expect(pq.top()).toEqual(11);
});

it("Method ”contains” works as expected", () => {
  const pq = new PriorityQueue<{ val: number }>((a, b) => a.val < b.val);
  pq.push({ val: 22 });
  pq.push({ val: 33 });
  pq.push({ val: 11 });
  expect(
    pq.contains({ val: 11 }, i => {
      return i.val === 11;
    }),
  ).toEqual(true);
});

it("Method ”clear” works as expected", () => {
  const pq = new PriorityQueue<{ val: number }>();
  pq.push({ val: 22 });
  pq.push({ val: 33 });
  pq.push({ val: 11 });
  expect(pq.empty()).toBe(false);
  expect(pq.size()).toBe(3);
  pq.clear();
  expect(pq.empty()).toBe(true);
});

it("Method toArray works as expected", () => {
  const pq = new PriorityQueue<{ val: number }>();
  const values = [22, 33, 11];
  for (const val of values) pq.push({ val });
  const arr = pq.toArray();
  for (let i = 0; i < arr.length; i++) {
    expect(arr[i].val).toEqual(values[i]);
  }
});
