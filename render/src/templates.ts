import type { Template } from "./types";

declare global {
  namespace NodeJS {
    interface Require {
      context(dir: string, deep: boolean, filter: RegExp): { keys(): string[]; (id: string): { template: Template<any> } };
    }
  }
}

// Every format's template: formats/<id>/template/index.ts exporting `template`, found when the bundle is built.
const found = require.context("@formats", true, /^\.\/[^/]+\/template\/index\.tsx?$/);

export const templates = found.keys().map((key) => found(key).template);
