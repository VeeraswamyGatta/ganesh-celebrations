# Ganesh Chaturthi 2026 – Sponsorship App 🎉

This is a Streamlit app to showcase sponsorship categories for the Ganesh Chaturthi celebration and collect interest from the community

## Split a composite image

Install the image dependency and split a 4-by-2 composite into seven JPEG files:

```bash
pip install -r requirements.txt
python split_image_blocks.py composite.jpg --output-dir split_blocks
```

The script processes blocks row by row, trims each block's outer whitespace, and writes `block_01.jpg` through `block_07.jpg`. Use `--columns`, `--rows`, and `--count` for a different layout, or `--no-trim` to preserve the full grid cells.
