# 
#   The following util functions implement partially the parsing of
# different mp4 atoms (Boxes). They were not extensively tested
# and their implementation was based on a combination of the following 
# resources: 
# 
#  1. Apple quicktime page (accessed Sept. 2022) here : https://developer.apple.com/library/archive/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html#//apple_ref/doc/uid/TP40000939-CH204-SW1
#  2. Cimarronsystems document (accessed Sept. 2022) here: http://www.cimarronsystems.com/wp-content/uploads/2017/04/Elements-of-the-H.264-VideoAAC-Audio-MP4-Movie-v2_0.pdf
# 
#  
def _b2i(b):
    return int.from_bytes(b, byteorder='big',signed=False)
def _b2s(b):
    return str(b,encoding='utf-8')

def _read_atoms_from_mp4(
        data,
        offs_start = 0,
        end_shift  = None,
        check_offsets_avail = False,
    ):
    """
    reads metadata and data from the first chunk of an MP4 file.
    
    The data are organized in "atoms" which are pre-pended with a 
    name and a size (totalling in most cases 8 bytes - 4 bytes 
    size and 4 bytes name)

    """

    offs_list = []
    ci = offs_start
    n_atoms = 0
    if end_shift is None:
        end_shift = len(data) - offs_start
    
    if check_offsets_avail:
        assert((offs_start + end_shift) <=len(data) )

    while ci < (offs_start + end_shift):
        # if ci > len(data):
            # raise Exception("You tried to access an incorrect memory address while parsing MP4 data.")

        atom_size = data[ci:ci+4]
        atom_name = data[ci+4:ci+8] 

        offs_atom = _b2i(atom_size)
        offs_list.append( tuple((_b2s(atom_name), ci, offs_atom)) )

        ci += offs_atom
        if offs_atom == 0:
            ci += 1
        n_atoms += 1
    return offs_list


def _read_sample_to_chunk_table(dat):
    c = 0
    triplets = []
    while c < len(dat):
        first_chunk = dat[c:c+4]
        samples_per_chunk = dat[c+4:c+8]
        sample_desc_id = dat[c+8:c+12]
        triplets.append((_b2i(first_chunk),_b2i(samples_per_chunk), _b2i(sample_desc_id)))
        c+=12
    return triplets

def _parse_common_header_structure(dat_with_header) -> dict:
    """
    Reads the first 12 bits which have common meaning for several
    atom types and returns a dict for parsing.
    """
    res = {}
    res['atomsize'] = _b2i(dat_with_header[0:4])
    res['atomtype'] = _b2s(dat_with_header[4:8])
    res['version_byte'] = dat_with_header[8]
    res['flags_bytes'] = dat_with_header[8:12]
    return res


def _parse_tkhd(tkhd_dat, _ch_dict):
    _ch_dict['description'] = 'Header of the track Atom'
    _ch_dict['creat_utc_time'] = _b2i(tkhd_dat[12:16])
    _ch_dict['modif_utc_time']      = _b2i(tkhd_dat[16:20])
    _ch_dict['track_id']          = _b2i(tkhd_dat[20:24])
    _ch_dict['reserved']          =      tkhd_dat[24:28]
    _ch_dict['duration']          = _b2i(tkhd_dat[28:32])
    # (for res['duration'] : Duration of track in movie coord system
    #   equals to the sum of durations of all track edits
    #   and if there is no edit list it is the sum of 
    #   sample durations.
    return _ch_dict

def _parse_mvhd(mvhd_dat, _ch_dict):
    _ch_dict['description']      = 'Header of the movie Atom'
    _ch_dict['creat_utc_time']   = _b2i(mvhd_dat[12:16])
    _ch_dict['modif_utc_time']   = _b2i(mvhd_dat[16:20])
    _ch_dict['timescale']        = _b2i(mvhd_dat[20:24])
    _ch_dict['duration']         = _b2i(mvhd_dat[24:28])
    _ch_dict['pref_rate']        = _b2i(mvhd_dat[28:32])
    _ch_dict['pref_volume']      = _b2i(mvhd_dat[32:34])
    _ch_dict['reserved']         =      mvhd_dat[34:44]
    _ch_dict['matrix']           =  [[_b2i(mvhd_dat[44 + (i + j*3)*4:44+(i+1+j*3)*4]) for i in range(0,3)] for j in range(0, 3)] 

    _remaining_fields = ['preview_time',
                       'preview_duration',
                       'poster_time',
                       'selection_time',
                       'selection_duration',
                       'current_time',
                       'next_track_id']
    for i, field_name in enumerate(_remaining_fields):
        _ch_dict[field_name] = _b2i(mvhd_dat[80+i*4:80+(i+1)*4])
    
    return _ch_dict


