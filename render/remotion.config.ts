// The templates live with their formats (formats/<id>/template/), outside this package. CF_FORMATS points at the
// formats folder when the engine renders from a copy of render/; their imports resolve from this package's packages.
import path from "node:path";
import { Config } from "@remotion/cli/config";

const formats = process.env.CF_FORMATS ?? path.resolve(process.cwd(), "../formats");

Config.overrideWebpackConfig((config) => ({
  ...config,
  resolve: {
    ...config.resolve,
    alias: { ...(config.resolve?.alias ?? {}), "@formats": formats },
    modules: [path.resolve(process.cwd(), "node_modules"), "node_modules"],
  },
}));
