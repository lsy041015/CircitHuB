Datasheet Table Detection Benchmark

Purpose:
- Store manufacturer PDF samples and expected table/pin-map bounding boxes.
- Measure OpenCV/PyMuPDF detection precision, recall, and IoU.

Suggested annotation format:

```json
{
  "pdf": "samples/lm358.pdf",
  "pages": [
    {
      "page": 3,
      "regions": [
        {"kind": "electrical_characteristics", "box": [50, 80, 420, 180]}
      ]
    }
  ]
}
```

Evaluation helper:
- `digikey_scraper.datasheet_benchmark.evaluate_detections`
