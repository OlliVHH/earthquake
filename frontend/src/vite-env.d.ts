// Human: Vite client env typings — documents VITE_API_BASE for import.meta.env.
// Agent: READS VITE_API_BASE at build time; no runtime code in this file.
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
