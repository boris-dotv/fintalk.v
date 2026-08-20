import os
import sys

os.environ.setdefault('SENTENCE_TRANSFORMERS_HOME', '/raidnvme/czc/SENTENCE_TRANSFORMERS_HOME')  # type: ignore[arg-type]
# Ensure the cache directory exists to avoid runtime errors
os.makedirs(os.environ['SENTENCE_TRANSFORMERS_HOME'], exist_ok=True)

# for huggingface
if os.path.dirname(os.path.abspath(__file__)).startswith('/home'):
    os.environ['HF_HOME'] = '/raidnvme/czc/HF_HOME'

# for modelscope
os.environ['CACHE_HOME'] = '/raidnvme/czc/MODELSCOPE_CACHE_HOME'
