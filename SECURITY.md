# Security

Content Factory runs on your machine. The engine listens on `127.0.0.1:8790` only and accepts requests that carry
its `X-Factory` header, so a web page cannot drive it. API keys for image providers are stored in the data folder's
`.env` file with owner-only permissions and are never sent anywhere except the provider they belong to.

## Reporting a vulnerability

Please report vulnerabilities privately through
[GitHub security advisories](https://github.com/jutsuhq/content-factory/security/advisories/new), not as a public
issue. Include the steps to reproduce and the version (Settings › About). We aim to answer within a week.
