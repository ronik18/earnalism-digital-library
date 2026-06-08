#!/bin/bash
# Monitor English audio generation progress

OUTPUT_DIR="${1:-.}/audio_output"
TOTAL_BOOKS=100

echo "=========================================="
echo "Earnalism English Audio Generation Monitor"
echo "=========================================="
echo ""

# Count generated files
mp3_count=$(find "$OUTPUT_DIR/en" -name "*.mp3" 2>/dev/null | wc -l)
json_count=$(find "$OUTPUT_DIR/en" -name "*_timestamps.json" 2>/dev/null | wc -l)

# Calculate percentages
mp3_percent=$((mp3_count * 100 / TOTAL_BOOKS))
json_percent=$((json_count * 100 / TOTAL_BOOKS))

echo "Audio Files Generated: $mp3_count / $TOTAL_BOOKS ($mp3_percent%)"
echo "Timestamp Files Generated: $json_count / $TOTAL_BOOKS ($json_percent%)"
echo ""

# Check total size
if [ -d "$OUTPUT_DIR/en" ]; then
  total_size=$(du -sh "$OUTPUT_DIR/en" 2>/dev/null | cut -f1)
  echo "Total Size: $total_size"
fi
echo ""

# Show latest log entries
if [ -f "english_audio_sync.log" ]; then
  echo "Latest Log Entries:"
  tail -5 english_audio_sync.log
fi
echo ""

# Show generation status
if [ -f "$OUTPUT_DIR/english_audio_sync_report.json" ]; then
  ready_count=$(grep -o '"sync_ready": true' "$OUTPUT_DIR/english_audio_sync_report.json" | wc -l)
  echo "Books Ready for Sync: $ready_count / $TOTAL_BOOKS"
fi

echo ""
echo "Run this command to watch progress:"
echo "  tail -f english_audio_sync.log"
