# A2 local codec characterization

PASS. Local synthetic fixtures used 20 warmups and 100 measurements per codec operation. v2 encoded values were smaller for all six fixtures (legacy/v2 bytes: public 126/114, reader-content 82/80, manifest 73/64, private 80/72, user document 93/83, session 70/61). v2 encode/decode was slower in this microbenchmark. This is not a production latency, capacity, or Redis-memory claim.
