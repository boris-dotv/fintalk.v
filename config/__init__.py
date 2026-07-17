import os
import sys

os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.path.join('/raidnvme/czc', 'SENTENCE_TRANSFORMERS_HOME')

# for huggingface
if os.path.dirname(os.path.abspath(__file__)).startswith('/home'):
    os.environ['HF_HOME'] = '/raidnvme/czc/HF_HOME'

# for modelscope
os.environ['CACHE_HOME'] = '/raidnvme/czc/MODELSCOPE_CACHE_HOME'
