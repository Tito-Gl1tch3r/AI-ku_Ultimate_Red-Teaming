import { hash } from "ohash";
import { resolve } from "path";
import { findUp } from "find-up";
import { createStorage } from "unstorage";
import { asyncExitHook } from "exit-hook";
import fsDriver from "unstorage/drivers/fs";
import type { AnyFunction } from "m-type-tools";

interface Cache {
  [hash: string]: any;
}

interface Options {
  /**
   * @default `${nearestNodeModules}/.cache/thermal-fn`
   */
  base?: string;
  /**
   * @default default
   */
  key?: string;
}

let nearestNodeModules: string;

export async function useThermal(options: Options = {}) {
  if (!nearestNodeModules) {
    nearestNodeModules = (await findUp("node_modules")) ?? "./node_modules";
  }
  const {
    base = resolve(nearestNodeModules, `.cache/thermal-fn`),
    key = "default",
  } = options;

  const storage = createStorage({
    driver: fsDriver({ base }),
  });

  let cache = ((await storage.getItem(key)) as any) || ({} as Cache);
  // Write only on exit
  asyncExitHook(
    async () => {
      await storage.setItem(key, cache);
    },
    {
      minimumWait: 500,
    }
  );

  async function invoke<T extends AnyFunction>(fn: T, ...rest: any[]): Promise<ReturnType<T>> {
    const fnKey = hash([fn, ...rest]);
    let oldResult = cache[fnKey];
    if (oldResult) {
      return oldResult;
    }
    const result = await fn(...rest);
    cache[fnKey] = result;
    return result;
  }

  async function refresh(key?: string) {
    if (key) {
      cache[key] = undefined;
      return
    }
    cache = {}
  }
  return {
    invoke,
    refresh,
  };
}