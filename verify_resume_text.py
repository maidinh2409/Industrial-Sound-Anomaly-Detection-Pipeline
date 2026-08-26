from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
import re, sys

def blocks(doc):
    for item in doc.iter_inner_content():
        if isinstance(item, Paragraph):
            if item.text.strip(): yield item.text
        elif isinstance(item, Table):
            for row in item.rows:
                for cell in row.cells:
                    if cell.text.strip(): yield cell.text

def tokens(path):
    text=' '.join(blocks(Document(path)))
    return re.findall(r"\S+",text)

a=tokens(sys.argv[1]); b=tokens(sys.argv[2])
print('source_tokens',len(a),'output_tokens',len(b),'identical',a==b)
if a!=b:
    for i,(x,y) in enumerate(zip(a,b)):
        if x!=y:
            print('first_difference',i,repr(x),repr(y)); break
    else: print('length_difference_only')
    raise SystemExit(1)
