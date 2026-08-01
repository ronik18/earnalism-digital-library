## Wave-1 execute snippet

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library

# Deterministic launcher (recommended):
bash internal/earnalism_intelligence/run_sprint1_wave1_migrate.sh postcheck

# Or, guard-mode with scoped execution:
bash internal/earnalism_intelligence/run_sprint1_wave1_migrate.sh guard
```

Optional explicit slugs in postcheck mode:

```bash
bash internal/earnalism_intelligence/run_sprint1_wave1_migrate.sh postcheck radharani muchiram-gurer-jibanchorit book-d19e96859f book-f5d593e1f4 book-edfcf810c5 the-tell-tale-heart the-yellow-wallpaper the-necklace
```
