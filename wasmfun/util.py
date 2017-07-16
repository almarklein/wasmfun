"""
Utils for working with WASM and binary data.
"""

import os


__all__ = ['inspect_bytes_at', 'hexdump', 'produce_example_html']


def inspect_bytes_at(bb, offset):
    """ Inspect bytes at the specified offset.
    """
    start = max(0, offset - 16)
    end = offset + 16
    bytes2show = bb[start:end]
    bytes2skip = bb[start:offset]
    text_offset = len(repr(bytes2skip))
    print(bytes2show)
    print('|'.rjust(text_offset))


def hexdump(bb):
    """ Do a hexdump of the given bytes.
    """
    i = 0
    line = 0
    while i < len(bb):
        ints = [hex(j)[2:].rjust(2, '0') for j in bb[i:i+16]]
        print(str(line).rjust(8, '0'), *ints, sep=' ')
        i += 16
        line += 1


CODE_PLACEHOLDER = 'CODE_PLACEHOLDER'
WASM_PLACEHOLDER = 'WASM_PLACEHOLDER'


def produce_example_html(filename, code, wasm):
    """ Generate an html file for the given code and wasm.
    """
    wasm_text = str(list(wasm))  # [0, 1, 12, ...]
    
    fname = os.path.basename(filename).rsplit('.', 1)[0]
    src_filename = os.path.join(os.path.dirname(__file__), 'template.html')
    with open(src_filename, 'rb') as f:
        html = f.read().decode()
    
    html = html.replace('<title></title>', '<title>%s</title>' % fname)
    html = html.replace(CODE_PLACEHOLDER, code)
    html = html.replace(WASM_PLACEHOLDER, 'wasm_data = new Uint8Array(' + wasm_text + ');')
    
    with open(filename, 'wb') as f:
        f.write(html.encode())
    print('Wrote example HTML to', filename)
