from .utils import _b2i, _b2s
from .utils import _read_table_or_header_data, _read_atoms_from_mp4
from typing import List, Union


NOT_IMPLEMENTED_PARSERS = set( ('dref',))

_MAX_LIST_PRINT = 10
def _trunc_print(v) -> str:
  if type(v) == bytes:
    return str(v)
  if type(v) == str:
    return str(v)
  if type(v) == list:
    if len(v) > _MAX_LIST_PRINT:
      list_string = "[%i,...,%i]"%(v[0], v[-1])
    else:
      list_string = '[' + ",".join(map(str, v)) +']'

    return '(List with %i elements: %s)'%(len(v), list_string)
  
  return str(v)

class MP4Data:
  def __init__(self, data, offs):
    self._parsed = _read_table_or_header_data(data, offs)

  def get_parsed_data(self):
    return self._parsed

  def __repr__(self):
    s = ''
    s += "Leaf Atom (%s) %i bytes\n"%(self._parsed['atomtype'],self._parsed['atomsize'])
    for k, v in self._parsed.items():
      if k in ['atomtype','atomsize']:
        continue
      s += "  %s : %s \n"%(k,_trunc_print(v))
    return s

class NoData(MP4Data):
  def __init__(self, *args, **kwargs):
    super(NoData, self).__init__(*args, **kwargs)

  def __repr__(self):
    s  = '----> WARNING: The data parser for \'%s\' has not been implemented yet!\n       Parsed results may be WRONG!\n\n'%self._parsed['atomtype']
    s += super().__repr__()
    return s

# _table_or_header_class_map = {
#   'stts' : MP4Data,
#   'stsd' : MP4Data,
#   'stsc' : MP4Data,
#   'stsz' : MP4Data,
#   'tkhd' : MP4Data,
#   'mvhd' : MP4Data,
#   'stco' : MP4Data
# }
_table_and_header_classes = set(['stts','stsd','stsc','stsz','tkhd','mvhd','stco'])
def _header_or_data_object_factory(atomtype):
    if atomtype in _table_and_header_classes:
        return MP4Data
    else:
        return NoData


def _is_header_type(t):
  return t[-2:] == 'hd'

OTHER_LEAF_TYPES = set(['prfl','crgn', 'tkhd','crgn','kmat','elst' ,'stts','stss','stsd','stsz','stco','stsc'])
def _is_leaf_type(t):
  if _is_header_type(t):
    return True
  if t in OTHER_LEAF_TYPES:
    return True
  return False
  
class MP4Atom:
    def __init__(
            self, 
            data : bytes,
            offs : int = None,
            shift : int = None,
            atom_type : str = None,
            is_root = False,
            check_offsets_avail = False
        ):
        """
        dat:
          A bit stream corresponding to an MP4 file

        offs: 
          Offset from where to start reading for this atom

        shift (optional):
          how large is the atom in bytes (dat[offs:offs+shift])

        atom_type:
          the type of atom (redundant - maybe remove)
        
        is_root:
           if this is a root node

        check_offsets_avail:
           whether to check if the offsets are available in the 
           loaded bytes. The intended use mainly works on the header,
           so the `mdat` may not be loaded (context where this is 
           useful is for instance streaming mp4 where we get the header
           in the first few chunks). If this is true, when trying to 
           parse the `moov` field it will throw an error if not all of 
           it is available.

        """
        self.data = data
        self._check_offsets_avail = check_offsets_avail 
        if offs is None:
          offs = 0
        self.offs = offs

        if atom_type is None:
          atom_type = _b2s(self.data[self.offs+4:self.offs+8])
          if is_root:
            atom_type = '(root)'

        self.atom_type = atom_type
        self.is_root = is_root
          
        if shift is None:
          if not self.is_root:
            shift = _b2i(self.data[self.offs:self.offs+4])
          else:
            shift = len(data)
          
        self.shift = shift
        self.children = None
        self.header = None
        self.is_leaf = _is_leaf_type(self.atom_type)
        self.get_children()
    
    @staticmethod
    def init_from_chunk(bytes_or_path_string : Union[bytes,str], head_chunk_max_size = 50000, check_offsets_avail= False):
      """ Factory method - create a parser either for a file or a set of bytes in memory

      Note that "chunk" in the name of this function is not related to the technical 
      term used in the documentation of Mpeg-4 and quicktime.

      Params:
        bytes_or_path_string:
          Either a bytes object or a string pointing to a file.
          If this is a string, then the file is oppened in binary read mode
          and a set of bytes are read into memory for further processing.

        head_chunk_max_size:
          Because MP4 files may be large, read a limmited ammount from the header 
          (assuming that the interesting parts are in the start of the file which is 
          usually the case for streamed data).
      """
      if type(bytes_or_path_string) == str:
        with open(bytes_or_path_string,'rb') as f:
          data = f.read(head_chunk_max_size)
      else:
        data = bytes_or_path_string
        
      atom = MP4Atom(data, 
                    is_root = True,
                    check_offsets_avail = check_offsets_avail)
      return atom

    def _raw_data(self):
        self.data[self.offs:self.offs+self.shift]

    def get_children(self) -> List[tuple]:
      if not self.is_leaf:
        if self.children is None:
          self.children = _read_atoms_from_mp4(self.data, 
                                              offs_start = self.offs,
                                              end_shift=self.shift-8,
                                              check_offsets_avail = self._check_offsets_avail
                                            )
      else:
        self.children = []
      return self.children
    
    def __getitem__(self, key : str) -> Union['MP4Atom', List['MP4Atom']]: 
      _at = []
      for _atom_type, _o, _s in self.children:
        if _atom_type == key:
          if _is_leaf_type(_atom_type):
            _m = _header_or_data_object_factory(_atom_type)(self.data, offs = _o)
          else:
            if _atom_type not in NOT_IMPLEMENTED_PARSERS:
              _m = MP4Atom(self.data,
                          offs = _o+8,
                          shift = _s,
                          atom_type = _atom_type,
                          check_offsets_avail = self._check_offsets_avail)
            else:
              _m = NoData(self.data, offs = _o)
          _at.append(_m)
      if len(_at) == 1:
        _at = _at[0]
      return _at

    def __repr__(self) -> str:
      # s = 'type: %s \n  Children: \n    '%self.atom_type + str(self.children)
      s = '(Atom of type \'%s\' with %i children\n'%(str(self.atom_type), len(self.children))
      for c, o, l in self.children:
        s += '  %s : (offs: %i, size: %i)\n'%(c, o, l)
      return s[:-1] + ')'

