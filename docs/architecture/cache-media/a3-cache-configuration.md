# A3 cache configuration

| Variable | Default | Range | Unit | Malformed/unsafe value | Railway change |
| --- | ---: | --- | --- | --- | --- |
| `REDIS_CACHE_MAX_UNCOMPRESSED_BYTES` | 262144 | 1..1048576 | bytes | Safe default retained | no |
| `REDIS_CACHE_MAX_STORED_BYTES` | 270336 | 1..1048576 | bytes | Safe default retained | no |

Both settings are non-secret and optional. Missing, malformed, zero, negative, or over-ceiling values cannot make the cache unlimited; the safe built-in default is used. A3 requires no Railway configuration mutation.
