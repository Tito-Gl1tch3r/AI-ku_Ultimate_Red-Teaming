import type { PriorityQueueInterface } from "types/priority-queue";

/**
 * ### Class - PriorityQueue
 *
 * A priority queue is an abstract data type similar to a regular queue or stack data structure
 * in which each element additionally has a "priority" associated with it. In a priority queue,
 * an element with high priority is served before an element with low priority. If two elements
 * have the same priority, they are served according to their order in the queue.
 */
export default class PriorityQueue<T> implements PriorityQueueInterface<T> {
  private queue: T[];
  private comparator?: (item1: T, item2: T) => boolean;

  constructor(comparator?: (item1: T, item2: T) => boolean) {
    this.queue = [];
    this.comparator = comparator;
  }

  /**
   * Returns an iterator over the elements in this collection.
   */
  public iterator() {
    return this.queue[Symbol.iterator]();
  }

  /**
   * Inserts the specified element into this priority queue.
   */
  public push(value: T) {
    this.queue.push(value);
    let pos = this.queue.length - 1;

    while (
      pos !== 0 &&
      this._compare(this.queue[this._parentOf(pos)], this.queue[pos])
    ) {
      this._swap(pos, this._parentOf(pos));
      pos = this._parentOf(pos);
    }
  }

  /**
   * Retrieves, but does not remove, the head of this queue, or returns
   * null if this queue is empty.
   */
  public top() {
    return this.queue.length > 0 ? this.queue[0] : null;
  }

  /**
   * Retrieves and removes the head of this queue, or returns null if
   * this queue is empty.
   */
  public pop() {
    if (this.queue.length === 0) {
      return null;
    }

    const item = this.queue[0];
    this.queue[0] = this.queue[this.queue.length - 1];
    this._swap(0, this.queue.length - 1);
    this.queue.pop();
    this._heapify(0);
    return item;
  }

  /**
   * Returns the number of elements in this collection.
   */
  public size() {
    return this.queue.length;
  }

  /**
   * Checks whether the queue is empty.
   */
  public empty() {
    return !this.queue.length;
  }

  /**
   * Returns an array containing all of the elements in this queue.
   */
  public toArray() {
    return [...this.queue];
  }

  /**
   * Removes all of the elements from this priority queue.
   */
  public clear() {
    this.queue = [];
  }

  /**
   * Returns true if this queue contains the specified element.
   */
  public contains(value: T, comparator?: (item: T) => boolean) {
    if (!this.queue.length) return false;

    const func = comparator || ((item: T): boolean => item === value);

    const mid = Math.floor(this.queue.length / 2);
    let childIndex1: number;
    let childIndex2: number;
    let index = 0;

    while (index <= mid - 1) {
      childIndex1 = 2 * index + 1;
      childIndex2 = 2 * index + 2;

      if (
        (this.queue[index] && func(this.queue[index])) ||
        (this.queue[childIndex1] && func(this.queue[childIndex1])) ||
        (this.queue[childIndex2] && func(this.queue[childIndex2]))
      ) {
        return true;
      }

      index++;
    }

    return false;
  }

  /**
   * Compare parent value and children value and swap them if conditions are satisfied
   * @param index
   */
  private _heapify(index: number) {
    const mid = Math.floor(this.queue.length / 2);
    let childIndex1: number;
    let childIndex2: number;
    let swapIndex: number;

    while (index <= mid - 1) {
      childIndex1 = 2 * index + 1;
      childIndex2 = 2 * index + 2;
      swapIndex = childIndex1;

      if (this._compare(this.queue[childIndex1], this.queue[childIndex2])) {
        swapIndex = childIndex2;
      }

      if (this._compare(this.queue[index], this.queue[swapIndex])) {
        this._swap(index, swapIndex);
      }

      index = swapIndex;
    }
  }

  /**
   * Swap 2 elememts
   * @param index1
   * @param index2
   */
  private _swap(index1: number, index2: number) {
    const temp = this.queue[index1];
    this.queue[index1] = this.queue[index2];
    this.queue[index2] = temp;
  }

  /**
   * Compare 2 elements
   * @param item1
   * @param item2
   */
  private _compare(item1: T, item2: T) {
    if (this.comparator) {
      return this.comparator(item1, item2);
    }
    return item1 > item2;
  }

  /**
   * Get parent's index of the current element
   * @param position
   */
  private _parentOf(position: number) {
    return Math.floor((position - 1) / 2);
  }
}