def _parse_stsz(stsz_dat, _ch_dict):
    _ch_dict['description'] = 'Sample size Atom. Contains a table of sample sizes for the parent track.'
    _ch_dict['sample_size'] = _b2i(stsz_dat[12:16])
    _ch_dict['num_entries'] = _b2i(stsz_dat[16:20])
    sample_size_table  = []; 
    c = 0
    while c < _ch_dict['num_entries']:
        sample_size_table.append(_b2i(stsz_dat[20+c*4:20+(c+1)*4]))
        c += 1

    _ch_dict['sample_size_table'] = sample_size_table
    return _ch_dict


def _read_sample_description_stsd(sample_table):
    """
    According to the quicktime ref "Sample Description Atoms" (part of the stsd desc.)
    the array is parsed as follows.
    
    [4-size][4-fmt][6-reserved][2 bytes -  index]
    """
    # sample_table = tab['stsd']
    num_sample_descr = int.from_bytes(sample_table[0:4],byteorder = 'big',signed = False) # 32 bits sample desc size
    data_fmt = sample_table[4:8] # 32 bits format
    reserved = sample_table[8:14] # all zeros if all good
    data_reference_index = sample_table[14:16] # index to correspond the sample to  a data reference
    res = {
        'num_sample_desc' : num_sample_descr,
         'data_fmt' : data_fmt, 
         'data_reference_index' : _b2i(data_reference_index)
    }
    res['description'] = 'The sample description table. Keeps track of how many compressed frames are stored in each sample.'
    return res

def _read_sample_description_stts(time_to_sample_table):
    res = {
        'sample_duration' :  _b2i(time_to_sample_table[0:4]),
        'sample_count' :  time_to_sample_table[4:8]
    }
    return res

def _read_stco_table(table_dat):
    """
    A table containing the sample offsets. 
    It should be equal in number to the number
     of entries defined in the num_entries field.
    """
    r = []
    c = 0
    while c < len(table_dat):
        t = _b2i(table_dat[0+c:4+c])
        r.append(t)
        c+=4
    return r

special_parsers = {
    'stsz' : _parse_stsz,
    'tkhd' : _parse_tkhd,
    'mvhd' : _parse_mvhd
}

def _read_table_or_header_data(data, offset):
    """
    Tables and headers have special fields that need their own parsers
    """
    res = _parse_common_header_structure(data[offset:offset+12])
    _atomsize  = res['atomsize']
    _atomtype  = res['atomtype']

    if _atomtype in special_parsers: # re-reading some bits here
        table_data = data[offset:offset+_atomsize]
        res = special_parsers[_atomtype](table_data, res)
        return res

    # After "Flags: (12 bytes)"
    res['num_entries']  = _b2i(data[offset+12:offset+16])
    table_dat = data[offset+16:offset+_atomsize]

    if res['atomtype'] == 'stsd':
        res['description'] = 'Sample description Atom'
        res['table_data'] = _read_sample_description_stsd(table_dat)
    if res['atomtype'] == 'stts':
        res['table_data'] = _read_sample_description_stts(table_dat)
    if res['atomtype'] == 'stsc':
        res['table_columns'] = ['first_chunk','sample_per_chunk','sample_description_id']
        res['table_data'] = _read_sample_to_chunk_table(table_dat)
    if res['atomtype'] == 'stco':
        res['description'] = 'Chunk offset data table.'
        res['table_data'] = _read_stco_table(table_dat)
    return res
