# yapyMP4
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mylonasc/yapyMP4/blob/main/mp4reader_demo.ipynb)

## Why another one?

"**Y**et **A**nother **Pa**rser in **Py**thon for **Mp4**"

This was implemented as a "learning exercise" and a thin (metadata reading) interface for the MP4 container format. It is not as complete as other standard tools (such as ffmpeg) but this code aspires to provide some functionality that is only available through c/c++ interfaces for manipulating and getting meta-data about parts of mp4 files.

The initial motivation is/was to be able to request and partially download `mp4` files from streaming endpoints (such as youtube) while only downloading the first few bytes of metadata (in order to learn the chunk/sample offsets). 

##  Usage:
(see also the notebook)

```python
from src.ypapymp4 import MP4Atom

# This will throw an error if the class does not find all the expected root nodes if check_offsets_avail is set to true 
root = MP4Atom.init_from_chunk('test.mp4', head_chunk_max_size = 200000,check_offsets_avail = False)
```
