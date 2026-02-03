declare module "toml" {
  function parse(input: string): Record<string, unknown>;
  export = { parse };
}
