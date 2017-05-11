"""
Utils for working with WASM and binary data.
"""

__all__ = ['inspect_bytes_at', 'hexdump', 'insert_wasm_into_html']


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


SPLIT_PLACEHOLDER = '\n// WASM_SPLIT_PLACEHOLDER\n'

def insert_wasm_into_html(filename, wasm):
    wasm_text = str(list(wasm))  # [0, 1, 12, ...]
    
    with open(filename, 'rb') as f:
        html = f.read().decode()
    
    htmlparts = html.split(SPLIT_PLACEHOLDER)
    assert len(htmlparts) == 3
    htmlparts[1] = 'wasm_data = new Uint8Array(' + wasm_text + ');'
    html = SPLIT_PLACEHOLDER.join(htmlparts)
    
    with open(filename, 'wb') as f:
        f.write(html.encode())
